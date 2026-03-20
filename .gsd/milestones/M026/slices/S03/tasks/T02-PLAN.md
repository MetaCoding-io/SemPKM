---
estimated_steps: 8
estimated_files: 8
---

# T02: Capture fresh screenshots, run Lighthouse audit, verify responsive layout

**Slice:** S03 — Screenshots, mobile polish, and SEO verification
**Milestone:** M026

## Description

The 17 screenshots in `docs/screenshots/` are from the v2.0 era and don't reflect current UI features (dashboards, canvas embeds, persona selector, new explorer modes). This task starts the demo Docker stack (which has 74 pre-populated objects across 4 Mental Models), captures 5-8 fresh screenshots, replaces the stale images, runs Lighthouse mobile audit on all 4 pages, and verifies responsive layout at 3 breakpoints (375px, 768px, 1200px).

**Skill note:** This task involves browser-based visual verification — the `frontend-design` skill may be relevant if CSS fixes are needed, but primarily this is screenshot capture + Lighthouse + responsive verification.

## Steps

1. **Start demo Docker stack** — From the main project directory, run:
   ```bash
   cd /home/james/Code/SemPKM
   docker compose -f docker-compose.demo.yml up -d
   ```
   Wait for the API to become healthy (check `http://localhost:8902/api/health`). If the stack is already running, skip the start step.

2. **Seed demo data** — Run the seed script inside the API container:
   ```bash
   docker compose -f docker-compose.demo.yml exec -T api python /app/scripts/seed-demo-data.py
   ```
   This creates 74 objects across 4 models with cross-model edges. Idempotent — safe to re-run.

3. **Capture fresh screenshots** — Open the demo instance at `http://localhost:3902` in the browser. Navigate to each key view and capture screenshots at 1440×900 viewport. Save each to `docs/screenshots/`:
   - `01-workspace-overview-dark.png` — main workspace with explorer sidebar, object open in editor (this is the og:image reference)
   - `02-graph-view.png` — graph view showing interconnected objects
   - `03-table-view.png` — table view with type filter pills and columns
   - `04-dashboard.png` — demo dashboard with cross-view context blocks
   - `05-canvas.png` — spatial canvas with nodes and edges
   - `06-object-read.png` — single object in read mode showing properties and body
   - `07-lint-panel.png` — lint/validation panel showing warnings
   
   Wait for htmx lazy-loading and SSE to finish before each capture (use `waitForLoadState('networkidle')` or equivalent). Screenshots should be PNG, 1440×900.

4. **Verify screenshots were saved** — Check that the key files exist and have recent timestamps:
   ```bash
   ls -la docs/screenshots/01-workspace-overview-dark.png
   file docs/screenshots/01-workspace-overview-dark.png
   ```

5. **Serve docs/ via local HTTP server** — Lighthouse requires HTTP, not file:// protocol:
   ```bash
   cd /home/james/Code/SemPKM/docs && python3 -m http.server 8080 &
   ```

6. **Run Lighthouse mobile audit** — Audit the homepage with mobile preset:
   ```bash
   npx lighthouse http://localhost:8080/index.html --preset=perf --output=json --chrome-flags="--headless --no-sandbox" | jq '.categories.performance.score'
   ```
   Target: ≥ 0.9. If below 0.9, check for performance issues (large images, render-blocking resources) and fix if feasible. Also spot-check one persona page.

7. **Verify responsive layout** — Open each of the 4 pages in the browser at 3 viewports and verify:
   - **375px** (mobile): No horizontal overflow, CTAs full-width and tappable, comparison table horizontally scrollable, nav shows hamburger menu, persona cards stack vertically
   - **768px** (tablet): Content fills width appropriately, grids collapse to 2-column or single-column, CTAs visible
   - **1200px** (desktop): Full layout with all columns, comparison table fits, persona dropdown in nav works
   
   Use `browser_set_viewport` to switch sizes and `browser_assert` to verify key elements are visible.

8. **Clean up** — Stop the demo Docker stack and local HTTP server:
   ```bash
   docker compose -f docker-compose.demo.yml down
   kill %1  # HTTP server background job
   ```

## Must-Haves

- [ ] Fresh screenshots in `docs/screenshots/` with today's date — at minimum `01-workspace-overview-dark.png` (referenced by og:image on all pages)
- [ ] At least 5 screenshots capturing distinct views of the current UI
- [ ] Lighthouse mobile performance score ≥ 0.9 on `docs/index.html`
- [ ] All 4 pages render correctly at 375px, 768px, and 1200px with no horizontal overflow
- [ ] All CTAs visible and accessible at all 3 breakpoints

## Verification

- `ls -la docs/screenshots/01-workspace-overview-dark.png` — file exists with today's date
- `find docs/screenshots/ -name '*.png' -newer /home/james/Code/SemPKM/.gsd/milestones/M026/slices/S03/S03-PLAN.md | wc -l` → ≥ 5
- Lighthouse JSON output `.categories.performance.score` ≥ 0.9
- Browser assertions at 375px, 768px, 1200px: no horizontal scrollbar, CTAs visible, nav functional

## Inputs

- `docs/index.html` — homepage with SEO fixes from T01
- `docs/from-obsidian.html`, `docs/from-notion.html`, `docs/fresh-start.html` — persona pages with SEO fixes from T01
- `docs/styles.css` — shared CSS from S01 (responsive breakpoints at 768px and 480px)
- `docker-compose.demo.yml` — demo stack config (ports 3902/8902, DEMO_MODE=true)
- `scripts/seed-demo-data.py` — seeds 74 objects across 4 Mental Models

## Expected Output

- `docs/screenshots/01-workspace-overview-dark.png` — fresh workspace overview screenshot
- `docs/screenshots/02-graph-view.png` — fresh graph view screenshot
- `docs/screenshots/03-table-view.png` — fresh table view screenshot
- `docs/screenshots/04-dashboard.png` — fresh dashboard screenshot
- `docs/screenshots/05-canvas.png` — fresh canvas screenshot
- `docs/screenshots/06-object-read.png` — fresh object read view screenshot
- `docs/screenshots/07-lint-panel.png` — fresh lint panel screenshot
- Lighthouse audit result ≥ 0.9 performance score
- Browser verification confirming responsive layout at 3 breakpoints
