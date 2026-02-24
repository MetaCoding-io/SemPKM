# Phase 12: Sidebar and Navigation - Research

**Researched:** 2026-02-23
**Domain:** Sidebar navigation, collapsible icon rail, user menu popover, Lucide SVG icons
**Confidence:** HIGH

## Summary

Phase 12 restructures the existing sidebar (`_sidebar.html`) from a flat nav list with Unicode emoji icons into a grouped, collapsible navigation system with Lucide SVG icons, a collapse-to-icon-rail toggle (Ctrl+B), and a user menu popover at the bottom. The existing sidebar is a simple 44-line Jinja2 partial with 8 hardcoded nav links using Unicode glyphs. The `.sidebar` CSS uses `position: fixed` at 220px width, and `.content-area` has `margin-left: 220px` -- both must transition smoothly during collapse.

The implementation is entirely frontend (HTML/CSS/JS) with one backend change: passing the current `User` object to the sidebar template context so the user menu can display name/initials. The auth system already has `GET /api/auth/me` and `POST /api/auth/logout` endpoints with full session management. Lucide icons load via CDN (`unpkg.com/lucide@0.575.0`) and replace elements marked with `data-lucide` attributes. The `createIcons()` function supports a `root` parameter for scoped re-initialization after htmx swaps.

**Primary recommendation:** Replace the existing `_sidebar.html` with a grouped section structure using Lucide icons, add a JS module for sidebar collapse state (localStorage) and user menu popover (HTML Popover API), and update CSS with transition rules for the 220px-to-48px width change.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Collapsible section headers: each group (Admin, Meta, Apps, Debug) has a clickable header that toggles show/hide of its items
- Home nav item removed entirely -- clicking the SemPKM brand logo navigates home
- Admin becomes a section header with sub-items (Users, Teams, Mental Models) rather than a single link to /admin/
- The /admin/ dashboard page is removed since its content is now accessible via direct sidebar nav links
- Lucide icons (SVG) replace all Unicode emoji icons -- same library planned for Phase 15 node type icons, loaded via CDN
- Ctrl+B toggles sidebar between 220px expanded and 48px icon rail
- Hovering over an icon in collapsed mode shows a tooltip with the item name (VS Code activity bar style)
- Toggle button lives at the top of the sidebar (next to or below the brand logo area)
- Thin horizontal divider lines separate sections even in collapsed icon rail mode
- Collapsed/expanded state persists across page reloads via localStorage
- User area pinned to the bottom of the sidebar shows: colored initials avatar circle + display name (no role badge)
- Avatar: first letter(s) of user's name on a colored circle background (Google/Slack style)
- Clicking the user area opens a popover with: Settings link (opens settings tab placeholder), Theme toggle (placeholder for Phase 13), and Logout button
- When sidebar is collapsed to icon rail, user area shows just the small avatar circle -- clicking opens the same popover
- Compact (VS Code-like) density: tight spacing, small text (12-13px), fits many items without scrolling
- Active nav item indicated by subtle background highlight only -- no left border accent
- Section headers: normal case labels (not uppercase) with a subtle divider line below
- Sidebar width stays at 220px expanded

### Claude's Discretion
- Exact Lucide icon choices for each nav item
- Exact spacing/padding values within compact constraints
- Popover positioning and animation
- Collapse/expand CSS transition timing
- How section collapse state interacts with sidebar collapse state

