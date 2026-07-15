from __future__ import annotations

import io
import importlib.util
import ssl
from pathlib import Path
from urllib.error import URLError

import pytest
from PIL import Image

from lego_element_lookup.icon_generation import brick_bounds, draw_icon, stud_centres, tile_bounds
from lego_element_lookup import preview
from lego_element_lookup.gui import app
from lego_element_lookup.preview import PreviewCache, PreviewError


class Headers:
    def __init__(self, content_type="image/jpeg"):
        self.content_type = content_type

    def get_content_type(self):
        return self.content_type


class Response:
    def __init__(self, payload, final_url="https://cdn.rebrickable.com/media/parts/elements/6212040.jpg", content_type="image/jpeg"):
        self.payload = payload
        self.final_url = final_url
        self.headers = Headers(content_type)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self, size):
        return self.payload[:size]

    def geturl(self):
        return self.final_url


def jpeg_bytes() -> bytes:
    output = io.BytesIO()
    Image.new("RGB", (800, 600), "white").save(output, format="JPEG")
    return output.getvalue()


def test_preview_download_is_validated_resized_and_cached(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(preview, "urlopen", lambda request, timeout, context: calls.append(context) or Response(jpeg_bytes()))
    cache = PreviewCache(tmp_path)
    url = "https://cdn.rebrickable.com/media/parts/elements/6212040.jpg"
    destination = cache.fetch(url)
    assert destination == cache.cached(url)
    with Image.open(destination) as image:
        assert image.format == "PNG"
        assert image.width <= 360 and image.height <= 260
    assert calls and calls[0].verify_mode == ssl.CERT_REQUIRED
    assert calls[0].check_hostname is True


def test_preview_rejects_untrusted_hosts_without_network(monkeypatch, tmp_path):
    monkeypatch.setattr(preview, "urlopen", lambda *args, **kwargs: pytest.fail("network should not be used"))
    with pytest.raises(PreviewError, match="No preview"):
        PreviewCache(tmp_path).fetch("https://example.invalid/part.jpg")


def test_preview_rejects_redirect_to_untrusted_host(monkeypatch, tmp_path):
    monkeypatch.setattr(
        preview,
        "urlopen",
        lambda request, timeout, context: Response(jpeg_bytes(), "https://example.invalid/redirect.jpg"),
    )
    with pytest.raises(PreviewError, match="No preview"):
        PreviewCache(tmp_path).fetch("https://cdn.rebrickable.com/media/parts/elements/6212040.jpg")


def test_missing_preview_has_clean_fallback(tmp_path):
    cache = PreviewCache(tmp_path)
    assert cache.cached(None) is None
    with pytest.raises(PreviewError, match="No preview available"):
        cache.fetch(None)


def test_preview_rejects_invalid_content_type(monkeypatch, tmp_path):
    monkeypatch.setattr(
        preview,
        "urlopen",
        lambda request, timeout, context: Response(b"not an image", content_type="text/html"),
    )
    with pytest.raises(PreviewError, match="Preview data is invalid") as raised:
        PreviewCache(tmp_path).fetch("https://cdn.rebrickable.com/media/parts/elements/6212040.jpg")
    assert raised.value.state == "invalid"


def test_verified_context_uses_certifi_without_bypassing_verification(monkeypatch):
    calls = []
    real_create_default_context = ssl.create_default_context

    def create_default_context(*, cafile):
        calls.append(cafile)
        return real_create_default_context(cafile=cafile)

    monkeypatch.setattr(preview.ssl, "create_default_context", create_default_context)
    context = preview.verified_ssl_context()
    assert calls == [preview.certifi.where()]
    assert context.verify_mode == ssl.CERT_REQUIRED
    assert context.check_hostname is True
    assert context.get_ca_certs()


def test_preview_preserves_ssl_failure_as_internal_cause(monkeypatch, tmp_path):
    ssl_error = ssl.SSLCertVerificationError(1, "certificate verify failed")
    url_error = URLError(ssl_error)

    def fail(request, timeout, context):
        raise url_error

    monkeypatch.setattr(preview, "urlopen", fail)
    with pytest.raises(PreviewError, match="^Preview could not be downloaded$") as raised:
        PreviewCache(tmp_path).fetch("https://cdn.rebrickable.com/media/parts/elements/6212040.jpg")
    assert raised.value.state == "download_failed"
    assert raised.value.__cause__ is url_error


def test_cached_preview_remains_available_offline(monkeypatch, tmp_path):
    url = "https://cdn.rebrickable.com/media/parts/elements/6212040.jpg"
    cache = PreviewCache(tmp_path)
    monkeypatch.setattr(preview, "urlopen", lambda request, timeout, context: Response(jpeg_bytes()))
    cached = cache.fetch(url)
    monkeypatch.setattr(preview, "urlopen", lambda *args, **kwargs: pytest.fail("cached fetch must remain offline"))
    assert cache.fetch(url) == cached


def test_pyinstaller_spec_collects_certifi_certificate_data():
    spec = (Path(__file__).parents[1] / "packaging" / "pyinstaller" / "lego-element-lookup.spec").read_text(encoding="utf-8")
    assert 'collect_data_files("certifi")' in spec


def test_desktop_preview_fetch_smoke_uses_preview_cache_without_opening_tk(monkeypatch, tmp_path, capsys):
    expected = tmp_path / "previews" / "cached.png"
    monkeypatch.setattr(app.PreviewCache, "fetch", lambda self, url: expected)
    assert app.main(["--preview-fetch-smoke", "https://cdn.rebrickable.com/example.jpg", str(tmp_path)]) == 0
    assert capsys.readouterr().out == "Preview cached: cached.png\n"


@pytest.mark.parametrize("size", [16, 32, 64, 128, 256, 512, 1024])
def test_icon_studs_are_centred(size):
    centres = stud_centres(size)
    assert sum(x for x, _ in centres) / len(centres) == size / 2
    assert sum(y for _, y in centres) / len(centres) == size / 2
    assert draw_icon(size).size == (size, size)


@pytest.mark.parametrize("size", [16, 32, 64, 128, 256, 512, 1024])
def test_icon_geometry_is_symmetric_with_consistent_outer_margins(size):
    tile = tile_bounds(size)
    brick = brick_bounds(size)
    assert tile[0] == tile[1]
    assert size - 1 - tile[2] == tile[0]
    assert size - 1 - tile[3] == tile[1]
    assert brick[0] == size - 1 - brick[2]
    assert brick[1] == size - 1 - brick[3]
    centres = stud_centres(size)
    xs = sorted({x for x, _ in centres}); ys = sorted({y for _, y in centres})
    assert xs[0] + xs[1] == 2 * (size // 2)
    assert ys[0] + ys[1] == 2 * (size // 2)
    assert draw_icon(size).getpixel((0, 0))[3] == 0


def test_generated_icon_formats_are_valid(tmp_path):
    script = Path(__file__).parents[1] / "assets" / "generate_icons.py"
    spec = importlib.util.spec_from_file_location("project_icon_generator", script)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.generate_assets(tmp_path)
    expected = {"icon.png": "PNG", "icon.icns": "ICNS", "icon.ico": "ICO"}
    for name, image_format in expected.items():
        with Image.open(tmp_path / name) as image:
            assert image.format == image_format
            assert image.width > 0 and image.height > 0
