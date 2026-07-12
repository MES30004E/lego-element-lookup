#!/bin/sh
set -eu
VERSION="${1:?version required}"
ARCH="${2:?architecture required}"
APP="dist/LEGO Element Lookup.app"
OUTPUT="dist/LEGO-Element-Lookup-v${VERSION}-macOS-${ARCH}.dmg"
STAGING="build/dmg"
rm -rf "$STAGING"
mkdir -p "$STAGING"
cp -R "$APP" "$STAGING/"
ln -s /Applications "$STAGING/Applications"
hdiutil create -volname "LEGO Element Lookup" -srcfolder "$STAGING" -ov -format UDZO "$OUTPUT"
echo "$OUTPUT"
