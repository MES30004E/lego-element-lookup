from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_bundle_size_reporter_writes_text_and_json(tmp_path):
    frozen = tmp_path / "LEGO Element Lookup.app"
    (frozen / "Contents" / "Frameworks").mkdir(parents=True)
    (frozen / "Contents" / "Frameworks" / "runtime.bin").write_bytes(b"x" * 20)
    (frozen / "Contents" / "Info.plist").write_bytes(b"y" * 5)
    archive = tmp_path / "LEGO-Element-Lookup.dmg"
    archive.write_bytes(b"z" * 10)
    output = tmp_path / "report.json"

    result = subprocess.run(
        [
            sys.executable,
            "tools/report_bundle_size.py",
            str(frozen),
            "--archive",
            str(archive),
            "--json",
            str(output),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    report = json.loads(output.read_text(encoding="utf-8"))
    assert "Frozen total: 25 B" in result.stdout
    assert report["bundle_type"] == "macos_app"
    assert report["total_bytes"] == 25
    assert report["archives"] == [{"path": str(archive), "bytes": 10}]
