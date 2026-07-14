from __future__ import annotations

import json

from lego_element_lookup.config import Preferences, Settings, load_settings, save_settings
from lego_element_lookup.gui.theme import DARK, LIGHT, palette_for
from lego_element_lookup.preview import PreviewCache


def test_schema_two_migrates_with_safe_preference_defaults(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"schema_version": 2, "default_set": "76344-1", "future": "kept"}))
    settings = load_settings(path, env={})
    assert settings.preferences == Preferences()
    save_settings(settings, path)
    stored = json.loads(path.read_text())
    assert stored["schema_version"] == 3 and stored["future"] == "kept"
    assert "rebrickable_api_key" not in stored


def test_invalid_preferences_fall_back_and_future_values_survive(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"preferences": {"theme": "neon", "preview_cache_limit_mb": "huge", "future": 4}}))
    settings = load_settings(path, env={})
    assert settings.preferences.theme == "system"
    assert settings.preferences.preview_cache_limit_mb == 250
    save_settings(settings, path)
    assert json.loads(path.read_text())["preferences"]["future"] == 4


def test_preview_cache_accounting_eviction_and_clear(tmp_path):
    cache = PreviewCache(tmp_path); cache.directory.mkdir()
    first = cache.directory / "first.png"; second = cache.directory / "second.png"
    first.write_bytes(b"a" * 700_000); second.write_bytes(b"b" * 700_000)
    cache._write_metadata({"first.png": {"last_access": 1}, "second.png": {"last_access": 2}})
    assert cache.size_bytes() == 1_400_000
    assert cache.enforce_limit(1, "oldest") == 1
    assert second.exists() and not first.exists()
    cache.clear(); assert cache.size_bytes() == 0


def test_palette_roles_and_selection():
    assert palette_for("dark") == DARK and palette_for("light") == LIGHT
    assert len(DARK.__dataclass_fields__) == 12
