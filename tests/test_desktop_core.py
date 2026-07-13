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
from lego_element_lookup.services import ApplicationService, ValidationError


class FakeKeyring:
    def __init__(self):
        self.value = None

    def get_password(self, service, username):
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


@pytest.mark.parametrize("value", ["", "abc", "76344", "76344-one"])
def test_invalid_set_numbers_are_rejected(value):
    with pytest.raises(ValidationError):
        ApplicationService.validate_set_num(value)


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
    assert "LEGO Element Lookup 1.2.2" in capsys.readouterr().out


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
