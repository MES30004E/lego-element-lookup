from lego_element_lookup.lookup import lego_colour


def test_lego_colour_id_and_name():
    colour = {"name": "Dark Red", "external_ids": {"LEGO": {"ext_ids": [154], "ext_descrs": [["New Dark Red"]]}}}
    assert lego_colour(colour) == ("154", "New Dark Red")


def test_colour_fallback():
    assert lego_colour({"id": 320, "name": "Dark Red"}) == ("Unknown", "Dark Red")
