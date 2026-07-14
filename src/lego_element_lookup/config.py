"""Configuration and per-user path handling."""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping

APP_NAME = "lego-element-lookup"
DEFAULT_SET = "76344-1"
CONFIG_SCHEMA_VERSION = 3


@dataclass(frozen=True)
class Preferences:
    """Non-secret desktop presentation and lookup preferences."""
    theme: str = "system"
    density: str = "comfortable"
    auto_copy: bool = True
    show_copied_confirmation: bool = True
    refocus_input: bool = True
    show_lego_colour_code: bool = True
    show_inventory_quantity: bool = True
    previews_enabled: bool = True
    auto_download_previews: bool = True
    preview_size: str = "medium"
    preview_cache_directory: Path | None = None
    preview_cache_limit_mb: int = 250
    preview_cache_eviction: str = "oldest"
    set_thumbnails_enabled: bool = True
    auto_cache_set_thumbnails: bool = True
    relationship_download_mode: str = "manual"
    update_channel: str = "stable"
    automatic_update_checks: bool = False
    window_layout_preset: str = "auto"
    last_window_width: int = 0
    last_window_height: int = 0
    extra: dict[str, object] = field(default_factory=dict, compare=False, repr=False)


def _preferences(value: object) -> Preferences:
    data = value if isinstance(value, dict) else {}
    def choice(key: str, allowed: set[str], default: str) -> str:
        candidate = data.get(key, default)
        return candidate if isinstance(candidate, str) and candidate in allowed else default
    def boolean(key: str, default: bool) -> bool:
        return data[key] if isinstance(data.get(key), bool) else default
    def bounded_int(key: str, default: int) -> int:
        value = data.get(key, default)
        return value if isinstance(value, int) and not isinstance(value, bool) and 0 <= value <= 10_000 else default
    def window_dimension(key: str, minimum: int, maximum: int) -> int:
        value = data.get(key, 0)
        return value if isinstance(value, int) and not isinstance(value, bool) and minimum <= value <= maximum else 0
    known = {field for field in Preferences.__dataclass_fields__ if field != "extra"}
    directory = data.get("preview_cache_directory")
    return Preferences(
        theme=choice("theme", {"system", "light", "dark"}, "system"),
        density=choice("density", {"comfortable", "compact"}, "comfortable"),
        auto_copy=boolean("auto_copy", True), show_copied_confirmation=boolean("show_copied_confirmation", True),
        refocus_input=boolean("refocus_input", True), show_lego_colour_code=boolean("show_lego_colour_code", True),
        show_inventory_quantity=boolean("show_inventory_quantity", True), previews_enabled=boolean("previews_enabled", True),
        auto_download_previews=boolean("auto_download_previews", True),
        preview_size=choice("preview_size", {"small", "medium", "large"}, "medium"),
        preview_cache_directory=Path(directory).expanduser() if isinstance(directory, str) and directory else None,
        preview_cache_limit_mb=bounded_int("preview_cache_limit_mb", 250),
        preview_cache_eviction=choice("preview_cache_eviction", {"oldest", "never"}, "oldest"),
        set_thumbnails_enabled=boolean("set_thumbnails_enabled", True),
        auto_cache_set_thumbnails=boolean("auto_cache_set_thumbnails", True),
        relationship_download_mode=choice("relationship_download_mode", {"manual"}, "manual"),
        update_channel=choice("update_channel", {"stable", "beta"}, "stable"),
        automatic_update_checks=boolean("automatic_update_checks", False),
        window_layout_preset=choice("window_layout_preset", {"auto", "wide", "tall", "compact"}, "auto"),
        last_window_width=window_dimension("last_window_width", 640, 7680),
        last_window_height=window_dimension("last_window_height", 720, 4320),
        extra={key: item for key, item in data.items() if key not in known},
    )


def _preferences_data(preferences: Preferences) -> dict[str, object]:
    data = dict(preferences.extra)
    for key in Preferences.__dataclass_fields__:
        if key != "extra":
            value = getattr(preferences, key)
            data[key] = str(value) if key == "preview_cache_directory" and value else value
    return data


class ConfigError(RuntimeError):
    """Raised when local configuration cannot be read."""


