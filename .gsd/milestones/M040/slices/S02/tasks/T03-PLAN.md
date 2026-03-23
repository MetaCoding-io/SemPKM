---
estimated_steps: 3
estimated_files: 12
---

# T03: Audit and fix cross-references

**Slice:** S02 — Orphan Chapter Integration & Renumbering
**Milestone:** M040

## Description

Audit all markdown cross-references between guide chapters to ensure none are broken by the renumbering. Fix any references in the renamed orphan files that point to old chapter numbers, and check existing chapters for any references to the orphan content.

## Steps

1. Grep all guide `.md` files for markdown links pointing to other guide files: `grep -rn '\[.*\](.*\.md)' docs/guide/*.md`
2. For each link, verify the target file exists on disk. Flag any broken links.
3. Check the 9 renamed files for internal references to other chapters — update any that use old chapter numbers in link text (e.g., "See Chapter 29" → "See Chapter 39" in the mental model catalog file)

## Must-Haves

- [ ] All markdown cross-references resolve to existing files
- [ ] Renamed files' internal references use correct chapter numbers
- [ ] No "Chapter NN" text references point to non-existent chapter numbers

## Verification

- `grep -rn '\[.*\](.*\.md)' docs/guide/*.md | while IFS= read -r line; do file=$(echo "$line" | grep -oP '\]\(\K[^)]+'); [ -f "docs/guide/$file" ] || echo "BROKEN: $line"; done` returns no BROKEN lines
- `grep -rn 'Chapter [0-9]' docs/guide/*.md` — manual spot-check that all referenced numbers correspond to real files

## Inputs

- All `docs/guide/*.md` files — checking cross-references

## Expected Output

- Any modified guide files with fixed cross-references (may be zero changes if no references were broken)
