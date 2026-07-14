"""Safe, bounded local cache for Rebrickable part thumbnails."""

from __future__ import annotations

import hashlib
import io
import json
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from PIL import Image, UnidentifiedImageError

from . import __version__
ALLOWED_IMAGE_HOSTS = {"cdn.rebrickable.com"}
MAX_IMAGE_BYTES = 5 * 1024 * 1024
MAX_IMAGE_PIXELS = 16_000_000
THUMBNAIL_SIZE = (360, 260)


class PreviewError(RuntimeError):
    """A safe user-facing part preview failure with a stable state code."""
    def __init__(self, message: str, state: str = "failed") -> None:
        super().__init__(message)
        self.state = state


class PreviewCache:
    def __init__(self, cache_directory: Path) -> None:
        self.directory = cache_directory / "previews"
        self.metadata_path = self.directory / "metadata.json"

    def path_for(self, url: str) -> Path:
        digest = hashlib.sha256(url.encode("utf-8")).hexdigest()
        return self.directory / f"{digest}.png"

    def cached(self, url: str | None) -> Path | None:
        if not url:
            return None
        path = self.path_for(url)
        if path.is_file():
            self._touch(url, path)
            return path
        return None

    def status(self, url: str | None) -> str:
        if not url:
            return "no_url"
        return "cached" if self.path_for(url).is_file() else "not_cached"

    def size_bytes(self) -> int:
        return sum(path.stat().st_size for path in self.directory.glob("*.png") if path.is_file()) if self.directory.exists() else 0

    def clear(self) -> None:
        if not self.directory.exists(): return
        for path in self.directory.glob("*.png"):
            path.unlink(missing_ok=True)
        self.metadata_path.unlink(missing_ok=True)

    def enforce_limit(self, limit_mb: int, eviction: str = "oldest") -> int:
        """Evict only part previews; intended for a background worker."""
        if eviction == "never": return 0
        limit = max(0, limit_mb) * 1024 * 1024
        entries = self._metadata()
        files = [(path, entries.get(path.name, {}).get("last_access", 0.0)) for path in self.directory.glob("*.png")]
        total = sum(path.stat().st_size for path, _ in files if path.exists())
        removed = 0
        for path, _ in sorted(files, key=lambda value: value[1]):
            if total <= limit: break
            size = path.stat().st_size if path.exists() else 0
            path.unlink(missing_ok=True); entries.pop(path.name, None); total -= size; removed += 1
        self._write_metadata(entries)
        return removed

    def _metadata(self) -> dict[str, dict[str, object]]:
        try:
            data = json.loads(self.metadata_path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
        except (OSError, json.JSONDecodeError):
            return {}

    def _write_metadata(self, data: dict[str, dict[str, object]]) -> None:
        self.directory.mkdir(parents=True, exist_ok=True)
        temporary = self.metadata_path.with_suffix(".tmp")
        temporary.write_text(json.dumps(data, sort_keys=True), encoding="utf-8")
        temporary.replace(self.metadata_path)

    def _touch(self, url: str, path: Path) -> None:
        entries = self._metadata(); entries[path.name] = {"url": url, "last_access": time.time()}
        try: self._write_metadata(entries)
        except OSError: pass

    def fetch(self, url: str | None) -> Path:
        if not url:
            raise PreviewError("No preview available", "no_url")
        cached = self.cached(url)
        if cached:
            return cached
        parsed = urlparse(url)
        if parsed.scheme != "https" or parsed.hostname not in ALLOWED_IMAGE_HOSTS:
            raise PreviewError("No preview available: URL is not trusted", "untrusted")
        request = Request(url, headers={"User-Agent": f"lego-element-lookup/{__version__}"})
        try:
            with urlopen(request, timeout=15) as response:
                final_url = response.geturl() if hasattr(response, "geturl") else url
                final_parsed = urlparse(final_url)
                if final_parsed.scheme != "https" or final_parsed.hostname not in ALLOWED_IMAGE_HOSTS:
                    raise PreviewError("No preview available: URL is not trusted", "untrusted")
                content_type = response.headers.get_content_type()
                if content_type not in {"image/jpeg", "image/png", "image/webp"}:
                    raise PreviewError("Preview data is invalid", "invalid")
                payload = response.read(MAX_IMAGE_BYTES + 1)
        except PreviewError:
            raise
        except TimeoutError:
            raise PreviewError("Preview request timed out", "timed_out") from None
        except URLError as exc:
            reason = getattr(exc, "reason", None)
            if isinstance(reason, OSError) and getattr(reason, "errno", None) in {101, 113}:
                raise PreviewError("Preview unavailable while offline", "offline") from None
            raise PreviewError("Preview could not be downloaded", "download_failed") from None
        except (HTTPError, OSError):
            raise PreviewError("Preview could not be downloaded", "download_failed") from None
        if len(payload) > MAX_IMAGE_BYTES:
            raise PreviewError("Preview image is too large", "invalid")
        try:
            with Image.open(io.BytesIO(payload)) as source:
                width, height = source.size
                if width <= 0 or height <= 0 or width * height > MAX_IMAGE_PIXELS:
                    raise PreviewError("Preview data is invalid", "invalid")
                source.load()
                image = source.convert("RGBA")
        except (UnidentifiedImageError, OSError, Image.DecompressionBombError):
            raise PreviewError("Preview data is invalid", "invalid") from None
        image.thumbnail(THUMBNAIL_SIZE, Image.Resampling.LANCZOS)
        self.directory.mkdir(parents=True, exist_ok=True)
        destination = self.path_for(url)
        temporary = destination.with_suffix(".png.tmp")
        try:
            image.save(temporary, format="PNG", optimize=True)
            temporary.replace(destination)
        except OSError as exc:
            temporary.unlink(missing_ok=True)
            raise PreviewError("Preview could not be cached", "cache_failed") from exc
        self._touch(url, destination)
        return destination
