from __future__ import annotations

import gzip
import io
from datetime import datetime, timedelta, timezone

import pytest
from PIL import Image

from lego_element_lookup import services, set_metadata
from lego_element_lookup.downloader import DownloadCancelled
from lego_element_lookup.relationship_cache import RelationshipCache, RelationshipCacheState
from lego_element_lookup.relationships import RelationshipDownloadError
from lego_element_lookup.secrets import SecretStore
from lego_element_lookup.services import ApplicationService, RELATED_DESIGN_LABELS
from lego_element_lookup.set_metadata import SetMetadata, SetMetadataError


class FakeKeyring:
    def get_password(self, service, username):
        return None

    def set_password(self, service, username, password):
        pass

    def delete_password(self, service, username):
        pass


def relationship_payload(rows):
    return gzip.compress(("rel_type,child_part_num,parent_part_num\n" + "\n".join(rows) + "\n").encode())


def service_at(tmp_path):
    return ApplicationService(settings_path=tmp_path / "config.json", secret_store=SecretStore(FakeKeyring()))


def test_relationship_service_reports_optional_states_and_direct_groups(monkeypatch, tmp_path, entries):
    service = service_at(tmp_path)
    service.settings = service.settings.__class__(None, "76344-1", tmp_path / "cache", True)
    assert service.relationship_cache_state().state is RelationshipCacheState.NOT_DOWNLOADED
    monkeypatch.setattr(
        services,
        "download_relationship_data",
        lambda: relationship_payload(["A,67696,57910", "M,62712,57910", "M,92013,57910"]),
    )
    service.refresh_relationship_data()
    match = service.lookup_cached("6212040", "76344-1", tmp_path / "missing") if False else None
    from lego_element_lookup.lookup import Match

    designs = service.related_designs(Match("67696", "0", "name", "colour"))
    assert designs is not None
    assert [item.part_num for item in designs.alternates] == ["57910"]
    assert not designs.moulds
    assert RELATED_DESIGN_LABELS[next(iter(designs.groups))] == "Alternate designs"
    cache = RelationshipCache(tmp_path / "cache")
    assert cache.load(now=datetime.now(timezone.utc) + timedelta(days=31)).state is RelationshipCacheState.STALE


def test_relationship_refresh_cancellation_and_failure_preserve_old_cache(monkeypatch, tmp_path):
    service = service_at(tmp_path)
    service.settings = service.settings.__class__(None, "76344-1", tmp_path / "cache", True)
    cache = RelationshipCache(tmp_path / "cache")
    cache.replace_from_gzip(relationship_payload(["A,old,parent"]))
    with pytest.raises(DownloadCancelled):
        service.refresh_relationship_data(cancelled=lambda: True)
    monkeypatch.setattr(services, "download_relationship_data", lambda: (_ for _ in ()).throw(RelationshipDownloadError("offline")))
    with pytest.raises(RelationshipDownloadError):
        service.refresh_relationship_data()
    assert [item.part_num for item in cache.load().index.related_designs("parent").alternates] == ["old"]


def test_relationship_refresh_does_not_send_api_key(monkeypatch, tmp_path):
    service = service_at(tmp_path)
    service.settings = service.settings.__class__("secret", "76344-1", tmp_path / "cache", True)
    calls = []

    def download():
        calls.append("called")
        return relationship_payload(["A,child,parent"])

    monkeypatch.setattr(services, "download_relationship_data", download)
    service.refresh_relationship_data()
    assert calls == ["called"]


def jpeg_bytes(size=(20, 20)):
    stream = io.BytesIO()
    Image.new("RGB", size, "red").save(stream, format="JPEG")
    return stream.getvalue()


