---
estimated_steps: 6
estimated_files: 4
---

# T03: Chapter 35 user guide + glossary and navigation updates

**Slice:** S04 — E2E Tests + User Guide
**Milestone:** M017

## Description

Write the Chapter 35 user guide documenting the GitHub sync app for end users. Clone Chapter 34 (Linear Sync) structure and adapt for GitHub's specifics: PAT-only auth (no OAuth), repository selection (vs Linear's team selection), the field mapping table from M017-RESEARCH.md, PR-to-issue linking (unique to GitHub sync), and the simplified status model (open/closed vs Linear's 5-state machine).

Also update the README TOC, glossary, and navigation links to chain correctly: Ch 34 → Ch 35 → Appendix A.

## Steps

1. **Read `docs/guide/34-linear-sync.md`** as the structural reference. Note the section headings, field mapping table format, and nav link pattern.

2. **Create `docs/guide/35-github-sync.md`** with these sections:
   - **Chapter 35: GitHub Sync** — Introduction paragraph (GitHub sync app connects GitHub Issues and PRs to bpkm:Task objects)
   - **Prerequisites** — basic-pkm model installed, GitHub PAT with `repo` scope
   - **Installing the App** — path: `/app/apps/github-sync`, same install flow as any app
   - **Connecting to GitHub** — PAT only (no OAuth per D206). Enter token, verify shows username.
   - **Selecting Repositories** — Multi-select checkboxes (vs Linear's team selection). Both public and private repos shown.
   - **Sync Configuration** — Direction (pull-only / bidirectional), Poll Interval
   - **Manual Sync** — Sync Now button
   - **Understanding Sync Stats** — Last sync time, Pull results (status/created/updated/errors), Push results
   - **Field Mapping** — Main table from M017-RESEARCH.md (GitHub field → bpkm property → transform → direction). Status mapping sub-table: open→todo, closed+completed→done, closed+not_planned→cancelled, reopened→todo.
   - **Push Sync** — Supported fields: title and status only. Loop prevention via lastSyncedAt comparison.
   - **PR-to-Issue Linking** — PRs sync as separate tasks with `externalProvider: "github-pr"`. Timeline API detects cross-references. `bpkm:dependsOn` edges created. Same-repo only.
   - **Admin Monitoring** — Admin > Applications shows status, task history
   - **Troubleshooting** — Common issues: wrong PAT scope, no repos appearing, no tasks after sync, push not reflected, app error status
   - **See Also** — Links to Ch 29 (App Platform), Ch 10 (Mental Models), Appendix A (env vars)
   - **Navigation** — Previous: Ch 34 | Next: Appendix A

3. **Update `docs/guide/README.md`** — Add `35. [GitHub Sync](35-github-sync.md)` after the Ch 34 entry (line 63).

4. **Update `docs/guide/appendix-d-glossary.md`** — Add **GitHub Sync** entry in alphabetical position: description of the app, reference to Chapter 35.

5. **Update `docs/guide/34-linear-sync.md`** — Change the "Next" navigation link at the bottom from `[Appendix A: Environment Variable Reference](appendix-a-environment-variables.md)` to `[Chapter 35: GitHub Sync](35-github-sync.md)`.

6. **Verify** navigation chain: Ch 33 → Ch 34 → Ch 35 → Appendix A.

## Must-Haves

- [ ] Chapter 35 exists with ≥10 section headings covering all aspects of GitHub sync
- [ ] Field mapping table matches M017-RESEARCH.md authoritative source
- [ ] Status mapping sub-table documents open/closed/state_reason → bpkm:taskStatus
- [ ] PR-to-Issue Linking section explains the unique GitHub-specific feature
- [ ] README TOC includes Ch 35 entry
- [ ] Glossary has GitHub Sync entry
- [ ] Navigation links chain correctly: Ch 34 → Ch 35 → Appendix A

## Verification

- `test -f docs/guide/35-github-sync.md && echo "exists"` → "exists"
- `grep -c "^##" docs/guide/35-github-sync.md` → ≥10
- `grep "35-github-sync" docs/guide/README.md` → finds TOC entry
- `grep -i "github sync" docs/guide/appendix-d-glossary.md` → finds glossary entry
- `grep "35-github-sync" docs/guide/34-linear-sync.md` → finds updated Next link

## Inputs

- `docs/guide/34-linear-sync.md` — Reference pattern (288 lines, ~15 heading sections, field mapping tables, nav links)
- `docs/guide/README.md` — TOC file to update (Ch 34 is on line 63)
- `docs/guide/appendix-d-glossary.md` — Glossary to extend with GitHub Sync entry
- M017-RESEARCH.md field mapping table — Authoritative source for GitHub → bpkm:Task mapping (12 fields with transform and direction columns)
- S01 summary: field_mapper does open→todo, closed+completed→done, closed+not_planned→cancelled, state_reason refinement
- S02 summary: PRs sync with externalProvider "github-pr", edges use bpkm:dependsOn, same-repo only
- S03 summary: push sync supports title + status only, loop prevention via lastSyncedAt comparison

## Observability Impact

Documentation-only task — no runtime signals change. The observability surface is the file system:
- `docs/guide/35-github-sync.md` exists and has ≥10 headings (verifiable via `grep -c "^##"`)
- Navigation chain integrity verifiable via `grep` for link targets across Ch 34, Ch 35, and Appendix A
- README TOC and glossary entries verifiable via `grep`

A future agent inspects this task's outcome by checking that the navigation chain is unbroken and the field mapping tables match M017-RESEARCH.md.

## Expected Output

- `docs/guide/35-github-sync.md` — Complete user guide chapter (~250-300 lines) with field mapping tables
- `docs/guide/README.md` — Updated with Ch 35 TOC entry
- `docs/guide/appendix-d-glossary.md` — Updated with GitHub Sync entry
- `docs/guide/34-linear-sync.md` — Updated Next navigation link pointing to Ch 35
