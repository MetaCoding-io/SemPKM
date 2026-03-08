# Phase 45: Obsidian Vault Scanner - Research

**Researched:** 2026-03-08
**Domain:** Obsidian Markdown vault parsing, ZIP upload, SSE progress streaming
**Confidence:** HIGH

## Summary

Phase 45 adds a ZIP-upload-based Obsidian vault scanner that extracts and analyzes markdown files, producing a summary dashboard of file counts, detected note types, frontmatter keys, wiki-link targets, tags, and warnings. The implementation integrates into the existing dockview workspace as a special-panel tab, reuses the established SSE broadcast pattern for progress streaming, and leverages the already-installed `python-frontmatter` library for YAML frontmatter parsing.

The backend work is straightforward Python file processing -- no new dependencies needed beyond what the project already has. The frontend follows established patterns (special-panel tab, htmx partials, SSE via EventSource). The primary complexity is the note type detection heuristic and ensuring the nginx proxy allows large ZIP uploads.

**Primary recommendation:** Build a `backend/app/obsidian/` module with scanner service, dataclasses for scan results, SSE broadcast, and router. Follow the lint module's architecture as the closest structural analog.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- ZIP upload only (no filesystem path option)
- No file size limit -- accept any vault size
- Uploaded vault persists on disk until import completes or user explicitly discards
- Non-markdown files (images, PDFs, attachments) are reported in scan results but not imported
- Workspace tab via dockview special-panel pattern (`openImportTab()`)
- Sidebar "Apps" section gets "Import Vault" link (alongside Object Browser, File Browser)
- Command Palette entry: "Import Vault" via Ctrl+K
- Available to any authenticated member (not owner-restricted)
- Single tab spans all 3 phases: Upload -> Scan Results -> Map (Phase 46) -> Import (Phase 47) -- each phase adds the next step to the same tab
- Summary dashboard layout: big stat numbers at top (notes, tags, links, attachments), then collapsible detail sections
- Collapsible sections for: Frontmatter Keys, Tags, Folders, Wiki-link Targets
- Detail level: key + count + sample values (e.g. "status (142 notes): draft, published, review")
- Progress bar with SSE during scan (stream files-scanned count, current file)
- Warnings section: broken wiki-links, empty notes, malformed frontmatter -- helps user clean up before import
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

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| OBSI-01 | User can upload/point to an Obsidian vault directory for scanning | ZIP upload via FastAPI UploadFile, special-panel tab pattern, sidebar/command palette integration |
| OBSI-02 | Scan results show file count, detected types, frontmatter keys, link targets, and tags | python-frontmatter parsing, wiki-link regex extraction, multi-signal type heuristic, SSE progress streaming |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| python-frontmatter | >=1.1.0 | YAML frontmatter parsing from markdown files | Already in pyproject.toml, proven in VFS module |
| FastAPI UploadFile | (built-in) | Multipart file upload endpoint | Standard FastAPI pattern, python-multipart already in deps |
| zipfile (stdlib) | (built-in) | ZIP archive extraction | Python stdlib, no dependency needed |
| asyncio.Queue + StreamingResponse | (built-in) | SSE progress broadcast | Established pattern in lint/broadcast.py |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| re (stdlib) | (built-in) | Wiki-link and tag regex extraction | Parsing `[[...]]` links and `#tag` patterns from markdown body |
| pathlib (stdlib) | (built-in) | Safe path handling within extracted vault | Directory traversal, extension filtering |
| shutil (stdlib) | (built-in) | Temp directory cleanup on discard | Removing extracted vault files |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| zipfile (stdlib) | streaming-unzip | stdlib is sufficient; vault ZIPs are read entirely anyway since we scan all files |
| python-frontmatter | manual YAML parsing | frontmatter handles edge cases (no frontmatter, malformed YAML, BOM); already proven in codebase |
| re for wiki-links | markdown-it parser | Regex is simpler for extraction-only use case; we don't need to render markdown |

**Installation:**
No new packages needed. All dependencies already present:
- `python-frontmatter>=1.1.0` in pyproject.toml
- `python-multipart` in uv.lock (required by FastAPI for file uploads)

## Architecture Patterns

### Recommended Project Structure
```
backend/app/obsidian/
    __init__.py
    scanner.py       # VaultScanner service: extract, parse, analyze
    models.py        # ScanResult, NoteInfo, VaultSummary dataclasses
    broadcast.py     # ScanBroadcast (copy lint/broadcast.py pattern)
    router.py        # /browser/import routes (upload, scan, SSE stream, discard)
frontend/static/
    css/import.css   # Import tab styles (stat cards, collapsible sections)
backend/app/templates/browser/
    import_page.html     # Upload form + scan results dashboard
    _import_upload.html  # Upload form partial (htmx target)
    _import_results.html # Scan results partial (htmx swap after scan)
```

