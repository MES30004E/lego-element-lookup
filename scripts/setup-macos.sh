#!/bin/sh
set -eu
python3 -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else "Python 3.10 or newer is required.")'
python3 -m venv .venv
. .venv/bin/activate
python -m pip install .
CONFIG_DIR="$HOME/Library/Application Support/lego-element-lookup"
CACHE_DIR="$HOME/Library/Caches/lego-element-lookup"
mkdir -p "$CONFIG_DIR" "$CACHE_DIR"
if [ ! -f "$CONFIG_DIR/config.json" ]; then cp config.example.json "$CONFIG_DIR/config.json"; fi
echo "Edit $CONFIG_DIR/config.json and replace YOUR_API_KEY_HERE with your Rebrickable API key."
printf "Download set 76344-1 now after editing the config? [y/N] "
read -r answer
case "$answer" in [Yy]*) lego-lookup download 76344-1 ;; esac
echo "Start with: . .venv/bin/activate && lego-lookup"
