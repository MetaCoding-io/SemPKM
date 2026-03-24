---
estimated_steps: 5
estimated_files: 7
skills_used:
  - frontend-design
  - review
---

# T03: UI routes + templates + CSS

**Slice:** S02 — Schedule Rules Engine + Daily Plan Generation
**Milestone:** M038

## Description

Wire the rules service and plan service to the user through htmx fragment routes, tab navigation, a today view (agenda layout), and a rules builder UI. This task adds 8 new routes to app.py, reworks main.html with a tab bar, creates 3 new templates, and extends the CSS.

All htmx URLs must use the `/app/media-scheduler/` proxy prefix (KNOWLEDGE.md rule). Lucide icons inside flex containers need `flex-shrink: 0` (CLAUDE.md rule).

## Steps

1. **Rework `apps/media-scheduler/frontend/templates/main.html`** — replace the current sidebar+episodes layout with a tabbed interface:
   - Keep the sidebar (sources) as-is
   - Replace the `ms-main` content area with a tab bar header containing 3 tabs: **Today** (default, icon: calendar), **Episodes** (icon: list-music), **Rules** (icon: sliders-horizontal)
   - Tab clicks use `hx-get` to load the corresponding fragment into a `#ms-tab-content` div:
     - Today → `hx-get="/app/media-scheduler/_fragments/today"`
     - Episodes → `hx-get="/app/media-scheduler/_fragments/items"` (existing route)
     - Rules → `hx-get="/app/media-scheduler/_fragments/rules"`
   - Default tab (Today) loads on page init via `hx-trigger="load"` on the content div
   - Tab active state managed via onclick toggling `.ms-tab-active` class

2. **Create `apps/media-scheduler/frontend/templates/today.html`** — agenda-style daily plan view:
   - Header: "Today's Plan" with date string and a "Generate Plan" button (`hx-post="/app/media-scheduler/_fragments/plan/generate"` targeting `#ms-tab-content`)
   - If plan entries exist: vertical list of plan entry cards, each showing:
     - Time slot (slotStart – slotEnd) in a left gutter
     - Item title, source name, duration badge
     - Status badge (pending/active/completed/skipped) with color coding
     - Play link if enclosure_url exists (opens in new tab)
   - If no plan entries: empty state with "No plan for today. Click Generate Plan to create one." message and a generate button
   - "Now playing" visual indicator on the entry whose time slot contains the current time (set via template variable, not JS)
   - Template receives: `entries` (list of dicts), `plan_date`, `has_plan` (bool)

3. **Create `apps/media-scheduler/frontend/templates/rules.html`** — rules list view:
   - Header: "Schedule Rules" with "Add Rule" button (`hx-get="/app/media-scheduler/_fragments/rules/add"` targeting `#ms-rule-form-area`)
   - A `#ms-rule-form-area` div (empty initially, receives inline form)
   - Rule list: each rule rendered as a card showing:
     - Name, priority badge
     - Conditions summary (e.g., "When commuting · Any time · Any location")
     - Action summary (e.g., "Play podcasts")
     - Enable/disable toggle (`hx-post="/app/media-scheduler/_fragments/rules/{id}/toggle"`)
     - Delete button (`hx-post="/app/media-scheduler/_fragments/rules/{id}/delete"`)
   - Both toggle and delete target `#ms-rules-list` to refresh the list
   - Template receives: `rules` (list of dicts)

4. **Create `apps/media-scheduler/frontend/templates/rule-form.html`** — add/edit rule inline form:
   - Condition section: 3 `<select>` dropdowns:
     - Location Zone: options = [Any, home, office, gym, transit, outdoors]
     - Activity: options = [Any, commuting, exercising, working, relaxing, cooking, reading]
     - Time Period: options = [Any, morning, afternoon, evening, night]
   - Optional time range: two `<input type="time">` fields (start, end) — shown/hidden via a "Specific time range" checkbox
   - Action section: radio group for action type (source_type / source_iri / category) + value input:
     - source_type: `<select>` with podcast, youtube, spotify
     - source_iri: text input for IRI (future: autocomplete)
     - category: text input for category IRI (future: autocomplete)
   - Name: text input (required)
   - Priority: number input (default: 10)
   - Buttons: Save (`hx-post="/app/media-scheduler/_fragments/rules"` targeting `#ms-rules-list`) and Cancel (removes the form via JS)
   - Template receives: `rule` (dict or None for new rule), `editing` (bool)

