---
estimated_steps: 23
estimated_files: 4
skills_used: []
---

# T03: Write PPV v2 user guide chapter and update all three index files

Create the PPV model user guide chapter and update all three index files that must stay in sync (KNOWLEDGE.md rule: 'User guide has THREE files that must stay in sync').

## Steps

1. Create `docs/guide/50-ppv-model.md` with content covering:
   - What the PPV model is (Pillars, Pipelines, Vaults — August Bradley's system)
   - Types included: PillarGroup, Pillar, ValueGoal, GoalOutcome, Project, ActionItem, WeeklyReview, MonthlyReview, QuarterlyReview, YearlyReview, PillarScore, GuidingPrinciples
   - 5 dashboards: Action Items (task management), Life Dashboard (pillar overview), Projects Board (project status), Goals Overview (value goals → outcomes), Review Hub (review navigation)
   - 5 workflows: Daily Check-in, Weekly Review (with pillar scoring), Monthly Review, Quarterly Review, Yearly Review
   - The review system: weekly → monthly → quarterly → yearly hierarchy, pillar scoring, enriched reflection fields
   - Installation: standard model install from admin page
   - Seed data: demo instances provided for exploring before adding own data
2. Update `docs/guide/README.md` — add entry `50. [PPV Model](50-ppv-model.md)` after line 76 (49. Media Scheduler).
3. Update `docs/guide/index.html` — add `<li><a href="#" data-file="50-ppv-model.md">50. PPV Model</a></li>` after the 49. Media Scheduler entry.
4. Update `backend/app/shell/router.py` — add `{"filename": "50-ppv-model.md", "title": "50. PPV Model", "icon": "compass"}` to the GUIDE_SECTIONS chapters list, before the "38. Hosted Demo" entry (which is the last non-appendix chapter).

## Must-Haves

- [ ] `docs/guide/50-ppv-model.md` exists with meaningful content (not a stub)
- [ ] `docs/guide/README.md` references the new chapter
- [ ] `docs/guide/index.html` references the new chapter
- [ ] `backend/app/shell/router.py` GUIDE_SECTIONS includes the new chapter entry

## Verification

- `test -f docs/guide/50-ppv-model.md && echo 'Guide exists'`
- `grep -q '50-ppv-model' docs/guide/README.md && echo 'README OK'`
- `grep -q '50-ppv-model' docs/guide/index.html && echo 'index.html OK'`
- `grep -q '50-ppv-model' backend/app/shell/router.py && echo 'router.py OK'`

## Inputs

- ``docs/guide/49-media-scheduler.md` — reference for chapter format and style`
- ``docs/guide/README.md` — table of contents to update`
- ``docs/guide/index.html` — HTML sidebar to update`
- ``backend/app/shell/router.py` — GUIDE_SECTIONS list to update (lines 31-145)`
- ``models/ppv/manifest.yaml` — source of truth for PPV model metadata`
- ``models/ppv/dashboards/ppv.json` — dashboard names and descriptions for documentation`
- ``models/ppv/workflows/ppv.json` — workflow names and descriptions for documentation`

## Expected Output

- ``docs/guide/50-ppv-model.md` — new PPV v2 user guide chapter`
- ``docs/guide/README.md` — updated with chapter 50 entry`
- ``docs/guide/index.html` — updated with chapter 50 sidebar entry`
- ``backend/app/shell/router.py` — updated GUIDE_SECTIONS with chapter 50`

## Verification

test -f docs/guide/50-ppv-model.md && grep -q '50-ppv-model' docs/guide/README.md && grep -q '50-ppv-model' docs/guide/index.html && grep -q '50-ppv-model' backend/app/shell/router.py && echo 'All 4 files OK'
