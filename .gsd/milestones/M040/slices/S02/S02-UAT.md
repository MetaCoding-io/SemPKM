# S02 UAT: Orphan Chapter Integration & Renumbering

## Preconditions
- Access to the `docs/guide/` directory
- Access to `backend/app/templates/guide.html`

---

## Test 1: No Duplicate Chapter Numbers

**Steps:**
1. Run: `ls docs/guide/[0-9]*.md | sed 's/.*\///' | grep -oP '^\d+' | sort -n | uniq -d`

**Expected:** Empty output (zero duplicates).

---

## Test 2: All 9 Formerly-Orphaned Files Exist

**Steps:**
1. Verify each file exists:
   - `docs/guide/39-mental-model-catalog.md`
   - `docs/guide/40-rss-reader.md`
   - `docs/guide/41-google-calendar-sync.md`
   - `docs/guide/42-todoist-sync.md`
   - `docs/guide/43-outlook-calendar-sync.md`
   - `docs/guide/44-caldav-calendar-sync.md`
   - `docs/guide/45-notion-import.md`
   - `docs/guide/46-ai-features.md`
   - `docs/guide/47-asana-sync.md`

**Expected:** All 9 files exist on disk.

---

## Test 3: Old Orphan Filenames Are Gone

**Steps:**
1. Verify these files do NOT exist:
   - `docs/guide/29-mental-model-catalog.md`
   - `docs/guide/32-rss-reader.md`
   - `docs/guide/36-google-calendar-sync.md`
   - `docs/guide/37-todoist-sync.md` (Todoist, not Monday)
   - `docs/guide/38-outlook-calendar-sync.md` (Outlook, not Hosted Demo)
   - `docs/guide/39-caldav-calendar-sync.md`
   - `docs/guide/39-notion-import.md`
   - `docs/guide/40-ai-features.md`
   - `docs/guide/40-asana-sync.md`

**Expected:** None of the old-numbered orphan files exist. Note: `37-monday-sync.md`, `38-hosted-demo.md` should still exist (they were not orphans).

---

## Test 4: Internal Headings Match Filenames

**Steps:**
1. For each file 39–47, check the first heading line contains the correct chapter number:
   ```
   head -3 docs/guide/39-mental-model-catalog.md  → should contain "Chapter 39"
   head -3 docs/guide/40-rss-reader.md             → should contain "Chapter 40"
   ...
   head -3 docs/guide/47-asana-sync.md             → should contain "Chapter 47"
   ```

**Expected:** Every file's `# Chapter NN:` heading matches its filename number.

---

## Test 5: README.md Contains All 9 Orphan Entries

**Steps:**
1. Run: `grep -c 'mental-model-catalog\|rss-reader\|google-calendar-sync\|todoist-sync\|outlook-calendar-sync\|caldav-calendar-sync\|notion-import\|ai-features\|asana-sync' docs/guide/README.md`

**Expected:** 9 matches (one per orphan chapter).

---

## Test 6: index.html Contains All 9 Orphan Entries

**Steps:**
1. Run: `grep -c 'mental-model-catalog\|rss-reader\|google-calendar-sync\|todoist-sync\|outlook-calendar-sync\|caldav-calendar-sync\|notion-import\|ai-features\|asana-sync' docs/guide/index.html`

**Expected:** 9 matches.

---

## Test 7: guide.html Contains All 9 Orphan Entries

**Steps:**
1. Run: `grep -c 'mental-model-catalog\|rss-reader\|google-calendar-sync\|todoist-sync\|outlook-calendar-sync\|caldav-calendar-sync\|notion-import\|ai-features\|asana-sync' backend/app/templates/guide.html`

**Expected:** 9 matches.

---

## Test 8: Disk File Count Matches README Entry Count

**Steps:**
1. Run: `diff <(ls docs/guide/[0-9]*.md | sed 's/.*\///' | grep -oP '^\d+' | sort -n) <(grep -oP '\d+(?=-)' docs/guide/README.md | sort -n | uniq)`

**Expected:** No differences (empty diff output).

---

## Test 9: Zero Broken Cross-References

**Steps:**
1. Run:
   ```
   grep -rnoP '\]\(\K[^)]+\.md[^)]*' docs/guide/*.md | while IFS=: read -r s l t; do b="${t%%#*}"; [ -f "docs/guide/$b" ] || echo "BROKEN: $s:$l -> $b"; done
   ```

**Expected:** Empty output (zero broken links).

---

## Test 10: Stale 29-mental-model-catalog Entries Removed

**Steps:**
1. Run: `grep '29-mental-model-catalog' docs/guide/README.md docs/guide/index.html backend/app/templates/guide.html`

**Expected:** Zero matches. The old `29-mental-model-catalog` entries have been replaced by `39-mental-model-catalog`.

---

## Edge Cases

### E1: Glossary References Updated
1. Run: `grep 'mental-model-catalog' docs/guide/appendix-d-glossary.md | head -3`
2. **Expected:** All references point to `39-mental-model-catalog.md`, not `29-mental-model-catalog.md`.

### E2: Prev/Next Nav Chain for Sync Apps
1. Open `docs/guide/41-google-calendar-sync.md` and check the footer navigation link targets.
2. **Expected:** Previous → `35-github-sync.md`, Next → `42-todoist-sync.md`. Both files exist.
3. Open `docs/guide/47-asana-sync.md` and check footer.
4. **Expected:** Previous → `44-caldav-calendar-sync.md`. File exists.

### E3: Personas Chapter Reference Updated
1. Run: `grep 'mental-model-catalog' docs/guide/30-personas.md`
2. **Expected:** Points to `39-mental-model-catalog.md`, not `29-mental-model-catalog.md`.
