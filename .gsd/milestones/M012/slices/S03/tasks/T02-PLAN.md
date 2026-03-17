---
estimated_steps: 5
estimated_files: 5
---

# T02: API routes, sidebar persona selector, and main.py wiring

**Slice:** S03 — Workspace Personas
**Milestone:** M012

## Description

Create the REST API routes and htmx browser routes for persona CRUD, wire the PersonaService into the FastAPI application, create the persona selector partial for the user popover, and modify the sidebar template to include it. This connects the T01 service layer to the UI surface that T03 will drive with JavaScript.

Follow the `dashboard/router.py` pattern: separate `browser_router` and `api_router`, dependency injection via `request.app.state`, user auth via `get_current_user`.

## Steps

1. Create `backend/app/persona/router.py` with two routers:

   **`api_router`** (prefix `/api/personas`, tags `["personas-api"]`):
   - `GET /` — list personas for current user. Return JSON array of `{id, name, is_active, created_at}` (metadata only — exclude layout_json and sidebar_positions_json to keep payloads small).
   - `POST /` — create persona. Accept JSON body `{name, layout_json?, sidebar_positions_json?, explorer_mode?}`. Call `service.create()`, then `service.activate()` on the new persona. Return created persona data with 201 status.
   - `GET /{persona_id}` — get persona by ID (full payload including layout_json, sidebar_positions_json, explorer_mode). Return 404 if not found or wrong user.
   - `PUT /{persona_id}` — update persona name. Accept JSON `{name}`. Return updated persona. 404 if not found or wrong user.
   - `DELETE /{persona_id}` — delete persona. Return 204 on success, 404 if not found or wrong user.
   - `POST /{persona_id}/activate` — activate persona. Return activated persona. 404 if not found.
   - `POST /{persona_id}/save-state` — save workspace state to persona. Accept JSON `{layout_json?, sidebar_positions_json?, explorer_mode?}`. Return updated persona. 404 if not found.

   **`browser_router`** (prefix `/browser/personas`, tags `["personas"]`):
   - `GET /selector` — render `_persona_selector.html` partial. Fetches persona list for current user, passes to template.

   **Helper**: `_get_persona_service(request: Request) -> PersonaService` — get service from `request.app.state.persona_service`.

   All routes require `user: User = Depends(get_current_user)`. Use `uuid.UUID` type for `persona_id` path params.

2. Register routers and service in `backend/app/main.py`:
   - Add import: `from app.persona.router import browser_router as persona_browser_router, api_router as persona_api_router`
   - In `create_app()` startup section (near line 325 where dashboard/workflow services are created): `from app.persona.service import PersonaService` then `app.state.persona_service = PersonaService(async_session_factory)`
   - Include routers (near line 510 where dashboard/workflow routers are included): `app.include_router(persona_browser_router)` and `app.include_router(persona_api_router)`

3. Create `backend/app/templates/components/_persona_selector.html`:
   ```html
   {# Persona selector partial — rendered inside user popover via hx-get #}
   <div class="persona-selector">
       <div class="persona-selector-header">
           <span class="persona-selector-title">Personas</span>
           <button class="persona-selector-action" onclick="createNewPersona()" title="New Persona">
               <i data-lucide="plus" style="width:14px;height:14px;"></i>
           </button>
       </div>
       <div class="persona-selector-list">
           {% for persona in personas %}
           <button class="persona-selector-item {% if persona.is_active %}active{% endif %}"
                   onclick="switchPersona('{{ persona.id }}'); var pop = document.getElementById('user-popover'); if (pop) pop.hidePopover();">
               <i data-lucide="{% if persona.is_active %}check-circle{% else %}circle{% endif %}"
                  class="persona-item-icon"></i>
               <span class="persona-item-name">{{ persona.name }}</span>
           </button>
           {% endfor %}
           {% if not personas %}
           <div class="persona-selector-empty">No personas yet</div>
           {% endif %}
       </div>
       <button class="persona-selector-save" onclick="saveCurrentPersonaState(); var pop = document.getElementById('user-popover'); if (pop) pop.hidePopover();">
           <i data-lucide="save" class="persona-save-icon"></i>
           <span>Save Current</span>
       </button>
   </div>
   ```
   Note: `switchPersona()`, `createNewPersona()`, and `saveCurrentPersonaState()` are JS functions defined in T03. The partial renders server-side with persona data; JS handles the interactions.

   After rendering, call `lucide.createIcons()` to render the Lucide icons inside the partial. Add `hx-on::after-settle="if (typeof lucide !== 'undefined') lucide.createIcons({attrs: {class: ['lucide']}})"` to the container div.