### Deferred Ideas (OUT OF SCOPE)
- Removing/replacing the admin dashboard page may surface items that need new homes -- capture as todos if discovered during implementation
- Settings page itself is Phase 15 scope -- the Settings link in the popover is a placeholder for now
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| NAV-01 | Sidebar collapses to a 48px icon rail via Ctrl+B toggle with smooth CSS transition | CSS transition on `.sidebar` width + `.content-area` margin-left; localStorage key for state persistence; keyboard shortcut handler integration with existing workspace.js |
| NAV-02 | Sidebar navigation is reorganized into grouped sections: Home, Admin, Meta, Apps, Debug | Note: CONTEXT.md removes Home as a nav item (brand logo navigates home). Sections are Admin, Meta, Apps, Debug with collapsible headers. Template restructure of `_sidebar.html` |
| NAV-03 | Apps section contains Object Browser and SPARQL Console; Debug section contains Commands, API Docs, Health Check, and Event Log | Existing routes: `/browser/` (Object Browser), `/sparql` (SPARQL), `/commands` (Commands), `/redoc` and `/docs` (API Docs), `/health/` (Health Check). Event Log is a placeholder (Phase 16) |
| NAV-04 | Meta section contains a Docs & Tutorials page | Placeholder link -- the Docs & Tutorials page is Phase 18 scope |
| NAV-05 | A VS Code-style user menu at the bottom of the sidebar shows user name/avatar with a popover containing Settings, Theme toggle, and Logout | HTML Popover API for the menu; `GET /api/auth/me` provides user data; backend must pass User to template context; colored initials avatar via CSS |
| NAV-06 | Logout action in user menu ends the session and redirects to login | Existing `handleLogout()` in auth.js calls `POST /api/auth/logout` and redirects to `/login.html` |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Lucide | 0.575.0 | SVG icon library | 1500+ consistent icons, tree-shakable, ISC license, `data-lucide` attribute + `createIcons()` for vanilla JS, same library planned for Phase 15 |
| HTML Popover API | Native | User menu popover | Baseline 2024, 87.5% global support, built-in light-dismiss, no library needed |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| localStorage | Native | Persist sidebar collapse state and section collapse states | On toggle actions, read on page load |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| HTML Popover API | Custom JS dropdown | Popover API is standard, handles focus trapping, light-dismiss, z-index stacking; custom dropdown requires all of this manually |
| CSS Anchor Positioning for popover | Absolute positioning with manual calc | CSS Anchor Positioning is Baseline 2025 (76.65% support, Firefox 147+ only). Use absolute positioning with `bottom: 100%` instead for broader compatibility |
| Lucide CDN (full bundle) | Lucide static (individual SVGs) | CDN bundle (~200KB) is simpler for development; individual SVGs have smaller footprint but require more template complexity. CDN is the user's locked decision |

**CDN Tag:**
```html
<script src="https://unpkg.com/lucide@0.575.0/dist/umd/lucide.min.js"></script>
```

## Architecture Patterns

### Current Sidebar Structure (being replaced)
```
backend/app/templates/
├── base.html                    # Includes _sidebar.html, defines dashboard-layout
├── components/
│   └── _sidebar.html            # 44 lines, flat nav with Unicode emoji icons
frontend/static/css/
├── style.css                    # .sidebar (fixed, 220px), .content-area (margin-left: 220px)
frontend/static/js/
├── workspace.js                 # Ctrl+B currently mapped to togglePane('nav-pane') -- needs remapping
├── auth.js                      # handleLogout() function already exists
```

### Target Sidebar Structure
```
backend/app/templates/
├── base.html                    # Updated: pass user to template context
├── components/
│   └── _sidebar.html            # Restructured: brand, grouped sections, user menu
frontend/static/css/
├── style.css                    # Updated: sidebar collapse transitions, icon rail, user menu
frontend/static/js/
├── sidebar.js                   # NEW: sidebar collapse, section toggle, icon tooltips
├── workspace.js                 # Updated: Ctrl+B remapped to sidebar collapse
├── auth.js                      # Unchanged (handleLogout already works)
```

### Pattern 1: Sidebar Collapse via CSS Transition
**What:** Toggle a CSS class on the sidebar that transitions width from 220px to 48px
**When to use:** Ctrl+B keyboard shortcut or toggle button click
**Example:**
```css
/* Source: standard CSS transition pattern */
.sidebar {
  width: 220px;
  transition: width 0.2s ease;
}

.sidebar.collapsed {
  width: 48px;
}

.sidebar.collapsed .nav-label,
.sidebar.collapsed .section-label,
.sidebar.collapsed .user-name {
  display: none;
}

.content-area {
  margin-left: 220px;
  transition: margin-left 0.2s ease;
}

.sidebar.collapsed ~ .content-area {
  margin-left: 48px;
}
```

**Important:** The existing `.sidebar` uses `position: fixed`, and `.content-area` uses `margin-left: 220px`. The `~` sibling selector will NOT work because `.sidebar` and `.content-area` are not siblings in the DOM (`.sidebar` is inside `.dashboard-layout` alongside `<main class="content-area">`). Instead, toggle a class on the parent `.dashboard-layout` or use a CSS variable approach:

```css
/* Better approach: class on parent container */
.dashboard-layout {
  --sidebar-width: 220px;
}

.dashboard-layout.sidebar-collapsed {
  --sidebar-width: 48px;
}

.sidebar {
  width: var(--sidebar-width);
  transition: width 0.2s ease;
}

.content-area {
  margin-left: var(--sidebar-width);
  transition: margin-left 0.2s ease;
}
```

