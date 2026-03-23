---
estimated_steps: 4
estimated_files: 9
---

# T01: Rename orphan files and assign unique chapter numbers

**Slice:** S02 — Orphan Chapter Integration & Renumbering
**Milestone:** M040

## Description

Rename 8 orphaned guide files (plus the duplicate `29-mental-model-catalog.md`) to unique chapter numbers, eliminating all collisions. The current highest linked chapter is 38 (Hosted Demo). Orphan files will be renumbered starting at 39.

## Steps

1. Verify the 9 colliding files exist on disk: `29-mental-model-catalog.md`, `32-rss-reader.md`, `36-google-calendar-sync.md`, `37-todoist-sync.md`, `38-outlook-calendar-sync.md`, `39-caldav-calendar-sync.md`, `39-notion-import.md`, `40-ai-features.md`, `40-asana-sync.md`
2. Use `git mv` to rename each file to its new chapter number:
   - `29-mental-model-catalog.md` → `39-mental-model-catalog.md`
   - `32-rss-reader.md` → `40-rss-reader.md`
   - `36-google-calendar-sync.md` → `41-google-calendar-sync.md`
   - `37-todoist-sync.md` → `42-todoist-sync.md`
   - `38-outlook-calendar-sync.md` → `43-outlook-calendar-sync.md`
   - `39-caldav-calendar-sync.md` → `44-caldav-calendar-sync.md`
   - `39-notion-import.md` → `45-notion-import.md`
   - `40-ai-features.md` → `46-ai-features.md`
   - `40-asana-sync.md` → `47-asana-sync.md`
3. Update the `# Chapter NN:` heading inside each renamed file to match its new number
4. Verify zero duplicate chapter numbers on disk

## Must-Haves

- [ ] All 9 files renamed with unique chapter numbers
- [ ] Internal chapter headings updated to match new numbers
- [ ] Zero duplicate chapter numbers on disk

## Verification

- `ls docs/guide/[0-9]*.md | sed 's/.*\///' | grep -oP '^\d+' | sort -n | uniq -d` returns empty
- Each renamed file exists at its new path

## Inputs

- `docs/guide/29-mental-model-catalog.md` — orphan with duplicate number
- `docs/guide/32-rss-reader.md` — orphan with duplicate number
- `docs/guide/36-google-calendar-sync.md` — orphan with duplicate number
- `docs/guide/37-todoist-sync.md` — orphan with duplicate number
- `docs/guide/38-outlook-calendar-sync.md` — orphan with duplicate number
- `docs/guide/39-caldav-calendar-sync.md` — orphan with duplicate number
- `docs/guide/39-notion-import.md` — orphan with duplicate number
- `docs/guide/40-ai-features.md` — orphan with duplicate number
- `docs/guide/40-asana-sync.md` — orphan with duplicate number

## Expected Output

- `docs/guide/39-mental-model-catalog.md` — renamed
- `docs/guide/40-rss-reader.md` — renamed
- `docs/guide/41-google-calendar-sync.md` — renamed
- `docs/guide/42-todoist-sync.md` — renamed
- `docs/guide/43-outlook-calendar-sync.md` — renamed
- `docs/guide/44-caldav-calendar-sync.md` — renamed
- `docs/guide/45-notion-import.md` — renamed
- `docs/guide/46-ai-features.md` — renamed
- `docs/guide/47-asana-sync.md` — renamed
