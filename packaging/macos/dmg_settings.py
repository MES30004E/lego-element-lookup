"""Deterministic dmgbuild settings for LEGO Element Lookup distribution images."""

from __future__ import annotations

import os


application = os.environ["DMG_APPLICATION"]
background = os.environ["DMG_BACKGROUND"]
format = "UDZO"
files = [application]
symlinks = {"Applications": "/Applications"}
window_rect = ((100, 100), (720, 450))
show_toolbar = False
show_status_bar = False
show_sidebar = False
show_pathbar = False
show_icon_preview = False
default_view = "icon-view"
icon_size = 96
text_size = 13
icon_locations = {
    "LEGO Element Lookup.app": (180, 250),
    "Applications": (540, 250),
}