### Pattern 1: Special-Panel Tab (Dockview)
**What:** Opens the import wizard as a dockview tab, reusing the established special-panel pattern.
**When to use:** Always -- this is the locked UI decision.
**Example:**
```javascript
// workspace.js -- follows openSettingsTab/openVfsTab pattern exactly
function openImportTab() {
    var tabKey = 'special:import';
    var dv = window._dockview;
    if (!dv) return;

    var existing = dv.panels.find(function(p) { return p.id === tabKey; });
    if (existing) { existing.api.setActive(); return; }

    if (!window._tabMeta) window._tabMeta = {};
    window._tabMeta[tabKey] = { label: 'Import Vault', dirty: false };

    dv.api.addPanel({
        id: tabKey,
        component: 'special-panel',
        params: { specialType: 'import', isView: false, isSpecial: true },
        title: 'Import Vault'
    });
}
window.openImportTab = openImportTab;
```

The `createComponentFn` in workspace-layout.js already handles `special-panel` by loading `/browser/{specialType}` via htmx -- so the route `/browser/import` will be loaded automatically.

### Pattern 2: ZIP Upload via FastAPI UploadFile
**What:** First file upload endpoint in the codebase. FastAPI's `UploadFile` with `python-multipart`.
**When to use:** For the vault ZIP upload endpoint.
**Example:**
```python
# router.py
from fastapi import UploadFile, File

@router.post("/import/upload")
async def upload_vault(
    request: Request,
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
):
    # Save to /app/data/imports/{user_id}/{timestamp}/
    # Extract ZIP contents
    # Return htmx partial with scan trigger
    ...
```

### Pattern 3: SSE Progress Stream (Lint Broadcast Clone)
**What:** Fan-out SSE for scan progress, following lint/broadcast.py exactly.
**When to use:** During vault scan to show files-scanned count and current file.
**Example:**
```python
# SSE events during scan
{"event": "scan_progress", "data": {"scanned": 142, "total": 500, "current": "Projects/my-note.md"}}
{"event": "scan_complete", "data": {"summary": {...}}}
{"event": "scan_error", "data": {"message": "..."}}
```

### Pattern 4: htmx Multi-Step Wizard in Single Tab
**What:** The import tab progresses through phases (Upload -> Results -> Map -> Import) by swapping htmx partials within the same tab.
**When to use:** Phase 45 implements Upload -> Results; Phase 46/47 extend the same tab.
**Example:**
```html
<!-- import_page.html -->
<div id="import-container">
    <div id="import-content">
        <!-- Initially shows upload form -->
        {% include "browser/_import_upload.html" %}
    </div>
</div>

<!-- _import_upload.html -->
<form hx-post="/browser/import/upload"
      hx-target="#import-content"
      hx-swap="innerHTML"
      hx-encoding="multipart/form-data">
    <input type="file" name="file" accept=".zip" />
    <button type="submit">Upload & Scan</button>
</form>
```

### Anti-Patterns to Avoid
- **Don't use `hx-target="#app-content"`** for sidebar link: The import tab should use `onclick="openImportTab()"` like settings/VFS, not htmx navigation (which replaces the workspace layout).
- **Don't extract ZIP to a predictable path** without user-scoping: Always include user ID in the extraction path to prevent cross-user access.
- **Don't block the event loop during ZIP extraction/scanning**: Use `asyncio.to_thread()` for synchronous file I/O operations (zipfile, frontmatter parsing).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| YAML frontmatter parsing | Custom YAML+markdown splitter | `python-frontmatter` | Handles BOM, missing frontmatter, malformed YAML gracefully |
| SSE broadcast | Custom event dispatch | Clone `lint/broadcast.py` pattern | Proven fan-out with backpressure handling |
| ZIP extraction | Custom binary parser | `zipfile` stdlib | Handles all ZIP variants, compression methods |
| Multipart upload | Custom form parsing | FastAPI `UploadFile` + `python-multipart` | Handles streaming, temp files, content-type |

**Key insight:** Every piece of infrastructure this phase needs either exists in the codebase already or is available in Python stdlib/FastAPI built-ins. Zero new dependencies.

## Common Pitfalls

