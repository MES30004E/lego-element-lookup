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
    return Settings(str(api_key).strip() if api_key else None, str(default_set).strip())
