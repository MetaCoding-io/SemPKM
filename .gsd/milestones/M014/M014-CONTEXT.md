---
depends_on: [M013]
---

# M014: Browser Extension Phase 1 — Smart Structured Capture

**Gathered:** 2026-03-16
**Status:** Queued — pending auto-mode execution

## Project Description

Chrome/Firefox browser extension for capturing typed, schema-validated objects from any web page. Popup UI with dynamic SHACL-driven forms, type selector populated from installed Mental Models, auto-population from page metadata and schema.org JSON-LD, relationship picker for linking to existing objects, and context menu integration for quick capture of selected text.

## Why This Milestone

Every PKM tool has a web clipper, but none offer structured capture with schema enforcement at clip time. Notion's clipper (1M+ users, 3.4★) can't set database properties during capture. SemPKM's extension captures typed objects with full SHACL forms — the user sets properties, creates relationships, and gets validation before the object reaches the graph.

## User-Visible Outcome

### When this milestone is complete, the user can:

- Click the SemPKM extension icon (or press Alt+S) to open a capture popup
- Select a type from installed Mental Models (Note, Concept, Contact, Paper, etc.)
- See a dynamic form generated from SHACL shapes with helptext, grouped fields, and validation
- Have title, URL, selected text, and author auto-populated from page metadata
- Search existing objects to create typed relationships at capture time
- Right-click selected text → "Save to SemPKM" for quick capture
- Configure instance URL and API key in extension settings
- See success/error feedback after saving

### Entry point / environment

- Entry point: Browser extension popup, context menu, keyboard shortcut (Alt+S)
- Environment: Chrome (Manifest V3), Firefox (WebExtension)
- Live dependencies involved: SemPKM instance (local or remote) via M013 API endpoints

## Completion Class

- Contract complete means: extension installs in Chrome and Firefox, popup renders SHACL forms correctly for all standard property types, objects are created via POST /api/commands
- Integration complete means: forms match the web app's SHACL forms, objects appear in object browser after capture, relationships link to real existing objects
- Operational complete means: extension works against local Docker instance and would work against any remote instance with API key auth

## Final Integrated Acceptance

To call this milestone complete, we must prove:

- User installs extension, configures localhost:3000, and captures a Note from a web page
- Type selector shows types from all installed Mental Models
- Selecting "Contact" (CRM model) renders CRM-specific fields (name, email, company, relationship)
- Schema.org Person data from a LinkedIn page auto-fills Contact fields
- User creates a relationship between the captured object and an existing Concept
- Object appears in SemPKM workspace with all properties and relationships intact

## Risks and Unknowns

- **SHACL form rendering in extension** — Must duplicate (simplified) form rendering logic from Jinja2 templates in vanilla JS. Won't support every SHACL edge case — just the common property types used in standard models.
- **Chrome Manifest V3 restrictions** — Service workers replace background pages. Limited execution context. Must handle API calls from service worker, not content script.
- **Cross-origin requests** — Extension needs to call SemPKM API from any page. Chrome extensions have `host_permissions` for this, but CORS still matters for preflight requests.

## Existing Codebase / Prior Art

- `.gsd/design/BROWSER-EXTENSION-DESIGN.md` — Full architecture, Phase 1 flow, SHACL renderer spec, data flow diagrams
- `backend/app/services/shapes.py` — ShapesService (source of truth for what the extension's form renderer must replicate)
- M013 endpoints — `/api/types`, `/api/shapes/{type}`, `/.well-known/sempkm`

> See `.gsd/DECISIONS.md` for all architectural and pattern decisions.

## Relevant Requirements

- New: EXT-01 (popup capture), EXT-02 (SHACL forms), EXT-03 (auto-population), EXT-04 (relationship picker), EXT-05 (context menu), EXT-06 (schema.org ingestion)

## Scope

### In Scope

- Chrome Manifest V3 extension structure
- Firefox WebExtension compatibility (95% shared codebase)
- Popup UI: type selector, dynamic SHACL form, save button
- SHACL form renderer in JS (string, date, boolean, enum, object reference, multi-value)
- Auto-population from page metadata (title, URL, author, selected text, schema.org JSON-LD)
- Relationship picker with object search via SPARQL
- Context menu "Save to SemPKM" for selected text
- Keyboard shortcut (Alt+S configurable)
- Settings page: instance URL, API key, default type, auto-fill preferences
- Instance connection test and status indicator
- Success/error toast notifications

### Out of Scope / Non-Goals

- Context overlay sidebar (Phase 2 — M015)
- AI-powered suggestions (Phase 3 — M028)
- Safari extension
- Offline capture queue
- Mobile browser extension

## Technical Constraints

- Vanilla JS (no React/Vue — keep it lightweight)
- Chrome Manifest V3 (service worker, no persistent background page)
- Must work with both API key and session cookie auth
- Extension popup has limited viewport (~400px wide)
- All API calls via M013 endpoints

## Integration Points

- **M013 API endpoints** — types, shapes, context-query, well-known discovery
- **POST /api/commands** — object creation
- **POST /api/sparql** — relationship search
- **IndieAuth** — OAuth2 flow for cloud instances
- **API key auth** — bearer token for local instances

## Open Questions

- **Extension distribution** — Chrome Web Store from day one, or sideload-only initially? Current thinking: sideload for early adopters, Web Store once stable.
- **Form subset** — Which SHACL features to support in the extension renderer? Current thinking: string, date, boolean, enum (sh:in), object reference (sh:class), multi-value, required indicator, groups, helptext. Skip: regex patterns, complex cardinality, nested shapes.