### Pattern 2: Lucide Icon Initialization with htmx
**What:** Initialize Lucide icons on page load and after htmx content swaps
**When to use:** Always -- sidebar is included in base.html and is not swapped by htmx, but future phases (Phase 13, 15) may use icons in dynamically loaded content
**Example:**
```javascript
// Source: https://lucide.dev/guide/packages/lucide
// Initial icon creation on page load
lucide.createIcons();

// Re-initialize after htmx swaps (scoped to swapped element)
document.addEventListener('htmx:afterSwap', function(e) {
  if (e.detail.target) {
    lucide.createIcons({ root: e.detail.target });
  }
});
```

### Pattern 3: Collapsible Section Headers
**What:** Click a section header to show/hide its child nav items
**When to use:** Each grouped section (Admin, Meta, Apps, Debug)
**Example:**
```html
<div class="sidebar-group" data-group="admin">
  <button class="sidebar-group-header" onclick="toggleSidebarGroup('admin')">
    <i data-lucide="chevron-right" class="group-chevron"></i>
    <span class="group-label">Admin</span>
  </button>
  <div class="sidebar-group-items">
    <a href="/admin/models" class="nav-link">
      <i data-lucide="brain"></i>
      <span class="nav-label">Mental Models</span>
    </a>
    <!-- more items -->
  </div>
</div>
```
```css
.sidebar-group-items {
  overflow: hidden;
  max-height: 500px;
  transition: max-height 0.2s ease;
}

.sidebar-group.collapsed .sidebar-group-items {
  max-height: 0;
}

.sidebar-group.collapsed .group-chevron {
  transform: rotate(0deg);
}

.sidebar-group .group-chevron {
  transform: rotate(90deg);
  transition: transform 0.2s ease;
}
```

### Pattern 4: User Menu with HTML Popover API
**What:** Clicking the user area at sidebar bottom opens a popover with Settings, Theme, Logout
**When to use:** User menu interaction
**Example:**
```html
<div class="sidebar-user" id="user-trigger">
  <button popovertarget="user-popover" class="user-area-btn">
    <span class="user-avatar" style="background-color: #4A90D9;">JD</span>
    <span class="user-name">James Doe</span>
  </button>
</div>

<div popover="auto" id="user-popover" class="user-popover">
  <a href="#" class="popover-item">
    <i data-lucide="settings"></i>
    <span>Settings</span>
  </a>
  <div class="popover-divider"></div>
  <button class="popover-item" onclick="handleLogout()">
    <i data-lucide="log-out"></i>
    <span>Log out</span>
  </button>
</div>
```

**Positioning:** Use absolute positioning relative to the trigger element (avoid CSS Anchor Positioning due to limited Firefox support). The popover should appear above and to the right of the user area:
```css
.user-popover {
  position: fixed;
  bottom: 60px;
  left: 8px;
  width: 200px;
  margin: 0;
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  background: var(--color-surface);
  box-shadow: 0 4px 12px rgba(0,0,0,0.15);
  padding: 4px 0;
}
```

### Pattern 5: Colored Initials Avatar (Google/Slack Style)
**What:** Generate a colored circle with user initials
**When to use:** User area at bottom of sidebar
**Example:**
```javascript
// Source: common pattern for Google/Slack-style avatars
function getInitials(name) {
  if (!name) return '?';
  var parts = name.trim().split(/\s+/);
  if (parts.length >= 2) return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
  return parts[0][0].toUpperCase();
}

function getAvatarColor(name) {
  // Deterministic color based on name hash
  var colors = ['#4A90D9', '#E67E22', '#27AE60', '#8E44AD', '#E74C3C', '#16A085', '#F39C12', '#2C3E50'];
  var hash = 0;
  for (var i = 0; i < name.length; i++) hash = name.charCodeAt(i) + ((hash << 5) - hash);
  return colors[Math.abs(hash) % colors.length];
}
```

