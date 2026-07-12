import json

import pytest

from lego_element_lookup.lookup import CacheFormatError, CacheMissingError, find_matches, load_inventory


def test_top_level_element_id(entries):
    match = find_matches(entries, "6212040")[0]
    assert match.part_code == "35480"
    assert match.rgb == "720E0F"


def test_image_element_id(entries):
    match = find_matches(entries, "6293739")[0]
    assert (match.part_code, match.part_name) == ("2420", "Plate 2 x 2 Corner")
    assert match.part_img_url.endswith("/6293739.jpg?x=1")


def test_normal_and_spare_duplicates_are_combined(entries):
    spare = {**entries[0], "quantity": 1, "is_spare": True}
    matches = find_matches([entries[0], spare], "6212040")
    assert len(matches) == 1
    assert (matches[0].quantity, matches[0].spare_quantity) == (2, 1)


def test_invalid_cache_json(tmp_path):
    path = tmp_path / "set.json"
    path.write_text("{broken", encoding="utf-8")
    with pytest.raises(CacheFormatError):
        load_inventory(path)


def test_missing_cache(tmp_path):
    with pytest.raises(CacheMissingError, match="lego-lookup download"):
        load_inventory(tmp_path / "76344-1.json")


def test_cache_accepts_api_shape(tmp_path, entries):
    path = tmp_path / "set.json"
    path.write_text(json.dumps({"results": entries}), encoding="utf-8")
    assert load_inventory(path) == entries
