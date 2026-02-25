#!/bin/bash
# Generate full (uncompressed) repo map for AI consumption
# Output: .meta/output/repomix-output.xml
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
META_DIR="$(dirname "$SCRIPT_DIR")"
REPO_DIR="$(dirname "$META_DIR")"

echo "==> Generating full repo map..."
docker run --rm \
  -v "$REPO_DIR":/app/repo \
  -v "$META_DIR/output":/app/output \
  -v "$META_DIR/repomix.config.json":/app/repomix.config.json:ro \
  -w /app/repo \
  ghcr.io/yamadashy/repomix \
  --config /app/repomix.config.json \
  .

echo "==> Done. Output at: .meta/output/repomix-output.xml"
echo "==> Token count tree:"
docker run --rm \
  -v "$REPO_DIR":/app/repo \
  -v "$META_DIR/output":/app/output \
  -w /app/repo \
  ghcr.io/yamadashy/repomix \
  --token-count-tree \
  --config /app/repomix.config.json \
  . 2>&1 | tail -30
