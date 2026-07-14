from __future__ import annotations

import json
import threading
from pathlib import Path

import pytest

from lego_element_lookup import downloader
from lego_element_lookup.config import Settings, load_settings, remove_legacy_api_key, save_settings
from lego_element_lookup.downloader import DownloadError
from lego_element_lookup.gui import app
from lego_element_lookup.gui.tasks import BackgroundTask
from lego_element_lookup.secrets import SecretStore, resolve_api_key
from lego_element_lookup import services
from lego_element_lookup.services import ApplicationService, ValidationError
from lego_element_lookup.set_metadata import SetMetadataError


class FakeKeyring:
    def __init__(self):
        self.value = None
        self.get_calls = 0

    def get_password(self, service, username):
        self.get_calls += 1
        return self.value

    def set_password(self, service, username, password):
        self.value = password

    def delete_password(self, service, username):
        self.value = None


def test_non_secret_settings_round_trip(tmp_path):
    path = tmp_path / "config.json"
    settings = Settings(None, "76344-1", tmp_path / "cache", True)
    save_settings(settings, path)
    saved = json.loads(path.read_text(encoding="utf-8"))
    assert "rebrickable_api_key" not in saved
    assert load_settings(path, env={}) == settings


def test_legacy_key_is_removed_atomically(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"rebrickable_api_key": "legacy-secret", "default_set": "76344-1"}), encoding="utf-8")
    remove_legacy_api_key(path)
    assert json.loads(path.read_text(encoding="utf-8")) == {"default_set": "76344-1"}


def test_key_resolution_precedence():
    backend = FakeKeyring()
    store = SecretStore(backend)
    store.save("keychain-key")
    assert resolve_api_key(store, "legacy-key", {"REBRICKABLE_API_KEY": "environment-key"}) == "environment-key"
    assert resolve_api_key(store, "legacy-key", {}) == "keychain-key"
    store.delete()
    assert resolve_api_key(store, "legacy-key", {}) == "legacy-key"


def test_service_configures_keychain_without_writing_secret(tmp_path):
    config_path = tmp_path / "config.json"
    backend = FakeKeyring()
    service = ApplicationService(settings_path=config_path, secret_store=SecretStore(backend))
    service.configure(api_key="private-value", set_num="76344-1", cache_directory=tmp_path / "cache")
    assert backend.value == "private-value"
    assert "private-value" not in config_path.read_text(encoding="utf-8")
    assert service.settings.setup_complete is True


def test_existing_inventory_does_not_force_onboarding_for_pre_schema_three_settings(tmp_path):
    cache = tmp_path / "cache"
    cache.mkdir()
    (cache / "76344-1.json").write_text(json.dumps({"schema_version": 1, "set_num": "76344-1", "results": []}), encoding="utf-8")
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps({"schema_version": 2, "default_set": "76344-1", "cache_directory": str(cache)}), encoding="utf-8")
    service = ApplicationService(settings_path=config_path, secret_store=SecretStore(FakeKeyring()))
    assert service.settings.setup_complete is False
    assert service.setup_required is False


def test_keychain_is_read_only_once_per_session():
    backend = FakeKeyring(); backend.value = "session-secret"
    store = SecretStore(backend)
    assert store.get() == "session-secret"
    assert store.get() == "session-secret"
    assert backend.get_calls == 1


def test_denied_keychain_access_does_not_loop():
    class Denied(FakeKeyring):
        def get_password(self, service, username):
            self.get_calls += 1
            raise RuntimeError("denied")
    backend = Denied(); store = SecretStore(backend)
    with pytest.raises(Exception, match="not allowed"):
        store.get()
    assert store.get() is None
    assert backend.get_calls == 1


def test_service_reuses_and_clears_session_key(tmp_path):
    backend = FakeKeyring(); backend.value = "stored-secret"
    service = ApplicationService(settings_path=tmp_path / "config.json", secret_store=SecretStore(backend))
    assert service.api_key() == "stored-secret"
    assert service.api_key() == "stored-secret" and backend.get_calls == 1
    service.replace_api_key("replacement", remember=False)
    assert service.api_key() == "replacement"
    service.remove_api_key()
    assert service._session_api_key is None


def test_inventory_and_set_downloads_reuse_retrieved_key(monkeypatch, tmp_path):
    backend = FakeKeyring(); backend.value = "stored-secret"
    service = ApplicationService(settings_path=tmp_path / "config.json", secret_store=SecretStore(backend))
    service.settings = Settings(None, "76344-1", tmp_path / "cache", True)
    keys = []
    monkeypatch.setattr(services, "download_inventory", lambda set_num, key, destination, **kwargs: keys.append(key) or 1)
    monkeypatch.setattr(services, "fetch_set_metadata", lambda set_num, key: (_ for _ in ()).throw(SetMetadataError("optional")))
    service.download()
    service.download(set_num="76345-1")
    assert keys == ["stored-secret", "stored-secret"]
    assert backend.get_calls == 1


@pytest.mark.parametrize("value", ["", "abc", "76344-one"])
def test_invalid_set_numbers_are_rejected(value):
    with pytest.raises(ValidationError):
        ApplicationService.validate_set_num(value)


@pytest.mark.parametrize(
    ("value", "canonical"),
    [("10334", "10334-1"), ("10334-1", "10334-1"), (" 10334 ", "10334-1"), (" 10334-1 ", "10334-1")],
)
def test_human_set_numbers_are_canonicalised(value, canonical):
    assert ApplicationService.validate_set_num(value) == canonical


def test_unsafe_pagination_url_is_rejected(monkeypatch, tmp_path):
    monkeypatch.setattr(
        downloader,
        "_request_json",
        lambda url, key: {"results": [], "next": "https://example.invalid/steal"},
    )
    with pytest.raises(DownloadError, match="unsafe pagination"):
        downloader.download_inventory("76344-1", "fake-key", tmp_path / "cache.json")


def test_cancelled_download_does_not_replace_cache(tmp_path):
    destination = tmp_path / "cache.json"
    destination.write_text("existing", encoding="utf-8")
    with pytest.raises(downloader.DownloadCancelled):
        downloader.download_inventory("76344-1", "fake-key", destination, cancelled=lambda: True)
    assert destination.read_text(encoding="utf-8") == "existing"


def test_desktop_smoke_mode_does_not_open_tk(capsys):
    assert app.main(["--smoke-test"]) == 0
    assert "LEGO Element Lookup 1.4.0" in capsys.readouterr().out


def test_background_task_delivers_widget_callbacks_on_polling_thread():
    class Owner:
        def __init__(self):
            self.callbacks = []

        def after(self, delay, callback):
            self.callbacks.append(callback)

    owner = Owner()
    callback_threads = []
    task = None

    def work():
        task.report((1, 10))
        return 10

    task = BackgroundTask(
        owner,
        work,
        lambda value: callback_threads.append(("success", threading.get_ident(), value)),
        lambda error: callback_threads.append(("error", threading.get_ident(), error)),
        lambda value: callback_threads.append(("progress", threading.get_ident(), value)),
    )
    main_thread = threading.get_ident()
    task.start()
    task.thread.join(timeout=2)
    while owner.callbacks:
        owner.callbacks.pop(0)()
    assert callback_threads == [
        ("progress", main_thread, (1, 10)),
        ("success", main_thread, 10),
    ]
