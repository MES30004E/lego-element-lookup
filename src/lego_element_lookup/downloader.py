"""Rebrickable inventory downloader."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from .lookup import validate_inventory_data

BASE_URL = "https://rebrickable.com/api/v3/lego/sets"
ALLOWED_HOST = "rebrickable.com"
MAX_RESPONSE_BYTES = 25 * 1024 * 1024


class DownloadError(RuntimeError):
    pass


class DownloadCancelled(DownloadError):
    pass


def _validate_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname != ALLOWED_HOST:
        raise DownloadError("Download failed: Rebrickable returned an unsafe pagination URL.")


def _request_json(url: str, api_key: str) -> dict[str, Any]:
    _validate_url(url)
    request = Request(url, headers={"Authorization": f"key {api_key}", "User-Agent": "lego-element-lookup/1.2"})
    try:
        with urlopen(request, timeout=30) as response:
            payload = response.read(MAX_RESPONSE_BYTES + 1)
    except HTTPError as exc:
        message = "API key was rejected" if exc.code in (401, 403) else f"Rebrickable returned HTTP {exc.code}"
        raise DownloadError(f"Download failed: {message}.") from None
    except (URLError, TimeoutError):
        raise DownloadError("Download failed: Rebrickable could not be reached.") from None
    if len(payload) > MAX_RESPONSE_BYTES:
        raise DownloadError("Download failed: Rebrickable returned an unexpectedly large response.")
    try:
        data = json.loads(payload)
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise DownloadError("Download failed: Rebrickable returned invalid JSON.") from None
    if not isinstance(data, dict):
        raise DownloadError("Download failed: Rebrickable returned an unexpected response.")
    return data


def test_connection(set_num: str, api_key: str) -> None:
    """Validate an API key and set without logging or returning the secret."""
    data = _request_json(f"{BASE_URL}/{set_num}/", api_key)
    if not data.get("set_num"):
        raise DownloadError("Connection succeeded, but the selected set was not recognised.")


def download_inventory(
    set_num: str,
    api_key: str,
    destination: Path,
    *,
    progress: Callable[[int, int], None] | None = None,
    cancelled: Callable[[], bool] | None = None,
) -> int:
    url: str | None = f"{BASE_URL}/{set_num}/parts/?page_size=1000&inc_part_details=1"
    results: list[dict[str, Any]] = []
    page_number = 0
    while url:
        if cancelled and cancelled():
            raise DownloadCancelled("Download cancelled.")
        page = _request_json(url, api_key)
        page_results = page.get("results") if isinstance(page, dict) else None
        if not isinstance(page_results, list) or not all(isinstance(item, dict) for item in page_results):
            raise DownloadError("Download failed: Rebrickable returned an unexpected response.")
        results.extend(page_results)
        page_number += 1
        if progress:
            progress(page_number, len(results))
        next_url = page.get("next")
        url = str(next_url) if next_url else None
        if url:
            _validate_url(url)
    payload = {"schema_version": 1, "set_num": set_num, "results": results}
    validate_inventory_data(payload)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(".json.tmp")
    try:
        temporary.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        temporary.replace(destination)
    except OSError as exc:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass
        raise DownloadError(f"Downloaded inventory could not be saved to {destination}.") from exc
    return len(results)
