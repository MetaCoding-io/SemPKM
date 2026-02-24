#!/bin/bash
# Analyze the SemPKM repository with CodeCharta
# Generates .cc.json files that can be loaded into CodeCharta Web Studio
# Runs: git log parser, source code metrics (via Tokei), and merges results
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
META_DIR="$(dirname "$SCRIPT_DIR")"
REPO_DIR="$(dirname "$META_DIR")"
OUTPUT_DIR="$META_DIR/output/codecharta"

mkdir -p "$OUTPUT_DIR"

echo "==> Step 1: Generating git log for analysis..."
git -C "$REPO_DIR" log --numstat --raw --topo-order > "$OUTPUT_DIR/git.log"

echo "==> Step 2: Running CodeCharta git log parser..."
docker run --rm \
  -v "$REPO_DIR":/mnt/repo:ro \
  -v "$OUTPUT_DIR":/mnt/output \
  codecharta/codecharta-analysis \
  ccsh gitlogparser log-scan \
    --git-log /mnt/output/git.log \
    --repo-path /mnt/repo \
    --output-file /mnt/output/gitlog-analysis.cc.json

echo "==> Step 3: Running source code metrics (Tokei)..."
docker run --rm \
  -v "$REPO_DIR":/mnt/repo:ro \
  -v "$OUTPUT_DIR":/mnt/output \
  codecharta/codecharta-analysis \
  ccsh tokeiimporter \
    /mnt/repo \
    --output-file /mnt/output/tokei-analysis.cc.json

echo "==> Step 4: Running raw source code structure parser..."
docker run --rm \
  -v "$REPO_DIR":/mnt/repo:ro \
  -v "$OUTPUT_DIR":/mnt/output \
  codecharta/codecharta-analysis \
  ccsh rawtextparser \
    /mnt/repo \
    --output-file /mnt/output/rawtext-analysis.cc.json

echo "==> Step 5: Merging all analysis results..."
docker run --rm \
  -v "$OUTPUT_DIR":/mnt/output \
  codecharta/codecharta-analysis \
  ccsh merge \
    /mnt/output/gitlog-analysis.cc.json.gz \
    /mnt/output/tokei-analysis.cc.json.gz \
    /mnt/output/rawtext-analysis.cc.json.gz \
    --output-file /mnt/output/sempkm-merged.cc.json

echo ""
echo "==> Analysis complete!"
echo "    Output files in: .meta/output/codecharta/"
echo ""
echo "    To visualize, either:"
echo "    1. Run: docker compose -f .meta/docker-compose.yml up codecharta-web"
echo "       Then open http://localhost:9100 and upload sempkm-merged.cc.json.gz"
echo "    2. Go to https://codecharta.com and upload the file directly"
