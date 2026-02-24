#!/bin/bash
# Generate compressed repo map (~70% fewer tokens) for AI consumption
# Uses Tree-sitter to extract only essential code structures
# Output: .meta/output/repomix-compressed.xml
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
META_DIR="$(dirname "$SCRIPT_DIR")"
REPO_DIR="$(dirname "$META_DIR")"

echo "==> Generating compressed repo map (Tree-sitter extraction)..."
docker run --rm \
  -v "$REPO_DIR":/app/repo \
  -v "$META_DIR/output":/app/output \
  -v "$META_DIR/repomix-compressed.config.json":/app/repomix.config.json:ro \
  -w /app/repo \
  ghcr.io/yamadashy/repomix \
  --config /app/repomix.config.json \
  .

echo "==> Done. Output at: .meta/output/repomix-compressed.xml"
