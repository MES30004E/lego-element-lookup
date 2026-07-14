#!/bin/sh
set -eu
VERSION="${1:?version required}"
APPDIR="build/LEGO-Element-Lookup.AppDir"
DESKTOP_ID="io.github.mes30004e.lego-element-lookup"
rm -rf "$APPDIR"
mkdir -p "$APPDIR/usr/bin" "$APPDIR/usr/share/metainfo"
cp -R "dist/LEGO Element Lookup/." "$APPDIR/usr/bin/"
cp packaging/linux/AppRun "$APPDIR/AppRun"
cp packaging/linux/lego-element-lookup "$APPDIR/usr/bin/lego-element-lookup"
cp "packaging/linux/${DESKTOP_ID}.desktop" "$APPDIR/${DESKTOP_ID}.desktop"
sed "s/@VERSION@/${VERSION}/g" "packaging/linux/${DESKTOP_ID}.metainfo.xml" > "$APPDIR/usr/share/metainfo/${DESKTOP_ID}.metainfo.xml"
for size in 16 32 48 64 128 256 512; do
    target="$APPDIR/usr/share/icons/hicolor/${size}x${size}/apps"
    mkdir -p "$target"
    cp "assets/linux/icons/${size}x${size}/${DESKTOP_ID}.png" "$target/${DESKTOP_ID}.png"
done
cp "assets/linux/icons/256x256/${DESKTOP_ID}.png" "$APPDIR/${DESKTOP_ID}.png"
chmod +x "$APPDIR/AppRun" "$APPDIR/usr/bin/LEGO Element Lookup" "$APPDIR/usr/bin/lego-element-lookup"
ARCH=x86_64 appimagetool "$APPDIR" "dist/LEGO-Element-Lookup-v${VERSION}-Linux-x86_64.AppImage"
tar -C dist -czf "dist/LEGO-Element-Lookup-v${VERSION}-Linux-x86_64.tar.gz" "LEGO Element Lookup"
