# S02: Orphan Chapter Integration & Renumbering

**Goal:** Link all 8 orphaned guide files into the guide navigation so users can discover them, eliminating chapter number collisions.
**Demo:** All guide `.md` files on disk appear in README.md, index.html, and guide.html. Zero duplicate chapter numbers.

## Must-Haves

- 8 orphan files renamed to unique chapter numbers (41–48 range, after current highest linked chapter 38)
- Each orphan added to README.md in the correct Part section
- Each orphan added to index.html sidebar
- Each orphan added to guide.html Jinja2 template
- Zero chapter number collisions on disk
- Cross-references within orphan files updated if they reference other chapters by number

## Verification

- `ls docs/guide/[0-9]*.md | sed 's/.*\///' | grep -oP '^\d+' | sort -n | uniq -d` returns empty (no duplicate numbers)
- `ls docs/guide/[0-9]*.md | wc -l` matches the count of numbered entries in README.md
- `grep -c "data-file" docs/guide/index.html` matches the count of numbered entries in README.md (approximately)
- `grep -rn "Chapter [0-9]" docs/guide/*.md` — spot-check that referenced chapter numbers resolve to real files

## Tasks

- [x] **T01: Rename orphan files and assign unique chapter numbers** `est:30m`
  - Why: 8 files have duplicate numbers (two 29s, two 32s, two 36s, two 37s, two 38s, two 39s, two 40s). They need unique numbers to be linkable.
  - Files: `docs/guide/29-mental-model-catalog.md`, `docs/guide/32-rss-reader.md`, `docs/guide/36-google-calendar-sync.md`, `docs/guide/37-todoist-sync.md`, `docs/guide/38-outlook-calendar-sync.md`, `docs/guide/39-caldav-calendar-sync.md`, `docs/guide/39-notion-import.md`, `docs/guide/40-ai-features.md`, `docs/guide/40-asana-sync.md`
  - Do: Rename each orphan to a unique number starting at 39 (since current highest linked is 38-hosted-demo). Proposed mapping: 39-mental-model-catalog, 40-rss-reader, 41-google-calendar-sync, 42-todoist-sync, 43-outlook-calendar-sync, 44-caldav-calendar-sync, 45-notion-import, 46-ai-features, 47-asana-sync. Use `git mv` for each rename. Update the `# Chapter NN:` heading inside each file to match its new number.
  - Verify: `ls docs/guide/[0-9]*.md | sed 's/.*\///' | grep -oP '^\d+' | sort -n | uniq -d` returns empty
  - Done when: Zero duplicate chapter numbers; all orphan files have unique sequential numbers

- [x] **T02: Add orphan entries to all 3 navigation files** `est:45m`
  - Why: The 3 navigation files (README.md, index.html, guide.html) must list every chapter for users to find them
  - Files: `docs/guide/README.md`, `docs/guide/index.html`, `backend/app/templates/guide.html`
  - Do: Add each renamed orphan to README.md in the appropriate Part section (sync apps go in Part VIII with other integrations; Mental Model Catalog near chapter 10/19; AI Features in Part VIII; Notion Import in Part VIII). Add matching `<a data-file="...">` entries to index.html. Add matching `<button hx-get="/guide/...">` entries to guide.html. Follow exact formatting patterns used by existing entries.
  - Verify: `diff <(ls docs/guide/[0-9]*.md | sed 's/.*\///' | grep -oP '^\d+' | sort -n) <(grep -oP '\d+(?=-)' docs/guide/README.md | sort -n | uniq)` shows no differences for numbered chapters
  - Done when: Every numbered `.md` file in `docs/guide/` has a corresponding entry in all 3 nav files

- [ ] **T03: Audit and fix cross-references** `est:20m`
  - Why: Orphan files may contain cross-references to other chapters by number; renumbered files need their internal references updated
  - Files: all renamed orphan files, plus any existing chapters that reference renumbered content
  - Do: Run `grep -rn 'Chapter [0-9]\|[0-9]*-[a-z].*\.md' docs/guide/*.md` to find all cross-references. Check each reference resolves to a real file. Fix any that point to old numbers. Check the 8 orphan files' internal chapter-number headings match their filenames.
  - Verify: `grep -rn '\[.*\](.*\.md)' docs/guide/*.md | while read line; do file=$(echo "$line" | grep -oP '\]\(\K[^)]+'); [ -f "docs/guide/$file" ] || echo "BROKEN: $line"; done` returns no BROKEN lines
  - Done when: All markdown cross-references between guide chapters resolve to existing files

## Observability / Diagnostics

This slice is documentation-only (static `.md`, `.html` files). No runtime services, APIs, or background processes are affected.

- **Inspection surface:** `ls docs/guide/[0-9]*.md | sed 's/.*\///' | grep -oP '^\d+' | sort -n | uniq -d` — returns empty when no duplicate chapter numbers exist.
- **Failure visibility:** A broken cross-reference (`[text](file.md)` pointing to a non-existent file) produces a 404 in both the static docs site and the in-app `/guide` route. The static site renders a broken link; the in-app guide returns an htmx swap error visible in browser dev tools.
- **Diagnostic command:** `grep -rn '\[.*\](.*\.md)' docs/guide/*.md | while read line; do file=$(echo "$line" | grep -oP '\]\(\K[^)]+'); [ -f "docs/guide/$file" ] || echo "BROKEN: $line"; done` — lists all broken markdown cross-references.

## Files Likely Touched

- `docs/guide/29-mental-model-catalog.md` → renamed
- `docs/guide/32-rss-reader.md` → renamed
- `docs/guide/36-google-calendar-sync.md` → renamed
- `docs/guide/37-todoist-sync.md` → renamed
- `docs/guide/38-outlook-calendar-sync.md` → renamed
- `docs/guide/39-caldav-calendar-sync.md` → renamed
- `docs/guide/39-notion-import.md` → renamed
- `docs/guide/40-ai-features.md` → renamed
- `docs/guide/40-asana-sync.md` → renamed
- `docs/guide/README.md`
- `docs/guide/index.html`
- `backend/app/templates/guide.html`