### Anti-Patterns to Avoid
- **Putting collapse logic in workspace.js alongside Split.js:** The sidebar collapse is a separate concern from the three-pane workspace layout. The existing Ctrl+B binding in workspace.js calls `togglePane('nav-pane')` (Split.js pane toggle). This must be remapped to the new sidebar collapse function. Keep sidebar logic in a separate `sidebar.js` file.
- **Using `display: none` for collapse animation:** Using `display: none` prevents CSS transitions. Use `width` transition with `overflow: hidden` instead.
- **Inlining user data via JavaScript fetch on every page load:** The sidebar is rendered server-side via Jinja2. Pass the `User` object in the template context rather than making a separate `GET /api/auth/me` call on every page load.
- **Using CSS Anchor Positioning for the popover:** Firefox 147+ only (released very recently). Use fixed/absolute positioning with manual coordinates for broader compatibility.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| SVG icons | Custom SVG sprite or inline SVGs | Lucide via CDN with `data-lucide` | 1500+ consistent icons, automatic replacement, `createIcons({ root })` for scoped init |
| Popover/dropdown menu | Custom JS event listeners, click-outside, z-index | HTML Popover API (`popover="auto"`) | Native light-dismiss, focus management, top-layer stacking, 87.5% browser support |
| Tooltip on hover | Custom tooltip JS library | CSS `title` attribute + optional CSS tooltip | Simplest approach for icon rail tooltips; VS Code uses native OS tooltips |
| Session logout | Custom session management | Existing `handleLogout()` in auth.js | Already calls `POST /api/auth/logout` and redirects |

**Key insight:** The sidebar is a server-rendered Jinja2 partial that does not change between htmx swaps (it is outside `#app-content`). This means initialization happens once on page load, and there is no cleanup/re-initialization concern for the sidebar itself. Lucide `createIcons()` only needs to run once for the sidebar.

## Common Pitfalls

### Pitfall 1: Ctrl+B Conflict with Existing Binding
**What goes wrong:** The workspace.js command palette already has Ctrl+B bound to `togglePane('nav-pane')` which collapses the Split.js nav pane. If both bindings are active, they conflict.
**Why it happens:** The keyboard shortcut was set up for the workspace three-pane layout (Phase 4), but Phase 12 redefines Ctrl+B for sidebar collapse.
**How to avoid:** Remove the `toggle-nav` command palette entry from workspace.js (or rebind it). The sidebar collapse handler should be registered in sidebar.js and should also work on non-workspace pages (e.g., admin, health).
**Warning signs:** Ctrl+B causes two things to happen simultaneously (sidebar collapses AND nav pane hides).

### Pitfall 2: Content-Area Margin Not Transitioning with Sidebar
**What goes wrong:** The `.content-area` has `margin-left: 220px` hardcoded in CSS. When the sidebar collapses, the content area doesn't slide over, leaving a gap.
**Why it happens:** The sidebar uses `position: fixed` and is not in the normal document flow. The content area margin must be updated in sync.
**How to avoid:** Use a CSS custom property `--sidebar-width` on `.dashboard-layout` that both `.sidebar` and `.content-area` reference. Toggle the class on the parent element.
**Warning signs:** Gap appears between collapsed sidebar and content area, or content area jumps instead of transitioning smoothly.

### Pitfall 3: Workspace Split.js Re-initialization After Sidebar Collapse
**What goes wrong:** When the sidebar width changes, the workspace's three Split.js panes may not resize correctly because Split.js calculates sizes based on the container width at initialization time.
**Why it happens:** Split.js uses percentage-based sizing. When the parent container width changes (because `margin-left` changed), the percentage calculations may be off.
**How to avoid:** After sidebar collapse transition ends, trigger a window resize event (`window.dispatchEvent(new Event('resize'))`) so Split.js recalculates. Alternatively, Split.js may handle this automatically since it uses percentage-based flex widths.
**Warning signs:** Split.js panes appear squished or overflow after sidebar toggle.

### Pitfall 4: User Data Not Available in Sidebar Template
**What goes wrong:** The `_sidebar.html` template is included from `base.html` but the current user is not passed in the template context. The user menu cannot show the user's name/initials.
**Why it happens:** Currently, route handlers pass `{"active_page": "home"}` or similar to templates but do NOT pass the `user` object. The sidebar is included via `{% include "components/_sidebar.html" %}` which inherits the parent template's context.
**How to avoid:** Two options: (a) Add middleware that injects the user into all template contexts, or (b) Use a client-side fetch to `/api/auth/me` on page load to populate the user area. Option (a) is cleaner since it is server-rendered. For Jinja2 + FastAPI, a template context processor or Jinja2 global would work. Alternatively, every route handler could pass `user` explicitly -- but this is error-prone and repetitive.
**Warning signs:** User name shows as empty/undefined in the sidebar.

