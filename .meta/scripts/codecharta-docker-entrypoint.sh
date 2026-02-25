#!/bin/bash
# CodeCharta analysis entrypoint — runs inside the codecharta-analysis container
# Generates metrics from git history, Tokei, and raw text, then merges results
set -euo pipefail

OUTPUT="/mnt/output"
REPO="/mnt/repo"
mkdir -p "$OUTPUT"

echo "==> Step 1: Generating git log..."
git -C "$REPO" log --numstat --raw --topo-order > "$OUTPUT/git.log" 2>/dev/null || {
  echo "    WARN: git log failed (repo may not have .git mounted). Skipping git analysis."
}

if [ -f "$OUTPUT/git.log" ] && [ -s "$OUTPUT/git.log" ]; then
  echo "==> Step 2: Running git log parser..."
  ccsh gitlogparser log-scan \
    --git-log "$OUTPUT/git.log" \
    --repo-path "$REPO" \
    --output-file "$OUTPUT/gitlog-analysis.cc.json" || true
fi

echo "==> Step 3: Running Tokei source code metrics..."
ccsh tokeiimporter \
  "$REPO" \
  --output-file "$OUTPUT/tokei-analysis.cc.json" || true

echo "==> Step 4: Running raw text parser..."
ccsh rawtextparser \
  "$REPO" \
  --output-file "$OUTPUT/rawtext-analysis.cc.json" || true

echo "==> Step 5: Merging all results..."
# Collect all generated files for merge
MERGE_FILES=""
for f in "$OUTPUT"/gitlog-analysis.cc.json* "$OUTPUT"/tokei-analysis.cc.json* "$OUTPUT"/rawtext-analysis.cc.json*; do
  [ -f "$f" ] && MERGE_FILES="$MERGE_FILES $f"
done

if [ -n "$MERGE_FILES" ]; then
  ccsh merge $MERGE_FILES --output-file "$OUTPUT/sempkm-merged.cc.json" || true
  echo ""
  echo "==> Analysis complete! Output files:"
  ls -lh "$OUTPUT"/*.cc.json* 2>/dev/null || echo "    (no output files found)"
  echo ""
  echo "    Open http://localhost:9100 and upload sempkm-merged.cc.json.gz"
else
  echo "==> ERROR: No analysis files were generated."
  exit 1
fi