def config_dir(env: Mapping[str, str] | None = None, platform: str | None = None) -> Path:
    values = os.environ if env is None else env
    system = sys.platform if platform is None else platform
    home = Path(values.get("HOME", str(Path.home())))
    if system == "darwin":
        return home / "Library" / "Application Support" / APP_NAME
    if system == "win32":
        return Path(values.get("APPDATA", home / "AppData" / "Roaming")) / APP_NAME
    return Path(values.get("XDG_CONFIG_HOME", home / ".config")) / APP_NAME


def cache_dir(env: Mapping[str, str] | None = None, platform: str | None = None) -> Path:
    values = os.environ if env is None else env
    system = sys.platform if platform is None else platform
    home = Path(values.get("HOME", str(Path.home())))
    if system == "darwin":
        return home / "Library" / "Caches" / APP_NAME
    if system == "win32":
        return Path(values.get("LOCALAPPDATA", home / "AppData" / "Local")) / APP_NAME / "cache"
    return Path(values.get("XDG_CACHE_HOME", home / ".cache")) / APP_NAME


def config_path() -> Path:
    return config_dir() / "config.json"


@dataclass(frozen=True)
class Settings:
    api_key: str | None
    default_set: str
    cache_directory: Path | None = None
    setup_complete: bool = False
    schema_version: int = CONFIG_SCHEMA_VERSION
    preferences: Preferences = field(default_factory=Preferences)
    extra: dict[str, object] = field(default_factory=dict, compare=False, repr=False)


def load_settings(path: Path | None = None, env: Mapping[str, str] | None = None) -> Settings:
    values = os.environ if env is None else env
    path = config_path() if path is None else path
    data: dict[str, object] = {}
    if path.exists():
        try:
            loaded = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ConfigError(f"Could not read configuration at {path}: {exc}") from exc
        if not isinstance(loaded, dict):
            raise ConfigError(f"Configuration at {path} must contain a JSON object.")
        data = loaded

    api_key = values.get("REBRICKABLE_API_KEY") or data.get("rebrickable_api_key")
    if api_key == "YOUR_API_KEY_HERE":
        api_key = None
    default_set = values.get("LEGO_LOOKUP_SET") or data.get("default_set") or DEFAULT_SET
    custom_cache = data.get("cache_directory")
    setup_complete = bool(data.get("setup_complete", False))
    schema_version = data.get("schema_version", 1)
    try:
        parsed_version = int(schema_version)
    except (TypeError, ValueError):
        parsed_version = 1
    known = {"rebrickable_api_key", "default_set", "cache_directory", "setup_complete", "schema_version", "preferences"}
    return Settings(
        str(api_key).strip() if api_key else None,
        str(default_set).strip(),
        Path(str(custom_cache)).expanduser() if custom_cache else None,
        setup_complete,
        parsed_version,
        _preferences(data.get("preferences")),
        {key: item for key, item in data.items() if key not in known},
    )


def settings_cache_dir(settings: Settings) -> Path:
    """Return the configured cache directory, or the platform default."""
    return settings.cache_directory or cache_dir()


def save_settings(settings: Settings, path: Path | None = None) -> None:
    """Atomically save non-secret settings with user-only permissions where supported."""
    path = config_path() if path is None else path
    path.parent.mkdir(parents=True, exist_ok=True)
    data = dict(settings.extra)
    data.update({
        "schema_version": CONFIG_SCHEMA_VERSION,
        "default_set": settings.default_set,
        "cache_directory": str(settings.cache_directory) if settings.cache_directory else None,
        "setup_complete": settings.setup_complete,
        "preferences": _preferences_data(settings.preferences),
    })
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    try:
        temporary.chmod(0o600)
    except OSError:
        pass
    temporary.replace(path)


def remove_legacy_api_key(path: Path | None = None) -> None:
    """Remove a legacy plaintext API key without disturbing other settings."""
    path = config_path() if path is None else path
    if not path.exists():
        return
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ConfigError(f"Could not migrate configuration at {path}: {exc}") from exc
    if not isinstance(data, dict) or "rebrickable_api_key" not in data:
        return
    data.pop("rebrickable_api_key", None)
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    try:
        temporary.chmod(0o600)
    except OSError:
        pass
    temporary.replace(path)


def validate_cache_directory(path: Path) -> Path:
    """Create and verify a cache directory without leaving probe files behind."""
    path = path.expanduser()
    try:
        path.mkdir(parents=True, exist_ok=True)
        probe = path / ".write-test"
        probe.touch(exist_ok=False)
        probe.unlink()
    except OSError as exc:
        raise ConfigError(f"Cache directory is not writable: {path}") from exc
    return path
