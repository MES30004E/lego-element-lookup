#!/bin/sh
set -eu
VERSION="${1:?version required}"
APPDIR="build/LEGO-Element-Lookup.AppDir"
rm -rf "$APPDIR"
mkdir -p "$APPDIR/usr/bin"
cp -R "dist/LEGO Element Lookup/." "$APPDIR/usr/bin/"
cp packaging/linux/AppRun "$APPDIR/AppRun"
cp packaging/linux/lego-element-lookup.desktop "$APPDIR/lego-element-lookup.desktop"
cp assets/icon.png "$APPDIR/lego-element-lookup.png"
chmod +x "$APPDIR/AppRun" "$APPDIR/usr/bin/LEGO Element Lookup"
ARCH=x86_64 appimagetool "$APPDIR" "dist/LEGO-Element-Lookup-v${VERSION}-Linux-x86_64.AppImage"
tar -C dist -czf "dist/LEGO-Element-Lookup-v${VERSION}-Linux-x86_64.tar.gz" "LEGO Element Lookup"
