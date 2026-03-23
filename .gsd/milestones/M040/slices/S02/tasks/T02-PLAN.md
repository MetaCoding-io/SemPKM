---
estimated_steps: 4
estimated_files: 3
---

# T02: Add orphan entries to all 3 navigation files

**Slice:** S02 — Orphan Chapter Integration & Renumbering
**Milestone:** M040

## Description

Add the 9 newly-numbered chapters (39–47) to all three guide navigation files: README.md (markdown links), index.html (sidebar `<a>` tags), and guide.html (Jinja2 `<button>` elements). Place each entry in the appropriate Part section.

## Steps

1. Read README.md to identify the correct Part section for each new chapter:
   - 39-mental-model-catalog → Part III (Mental Models), after chapter 10
   - 40-rss-reader → Part VIII (Discovery and Integration), with other apps
   - 41–44 (sync apps: Google Calendar, Todoist, Outlook, CalDAV) → Part VIII, after existing sync chapters (34–37)
   - 45-notion-import → Part VIII, near 24-obsidian-onboarding
   - 46-ai-features → Part VIII
   - 47-asana-sync → Part VIII, with other sync apps
2. Add markdown link entries to README.md in the correct positions
3. Add matching `<a data-file="NN-slug.md">` entries to index.html in the same order
4. Add matching `<button hx-get="/guide/NN-slug">` entries to guide.html in the same order

## Must-Haves

- [ ] All 9 chapters linked in README.md
- [ ] All 9 chapters linked in index.html
- [ ] All 9 chapters linked in guide.html
- [ ] Entries placed in logically appropriate Part sections

## Verification

- Count of numbered chapter entries in README.md matches count of `[0-9]*.md` files in `docs/guide/`
- `grep -c "mental-model-catalog\|rss-reader\|google-calendar\|todoist\|outlook-calendar\|caldav\|notion-import\|ai-features\|asana" docs/guide/README.md` returns 9
- Same grep on index.html and guide.html also returns 9 each

## Inputs

- `docs/guide/README.md` — existing TOC to extend
- `docs/guide/index.html` — existing sidebar to extend
- `backend/app/templates/guide.html` — existing template to extend

## Expected Output

- `docs/guide/README.md` — updated with 9 new chapter entries
- `docs/guide/index.html` — updated with 9 new sidebar entries
- `backend/app/templates/guide.html` — updated with 9 new button entries
