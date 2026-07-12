"""Rebrickable inventory downloader."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

BASE_URL = "https://rebrickable.com/api/v3/lego/sets"


class DownloadError(RuntimeError):
    pass


def download_inventory(set_num: str, api_key: str, destination: Path) -> int:
    url: str | None = f"{BASE_URL}/{set_num}/parts/?page_size=1000&inc_part_details=1"
    results: list[dict[str, Any]] = []
    while url:
        request = Request(url, headers={"Authorization": f"key {api_key}", "User-Agent": "lego-element-lookup/1.0"})
        try:
            with urlopen(request, timeout=30) as response:
                page = json.load(response)
        except HTTPError as exc:
            message = "API key was rejected" if exc.code in (401, 403) else f"Rebrickable returned HTTP {exc.code}"
            raise DownloadError(f"Download failed: {message}.") from exc
        except (URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise DownloadError(f"Download failed: {exc}") from exc
        page_results = page.get("results") if isinstance(page, dict) else None
        if not isinstance(page_results, list):
            raise DownloadError("Download failed: Rebrickable returned an unexpected response.")
        results.extend(page_results)
        next_url = page.get("next")
        url = str(next_url) if next_url else None
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(".json.tmp")
    temporary.write_text(json.dumps({"set_num": set_num, "results": results}, indent=2), encoding="utf-8")
    temporary.replace(destination)
    return len(results)
