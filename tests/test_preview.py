from __future__ import annotations

import io

import pytest
from PIL import Image

from lego_element_lookup.icon_generation import draw_icon, stud_centres
from lego_element_lookup import preview
from lego_element_lookup.preview import PreviewCache, PreviewError


class Headers:
    def get_content_type(self):
        return "image/jpeg"


class Response:
    headers = Headers()

    def __init__(self, payload, final_url="https://cdn.rebrickable.com/media/parts/elements/6212040.jpg"):
        self.payload = payload
        self.final_url = final_url

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
    monkeypatch.setattr(preview, "urlopen", lambda request, timeout: Response(jpeg_bytes()))
    cache = PreviewCache(tmp_path)
    url = "https://cdn.rebrickable.com/media/parts/elements/6212040.jpg"
    destination = cache.fetch(url)
    assert destination == cache.cached(url)
    with Image.open(destination) as image:
        assert image.format == "PNG"
        assert image.width <= 360 and image.height <= 260


def test_preview_rejects_untrusted_hosts_without_network(monkeypatch, tmp_path):
    monkeypatch.setattr(preview, "urlopen", lambda *args, **kwargs: pytest.fail("network should not be used"))
    with pytest.raises(PreviewError, match="No preview"):
        PreviewCache(tmp_path).fetch("https://example.invalid/part.jpg")


def test_preview_rejects_redirect_to_untrusted_host(monkeypatch, tmp_path):
    monkeypatch.setattr(
        preview,
        "urlopen",
        lambda request, timeout: Response(jpeg_bytes(), "https://example.invalid/redirect.jpg"),
    )
    with pytest.raises(PreviewError, match="No preview"):
        PreviewCache(tmp_path).fetch("https://cdn.rebrickable.com/media/parts/elements/6212040.jpg")


def test_missing_preview_has_clean_fallback(tmp_path):
    cache = PreviewCache(tmp_path)
    assert cache.cached(None) is None
    with pytest.raises(PreviewError, match="No preview available"):
        cache.fetch(None)


@pytest.mark.parametrize("size", [16, 32, 64, 128, 256, 512])
def test_icon_studs_are_centred(size):
    centres = stud_centres(size)
    assert sum(x for x, _ in centres) / len(centres) == size / 2
    assert sum(y for _, y in centres) / len(centres) == size / 2
    assert draw_icon(size).size == (size, size)
