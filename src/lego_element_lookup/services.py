"""UI-independent application services shared by the CLI and desktop app."""

from __future__ import annotations

import os
import re
import subprocess
import sys
from dataclasses import replace
from pathlib import Path
from typing import Callable

from .config import (
    Settings,
    config_path,
    load_settings,
    remove_legacy_api_key,
    save_settings,
    settings_cache_dir,
    validate_cache_directory,
)
from .downloader import download_inventory, test_connection
from .lookup import Match, find_matches, load_inventory
from .preview import PreviewCache
from .secrets import SecretStore, SecretStoreError, resolve_api_key

SET_PATTERN = re.compile(r"\d+-\d+\Z")


class ValidationError(ValueError):
    pass


class ApplicationService:
    def __init__(self, *, settings_path: Path | None = None, secret_store: SecretStore | None = None) -> None:
        self.settings_path = settings_path or config_path()
        self.secret_store = secret_store or SecretStore()
        self.settings = load_settings(self.settings_path)
        self._inventory: list[dict[str, object]] | None = None
        self._session_api_key: str | None = None

    @property
    def cache_directory(self) -> Path:
        return settings_cache_dir(self.settings)

    @property
    def cache_file(self) -> Path:
        return self.cache_directory / f"{self.settings.default_set}.json"

    @property
    def setup_required(self) -> bool:
        return not self.settings.setup_complete or not self.cache_file.exists()

    def api_key(self) -> str | None:
        return self._session_api_key or resolve_api_key(self.secret_store, self.settings.api_key)

    @staticmethod
    def validate_element_id(element_id: str) -> str:
        value = element_id.strip()
        if not value or not value.isdigit():
            raise ValidationError("Enter a numerical LEGO element ID.")
        return value

    @staticmethod
    def validate_set_num(set_num: str) -> str:
        value = set_num.strip()
        if not SET_PATTERN.fullmatch(value):
            raise ValidationError("Enter a set number such as 76344-1.")
        return value

    def load_inventory(self, *, force: bool = False) -> int:
        if force or self._inventory is None:
            self._inventory = load_inventory(self.cache_file)
        return len(self._inventory)

    def lookup(self, element_id: str) -> list[Match]:
        value = self.validate_element_id(element_id)
        self.load_inventory()
        return find_matches(self._inventory or [], value)

    @classmethod
    def lookup_cached(cls, element_id: str, set_num: str, directory: Path) -> list[Match]:
        """One-off cache lookup used by the command-line interface."""
        value = cls.validate_element_id(element_id)
        return find_matches(load_inventory(directory / f"{set_num}.json"), value)

    def test_connection(self, api_key: str, set_num: str) -> None:
        test_connection(self.validate_set_num(set_num), api_key.strip())

    def download(
        self,
        *,
        set_num: str | None = None,
        api_key: str | None = None,
        cache_directory: Path | None = None,
        progress: Callable[[int, int], None] | None = None,
        cancelled: Callable[[], bool] | None = None,
    ) -> int:
        target_set = self.validate_set_num(set_num or self.settings.default_set)
        key = (api_key or self.api_key() or "").strip()
        if not key:
            raise ValidationError("A Rebrickable API key is required to download an inventory.")
        destination = (cache_directory or self.cache_directory) / f"{target_set}.json"
        count = download_inventory(target_set, key, destination, progress=progress, cancelled=cancelled)
        if target_set == self.settings.default_set:
            self._inventory = None
        return count

    def configure(
        self,
        *,
        api_key: str,
        set_num: str,
        cache_directory: Path | None,
        remember_key: bool = True,
    ) -> None:
        selected_set = self.validate_set_num(set_num)
        selected_cache = validate_cache_directory(cache_directory or settings_cache_dir(replace(self.settings, cache_directory=None)))
        custom_cache = selected_cache if cache_directory else None
        if remember_key:
            self.secret_store.save(api_key)
            remove_legacy_api_key(self.settings_path)
            self._session_api_key = None
        else:
            self.secret_store.save_for_session(api_key)
            self._session_api_key = api_key.strip()
        self.settings = Settings(None, selected_set, custom_cache, True)
        save_settings(self.settings, self.settings_path)
        self._inventory = None

    def change_set(self, set_num: str) -> bool:
        selected_set = self.validate_set_num(set_num)
        updated = replace(self.settings, default_set=selected_set)
        save_settings(updated, self.settings_path)
        self.settings = updated
        self._inventory = None
        return self.cache_file.exists()

    def open_cache_folder(self) -> None:
        directory = validate_cache_directory(self.cache_directory)
        if sys.platform == "win32":
            os.startfile(directory)  # type: ignore[attr-defined]
            return
        command = ["open", str(directory)] if sys.platform == "darwin" else ["xdg-open", str(directory)]
        subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def cached_preview(self, match: Match) -> Path | None:
        return PreviewCache(self.cache_directory).cached(match.part_img_url)

    def fetch_preview(self, match: Match) -> Path:
        return PreviewCache(self.cache_directory).fetch(match.part_img_url)

    def migrate_legacy_secret(self) -> bool:
        if not self.settings.api_key:
            return False
        try:
            self.secret_store.save(self.settings.api_key)
            remove_legacy_api_key(self.settings_path)
        except SecretStoreError:
            return False
        self.settings = replace(self.settings, api_key=None)
        return True
