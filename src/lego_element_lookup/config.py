"""Configuration and per-user path handling."""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

APP_NAME = "lego-element-lookup"
DEFAULT_SET = "76344-1"
CONFIG_SCHEMA_VERSION = 2


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
    return Settings(
        str(api_key).strip() if api_key else None,
        str(default_set).strip(),
        Path(str(custom_cache)).expanduser() if custom_cache else None,
        setup_complete,
        parsed_version,
    )


def settings_cache_dir(settings: Settings) -> Path:
    """Return the configured cache directory, or the platform default."""
    return settings.cache_directory or cache_dir()


def save_settings(settings: Settings, path: Path | None = None) -> None:
    """Atomically save non-secret settings with user-only permissions where supported."""
    path = config_path() if path is None else path
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "schema_version": CONFIG_SCHEMA_VERSION,
        "default_set": settings.default_set,
        "cache_directory": str(settings.cache_directory) if settings.cache_directory else None,
        "setup_complete": settings.setup_complete,
    }
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
