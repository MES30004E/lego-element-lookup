"""Safe, bounded local cache for Rebrickable part thumbnails."""

from __future__ import annotations

import hashlib
import io
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from PIL import Image, UnidentifiedImageError

ALLOWED_IMAGE_HOSTS = {"cdn.rebrickable.com"}
MAX_IMAGE_BYTES = 5 * 1024 * 1024
MAX_IMAGE_PIXELS = 16_000_000
THUMBNAIL_SIZE = (360, 260)


class PreviewError(RuntimeError):
    """A safe user-facing part preview failure."""


class PreviewCache:
    def __init__(self, cache_directory: Path) -> None:
        self.directory = cache_directory / "previews"

    def path_for(self, url: str) -> Path:
        digest = hashlib.sha256(url.encode("utf-8")).hexdigest()
        return self.directory / f"{digest}.png"

    def cached(self, url: str | None) -> Path | None:
        if not url:
            return None
        path = self.path_for(url)
        return path if path.is_file() else None

    def fetch(self, url: str | None) -> Path:
        if not url:
            raise PreviewError("No preview available")
        cached = self.cached(url)
        if cached:
            return cached
        parsed = urlparse(url)
        if parsed.scheme != "https" or parsed.hostname not in ALLOWED_IMAGE_HOSTS:
            raise PreviewError("No preview available")
        request = Request(url, headers={"User-Agent": "lego-element-lookup/1.2"})
        try:
            with urlopen(request, timeout=15) as response:
                final_url = response.geturl() if hasattr(response, "geturl") else url
                final_parsed = urlparse(final_url)
                if final_parsed.scheme != "https" or final_parsed.hostname not in ALLOWED_IMAGE_HOSTS:
                    raise PreviewError("No preview available")
                content_type = response.headers.get_content_type()
                if content_type not in {"image/jpeg", "image/png", "image/webp"}:
                    raise PreviewError("No preview available")
                payload = response.read(MAX_IMAGE_BYTES + 1)
        except PreviewError:
            raise
        except (HTTPError, URLError, TimeoutError, OSError):
            raise PreviewError("Preview unavailable offline") from None
        if len(payload) > MAX_IMAGE_BYTES:
            raise PreviewError("No preview available")
        try:
            with Image.open(io.BytesIO(payload)) as source:
                width, height = source.size
                if width <= 0 or height <= 0 or width * height > MAX_IMAGE_PIXELS:
                    raise PreviewError("No preview available")
                source.load()
                image = source.convert("RGBA")
        except (UnidentifiedImageError, OSError, Image.DecompressionBombError):
            raise PreviewError("No preview available") from None
        image.thumbnail(THUMBNAIL_SIZE, Image.Resampling.LANCZOS)
        self.directory.mkdir(parents=True, exist_ok=True)
        destination = self.path_for(url)
        temporary = destination.with_suffix(".png.tmp")
        try:
            image.save(temporary, format="PNG", optimize=True)
            temporary.replace(destination)
        except OSError as exc:
            temporary.unlink(missing_ok=True)
            raise PreviewError("Preview could not be cached") from exc
        return destination