4. Modify `backend/app/templates/components/_sidebar.html` — add persona selector in user popover:
   - Between the "Layouts" link and the theme row (around line 175, after the Layouts `<a>` and before `<div class="popover-theme-row">`), add:
   ```html
   <div class="popover-divider"></div>
   <div id="persona-selector-container"
        hx-get="/browser/personas/selector"
        hx-trigger="load"
        hx-swap="innerHTML">
   </div>
   <div class="popover-divider"></div>
   ```
   This eagerly loads the persona selector partial when the page loads (not on popover toggle — simpler and avoids load delay when opening popover).

5. Add persona selector CSS to `frontend/static/css/workspace.css`:
   - `.persona-selector` — padding, border-radius
   - `.persona-selector-header` — flex row with title and + button
   - `.persona-selector-title` — small uppercase label
   - `.persona-selector-list` — max-height with overflow scroll for many personas
   - `.persona-selector-item` — flex row, cursor pointer, hover highlight; when `.active`: accent color text/icon
   - `.persona-item-icon` — Lucide icon sizing with `flex-shrink: 0` per CLAUDE.md rules
   - `.persona-selector-save` — full-width button at bottom
   - `.persona-selector-empty` — muted text for no-personas state
   - Follow existing popover styling patterns (`.popover-item` for reference)

## Must-Haves

- [ ] All 7 API endpoints respond with correct status codes and payloads
- [ ] `POST /api/personas` creates and auto-activates the new persona
- [ ] `GET /api/personas` returns metadata only (no layout_json in list)
- [ ] `GET /api/personas/{id}` returns full payload (with layout_json)
- [ ] PersonaService instantiated in `create_app()` and stored on `app.state`
- [ ] Both routers registered in `main.py`
- [ ] Persona selector renders in user popover with active persona indicated
- [ ] Lucide icons render correctly in persona selector (flex-shrink: 0)

## Verification

- `docker compose up -d --build api` then `curl -s http://localhost:8001/api/personas -H "Cookie: ..."` returns JSON array
- Open workspace in browser → user popover shows persona selector section
- Manually test API: create persona via curl POST, verify it appears in list, verify GET by ID returns full payload

## Observability Impact

- Signals added/changed: API routes log at INFO level on create/activate/delete persona
- How a future agent inspects this: `curl /api/personas` for list, check `personas` table in SQLite
- Failure state exposed: 404 on bad persona ID, 403-equivalent (None return) on wrong user

## Inputs

- `backend/app/persona/models.py` — Persona model (from T01)
- `backend/app/persona/service.py` — PersonaService (from T01)
- `backend/app/dashboard/router.py` — reference router pattern (dual router, dependency injection, auth)
- `backend/app/main.py` — registration pattern for routers and services
- `backend/app/templates/components/_sidebar.html` — existing user popover structure
- `frontend/static/css/workspace.css` — existing popover styling patterns

## Expected Output

- `backend/app/persona/router.py` — REST API + browser routes for persona CRUD
- `backend/app/main.py` — modified to register persona routers and service
- `backend/app/templates/components/_persona_selector.html` — htmx persona selector partial
- `backend/app/templates/components/_sidebar.html` — modified to include persona selector container
- `frontend/static/css/workspace.css` — persona selector styling added