5. **Add 8 routes to `apps/media-scheduler/app.py`** and extend CSS:
   - `GET /_fragments/today` — query today's plan entries via SPARQL, render today.html
   - `GET /_fragments/rules` — load rules via rules_service.load_rules(), render rules.html
   - `GET /_fragments/rules/add` — render empty rule-form.html
   - `POST /_fragments/rules` — parse form, call add_rule(), return updated rules list
   - `POST /_fragments/rules/{id}/toggle` — call toggle_rule(), return updated rules list
   - `POST /_fragments/rules/{id}/delete` — call delete_rule(), return updated rules list
   - `POST /_fragments/plan/generate` — call generate_plan(), return today view
   - `GET /_fragments/current-suggestion` — query the current/next plan entry, return minimal HTML (for S05 mobile use)
   - SPARQL for today view: query PlanEntry objects where plan date = today, joined with MediaItem data, ordered by slotOrder
   - Extend `apps/media-scheduler/frontend/static/styles.css` with:
     - `.ms-tabs` tab bar (flex row, border-bottom, gap)
     - `.ms-tab` individual tab (flex items, cursor pointer, hover/active states)
     - `.ms-tab-active` highlighted tab
     - `.ms-plan-entry` card (flex row, time gutter + content + status)
     - `.ms-time-slot` time display
     - `.ms-now-playing` highlight for current entry
     - `.ms-rule-card` rule list item
     - `.ms-rule-form` inline form styling
     - `.ms-priority-badge` priority number badge
     - `.ms-status-badge` with color variants (pending=muted, active=blue, completed=green, skipped=orange, replaced=gray)
     - Tab icon SVGs get `flex-shrink: 0` per CLAUDE.md rule

## Must-Haves

- [ ] main.html has tab bar with Today (default), Episodes, Rules tabs
- [ ] Tab clicks load fragments via hx-get with correct proxy-prefixed URLs
- [ ] today.html renders plan entries as agenda cards with time slots, or shows empty state
- [ ] rules.html lists rules with name, conditions summary, action summary, toggle, delete
- [ ] rule-form.html has condition dropdowns, action type radio, name, priority, save/cancel
- [ ] All 8 routes registered in app.py and return valid HTML fragments
- [ ] All htmx URLs in all templates use `/app/media-scheduler/` prefix
- [ ] CSS extends cleanly with tab nav, plan entries, rule cards, status badges
- [ ] Lucide icons in flex containers have `flex-shrink: 0`

## Verification

- `rg 'hx-get="|hx-post="' apps/media-scheduler/frontend/templates/ | grep -v '/app/media-scheduler/'` — returns empty (all URLs prefixed)
- `test -f apps/media-scheduler/frontend/templates/today.html && test -f apps/media-scheduler/frontend/templates/rules.html && test -f apps/media-scheduler/frontend/templates/rule-form.html && echo "OK"` — prints OK
- `grep -c "ms-tab" apps/media-scheduler/frontend/static/styles.css` — returns ≥ 3
- `grep -c "@media_scheduler_app.route" apps/media-scheduler/app.py` — returns ≥ 13 (5 existing + 8 new)

## Inputs

- `apps/media-scheduler/services/rules_service.py` — load_rules, add_rule, delete_rule, toggle_rule (from T01)
- `apps/media-scheduler/services/plan_service.py` — generate_plan (from T02)
- `apps/media-scheduler/app.py` — existing app with 5 routes + generate-plan task handler (from T02)
- `apps/media-scheduler/frontend/templates/main.html` — existing template to rework
- `apps/media-scheduler/frontend/static/styles.css` — existing CSS to extend

## Expected Output

- `apps/media-scheduler/app.py` — extended with 8 new routes
- `apps/media-scheduler/frontend/templates/main.html` — reworked with tab navigation
- `apps/media-scheduler/frontend/templates/today.html` — new today plan view template
- `apps/media-scheduler/frontend/templates/rules.html` — new rules list template
- `apps/media-scheduler/frontend/templates/rule-form.html` — new rule form template
- `apps/media-scheduler/frontend/static/styles.css` — extended with tab/plan/rule styles