### Pitfall 1: nginx Blocks Large Uploads
**What goes wrong:** nginx default `client_max_body_size` is 1MB. Large vaults will get HTTP 413.
**Why it happens:** The catch-all `location /` in nginx.conf has no size override.
**How to avoid:** Add a dedicated `location /browser/import/upload` block in nginx.conf with `client_max_body_size 0` (unlimited, per user decision of no file size limit). Also needs `proxy_request_buffering off` for streaming large uploads without nginx buffering the entire file to disk first.
**Warning signs:** HTTP 413 "Request Entity Too Large" on upload.

### Pitfall 2: Blocking the Event Loop During Scan
**What goes wrong:** Synchronous file I/O (zipfile extraction, frontmatter parsing of hundreds of files) blocks the asyncio event loop, freezing all other requests.
**Why it happens:** `zipfile.extractall()` and `frontmatter.load()` are synchronous stdlib calls.
**How to avoid:** Run the scan in `asyncio.to_thread()` or use `run_in_executor()`. Push SSE progress events from the thread via a thread-safe queue.
**Warning signs:** All API requests hang during scan of a large vault.

### Pitfall 3: ZIP Slip (Path Traversal)
**What goes wrong:** Malicious ZIP files contain entries with `../` paths that extract outside the target directory.
**Why it happens:** `zipfile.extractall()` does NOT validate paths by default in older Python versions (fixed in 3.12+ with `filter='data'`).
**How to avoid:** Use `zipfile.extractall(path, filter='data')` (Python 3.12+) or validate each member path before extraction. The project uses Python 3.12+ based on the Dockerfile.
**Warning signs:** Files appearing outside the expected extraction directory.

### Pitfall 4: SSE Needs Dedicated nginx Location Block
**What goes wrong:** nginx buffers SSE responses, causing progress updates to arrive in batches instead of real-time.
**Why it happens:** The default `location /` proxy does not have `proxy_buffering off`.
**How to avoid:** Add a dedicated `location /browser/import/scan/stream` block with `proxy_buffering off`, `X-Accel-Buffering: no`, same pattern as lint SSE and LLM streaming blocks.
**Warning signs:** Progress bar jumps from 0% to 100% with no intermediate updates.

### Pitfall 5: Obsidian Frontmatter Field Casing Variations
**What goes wrong:** Type detection misses notes because users use "Type", "TYPE", "type" inconsistently.
**Why it happens:** YAML keys are case-sensitive by spec.
**How to avoid:** Normalize frontmatter keys to lowercase before matching against type-detection fields.
**Warning signs:** Notes incorrectly classified as "Uncategorized" despite having type frontmatter.

### Pitfall 6: Wiki-Link Regex Edge Cases
**What goes wrong:** Regex misses or double-counts links embedded in code blocks, or matches `![[embeds]]` as regular links.
**Why it happens:** Simple regex doesn't understand markdown structure.
**How to avoid:** For this phase (scan summary only), approximate counts are acceptable. Exclude `![[...]]` embeds from wiki-link count (separate embed count). Skip content inside triple-backtick code blocks.
**Warning signs:** Link counts significantly higher than expected (counting code examples).

## Code Examples

### Wiki-Link Extraction Regex
```python
import re

# Match [[target]], [[target|alias]], [[target#heading]], [[target#heading|alias]]
# Excludes ![[embeds]] via negative lookbehind
WIKILINK_RE = re.compile(r'(?<!!)\[\[([^\]\|#]+)(?:#[^\]\|]*)?\s*(?:\|[^\]]*)?\]\]')

# Match #tag (Obsidian tags: alphanumeric, hyphens, underscores, slashes, no leading digit)
# Must be preceded by whitespace or start of line
TAG_RE = re.compile(r'(?:^|\s)#([a-zA-Z][a-zA-Z0-9_/-]*)', re.MULTILINE)

def extract_wikilinks(content: str) -> list[str]:
    """Extract wiki-link targets from markdown content, skipping code blocks."""
    # Strip fenced code blocks first
    cleaned = re.sub(r'```[\s\S]*?```', '', content)
    return WIKILINK_RE.findall(cleaned)

def extract_tags(content: str) -> list[str]:
    """Extract #tags from markdown body (not frontmatter -- those come from YAML)."""
    cleaned = re.sub(r'```[\s\S]*?```', '', content)
    return TAG_RE.findall(cleaned)
```

