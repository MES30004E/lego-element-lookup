"""Read cached inventories and look up LEGO element IDs."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlparse


class CacheError(RuntimeError):
    """Base class for friendly cache errors."""


class CacheMissingError(CacheError):
    pass


class CacheFormatError(CacheError):
    pass


@dataclass
class Match:
    part_code: str
    colour_code: str
    part_name: str
    colour_name: str
    rgb: str | None = None
    part_img_url: str | None = None
    quantity: int = 0
    spare_quantity: int = 0

    @property
    def candidate_id(self) -> tuple[str, str, str, str, str | None, str | None, int, int]:
        """Stable identity used to reject stale asynchronous GUI callbacks."""
        return (
            self.part_code,
            self.colour_code,
            self.part_name,
            self.colour_name,
            self.rgb,
            self.part_img_url,
            self.quantity,
            self.spare_quantity,
        )


def image_element_id(entry: dict[str, Any]) -> str:
    url = str((entry.get("part") or {}).get("part_img_url") or "").strip()
    return Path(urlparse(url).path).stem if url else ""


def lego_colour(colour: dict[str, Any]) -> tuple[str, str]:
    lego = ((colour.get("external_ids") or {}).get("LEGO") or {})
    ids = lego.get("ext_ids") or []
    descriptions = lego.get("ext_descrs") or []
    code = str(ids[0]) if ids else "Unknown"
    name = str(colour.get("name") or "Unknown")
    if descriptions:
        first = descriptions[0]
        if isinstance(first, list) and first:
            name = str(first[0])
        elif isinstance(first, str) and first:
            name = first
    return code, name


def validate_inventory_data(data: object) -> list[dict[str, Any]]:
    """Validate the cache envelope and fields required by lookup."""
    results = data.get("results") if isinstance(data, dict) else data
    if not isinstance(results, list) or not all(isinstance(item, dict) for item in results):
        raise CacheFormatError("The cache must contain a list of inventory entries.")
    for index, entry in enumerate(results):
        part = entry.get("part")
        colour = entry.get("color")
        if not isinstance(part, dict) or not isinstance(colour, dict):
            raise CacheFormatError(f"Inventory entry {index + 1} is missing part or colour data.")
        if not part.get("part_num") or not part.get("name"):
            raise CacheFormatError(f"Inventory entry {index + 1} is missing required part fields.")
        quantity = entry.get("quantity", 0)
        if isinstance(quantity, bool) or not isinstance(quantity, (int, str)):
            raise CacheFormatError(f"Inventory entry {index + 1} has an invalid quantity.")
        try:
            int(quantity)
        except (TypeError, ValueError):
            raise CacheFormatError(f"Inventory entry {index + 1} has an invalid quantity.") from None
    return results


def load_inventory(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise CacheMissingError(
            f"No cached inventory exists at {path}.\nDownload it with: lego-lookup download {path.stem}"
        )
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise CacheFormatError(f"The cache file is not valid JSON: {path}") from exc
    except OSError as exc:
        raise CacheError(f"Could not read cache file {path}: {exc}") from exc
    try:
        return validate_inventory_data(data)
    except CacheFormatError as exc:
        raise CacheFormatError(f"The cache file has an unexpected format: {path}. {exc}") from exc


def find_matches(inventory: Iterable[dict[str, Any]], element_id: str) -> list[Match]:
    combined: dict[tuple[str, str, str, str], Match] = {}
    for entry in inventory:
        identifiers = {str(entry.get("element_id") or "").strip(), image_element_id(entry)}
        if element_id not in identifiers:
            continue
        part = entry.get("part") or {}
        code, name = lego_colour(entry.get("color") or {})
        key = (str(part.get("part_num") or "Unknown"), code, str(part.get("name") or "Unknown"), name)
        rgb = (entry.get("color") or {}).get("rgb")
        image_url = part.get("part_img_url")
        match = combined.setdefault(
            key,
            Match(
                *key,
                rgb=str(rgb) if rgb else None,
                part_img_url=str(image_url).strip() if image_url else None,
            ),
        )
        try:
            quantity = int(entry.get("quantity") or 0)
        except (TypeError, ValueError):
            quantity = 0
        if entry.get("is_spare"):
            match.spare_quantity += quantity
        else:
            match.quantity += quantity
    return list(combined.values())
