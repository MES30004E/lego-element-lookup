from __future__ import annotations

import pytest


@pytest.fixture
def entries():
    colour = {
        "id": 320,
        "name": "Dark Red",
        "external_ids": {"LEGO": {"ext_ids": [154], "ext_descrs": [["Dark red"]]}},
    }
    return [
        {
            "element_id": "6212040",
            "quantity": 2,
            "is_spare": False,
            "part": {"part_num": "35480", "name": "Plate Special 1 x 2 Rounded with 2 Open Studs", "part_img_url": "https://cdn.example/6212040.jpg"},
            "color": colour,
        },
        {
            "element_id": "different",
            "quantity": 1,
            "is_spare": False,
            "part": {"part_num": "2420", "name": "Plate 2 x 2 Corner", "part_img_url": "https://cdn.example/parts/6293739.jpg?x=1"},
            "color": {"name": "Medium Azure", "external_ids": {"LEGO": {"ext_ids": [322], "ext_descrs": [["Medium Azure"]]}}},
        },
    ]