class Response:
    def __init__(self, payload, url="https://cdn.rebrickable.com/media/sets/76344-1.jpg", content_type="image/jpeg"):
        self.payload = payload
        self._url = url
        self.headers = type("Headers", (), {"get_content_type": lambda self: content_type})()

    def read(self, _limit):
        return self.payload

    def geturl(self):
        return self._url

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def test_set_metadata_and_preview_are_cached_atomically(monkeypatch, tmp_path):
    payload = {
        "set_num": "76344-1",
        "name": "Hogwarts Iconic Set",
        "set_img_url": "https://cdn.rebrickable.com/media/sets/76344-1.jpg",
        "year": 2021,
        "num_parts": 3010,
    }
    monkeypatch.setattr(set_metadata, "_request_json", lambda url, key: payload)
    metadata = set_metadata.fetch_set_metadata("76344-1", "private-key")
    set_metadata.save_set_metadata(tmp_path, metadata)
    assert set_metadata.load_set_metadata(tmp_path, "76344-1") == metadata
    monkeypatch.setattr(set_metadata, "urlopen", lambda request, timeout: Response(jpeg_bytes()))
    preview = set_metadata.fetch_set_preview(tmp_path, metadata)
    assert preview == set_metadata.cached_set_preview(tmp_path, "76344-1")


def test_set_preview_rejects_untrusted_redirect_and_large_images(monkeypatch, tmp_path):
    metadata = SetMetadata("76344-1", "Name", "https://cdn.rebrickable.com/media/sets/a.jpg")
    monkeypatch.setattr(
        set_metadata,
        "urlopen",
        lambda request, timeout: Response(jpeg_bytes(), url="https://example.invalid/image.jpg"),
    )
    with pytest.raises(SetMetadataError, match="No set image"):
        set_metadata.fetch_set_preview(tmp_path, metadata)
    monkeypatch.setattr(set_metadata, "urlopen", lambda request, timeout: Response(b"x" * (set_metadata.MAX_IMAGE_BYTES + 1)))
    with pytest.raises(SetMetadataError, match="unexpectedly large"):
        set_metadata.fetch_set_preview(tmp_path, metadata)


def test_metadata_failure_does_not_break_inventory_download(monkeypatch, tmp_path):
    service = service_at(tmp_path)
    service.settings = service.settings.__class__(None, "76344-1", tmp_path / "cache", True)
    monkeypatch.setattr(services, "download_inventory", lambda *args, **kwargs: 4)
    monkeypatch.setattr(services, "fetch_set_metadata", lambda *args, **kwargs: (_ for _ in ()).throw(SetMetadataError("bad")))
    assert service.download(api_key="private") == 4


def test_downloaded_sets_use_cached_metadata_when_available(tmp_path, entries):
    service = service_at(tmp_path)
    service.settings = service.settings.__class__(None, "76344-1", tmp_path / "cache", True)
    service.cache_directory.mkdir(parents=True)
    import json
    (service.cache_directory / "76344-1.json").write_text(json.dumps({"results": entries}), encoding="utf-8")
    set_metadata.save_set_metadata(service.cache_directory, SetMetadata("76344-1", "Hogwarts Iconic Set"))
    assert service.downloaded_sets() == [SetMetadata("76344-1", "Hogwarts Iconic Set")]


def test_downloaded_sets_exclude_hidden_relationship_and_malformed_files(tmp_path, entries):
    import json
    service = service_at(tmp_path)
    service.settings = service.settings.__class__(None, "76344-1", tmp_path / "cache", True)
    service.cache_directory.mkdir(parents=True)
    valid = json.dumps({"schema_version": 1, "set_num": "76344-1", "results": entries})
    (service.cache_directory / "76344-1.json").write_text(valid, encoding="utf-8")
    (service.cache_directory / "._76344-1.json").write_bytes(b"\x00AppleDouble")
    (service.cache_directory / "relationships-v1.json").write_text("{}", encoding="utf-8")
    (service.cache_directory / "._relationships-v1.json").write_bytes(b"\x00AppleDouble")
    (service.cache_directory / ".DS_Store").write_text("ignored")
    (service.cache_directory / "10305-1.json").write_text("{malformed", encoding="utf-8")
    (service.cache_directory / "10305-1.json.tmp").write_text(valid, encoding="utf-8")
    assert [item.set_num for item in service.downloaded_sets()] == ["76344-1"]