### Frontmatter Type Detection
```python
# Recommended fields to check for note type (Claude's discretion)
TYPE_FIELDS = ["type", "category", "class", "kind", "note_type", "notetype"]

def detect_note_type(
    frontmatter: dict,
    folder_path: str,
    body_tags: list[str],
    fm_tags: list[str],
) -> tuple[str, str]:
    """Detect note type using multi-signal heuristic.

    Returns (detected_type, signal_source) e.g. ("project", "frontmatter:type")
    """
    # Signal 1: Explicit frontmatter type field (highest priority)
    fm_lower = {k.lower(): v for k, v in frontmatter.items()}
    for field in TYPE_FIELDS:
        if field in fm_lower and fm_lower[field]:
            value = str(fm_lower[field]).strip()
            if value:
                return (value, f"frontmatter:{field}")

    # Signal 2: Folder name (second priority)
    # Use the immediate parent folder name
    parts = folder_path.strip("/").split("/")
    if parts and parts[-1]:
        folder_name = parts[-1]
        # Skip common non-type folders
        skip_folders = {"attachments", "assets", "images", "templates", "archive", "daily", "inbox"}
        if folder_name.lower() not in skip_folders:
            return (folder_name, "folder")

    # Signal 3: Tags (tertiary)
    all_tags = fm_tags + body_tags
    if all_tags:
        # Use first tag as type hint
        return (all_tags[0], "tag")

    return ("Uncategorized", "none")
```

### ScanResult Dataclass
```python
from dataclasses import dataclass, field

@dataclass
class FrontmatterKeySummary:
    key: str
    count: int
    sample_values: list[str]  # Up to 5 unique sample values

@dataclass
class TagSummary:
    tag: str
    count: int

@dataclass
class NoteTypeGroup:
    type_name: str
    signal_source: str  # "frontmatter:type", "folder", "tag", "none"
    count: int
    sample_notes: list[str]  # Up to 10 note paths

@dataclass
class ScanWarning:
    severity: str  # "warning", "info"
    category: str  # "broken_link", "empty_note", "malformed_frontmatter"
    message: str
    file_path: str

@dataclass
class VaultScanResult:
    """Complete scan result, persisted as JSON for Phase 46/47."""
    vault_name: str
    total_files: int
    markdown_files: int
    attachment_files: int
    other_files: int
    folders: list[str]
    type_groups: list[NoteTypeGroup]
    frontmatter_keys: list[FrontmatterKeySummary]
    tags: list[TagSummary]
    wikilink_targets: list[tuple[str, int]]  # (target, count)
    warnings: list[ScanWarning]
    scan_duration_seconds: float
    extract_path: str  # Absolute path to extracted vault for Phase 46/47
```

### Upload and Extract Pattern
```python
import zipfile
import tempfile
from pathlib import Path

IMPORT_BASE = Path("/app/data/imports")

async def handle_upload(file: UploadFile, user_id: int) -> Path:
    """Save uploaded ZIP and extract to user-scoped directory."""
    import_dir = IMPORT_BASE / str(user_id) / str(int(time.time()))
    import_dir.mkdir(parents=True, exist_ok=True)

    zip_path = import_dir / "vault.zip"
    extract_path = import_dir / "vault"

    # Stream upload to disk (don't hold entire ZIP in memory)
    async with aiofiles.open(zip_path, 'wb') as f:
        while chunk := await file.read(8192):
            await f.write(chunk)

    # Extract in thread to avoid blocking event loop
    def _extract():
        with zipfile.ZipFile(zip_path, 'r') as zf:
            zf.extractall(extract_path, filter='data')  # Safe extraction
        # Remove ZIP after extraction to save space
        zip_path.unlink()

    await asyncio.to_thread(_extract)
    return extract_path
```

