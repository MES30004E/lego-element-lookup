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
from .downloader import DownloadCancelled, download_inventory, test_connection
from .lookup import CacheError, Match, find_matches, load_inventory
from .preview import PreviewCache
from .relationship_cache import RelationshipCache, RelationshipCacheMetadata, RelationshipCacheResult
from .relationships import RelatedDesigns, RelationshipType, download_relationship_data
from .secrets import SecretStore, SecretStoreError, resolve_api_key
from .set_metadata import (
    SetMetadata,
    SetMetadataError,
    cached_set_preview,
    fetch_set_metadata,
    fetch_set_preview,
    load_set_metadata,
    save_set_metadata,
)

SET_PATTERN = re.compile(r"\d+-\d+\Z")
PLAIN_SET_PATTERN = re.compile(r"\d+\Z")
RELATED_DESIGN_LABELS = {
    RelationshipType.ALTERNATE: "Alternate designs",
    RelationshipType.MOULD: "Mould variants",
    RelationshipType.PRINT: "Decorated variants",
    RelationshipType.PATTERN: "Decorated variants",
    RelationshipType.PAIR: "Related components",
    RelationshipType.SUBPART: "Related components",
}


class ValidationError(ValueError):
    pass


class SetRemovalError(RuntimeError):
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
        """Require setup only when the selected inventory is absent.

        Older desktop configurations can predate ``setup_complete`` while still
        containing a valid downloaded inventory. They remain usable offline
        after an upgrade instead of being forced back through onboarding.
        """
        return not self.cache_file.is_file()

    def api_key(self) -> str | None:
        key = self._session_api_key or resolve_api_key(self.secret_store, self.settings.api_key)
        if not key and self.secret_store.access_denied:
            raise ValidationError("Secure keychain access was not allowed. Enter the API key again to use it for this session.")
        return key

    def clear_session_key(self) -> None:
        self._session_api_key = None
        self.secret_store.clear_session()

    def replace_api_key(self, api_key: str, *, remember: bool) -> None:
        self.clear_session_key()
        if remember:
            self.secret_store.save(api_key)
        else:
            self.secret_store.save_for_session(api_key)
            self._session_api_key = api_key.strip()

    def remove_api_key(self) -> None:
        self.clear_session_key()
        self.secret_store.delete()

    @staticmethod
    def validate_element_id(element_id: str) -> str:
        value = element_id.strip()
        if not value or not value.isdigit():
            raise ValidationError("Enter a numerical LEGO element ID.")
        return value

    @staticmethod
    def validate_set_num(set_num: str) -> str:
        value = set_num.strip()
        if PLAIN_SET_PATTERN.fullmatch(value):
            return f"{value}-1"
        if not SET_PATTERN.fullmatch(value):
            raise ValidationError("Enter a numerical LEGO set number, for example 10334.")
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
        # Metadata is helpful presentation data, not a prerequisite for an offline inventory.
        try:
            metadata = fetch_set_metadata(target_set, key)
            save_set_metadata(cache_directory or self.cache_directory, metadata)
        except SetMetadataError:
            pass
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
            self.replace_api_key(api_key, remember=True)
            remove_legacy_api_key(self.settings_path)
        else:
            self.replace_api_key(api_key, remember=False)
        self.settings = replace(self.settings, api_key=None, default_set=selected_set, cache_directory=custom_cache, setup_complete=True)
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
        return self.preview_cache().cached(match.part_img_url)

    def fetch_preview(self, match: Match) -> Path:
        return self.preview_cache().fetch(match.part_img_url)

    def preview_cache(self) -> PreviewCache:
        return PreviewCache(self.settings.preferences.preview_cache_directory or self.cache_directory)

    def preview_cache_size(self) -> int:
        return self.preview_cache().size_bytes()

    def clear_preview_cache(self) -> None:
        self.preview_cache().clear()

    def enforce_preview_cache_limit(self) -> int:
        preferences = self.settings.preferences
        return self.preview_cache().enforce_limit(preferences.preview_cache_limit_mb, preferences.preview_cache_eviction)

    def relationship_cache_state(self) -> RelationshipCacheResult:
        """Inspect optional related-design data without affecting inventory lookup."""
        return RelationshipCache(self.cache_directory).load()

    def related_designs(self, match: Match) -> RelatedDesigns | None:
        cache = self.relationship_cache_state()
        return cache.index.related_designs(match.part_code) if cache.index else None

    def refresh_relationship_data(
        self,
        *,
        progress: Callable[[int, int], None] | None = None,
        cancelled: Callable[[], bool] | None = None,
    ) -> RelationshipCacheMetadata:
        """Download public Rebrickable relationship data without an API key."""
        if cancelled and cancelled():
            raise DownloadCancelled("Related-design download cancelled.")
        if progress:
            progress(0, 1)
        payload = download_relationship_data()
        if cancelled and cancelled():
            raise DownloadCancelled("Related-design download cancelled.")
        metadata = RelationshipCache(self.cache_directory).replace_from_gzip(payload)
        if progress:
            progress(1, 1)
        return metadata

    def set_metadata(self, set_num: str | None = None) -> SetMetadata | None:
        return load_set_metadata(self.cache_directory, set_num or self.settings.default_set)

    def cached_set_preview(self, set_num: str | None = None) -> Path | None:
        return cached_set_preview(self.cache_directory, set_num or self.settings.default_set)

    def fetch_set_preview(self, set_num: str | None = None) -> Path:
        target_set = set_num or self.settings.default_set
        metadata = self.set_metadata(target_set)
        if not metadata:
            raise SetMetadataError("Set metadata is not cached.")
        return fetch_set_preview(self.cache_directory, metadata)

    def downloaded_sets(self) -> list[SetMetadata]:
        """Return validated root inventory caches, excluding metadata and support files."""
        if not self.cache_directory.exists():
            return []
        sets: dict[str, SetMetadata] = {}
        for inventory in sorted(self.cache_directory.glob("*.json")):
            set_num = inventory.stem
            if inventory.name.startswith(".") or not SET_PATTERN.fullmatch(set_num):
                continue
            try:
                load_inventory(inventory)
            except CacheError:
                continue
            metadata = self.set_metadata(set_num)
            sets[set_num] = metadata or SetMetadata(set_num, "Downloaded set")
        return [sets[set_num] for set_num in sorted(sets)]

    def remove_downloaded_sets(self, set_nums: list[str], *, delete_set_assets: bool = False) -> tuple[str, ...]:
        """Remove selected inventory caches and, optionally, their per-set presentation data.

        Root inventory files are the downloaded-set registry. Part previews are
        shared globally, so they are deliberately outside this operation.
        """
        selected = tuple(sorted({self.validate_set_num(value) for value in set_nums}))
        if self.settings.default_set in selected:
            raise SetRemovalError("Switch to another downloaded set before removing the active set.")
        base = self.cache_directory.resolve(strict=False)

        def target(*parts: str) -> Path:
            path = self.cache_directory.joinpath(*parts)
            parent = path.parent.resolve(strict=False)
            if parent != base and base not in parent.parents:
                raise SetRemovalError("Refusing to remove data outside the configured cache folder.")
            return path

        removed: list[str] = []
        for set_num in selected:
            inventory = target(f"{set_num}.json")
            if not inventory.is_file() and not inventory.is_symlink():
                continue
            try:
                inventory.unlink()
                target(f"._{set_num}.json").unlink(missing_ok=True)
                if delete_set_assets:
                    directory = target("sets", set_num)
                    for name in ("metadata.json", "preview.png", "._metadata.json", "._preview.png"):
                        target("sets", set_num, name).unlink(missing_ok=True)
                    try:
                        directory.rmdir()
                    except OSError:
                        pass
                    target("sets", f"._{set_num}").unlink(missing_ok=True)
            except OSError:
                raise SetRemovalError(f"Could not remove cached data for set {set_num}.") from None
            removed.append(set_num)
        return tuple(removed)

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
