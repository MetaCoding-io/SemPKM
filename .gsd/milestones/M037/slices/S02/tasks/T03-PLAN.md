---
estimated_steps: 4
estimated_files: 4
skills_used:
  - frontend-design
  - accessibility
---

# T03: Settings UI — Context Rules category panel with CRUD and test

**Slice:** S02 — Auto-Persona Rules Engine & Settings UI
**Milestone:** M037

## Description

Add a "Context Rules" category to the Settings page where users can create, edit, delete, and test context-to-persona rules. The UI follows the existing settings page pattern: a sidebar button triggers showing a panel that lazy-loads content via htmx. The rule builder form has condition dropdowns (location_zone, activity, time_period), a calendar_busy checkbox, a target persona dropdown, priority, enabled toggle, and a "Test against current context" button.

## Steps

1. Add "Context Rules" sidebar button and panel div to `backend/app/templates/browser/settings_page.html`:
   - Add a `<button class="settings-category-btn" data-category="context-rules" onclick="showSettingsCategory('context-rules')">Context Rules</button>` after the "Authorized Apps" button (or in a logical position)
   - Add the corresponding panel div:
   ```html
   <div class="settings-category-panel" id="category-context-rules"
        data-category="context-rules" style="display:none">
     <div class="settings-category-header">
       <h2 class="settings-category-title">Context Rules</h2>
     </div>
     <div id="context-rules-content"
          hx-get="/browser/settings/context-rules"
          hx-trigger="load"
          hx-swap="innerHTML">
       <p class="settings-loading">Loading context rules...</p>
     </div>
   </div>
   ```

2. Create `backend/app/templates/browser/_context_rules.html` template partial:
   - **Rule list section**: Display existing rules in a list/table. Each rule shows: name, conditions summary (e.g., "Location: office, Time: work_hours"), target persona name, priority, enabled toggle. Each has Edit and Delete buttons.
   - **Create/Edit form**: Collapsible form with fields:
     - Rule name (text input, required)
     - Conditions section: location_zone (select: home/office/transit/gym/other or empty for "any"), activity (select: stationary/walking/driving/cycling/running or empty), time_period (select: morning/work_hours/afternoon/evening/night or empty), calendar_busy (checkbox)
     - Target persona (select dropdown — populated via htmx from `/api/personas`)
     - Priority (number input, default 0, higher = evaluated first)
     - Enabled (checkbox, default checked)
   - **Delete**: htmx DELETE with `hx-confirm="Delete this rule?"` confirmation
   - **Test button**: "Test against current context" button that POSTs to `/api/context/rules/test` and displays the result (matched rule name + persona, or "No rule matches current context")
   - All form submissions use htmx: `hx-post="/api/context/rules"` for create, `hx-put` for edit, targeting the rule list for refresh after mutation
   - Use `hx-vals` or hidden inputs for JSON conditions assembly from the individual dropdowns

3. Add browser route for the settings partial in `backend/app/browser/settings.py` (or create a new route file if settings.py doesn't handle custom category routes):
   - `GET /browser/settings/context-rules` — renders `_context_rules.html` with the user's existing rules (fetched via RulesEngine.list_rules) and available personas (fetched via PersonaService.list_for_user)
   - The route needs auth (session-based, since this is a browser route)
   - If `settings.py` doesn't have a pattern for this, follow the IndieAuth tokens list pattern (`/api/indieauth/tokens/list`) — a route that returns an HTML fragment

4. Add styles to `frontend/static/css/settings.css`:
   - `.context-rules-list` — rule cards/rows
   - `.context-rule-card` — individual rule display with conditions summary, persona badge, priority, enabled toggle
   - `.context-rule-form` — form layout matching existing settings patterns
   - `.context-rule-conditions` — grid/flex layout for condition dropdowns
   - `.context-rule-test-result` — match/no-match indicator (green check / red X)
   - Follow existing settings.css patterns (`.settings-row`, `.settings-section`, etc.) for visual consistency
   - Ensure Lucide icons in flex containers follow the project rule: CSS sizing with `flex-shrink: 0`

## Must-Haves

- [ ] "Context Rules" button appears in settings sidebar
- [ ] Panel loads rule list and create form via htmx
- [ ] Create rule form submits to API and refreshes list
- [ ] Edit rule form pre-fills existing values and submits update
- [ ] Delete button removes rule with confirmation
- [ ] Test button shows match/no-match result for current context
- [ ] Persona dropdown populated with user's actual personas
- [ ] Condition dropdowns offer meaningful options matching context field values
- [ ] Styles consistent with existing settings page

## Verification

- Start Docker stack (`docker compose up -d`), navigate to Settings page
- Verify "Context Rules" appears in sidebar
- Click it → panel loads (no JS errors in console)
- Create a rule → appears in list
- Edit the rule → changes saved
- Test against current context → shows result
- Delete the rule → removed from list
- `grep -q "context-rules" backend/app/templates/browser/settings_page.html` — category exists
- `test -f backend/app/templates/browser/_context_rules.html` — template exists

## Inputs

- `backend/app/templates/browser/settings_page.html` — existing settings page structure (add category button + panel)
- `backend/app/templates/browser/_indieauth_settings.html` — pattern reference for htmx settings panel
- `backend/app/browser/settings.py` — existing settings routes
- `backend/app/context/rules_router.py` — CRUD API endpoints from T02
- `backend/app/context/rules_engine.py` — RulesEngine.list_rules() from T01
- `backend/app/persona/service.py` — PersonaService.list_for_user() for persona dropdown
- `frontend/static/css/settings.css` — existing settings styles

## Expected Output

- `backend/app/templates/browser/settings_page.html` — modified with Context Rules category
- `backend/app/templates/browser/_context_rules.html` — new template partial
- `backend/app/browser/settings.py` — modified with context rules route (or new route file)
- `frontend/static/css/settings.css` — modified with rule builder styles
