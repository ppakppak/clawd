#!/usr/bin/env bash
set -euo pipefail

CONFIG="$HOME/.config/terminator/config"
LAYOUT="openclaw-split"

if ! command -v terminator >/dev/null 2>&1; then
  echo "[ERR] terminator not found"
  exit 1
fi

if ! terminator --list-layouts 2>/dev/null | grep -qx "$LAYOUT"; then
  echo "[ERR] layout '$LAYOUT' not found in $CONFIG"
  exit 1
fi

exec terminator -g "$CONFIG" -l "$LAYOUT"
