#!/usr/bin/env python3
"""Report frozen desktop bundle sizes without requiring platform-specific tools.

Examples:
    python tools/report_bundle_size.py "dist/LEGO Element Lookup.app" \
        --archive dist/LEGO-Element-Lookup-v1.4.0-macOS-arm64.dmg \
        --json build/bundle-size-macos-arm64.json
    python tools/report_bundle_size.py dist/LEGO-Element-Lookup.AppDir --json build/linux.json
    python tools/report_bundle_size.py dist/LEGO-Element-Lookup.AppImage --json build/linux-appimage.json
"""

from __future__ import annotations

import argparse
import json
import subprocess
import tempfile
from collections import defaultdict
from pathlib import Path
from typing import Any


def human_size(size: int) -> str:
    value = float(size)
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if value < 1024 or unit == "TiB":
            return f"{value:.1f} {unit}" if unit != "B" else f"{int(value)} B"
        value /= 1024
    raise AssertionError("unreachable")


def classify(path: Path) -> str:
    if path.suffix == ".AppImage":
        return "appimage"
    if path.suffix == ".app":
        return "macos_app"
    if path.name.endswith(".AppDir"):
        return "linux_appdir"
    return "frozen_directory"


def directory_report(path: Path) -> dict[str, Any]:
    files: list[tuple[Path, int]] = []
    groups: defaultdict[str, int] = defaultdict(int)
    for file_path in path.rglob("*"):
        if file_path.is_symlink():
            size = file_path.lstat().st_size
        elif file_path.is_file():
            size = file_path.stat().st_size
        else:
            continue
        files.append((file_path, size))
        relative = file_path.relative_to(path)
        top_level = relative.parts[0] if len(relative.parts) > 1 else "."
        groups[top_level] += size
    files.sort(key=lambda item: (-item[1], str(item[0])))
    return {
        "frozen_directory": str(path),
        "total_bytes": sum(size for _, size in files),
        "top_level_directories": [
            {"name": name, "bytes": size}
            for name, size in sorted(groups.items(), key=lambda item: (-item[1], item[0]))
        ],
        "largest_files": [
            {"path": str(file_path.relative_to(path)), "bytes": size}
            for file_path, size in files[:50]
        ],
    }


def extract_appimage(path: Path) -> tuple[dict[str, Any], Path]:
    with tempfile.TemporaryDirectory(prefix="lego-element-lookup-appimage-") as temporary:
        temporary_path = Path(temporary)
        try:
            subprocess.run(
                [str(path.resolve()), "--appimage-extract"],
                cwd=temporary_path,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
        except (OSError, subprocess.CalledProcessError) as exc:
            details = exc.stderr.strip() if isinstance(exc, subprocess.CalledProcessError) and exc.stderr else str(exc)
            raise RuntimeError(f"Could not extract AppImage {path}: {details}") from exc
        extracted = temporary_path / "squashfs-root"
        if not extracted.is_dir():
            raise RuntimeError(f"AppImage extraction did not create {extracted}.")
        report = directory_report(extracted)
    return report, path


def add_archives(report: dict[str, Any], archives: list[Path]) -> None:
    report["archives"] = [
        {"path": str(path), "bytes": path.stat().st_size}
        for path in archives
    ]


def format_report(report: dict[str, Any]) -> str:
    lines = [
        f"Bundle type: {report['bundle_type']}",
        f"Frozen directory: {report['frozen_directory']}",
        f"Frozen total: {human_size(report['total_bytes'])} ({report['total_bytes']} bytes)",
        "",
        "Top-level directories:",
    ]
    lines.extend(f"  {entry['name']}: {human_size(entry['bytes'])}" for entry in report["top_level_directories"])
    lines.extend(["", "Largest files (top 50):"])
    lines.extend(
        f"  {human_size(entry['bytes']):>10}  {entry['path']}" for entry in report["largest_files"]
    )
    if report["archives"]:
        lines.extend(["", "Final archives/installers:"])
        lines.extend(
            f"  {human_size(entry['bytes']):>10}  {entry['path']}" for entry in report["archives"]
        )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("target", type=Path, help="Frozen directory, .app bundle, AppDir, or AppImage")
    parser.add_argument("--archive", type=Path, action="append", default=[], help="Final installer/archive to measure")
    parser.add_argument("--json", type=Path, required=True, help="Write machine-readable JSON report here")
    args = parser.parse_args(argv)

    target = args.target
    if not target.exists():
        parser.error(f"target does not exist: {target}")
    missing_archives = [path for path in args.archive if not path.is_file()]
    if missing_archives:
        parser.error(f"archive does not exist: {missing_archives[0]}")

    bundle_type = classify(target)
    if bundle_type == "appimage":
        report, _ = extract_appimage(target)
    elif target.is_dir():
        report = directory_report(target)
    else:
        parser.error("target must be a directory, .app bundle, AppDir, or AppImage")
    report["bundle_type"] = bundle_type
    add_archives(report, args.archive)
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(format_report(report))
    print(f"\nJSON report: {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
