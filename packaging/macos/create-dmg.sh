#!/bin/sh
set -eu

VERSION="${1:?version required}"
ARCH="${2:?architecture required}"
APP="${APP:-dist/LEGO Element Lookup.app}"
OUTPUT_DIR="${OUTPUT_DIR:-dist}"
OUTPUT="$OUTPUT_DIR/LEGO-Element-Lookup-v${VERSION}-macOS-${ARCH}.dmg"
VOLUME_LABEL="LEGO Element Lookup"
MAX_ATTEMPTS=3
PYTHON="${PYTHON:-python3}"
TMP_BASE="${TMPDIR:-/tmp}"
WORK_DIR="$(mktemp -d "${TMP_BASE%/}/lego-element-lookup-dmg-${ARCH}.XXXXXX")"
TEMP_DMG="$WORK_DIR/LEGO-Element-Lookup-v${VERSION}-macOS-${ARCH}.working.dmg"
MOUNTS_FILE="$WORK_DIR/owned-mounts.txt"
INFO_FILE="$WORK_DIR/hdiutil-info.plist"

detach_owned_mounts() {
    : > "$MOUNTS_FILE"
    if ! hdiutil info -plist > "$INFO_FILE" 2>/dev/null; then
        echo "Warning: could not inspect existing disk images; continuing with isolated paths." >&2
        return
    fi
    if ! python3 - "$INFO_FILE" "$OUTPUT" "$TEMP_DMG" "$WORK_DIR" > "$MOUNTS_FILE" <<'PY'
import os
import plistlib
import sys

info_file = sys.argv[1]
output, temporary, work_dir = (os.path.abspath(value) for value in sys.argv[2:])
try:
    with open(info_file, "rb") as stream:
        data = plistlib.load(stream)
except Exception:
    raise SystemExit(0)

for image in data.get("images", []):
    image_path = image.get("image-path")
    if not image_path:
        continue
    image_path = os.path.abspath(image_path)
    owned = image_path in {output, temporary} or image_path.startswith(work_dir + os.sep)
    if not owned:
        continue
    for entity in image.get("system-entities", []):
        device = entity.get("dev-entry")
        mount_point = entity.get("mount-point", "")
        if device and os.path.basename(mount_point).startswith("LEGO Element Lookup"):
            print(device)
PY
    then
        echo "Warning: could not inspect existing disk images; continuing with isolated paths." >&2
        : > "$MOUNTS_FILE"
    fi

    while IFS= read -r device; do
        [ -n "$device" ] || continue
        echo "Detaching stale LEGO Element Lookup image at $device"
        hdiutil detach "$device" >/dev/null 2>&1 || hdiutil detach -force "$device" >/dev/null 2>&1 || true
    done < "$MOUNTS_FILE"
}

cleanup() {
    status=$?
    trap - EXIT HUP INT TERM
    set +e
    detach_owned_mounts
    rm -f "$TEMP_DMG"
    rm -rf "$WORK_DIR"
    exit "$status"
}
trap cleanup EXIT HUP INT TERM

if [ ! -d "$APP" ]; then
    echo "Application bundle not found: $APP" >&2
    exit 1
fi

BACKGROUND="${DMG_BACKGROUND:-assets/dmg/background@2x.png}"
if [ ! -f "$BACKGROUND" ]; then
    echo "DMG background not found: $BACKGROUND. Run python assets/generate_icons.py first." >&2
    exit 1
fi

detach_owned_mounts
mkdir -p "$OUTPUT_DIR"
rm -f "$OUTPUT"
find "$OUTPUT_DIR" -maxdepth 1 -type f -name "$(basename "$OUTPUT").tmp-*" -exec rm -f {} \;

attempt=1
while [ "$attempt" -le "$MAX_ATTEMPTS" ]; do
    rm -f "$TEMP_DMG"
    echo "Creating macOS DMG (attempt $attempt of $MAX_ATTEMPTS)…"
    if DMG_APPLICATION="$APP" DMG_BACKGROUND="$BACKGROUND" \
        "$PYTHON" -m dmgbuild -s packaging/macos/dmg_settings.py "$VOLUME_LABEL" "$TEMP_DMG"; then
        mv "$TEMP_DMG" "$OUTPUT"
        echo "$OUTPUT"
        exit 0
    fi

    echo "hdiutil create failed on attempt $attempt." >&2
    detach_owned_mounts
    if [ "$attempt" -eq "$MAX_ATTEMPTS" ]; then
        echo "DMG creation failed after $MAX_ATTEMPTS attempts." >&2
        exit 1
    fi
    delay=$((attempt * 2))
    echo "Retrying in ${delay} seconds with a clean temporary image…" >&2
    sleep "$delay"
    attempt=$((attempt + 1))
done
