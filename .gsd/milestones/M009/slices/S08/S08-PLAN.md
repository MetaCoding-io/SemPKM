# S08: User Guide Documentation

**Goal:** `docs/guide/` has a chapter covering app management (installing, monitoring, uninstalling from admin) and app development (SDK reference, manifest format, frontend integration levels). Glossary updated. README TOC updated.
**Demo:** A reader can follow Chapter 29 to understand how to install and manage apps from the admin portal, and how to build a new app using the SDK — with the test app as the reference implementation.

## Must-Haves

- Chapter 29 (`docs/guide/29-app-platform.md`) with two main sections: "Managing Apps" (user-facing) and "Building Apps with the SDK" (developer-facing)
- ~5 glossary entries in `docs/guide/appendix-d-glossary.md` (App Contribution, App Manifest, App Platform, App Sandbox, App SDK) inserted alphabetically
- README.md TOC updated with Chapter 29 in Part VIII
- Navigation chain: ch. 28 footer points to ch. 29, ch. 29 footer points to Appendix A

## Verification

- `test -f docs/guide/29-app-platform.md` — file exists
- `grep -c "## Managing Apps" docs/guide/29-app-platform.md` — returns 1
- `grep -c "## Building Apps" docs/guide/29-app-platform.md` — returns 1
- `grep "App Platform" docs/guide/appendix-d-glossary.md` — glossary entry present
- `grep "App SDK" docs/guide/appendix-d-glossary.md` — glossary entry present
- `grep "App Manifest" docs/guide/appendix-d-glossary.md` — glossary entry present
- `grep "App Sandbox" docs/guide/appendix-d-glossary.md` — glossary entry present
- `grep "App Contribution" docs/guide/appendix-d-glossary.md` — glossary entry present
- `grep "29-app-platform" docs/guide/README.md` — TOC entry present
- `grep "29-app-platform" docs/guide/28-dashboards-and-workflows.md` — ch. 28 footer updated
- `grep "Appendix A" docs/guide/29-app-platform.md` — ch. 29 footer points to next
- `find docs/guide/ -name "29-app-platform.md" -empty` — returns nothing (file is non-empty, failure-path check)

## Tasks

- [ ] **T01: Write Chapter 29 — App Platform guide page** `est:45m`
  - Why: The main deliverable of S08. Covers both user-facing app management and developer-facing SDK reference. All source material exists in-repo (design doc, test app, SDK source, admin templates).
  - Files: `docs/guide/29-app-platform.md`
  - Do: Write ~200-250 line markdown chapter with two main H2 sections. "Managing Apps" covers: the Applications admin page, installing from disk, status indicators, start/stop/restart, task monitoring, uninstalling with/without data. "Building Apps with the SDK" covers: directory structure, manifest.yaml reference (use test-app manifest as example), App class decorators, AppContext and 5 clients, fragment routes and templates, task handlers, frontend integration levels (L1/L2/L3), permissions. Reference `apps/test-app/` as the canonical example throughout. Include header navigation and footer navigation placeholders.
  - Verify: `test -f docs/guide/29-app-platform.md && grep -c "## Managing Apps" docs/guide/29-app-platform.md && grep -c "## Building Apps" docs/guide/29-app-platform.md`
  - Done when: Chapter 29 exists with both sections, practical examples from test-app, and correct structure matching existing chapter conventions (h1 title, h2 sections, h3 subsections, code blocks, tips).

- [ ] **T02: Add glossary entries, update README TOC, and wire navigation chain** `est:15m`
  - Why: Integrates ch. 29 into the existing guide structure — readers can discover it from the TOC and navigate to/from adjacent pages.
  - Files: `docs/guide/appendix-d-glossary.md`, `docs/guide/README.md`, `docs/guide/28-dashboards-and-workflows.md`, `docs/guide/29-app-platform.md`
  - Do: (1) Insert 5 glossary entries alphabetically between "ABox" and "Block": App Contribution, App Manifest, App Platform, App Sandbox, App SDK — each with a one-sentence definition and a "See Chapter 29" link. (2) Add `29. [App Platform](29-app-platform.md)` to README.md Part VIII after ch. 28. (3) Update ch. 28 footer: change `Next: Appendix A` to `Next: Chapter 29: App Platform`. (4) Update ch. 29 footer: `Previous: Chapter 28 | Next: Appendix A`.
  - Verify: `grep "App Platform" docs/guide/appendix-d-glossary.md && grep "29-app-platform" docs/guide/README.md && grep "29-app-platform" docs/guide/28-dashboards-and-workflows.md && grep "Appendix A" docs/guide/29-app-platform.md`
  - Done when: All 5 glossary entries present in alphabetical order, README TOC has ch. 29, navigation chain is ch. 28 → ch. 29 → Appendix A.

## Files Likely Touched

- `docs/guide/29-app-platform.md` (new)
- `docs/guide/appendix-d-glossary.md` (modify — add 5 entries)
- `docs/guide/README.md` (modify — add TOC entry)
- `docs/guide/28-dashboards-and-workflows.md` (modify — update footer navigation)
- **Glossary ordering:** New entries must appear in alphabetical order between existing entries (verify by visual inspection or `grep -n "^- \*\*App" docs/guide/appendix-d-glossary.md`).
- **Failure visibility:** If the chapter file is missing or malformed, the `grep` verification commands in the Verification section return non-zero exit codes — suitable for CI gating.

## Observability / Diagnostics

- **Runtime signals:** None — this slice produces static documentation files only. No logs, metrics, or runtime behavior changes.
- **Inspection surfaces:** Run the `grep` commands in the Verification section to confirm all content is in place. `wc -l docs/guide/29-app-platform.md` confirms chapter length. `grep -n "^\*\*App" docs/guide/appendix-d-glossary.md` confirms glossary entries are present and ordered.
- **Failure visibility:** Missing or malformed content causes `grep` verification commands to return non-zero exit codes. Broken internal links can be detected with `for f in $(grep -oP '\]\(\K[^)]+\.md' docs/guide/29-app-platform.md); do test -f "docs/guide/$f" || echo "BROKEN: $f"; done`.
- **Redaction constraints:** None — documentation contains no secrets.

## Files Likely Touched

- `docs/guide/29-app-platform.md` (new)
- `docs/guide/appendix-d-glossary.md` (modify — add 5 entries)
- `docs/guide/README.md` (modify — add TOC entry)
- `docs/guide/28-dashboards-and-workflows.md` (modify — update footer navigation)
