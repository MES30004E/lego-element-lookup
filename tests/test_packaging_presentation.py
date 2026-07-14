"""Static checks for reproducible desktop-installer presentation assets."""

from __future__ import annotations

import subprocess
import sys
import tomllib
import xml.etree.ElementTree as ET
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DESKTOP_ID = "io.github.mes30004e.lego-element-lookup"


def package_version() -> str:
    with (ROOT / "pyproject.toml").open("rb") as stream:
        return tomllib.load(stream)["project"]["version"]


def test_generated_packaging_artwork_has_required_outputs():
    subprocess.run([sys.executable, "assets/generate_icons.py"], cwd=ROOT, check=True)
    required = [
        ROOT / "assets/dmg/background.png",
        ROOT / "assets/dmg/background@2x.png",
        ROOT / "assets/installer/windows/wizard-large.bmp",
        ROOT / "assets/installer/windows/wizard-small.bmp",
    ]
    required.extend(
        ROOT / f"assets/linux/icons/{size}x{size}/{DESKTOP_ID}.png"
        for size in (16, 32, 48, 64, 128, 256, 512)
    )
    assert all(path.is_file() and path.stat().st_size > 0 for path in required)


def test_macos_dmg_settings_define_a_clean_drag_install_layout():
    settings = (ROOT / "packaging/macos/dmg_settings.py").read_text(encoding="utf-8")
    script = (ROOT / "packaging/macos/create-dmg.sh").read_text(encoding="utf-8")
    assert '"Applications": "/Applications"' in settings
    assert '"LEGO Element Lookup.app": (180, 250)' in settings
    assert '"Applications": (540, 250)' in settings
    assert "show_toolbar = False" in settings
    assert "show_sidebar = False" in settings
    assert '"$PYTHON" -m dmgbuild' in script
    assert "MAX_ATTEMPTS=3" in script
    assert "detach_owned_mounts" in script


def test_pyinstaller_excludes_appledouble_sidecars_from_release_bundles():
    spec = (ROOT / "packaging/pyinstaller/lego-element-lookup.spec").read_text(encoding="utf-8")
    assert "without_appledouble" in spec
    assert "a.datas = without_appledouble(a.datas)" in spec
    assert "a.binaries = without_appledouble(a.binaries)" in spec


def test_windows_installer_preserves_per_user_upgrade_and_uninstall_behaviour():
    installer = (ROOT / "packaging/windows/installer.iss").read_text(encoding="utf-8")
    assert "AppId={{A252F0AE-799B-4930-81BE-7CE34EC725AE}" in installer
    assert "PrivilegesRequired=lowest" in installer
    assert "DefaultDirName={localappdata}\\Programs\\LEGO Element Lookup" in installer
    assert "SetupIconFile={#AppIcon}" in installer
    assert "WizardImageFile={#WizardLargeImage}" in installer
    assert "WizardSmallImageFile={#WizardSmallImage}" in installer
    assert "AppPublisher=" in installer and "AppSupportURL=" in installer and "AppUpdatesURL=" in installer
    assert "UninstallDisplayName={#AppName}" in installer
    assert "Name: \"desktopicon\"" in installer
    assert "Flags: nowait postinstall skipifsilent" in installer
    assert "CloseApplications=yes" in installer
    assert "force-close" in installer
    assert "DeleteType: filesandordirs" not in installer
    assert f'#define AppVersion "{package_version()}"' in installer


def test_linux_desktop_and_appstream_metadata_are_consistent():
    desktop = ROOT / f"packaging/linux/{DESKTOP_ID}.desktop"
    metadata = ROOT / f"packaging/linux/{DESKTOP_ID}.metainfo.xml"
    values = dict(
        line.split("=", 1)
        for line in desktop.read_text(encoding="utf-8").splitlines()
        if "=" in line and not line.startswith("#")
    )
    assert values["Type"] == "Application"
    assert values["Exec"] == "lego-element-lookup"
    assert values["Icon"] == DESKTOP_ID
    assert values["Terminal"] == "false"
    assert {"Utility", "Education"}.issubset(set(values["Categories"].split(";")))
    root = ET.parse(metadata).getroot()
    assert root.findtext("id") == DESKTOP_ID
    assert root.findtext("launchable") == f"{DESKTOP_ID}.desktop"
    assert root.find("releases/release").attrib["version"] == "@VERSION@"
    assert "LEGO Group" in metadata.read_text(encoding="utf-8")


def test_linux_appimage_stages_metadata_icons_and_version_substitution():
    script = (ROOT / "packaging/linux/build-appimage.sh").read_text(encoding="utf-8")
    assert 'DESKTOP_ID="io.github.mes30004e.lego-element-lookup"' in script
    assert 'sed "s/@VERSION@/${VERSION}/g"' in script
    assert "usr/share/metainfo" in script
    assert "usr/share/icons/hicolor/${size}x${size}/apps" in script
    assert '"$APPDIR/${DESKTOP_ID}.desktop"' in script
    assert '"$APPDIR/${DESKTOP_ID}.png"' in script
