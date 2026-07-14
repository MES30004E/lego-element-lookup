# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path
import sys
import tomllib

root = Path(SPECPATH).parents[1]
version = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]
icon = root / "assets" / ("icon.ico" if sys.platform == "win32" else "icon.icns" if sys.platform == "darwin" else "icon.png")

a = Analysis(
    [str(root / "packaging" / "desktop_entry.py")],
    pathex=[str(root / "src")],
    datas=[(str(root / "LICENSE"), "."), (str(root / "assets" / "icon.png"), "assets")],
    hiddenimports=["keyring.backends.macOS", "keyring.backends.Windows", "keyring.backends.SecretService"],
    excludes=["pytest"],
    noarchive=False,
)

# External-volume development environments can contain macOS AppleDouble
# sidecars. They are metadata debris, never runtime inputs, and must not enter
# release bundles on any platform.
def without_appledouble(entries):
    return [
        entry for entry in entries
        if not any(part.startswith("._") for part in entry[0].replace("\\", "/").split("/"))
    ]


a.datas = without_appledouble(a.datas)
a.binaries = without_appledouble(a.binaries)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="LEGO Element Lookup",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    icon=str(icon),
)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name="LEGO Element Lookup")

if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name="LEGO Element Lookup.app",
        icon=str(icon),
        bundle_identifier="com.mes30004e.lego-element-lookup",
        info_plist={
            "LSMinimumSystemVersion": "12.0",
            "NSHighResolutionCapable": True,
            "CFBundleShortVersionString": version,
            "CFBundleVersion": version,
        },
    )
