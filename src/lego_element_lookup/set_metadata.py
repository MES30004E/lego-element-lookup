"""Optional Rebrickable set metadata and offline thumbnail cache."""

from __future__ import annotations

import io
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from PIL import Image, UnidentifiedImageError

from . import __version__
from .downloader import BASE_URL, DownloadError, _request_json

ALLOWED_IMAGE_HOSTS = {"cdn.rebrickable.com"}
MAX_IMAGE_BYTES = 5 * 1024 * 1024
MAX_IMAGE_PIXELS = 16_000_000
THUMBNAIL_SIZE = (360, 260)


class SetMetadataError(RuntimeError):
    pass


@dataclass(frozen=True)
class SetMetadata:
    set_num: str
    name: str
    image_url: str | None = None
    year: int | None = None
    num_parts: int | None = None


def set_directory(cache_directory: Path, set_num: str) -> Path:
    return cache_directory / "sets" / set_num


def metadata_path(cache_directory: Path, set_num: str) -> Path:
    return set_directory(cache_directory, set_num) / "metadata.json"


def preview_path(cache_directory: Path, set_num: str) -> Path:
    return set_directory(cache_directory, set_num) / "preview.png"


def _optional_positive_int(value: object) -> int | None:
    try:
        parsed = int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    return parsed if parsed >= 0 else None


def _metadata_from_api(data: dict[str, Any], expected_set_num: str) -> SetMetadata:
    set_num = str(data.get("set_num") or "").strip()
    name = str(data.get("name") or "").strip()
    if set_num != expected_set_num or not name:
        raise SetMetadataError("Rebrickable returned invalid set metadata.")
    image_url = str(data.get("set_img_url") or "").strip() or None
    if image_url:
        parsed = urlparse(image_url)
        if parsed.scheme != "https" or parsed.hostname not in ALLOWED_IMAGE_HOSTS:
            image_url = None
    return SetMetadata(
        set_num=set_num,
        name=name,
        image_url=image_url,
        year=_optional_positive_int(data.get("year")),
        num_parts=_optional_positive_int(data.get("num_parts")),
    )


def fetch_set_metadata(set_num: str, api_key: str) -> SetMetadata:
    """Fetch structured metadata using the existing authenticated Rebrickable client."""
    try:
        data = _request_json(f"{BASE_URL}/{set_num}/", api_key)
    except DownloadError as exc:
        raise SetMetadataError("Set metadata could not be downloaded.") from exc
    return _metadata_from_api(data, set_num)


def load_set_metadata(cache_directory: Path, set_num: str) -> SetMetadata | None:
    path = metadata_path(cache_directory, set_num)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError
        metadata = SetMetadata(
            set_num=str(data["set_num"]),
            name=str(data["name"]),
            image_url=str(data["image_url"]) if data.get("image_url") else None,
            year=_optional_positive_int(data.get("year")),
            num_parts=_optional_positive_int(data.get("num_parts")),
        )
        if metadata.set_num != set_num or not metadata.name:
            return None
        if metadata.image_url:
            parsed = urlparse(metadata.image_url)
            if parsed.scheme != "https" or parsed.hostname not in ALLOWED_IMAGE_HOSTS:
                return SetMetadata(metadata.set_num, metadata.name, None, metadata.year, metadata.num_parts)
        return metadata
    except (OSError, ValueError, TypeError, json.JSONDecodeError, KeyError):
        return None


def save_set_metadata(cache_directory: Path, metadata: SetMetadata) -> None:
    path = metadata_path(cache_directory, metadata.set_num)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".json.tmp")
    data = {
        "set_num": metadata.set_num,
        "name": metadata.name,
        "image_url": metadata.image_url,
        "year": metadata.year,
        "num_parts": metadata.num_parts,
    }
    try:
        temporary.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        temporary.replace(path)
    except OSError as exc:
        temporary.unlink(missing_ok=True)
        raise SetMetadataError("Set metadata could not be cached.") from exc


def cached_set_preview(cache_directory: Path, set_num: str) -> Path | None:
    path = preview_path(cache_directory, set_num)
    return path if path.is_file() else None


def fetch_set_preview(cache_directory: Path, metadata: SetMetadata) -> Path:
    cached = cached_set_preview(cache_directory, metadata.set_num)
    if cached:
        return cached
    if not metadata.image_url:
        raise SetMetadataError("No set image available.")
    parsed = urlparse(metadata.image_url)
    if parsed.scheme != "https" or parsed.hostname not in ALLOWED_IMAGE_HOSTS:
        raise SetMetadataError("No set image available.")
    request = Request(metadata.image_url, headers={"User-Agent": f"lego-element-lookup/{__version__}"})
    try:
        with urlopen(request, timeout=15) as response:
            final = urlparse(response.geturl() if hasattr(response, "geturl") else metadata.image_url)
            if final.scheme != "https" or final.hostname not in ALLOWED_IMAGE_HOSTS:
                raise SetMetadataError("No set image available.")
            if response.headers.get_content_type() not in {"image/jpeg", "image/png", "image/webp"}:
                raise SetMetadataError("No set image available.")
            payload = response.read(MAX_IMAGE_BYTES + 1)
    except SetMetadataError:
        raise
    except (HTTPError, URLError, TimeoutError, OSError):
        raise SetMetadataError("Set image unavailable offline.") from None
    if len(payload) > MAX_IMAGE_BYTES:
        raise SetMetadataError("Set image is unexpectedly large.")
    try:
        with Image.open(io.BytesIO(payload)) as source:
            width, height = source.size
            if width <= 0 or height <= 0 or width * height > MAX_IMAGE_PIXELS:
                raise SetMetadataError("No set image available.")
            source.load()
            image = source.convert("RGBA")
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError):
        raise SetMetadataError("No set image available.") from None
    image.thumbnail(THUMBNAIL_SIZE, Image.Resampling.LANCZOS)
    destination = preview_path(cache_directory, metadata.set_num)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(".png.tmp")
    try:
        image.save(temporary, format="PNG", optimize=True)
        temporary.replace(destination)
    except OSError as exc:
        temporary.unlink(missing_ok=True)
        raise SetMetadataError("Set image could not be cached.") from exc
    return destination
