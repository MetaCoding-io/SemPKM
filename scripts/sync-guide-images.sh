#!/usr/bin/env bash
# Sync e2e screenshots into docs/guide/images/ for the user guide.
# Copies light-mode variants only (skips *-dark.png), plus the two
# dark-only shots (11-dark-mode, 12-dark-mode-graph).
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SRC="$REPO_ROOT/e2e/screenshots"
DST="$REPO_ROOT/docs/guide/images"

mkdir -p "$DST"

copied=0
for f in "$SRC"/*.png; do
  name="$(basename "$f")"
  # Skip dark variants (but keep 11-dark-mode.png and 12-dark-mode-graph.png which have no light version)
  if [[ "$name" == *-dark.png && "$name" != "11-dark-mode.png" && "$name" != "12-dark-mode-graph.png" ]]; then
    continue
  fi
  cp "$f" "$DST/$name"
  copied=$((copied + 1))
done

echo "Synced $copied screenshots to docs/guide/images/"
