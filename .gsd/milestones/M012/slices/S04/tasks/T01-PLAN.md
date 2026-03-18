---
estimated_steps: 5
estimated_files: 3
---

# T01: Merge S01/S02 branch code into main

**Slice:** S04 — E2E Tests & User Guide
**Milestone:** M012

## Description

S01 (event log labels/helptext/autocomplete) and S02 (body.diff) were implemented on the `milestone/M012` branch. S03 (personas) was implemented directly on `main`. This task merges the branch so all three feature sets exist in the working directory. Without this merge, the Docker test stack (which mounts volumes from the working directory) cannot serve S01/S02 features, and E2E tests for those features cannot pass.

The merge should be clean: S01/S02 touch event log and shapes files, S03 touches persona and workspace files — disjoint code areas. The only potential conflicts are `backend/app/main.py` (router registration) and `frontend/static/css/workspace.css` (both slices added styles). The diff shows persona files are being _removed_ from M012 branch (since they were added to main after the branch diverged), which means the merge will correctly keep main's versions.

## Steps

1. Run `git merge milestone/M012 --no-edit` from main branch. If conflicts arise, resolve them:
   - `backend/app/main.py`: keep main's version (has persona router registration), add any S01/S02 additions
   - `frontend/static/css/workspace.css`: keep both sets of style additions (S01 event autocomplete styles + S03 persona styles)
   - `.gsd/` files: keep main's version for state/planning files (these are metadata, not code)
2. Verify key S01 files exist: `backend/app/services/shapes.py` has `get_labels_for_predicates`, `backend/app/browser/events.py` has `suggest-types`/`suggest-predicates`/`suggest-objects`, `backend/app/templates/browser/_event_suggestions.html` exists
3. Verify key S02 files exist: `backend/app/commands/handlers/body_diff.py` exists, `backend/tests/test_body_diff.py` exists
4. Verify S03 files still intact: `backend/app/persona/service.py`, `backend/app/persona/router.py` exist
5. Run `python -m pytest backend/tests/ --tb=short` to confirm no test regressions from the merge

## Must-Haves

- [ ] `milestone/M012` branch merged into `main` with no conflict markers
- [ ] S01/S02 code present in working directory (body_diff handler, event suggestions, label resolution)
- [ ] S03 persona code still intact
- [ ] Backend test suite passes (940+ tests, 0 failures)

## Verification

- `grep -rn "^<<<<<<< " backend/ frontend/ --include="*.py" --include="*.html" --include="*.js" --include="*.css"` — returns zero results
- `test -f backend/app/commands/handlers/body_diff.py && echo OK` — OK
- `grep -c "suggest-types" backend/app/browser/events.py` — ≥1
- `test -f backend/app/persona/service.py && echo OK` — OK
- `python -m pytest backend/tests/ --tb=short` — passes

## Observability Impact

**Signals changed:** After this merge, the working directory contains all M012 feature code (S01 event log polish, S02 body.diff, S03 personas). The Docker test stack (which volume-mounts from the working directory) will serve all three feature sets.

**Inspection:** `git log --oneline -1` shows the merge commit. `git diff --stat HEAD~1` shows all files brought in from the branch. Key files can be verified with existence checks listed in the Verification section.

**Failure state:** If the merge introduced conflicts, `grep -rn "^<<<<<<< " backend/ frontend/` will find conflict markers. If the merge broke code, `python -m pytest backend/tests/ --tb=short` will show test failures with tracebacks identifying the broken module.

## Inputs

- `milestone/M012` branch containing S01/S02 code (event log labels, helptext, autocomplete, body.diff)
- `main` branch containing S03 code (personas)

## Expected Output

- Main branch contains all M012 feature code (S01 + S02 + S03) in a single commit
- Backend test suite passes, confirming no merge regressions