### Pitfall 5: Popover Positioning in Collapsed Sidebar
**What goes wrong:** When the sidebar is collapsed to 48px, the user popover opens at the wrong position (overlapping the sidebar or off-screen).
**Why it happens:** The popover uses fixed positioning based on the full-width sidebar dimensions.
**How to avoid:** Adjust the popover's `left` position based on whether the sidebar is collapsed. Use the sidebar width variable or check for the `collapsed` class.
**Warning signs:** Popover appears behind the sidebar, half off-screen, or at an unexpected position.

### Pitfall 6: Section Collapse State vs Sidebar Collapse State Interaction
**What goes wrong:** When the sidebar is collapsed to icon rail, section collapse states become irrelevant (all items are hidden anyway). But when the sidebar expands again, the sections should restore their previous collapsed/expanded states.
**Why it happens:** If section states are not persisted independently, they may reset when the sidebar expands.
**How to avoid:** Store section collapse states in localStorage separately from the sidebar collapse state. When the sidebar expands, apply the stored section states.
**Warning signs:** Sections all expand when sidebar is un-collapsed, even if user had them collapsed.

## Code Examples

### Backend: Passing User to Template Context
```python
# Source: existing pattern in backend/app/auth/dependencies.py
# Option A: Jinja2 context processor (recommended)
# In main.py, add a global template function:
from app.auth.dependencies import get_current_user

# Simple approach: make user available in all templates
# by having route handlers pass it explicitly
@router.get("/")
async def dashboard(request: Request, user: User = Depends(get_current_user)):
    templates = request.app.state.templates
    return templates.TemplateResponse(
        request, "dashboard.html", {"active_page": "home", "user": user}
    )
```

### Sidebar HTML Template Structure
```html
<!-- Source: pattern based on CONTEXT.md decisions -->
<aside class="sidebar" id="app-sidebar">
    <div class="sidebar-brand">
        <a href="/" hx-get="/" hx-target="#app-content" hx-swap="innerHTML" hx-push-url="true">
            <span class="brand-icon"><i data-lucide="hexagon"></i></span>
            <span class="brand-text">SemPKM</span>
        </a>
        <button class="sidebar-toggle" onclick="toggleSidebar()" title="Toggle sidebar (Ctrl+B)">
            <i data-lucide="panel-left"></i>
        </button>
    </div>

    <nav class="sidebar-nav">
        <!-- Admin section -->
        <div class="sidebar-group" data-group="admin">
            <button class="sidebar-group-header" onclick="toggleSidebarGroup(this)">
                <i data-lucide="chevron-right" class="group-chevron"></i>
                <span class="group-label">Admin</span>
            </button>
            <div class="sidebar-group-items">
                <a href="/admin/models" class="nav-link" data-tooltip="Mental Models">
                    <i data-lucide="brain" class="nav-icon"></i>
                    <span class="nav-label">Mental Models</span>
                </a>
                <!-- Users, Teams items -->
            </div>
        </div>
        <div class="sidebar-divider"></div>
        <!-- More sections: Meta, Apps, Debug -->
    </nav>

    <div class="sidebar-user">
        <button popovertarget="user-popover" class="user-area-btn">
            <span class="user-avatar">{{ user_initials }}</span>
            <span class="user-name">{{ user.display_name or user.email }}</span>
        </button>
    </div>
</aside>

<div popover="auto" id="user-popover" class="user-popover">
    <!-- Settings, Theme toggle, Logout -->
</div>
```

### Recommended Lucide Icon Mapping
```
Admin Section:
  Mental Models  -> brain
  Users          -> users
  Teams          -> users-round (or group)

Meta Section:
  Docs & Tutorials -> book-open

Apps Section:
  Object Browser   -> folder-tree (or folder-open)
  SPARQL Console   -> database

Debug Section:
  Commands         -> terminal
  API Docs         -> file-text
  Health Check     -> heart-pulse (or activity)
  Event Log        -> scroll-text (or list)

Sidebar Controls:
  Toggle collapse  -> panel-left
  Brand logo       -> hexagon (or a custom mark)
  Section chevron  -> chevron-right (rotates 90deg when expanded)

User Menu:
  Settings         -> settings
  Theme toggle     -> sun (or moon)
  Logout           -> log-out
```