### SSE Progress Pattern
```python
# Recommended SSE events and frequency
# Emit progress every 10 files or every 500ms, whichever comes first
# Events:
#   scan_progress: {scanned: int, total: int, current_file: str}
#   scan_complete: {result_id: str}  -- client fetches full results via htmx
#   scan_error:    {message: str}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Obsidian YAML frontmatter | Obsidian "Properties" (still YAML) | Obsidian v1.4 (2023) | Same wire format, just new UI in Obsidian. Parser unchanged. |
| `zipfile.extractall()` unsafe | `filter='data'` param for safe extraction | Python 3.12 | Must use `filter='data'` to prevent ZIP slip attacks |

**Deprecated/outdated:**
- Obsidian's `cssclass` frontmatter key was renamed to `cssclasses` (plural) in Obsidian 1.4. Scanner should recognize both.
- Obsidian supports both `tag` and `tags` as frontmatter keys. Scanner must check both.

## Open Questions

1. **aiofiles dependency**
   - What we know: The upload streaming pattern benefits from async file writes to avoid blocking the event loop while saving the ZIP.
   - What's unclear: Whether `aiofiles` is already in dependencies.
   - Recommendation: Check pyproject.toml. If not present, use `asyncio.to_thread()` with regular `open()` instead -- avoids adding a new dependency for one use case.

2. **Nested ZIP root folder**
   - What we know: Many ZIP tools wrap contents in a single root folder (e.g., `my-vault/` containing all files). Obsidian vaults exported from backup plugins may or may not have this.
   - What's unclear: Whether the scanner should auto-detect and skip the wrapper folder.
   - Recommendation: After extraction, check if there's a single top-level directory containing `.obsidian/`. If so, use that as the vault root. If `.obsidian/` is at the extraction root, use extraction root.

3. **Concurrent imports per user**
   - What we know: The tab is singleton (dockview reuses existing panel).
   - What's unclear: Whether to prevent a second upload while a scan is in progress.
   - Recommendation: Allow only one active import per user. If an import directory already exists, show "Resume" or "Discard & Start Over" options.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | Playwright (e2e only -- no backend unit tests exist) |
| Config file | `e2e/playwright.config.ts` |
| Quick run command | `cd /home/james/Code/SemPKM/e2e && npx playwright test --project=chromium -g "import"` |
| Full suite command | `cd /home/james/Code/SemPKM/e2e && npx playwright test --project=chromium` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| OBSI-01 | Upload ZIP, vault extracted, tab opens | e2e | `npx playwright test --project=chromium e2e/tests/14-obsidian-import/01-upload.spec.ts` | No -- Wave 0 |
| OBSI-02 | Scan results show counts, types, keys, links, tags | e2e | `npx playwright test --project=chromium e2e/tests/14-obsidian-import/02-scan-results.spec.ts` | No -- Wave 0 |

### Sampling Rate
- **Per task commit:** Manual verification via Docker stack (port 3000)
- **Per wave merge:** Full e2e suite
- **Phase gate:** Full suite green before verify

### Wave 0 Gaps
- [ ] `e2e/tests/14-obsidian-import/01-upload.spec.ts` -- covers OBSI-01 (upload + tab)
- [ ] `e2e/tests/14-obsidian-import/02-scan-results.spec.ts` -- covers OBSI-02 (scan results display)
- [ ] Test fixture: small Obsidian vault ZIP with known content (5-10 notes, frontmatter, wiki-links, tags)
- [ ] Note: E2e test files cannot be modified per project convention, but can be created fresh

## Sources

### Primary (HIGH confidence)
- Codebase inspection: `backend/app/lint/broadcast.py` -- SSE broadcast pattern
- Codebase inspection: `frontend/static/js/workspace.js` -- special-panel tab pattern (openSettingsTab, openVfsTab)
- Codebase inspection: `frontend/static/js/workspace-layout.js` -- createComponentFn special-panel handling
- Codebase inspection: `backend/app/vfs/resources.py` -- python-frontmatter usage
- Codebase inspection: `frontend/nginx.conf` -- proxy configuration, SSE blocks, client_max_body_size
- Codebase inspection: `docker-compose.yml` -- volume mounts, `/app/data` persistent storage
- Codebase inspection: `backend/pyproject.toml` -- existing dependencies

### Secondary (MEDIUM confidence)
- [Obsidian Help - How Obsidian stores data](https://help.obsidian.md/Files+and+folders/How+Obsidian+stores+data) -- vault structure
- [Obsidian Help - Properties](https://help.obsidian.md/Editing+and+formatting/Properties) -- frontmatter/properties format
- [DeepWiki - Markdown Formatting and Syntax](https://deepwiki.com/obsidianmd/obsidian-help/4.1-markdown-formatting-and-syntax) -- wiki-link syntax

### Tertiary (LOW confidence)
- Wiki-link regex patterns from community implementations -- validated against known Obsidian syntax

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all libraries already in the project, zero new deps
- Architecture: HIGH -- follows established patterns (special-panel, SSE broadcast, htmx partials)
- Pitfalls: HIGH -- nginx upload size, event loop blocking, ZIP slip are well-documented issues
- Wiki-link regex: MEDIUM -- based on community patterns, covers main cases but edge cases possible

**Research date:** 2026-03-08
**Valid until:** 2026-04-08 (stable domain, no fast-moving dependencies)
