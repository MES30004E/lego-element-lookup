from __future__ import annotations

import json

import pytest

from lego_element_lookup import services, set_metadata
from lego_element_lookup.config import Settings
from lego_element_lookup.gui.set_manager import DownloadedSetManager, set_manager_label
from lego_element_lookup.secrets import SecretStore
from lego_element_lookup.services import ApplicationService, SetRemovalError, ValidationError
from lego_element_lookup.set_metadata import SetMetadata


class Keyring:
    def __init__(self):
        self.value = "stored-secret"
        self.deleted = False

    def get_password(self, _service, _account):
        return self.value

    def set_password(self, _service, _account, value):
        self.value = value

    def delete_password(self, _service, _account):
        self.deleted = True


def service_at(tmp_path, active="76344-1"):
    backend = Keyring()
    service = ApplicationService(settings_path=tmp_path / "config.json", secret_store=SecretStore(backend))
    service.settings = Settings(None, active, tmp_path / "cache", True)
    return service, backend


def inventory(service, set_num, entries):
    service.cache_directory.mkdir(parents=True, exist_ok=True)
    path = service.cache_directory / f"{set_num}.json"
    path.write_text(json.dumps({"schema_version": 1, "set_num": set_num, "results": entries}), encoding="utf-8")
    return path


def test_numeric_download_uses_and_stores_canonical_set(monkeypatch, tmp_path):
    service, _ = service_at(tmp_path)
    calls = []
    monkeypatch.setattr(services, "download_inventory", lambda set_num, key, destination, **kwargs: calls.append((set_num, destination)) or 1)
    monkeypatch.setattr(services, "fetch_set_metadata", lambda set_num, key: SetMetadata(set_num, "Retro Radio"))
    assert service.download(set_num=" 10334 ", api_key="fake-key") == 1
    assert calls[0][0] == "10334-1"
    assert calls[0][1].name == "10334-1.json"
    service.configure(api_key="fake-key", set_num="10334", cache_directory=service.cache_directory, remember_key=False)
    assert service.settings.default_set == "10334-1"


def test_failed_numeric_download_preserves_active_set(monkeypatch, tmp_path):
    service, _ = service_at(tmp_path)
    monkeypatch.setattr(services, "download_inventory", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("network failure")))
    with pytest.raises(RuntimeError, match="network failure"):
        service.download(set_num="10334", api_key="fake-key")
    assert service.settings.default_set == "76344-1"


def test_remove_set_deletes_only_selected_inventory_and_optional_set_assets(tmp_path, entries):
    service, backend = service_at(tmp_path)
    selected = inventory(service, "10334-1", entries)
    other = inventory(service, "76344-1", entries)
    metadata = SetMetadata("10334-1", "Retro Radio")
    set_metadata.save_set_metadata(service.cache_directory, metadata)
    preview = set_metadata.preview_path(service.cache_directory, "10334-1")
    preview.write_bytes(b"preview")
    relationship = service.cache_directory / "relationships-v1.json"
    relationship.write_text("{}", encoding="utf-8")
    unrelated = service.cache_directory / "notes.txt"
    unrelated.write_text("keep", encoding="utf-8")
    sidecar = service.cache_directory / "._10334-1.json"
    sidecar.write_bytes(b"AppleDouble")
    assert service.remove_downloaded_sets(["10334"], delete_set_assets=True) == ("10334-1",)
    assert not selected.exists() and not sidecar.exists()
    assert not set_metadata.metadata_path(service.cache_directory, "10334-1").exists()
    assert not preview.exists()
    assert other.exists() and relationship.exists() and unrelated.exists()
    assert backend.value == "stored-secret" and not backend.deleted


def test_removal_without_asset_option_preserves_per_set_metadata(tmp_path, entries):
    service, _ = service_at(tmp_path)
    inventory(service, "10334-1", entries)
    set_metadata.save_set_metadata(service.cache_directory, SetMetadata("10334-1", "Retro Radio"))
    service.remove_downloaded_sets(["10334-1"])
    assert set_metadata.metadata_path(service.cache_directory, "10334-1").exists()


@pytest.mark.parametrize("value", ["../76344-1", "76344-1/../../outside", "not-a-set"])
def test_set_removal_rejects_path_traversal(value, tmp_path):
    service, _ = service_at(tmp_path)
    with pytest.raises(ValidationError):
        service.remove_downloaded_sets([value])


def test_active_and_last_set_removal_requires_switch(tmp_path, entries):
    service, _ = service_at(tmp_path)
    active = inventory(service, "76344-1", entries)
    with pytest.raises(SetRemovalError, match="Switch"):
        service.remove_downloaded_sets(["76344-1"])
    assert active.exists()


def test_set_manager_marks_only_the_active_set():
    assert set_manager_label("76344-1", "Iron Man", "76344-1").endswith("Active")
    assert not set_manager_label("10334-1", "Retro Radio", "76344-1").endswith("Active")


def test_downloaded_set_manager_refreshes_after_removal(monkeypatch):
    events = []
    manager = object.__new__(DownloadedSetManager)
    manager.service = type(
        "Service",
        (),
        {
            "settings": type("Settings", (), {"default_set": "76344-1"})(),
            "remove_downloaded_sets": lambda self, values, delete_set_assets=False: events.append((values, delete_set_assets)) or tuple(values),
        },
    )()
    manager._variables = {"10334-1": type("Var", (), {"get": lambda self: True})()}
    manager.delete_assets = type("Var", (), {"get": lambda self: True})()
    manager._refresh = lambda: events.append("refresh")
    manager.on_changed = lambda removed: events.append(("changed", removed))
    monkeypatch.setattr("lego_element_lookup.gui.set_manager.messagebox.askyesno", lambda *args, **kwargs: True)
    DownloadedSetManager._remove(manager)
    assert events == [(["10334-1"], True), "refresh", ("changed", ("10334-1",))]
