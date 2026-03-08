# Phase 45: Obsidian Vault Scanner - Context

**Gathered:** 2026-03-08
**Status:** Ready for planning

<domain>
## Phase Boundary

Users can upload an Obsidian vault (as ZIP) and see a clear summary of what it contains — file count, detected note categories, frontmatter keys, wiki-link targets, tags, and potential issues. No configuration or mapping decisions required at this stage (mapping is Phase 46, import is Phase 47). The scan results persist on disk so subsequent phases can reference them without re-uploading.

</domain>

<decisions>
## Implementation Decisions

### Vault Input Method
- ZIP upload only (no filesystem path option)
- No file size limit — accept any vault size
- Uploaded vault persists on disk until import completes or user explicitly discards
- Non-markdown files (images, PDFs, attachments) are reported in scan results but not imported

### UI Location
- Workspace tab via dockview special-panel pattern (`openImportTab()`)
- Sidebar "Apps" section gets "Import Vault" link (alongside Object Browser, File Browser)
- Command Palette entry: "Import Vault" via Ctrl+K
- Available to any authenticated member (not owner-restricted)
- Single tab spans all 3 phases: Upload → Scan Results → Map (Phase 46) → Import (Phase 47) — each phase adds the next step to the same tab

### Scan Results Display
- Summary dashboard layout: big stat numbers at top (notes, tags, links, attachments), then collapsible detail sections
- Collapsible sections for: Frontmatter Keys, Tags, Folders, Wiki-link Targets
- Detail level: key + count + sample values (e.g. "status (142 notes): draft, published, review")
- Progress bar with SSE during scan (stream files-scanned count, current file)
- Warnings section: broken wiki-links, empty notes, malformed frontmatter — helps user clean up before import

### Note Type Detection
- Multi-signal heuristic: frontmatter field > folder structure > tags
- Priority: explicit frontmatter "type"/"category" field wins, folder name as fallback, tags as tertiary signal
- Scan results group notes by detected category with expandable note lists per group
- Notes matching no signal go to explicit "Uncategorized" group (user assigns type during Phase 46 mapping)

### Claude's Discretion
- Exact frontmatter field names to check for type detection (e.g. "type", "category", "class", "kind")
- Temp storage location for extracted vault files
- SSE event format and progress update frequency
- ZIP extraction strategy (streaming vs full extract)
- Exact stat card styling and collapsible section UI details

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `python-frontmatter` library: Already used in VFS module for Markdown+YAML parsing (`backend/app/vfs/resources.py`)
- SSE broadcast pattern: `backend/app/lint/broadcast.py` — asyncio.Queue fan-out, 30s keepalive. Reuse for scan progress
- Special-panel tab pattern: `workspace.js` openSettingsTab/openVfsTab — template for `openImportTab()`
- Command Palette registration: `ninja-keys` with `window._commandPaletteCommands` array

### Established Patterns
- Special tabs: `openXxxTab()` → dockview `special-panel` → `workspace-layout.js` createComponentFn → `htmx.ajax('GET', '/browser/{specialType}', ...)`
- Admin/browser routes: Dual response (full page or htmx partial via `block_name="content"`)
- File uploads: No existing multipart/form-data pattern — FastAPI `UploadFile` will be new
- Model install: `InstallResult` dataclass with success/errors/warnings — good pattern for `ScanResult`

### Integration Points
- Sidebar "Apps" section: `backend/app/templates/components/_sidebar.html` lines 67-89
- Browser router: `backend/app/browser/router.py` — add `/browser/import` route
- Command Palette: `workspace.js` commands array — add "Import Vault" entry
- Scan data persisted for Phase 46-47: likely as JSON in a temp/import directory

</code_context>

<specifics>
## Specific Ideas

- Dashboard layout inspired by the lint dashboard summary bar (big numbers at top, details below)
- "Uncategorized" group should be visually distinct so user knows these need attention during mapping
- Warnings section similar to lint panel's severity badges — count + expandable details

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 45-obsidian-vault-scanner*
*Context gathered: 2026-03-08*
