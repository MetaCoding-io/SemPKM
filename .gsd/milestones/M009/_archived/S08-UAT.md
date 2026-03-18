# S08: User Guide Documentation — UAT

**Milestone:** M009
**Written:** 2026-03-17

## UAT Type

- UAT mode: artifact-driven
- Why this mode is sufficient: This slice produces static documentation files only — no runtime behavior, no backend changes, no frontend changes. All verification is structural (file existence, content presence, link integrity).

## Preconditions

- The M009 worktree has the latest code from all S01–S07 slices merged.
- `docs/guide/` directory exists with existing chapters 1–28 and appendices A–D.

## Smoke Test

Open `docs/guide/29-app-platform.md` in any markdown viewer — confirm it renders with a title, two main sections, code blocks, and navigation footer.

## Test Cases

### 1. Chapter 29 exists and has correct structure

1. `test -f docs/guide/29-app-platform.md` — file exists.
2. `head -5 docs/guide/29-app-platform.md` — first line is `# Chapter 29: App Platform`.
3. `grep -c "## Managing Apps" docs/guide/29-app-platform.md` — returns exactly 1.
4. `grep -c "## Building Apps" docs/guide/29-app-platform.md` — returns exactly 1.
5. `wc -l docs/guide/29-app-platform.md` — between 200 and 400 lines.
6. **Expected:** Chapter has H1 title, two H2 sections (user-facing and developer-facing), reasonable length.

### 2. Managing Apps section covers admin workflows

1. `grep "### Installing an App" docs/guide/29-app-platform.md` — subsection present.
2. `grep "### App Status" docs/guide/29-app-platform.md` — status indicators documented.
3. `grep "### Starting, Stopping" docs/guide/29-app-platform.md` — lifecycle actions covered.
4. `grep "### Task Monitoring" docs/guide/29-app-platform.md` — task management covered.
5. `grep "### Uninstalling" docs/guide/29-app-platform.md` — uninstall workflow covered.
6. **Expected:** All 5 subsections exist covering the admin portal app management workflow.

### 3. Building Apps section covers SDK reference

1. `grep "### App Directory Structure" docs/guide/29-app-platform.md` — directory layout documented.
2. `grep "### The Manifest File" docs/guide/29-app-platform.md` — manifest.yaml reference present.
3. `grep "### The App Class" docs/guide/29-app-platform.md` — App class and decorators covered.
4. `grep "### AppContext" docs/guide/29-app-platform.md` — SDK clients documented.
5. `grep "### Fragment Routes" docs/guide/29-app-platform.md` — route pattern documented.
6. `grep "### Task Handlers" docs/guide/29-app-platform.md` — task registration covered.
7. `grep "### Frontend Integration Levels" docs/guide/29-app-platform.md` — L1/L2/L3 covered.
8. `grep "### Permissions" docs/guide/29-app-platform.md` — permission model documented.
9. **Expected:** All 8 developer-facing subsections present.

### 4. Code examples are present and reference test-app

1. `grep -c 'test-app' docs/guide/29-app-platform.md` — at least 2 references to the test app.
2. `grep -c '```' docs/guide/29-app-platform.md` — at least 6 (3 code blocks × open+close).
3. `grep "manifest.yaml" docs/guide/29-app-platform.md | wc -l` — at least 3 references.
4. `grep "AppContext" docs/guide/29-app-platform.md | wc -l` — at least 3 references.
5. **Expected:** Chapter includes YAML and Python code blocks with real examples from the test app.

### 5. Glossary entries present and alphabetically ordered

1. `grep "App Contribution" docs/guide/appendix-d-glossary.md` — entry present.
2. `grep "App Manifest" docs/guide/appendix-d-glossary.md` — entry present.
3. `grep "App Platform" docs/guide/appendix-d-glossary.md` — entry present.
4. `grep "App Sandbox" docs/guide/appendix-d-glossary.md` — entry present.
5. `grep "App SDK" docs/guide/appendix-d-glossary.md` — entry present.
6. Inspect line numbers: entries appear in alphabetical order (Contribution < Manifest < Platform < Sandbox < SDK).
7. Each entry contains a `See [Chapter 29` cross-reference link.
8. **Expected:** 5 entries, alphabetically ordered, each with Chapter 29 link.

### 6. README TOC updated

1. `grep "29-app-platform" docs/guide/README.md` — TOC entry present.
2. The entry appears after chapter 28 and before appendices.
3. **Expected:** `29. [App Platform](29-app-platform.md)` in Part VIII.

### 7. Navigation chain wired correctly

1. `grep "29-app-platform" docs/guide/28-dashboards-and-workflows.md` — ch. 28 footer points to ch. 29.
2. `grep "28-dashboards" docs/guide/29-app-platform.md` — ch. 29 Previous points to ch. 28.
3. `grep "Appendix A" docs/guide/29-app-platform.md` — ch. 29 Next points to Appendix A.
4. `grep "appendix-a" docs/guide/29-app-platform.md` — link uses correct filename.
5. **Expected:** ch. 28 → ch. 29 → Appendix A chain is complete and bidirectional where relevant.

### 8. No broken internal links

1. Extract all `.md` links from Chapter 29: `grep -oP '\]\(\K[^)]+\.md' docs/guide/29-app-platform.md`
2. For each link, verify the target file exists: `test -f docs/guide/$link`
3. **Expected:** All referenced `.md` files exist. Zero broken links.

## Edge Cases

### Empty or malformed chapter file

1. `find docs/guide/ -name "29-app-platform.md" -empty` — must return nothing.
2. `head -1 docs/guide/29-app-platform.md` — must start with `#` (valid markdown heading).
3. **Expected:** File is non-empty and starts with a valid heading.

### Glossary ordering disruption

1. `grep -n "^\*\*" docs/guide/appendix-d-glossary.md | head -15` — inspect first 15 bold terms.
2. Verify "App *" entries appear after "ABox" and before "Block" (or next non-App entry).
3. **Expected:** Alphabetical order preserved across all glossary entries, not just the new ones.

## Failure Signals

- `grep -c "## Managing Apps"` returns 0 — chapter structure is wrong or file is missing.
- `grep "29-app-platform" docs/guide/README.md` returns empty — TOC not updated.
- `grep "29-app-platform" docs/guide/28-dashboards-and-workflows.md` returns empty — navigation chain broken.
- Any broken `.md` link from Chapter 29 — internal link integrity failure.
- Glossary entries not in alphabetical order — insertion was done incorrectly.

## Requirements Proved By This UAT

- None directly validated — this UAT proves documentation artifact completeness, not runtime behavior. The documented features (APP-01 through APP-14) were validated in S01–S07.

## Not Proven By This UAT

- Accuracy of documentation against live system behavior (would require running the Docker stack and comparing documented workflows against actual admin UI).
- Completeness of SDK API coverage (would require auditing every SDK public method against chapter content).
- Reader comprehension (would require human review of the guide chapter).

## Notes for Tester

- This is a documentation-only slice. All tests are `grep`/`test` commands that can be run without Docker.
- The test-app manifest example in Chapter 29 is intentionally condensed — the full manifest is at `apps/test-app/manifest.yaml`.
- Glossary entries use bold formatting (`**App Platform**`) matching the existing appendix-d style.