### localStorage Keys
```javascript
// Sidebar collapse state
var SIDEBAR_KEY = 'sempkm_sidebar_collapsed';  // 'true' or absent

// Section collapse states
var SECTION_KEY = 'sempkm_sidebar_sections';   // JSON: {"admin": true, "debug": false}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Custom JS dropdown menus | HTML Popover API | 2023-2024 (Baseline 2024) | No need for click-outside listeners, z-index management, or focus trapping |
| Font Awesome / icon fonts | Lucide SVG icons | 2022+ | Tree-shakable, consistent 24x24 grid, no font rendering issues, ISC license |
| jQuery sidebar toggles | CSS transitions + vanilla JS | 2020+ | No jQuery dependency, smoother transitions, less code |
| CSS `display: none` toggle | CSS `width` transition with `overflow: hidden` | Standard practice | Enables smooth animation instead of instant show/hide |

**Deprecated/outdated:**
- Unicode emoji icons for navigation: inconsistent rendering across OSes, no consistent sizing, replaced by SVG icons
- CSS Anchor Positioning for popover placement: too new (Firefox 147+, Feb 2026), use fixed positioning instead

## Open Questions

1. **Admin sub-items routing**
   - What we know: CONTEXT.md says Admin becomes a section with sub-items (Users, Teams, Mental Models). Currently `/admin/` renders an index page with cards linking to `/admin/models` and `/admin/webhooks`. There are no `/admin/users` or `/admin/teams` routes.
   - What's unclear: Should Users and Teams links be added as working routes, or as placeholder links (like Settings)?
   - Recommendation: Add them as placeholder nav links pointing to `/admin/users` and `/admin/teams`. If clicked, show a "Coming soon" placeholder. The admin/index.html dashboard page is being removed, but the existing `/admin/models` and `/admin/webhooks` routes should remain accessible. Consider whether "Webhooks" should also appear in the Admin section.

2. **Event Log nav item**
   - What we know: NAV-03 requires Event Log in the Debug section. The Event Log explorer is Phase 16 scope.
   - What's unclear: Should the nav link be a placeholder, or should it be omitted until Phase 16?
   - Recommendation: Add it as a placeholder link (consistent with Settings and Docs & Tutorials placeholders). Clicking could show a "Coming soon" message in the editor area.

3. **How to pass User to all template contexts**
   - What we know: Every route handler already gets the user via `Depends(get_current_user)`. The sidebar needs user display_name/email for the user menu.
   - What's unclear: Whether to use a Jinja2 context processor, middleware, or explicit passing in every handler.
   - Recommendation: Use a FastAPI middleware that attaches the user to `request.state.user`, then reference it in Jinja2 templates as `request.state.user`. This avoids modifying every route handler. Alternatively, since `_sidebar.html` uses `{% include %}`, all template context from the parent is available -- so passing `user` in each route handler context dict works but requires touching every handler. The middleware approach is cleaner and avoids missing it in new routes.

4. **API Docs consolidation**
   - What we know: Currently there are two API Docs links (ReDoc and Swagger). They use `onclick="return loadDocsIframe()"` to load in an iframe.
   - What's unclear: Should both remain in the sidebar, or consolidate to one?
   - Recommendation: Keep both as sub-items in the Debug section. They use a special iframe loading pattern that must be preserved.

## Sources

### Primary (HIGH confidence)
- Lucide official docs (https://lucide.dev/guide/packages/lucide) - `createIcons()` API, `data-lucide` attribute, `root` parameter for scoped initialization, `createElement()` API
- MDN Popover API (https://developer.mozilla.org/en-US/docs/Web/API/Popover_API/Using) - `popover="auto"`, `popovertarget`, programmatic control, events, CSS styling
- jsDelivr CDN (https://www.jsdelivr.com/package/npm/lucide) - Lucide v0.575.0 (published 2026-02-19)
- Existing codebase analysis - `_sidebar.html`, `base.html`, `style.css`, `workspace.js`, `auth.js`, `cleanup.js`, `auth/router.py`, `auth/models.py`, `shell/router.py`

### Secondary (MEDIUM confidence)
- CanIUse Popover API (https://caniuse.com/mdn-api_htmlelement_popover) - 87.49% global support, Baseline 2024
- CanIUse CSS Anchor Positioning (https://caniuse.com/css-anchor-positioning) - 76.65% global support, Firefox 147+

### Tertiary (LOW confidence)
- None -- all findings verified against official sources

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Lucide docs verified via official site, Popover API verified via MDN
- Architecture: HIGH - Based on direct analysis of existing codebase (`_sidebar.html`, `base.html`, CSS, JS files)
- Pitfalls: HIGH - Identified from codebase inspection (Ctrl+B conflict verified in workspace.js line 578, margin-left issue verified in style.css line 587, user data gap verified by checking all route handlers)

**Research date:** 2026-02-23
**Valid until:** 2026-03-23 (stable domain, no fast-moving dependencies)
