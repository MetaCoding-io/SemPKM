# Phase 47: Obsidian Batch Import - Research

**Researched:** 2026-03-08
**Domain:** Backend import executor, Command API integration, SSE progress, wiki-link/tag resolution
**Confidence:** HIGH

## Summary

Phase 47 implements the batch import executor that reads the scan result and mapping configuration produced by Phases 45-46, then creates RDF objects and edges via the internal Command API. The architecture is straightforward: a new `ImportExecutor` class in the obsidian module that reads notes from disk, applies the mapping config, calls command handlers directly (not via HTTP), and broadcasts progress via the existing SSE fan-out pattern.

The key technical challenges are: (1) wiki-link resolution requiring a two-pass approach (create all objects first, then resolve links between them), (2) efficient batching to avoid overwhelming the triplestore with per-note transactions while keeping progress granular, and (3) the re-import deduplication query using `sempkm:importSource` property lookups.

**Primary recommendation:** Build a single `ImportExecutor` class that calls command handlers (`handle_object_create`, `handle_body_set`, `handle_edge_create`) directly to produce `Operation` objects, then commits them via `EventStore.commit()` in small batches (5-10 objects per transaction). This avoids HTTP overhead and keeps the import within a single authenticated context.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Wiki-link predicate: `dcterms:references` for all wiki-link-derived edges (one-way only)
- Unresolved wiki-link targets: Skip the edge, collect in unresolved links report
- Wiki-link aliases (`[[note|display text]]`): Store display text as `rdfs:label` annotation on the edge
- Wiki-link resolution: Match against note filenames (sans extension) within the import set
- Tag representation: Plain literal property values using `schema:keywords` (one per tag, multi-valued), NOT edges to Concept objects
- Nested tags: Preserve full path (e.g., `#project/active` -> `"project/active"`), strip `#` prefix
- Tags from frontmatter `tags:` field and inline `#tag` syntax treated identically
- Batching: Per-object batches (object.create + body.set + properties per note), second pass for edges
- Progress UX: Progress bar with live scrolling log via SSE broadcast (reuse scan progress pattern)
- Progress events: Object count (X/N), current note filename, phase indicator (objects -> edges)
- Post-import summary: Counts (created, skipped-errors, skipped-existing, edges created, unresolved links) + "Browse Imported Objects" button
- Error handling: Skip failures and continue, no rollback, report all in summary
- Re-import: Store `sempkm:importSource` property on each imported object, query on re-import to skip existing
- Import directory: Keep on disk until user explicitly discards

### Claude's Discretion
- Exact SSE event format and update frequency
- Command API batch composition details (how many commands per batch call)
- Edge batch sizing for wiki-link pass
- "Browse Imported Objects" button behavior (open nav tree, table view, etc.)
- Error detail formatting in summary
- How to handle edge cases (empty body notes, notes with only frontmatter, etc.)

### Deferred Ideas (OUT OF SCOPE)
None
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| OBSI-06 | Batch import creates objects with bodies, properties, and edges via Command API | ImportExecutor calls handle_object_create + handle_body_set + properties directly, commits via EventStore; edge pass uses handle_edge_create for wiki-links |
| OBSI-07 | Wiki-links and tags are resolved to edges between imported objects | Wiki-links resolved by filename matching within import set -> dcterms:references edges; tags stored as schema:keywords literal values on each object |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| python-frontmatter | (existing) | Parse Obsidian note frontmatter + body | Already used by scanner and preview step |
| rdflib | (existing) | Build RDF triples for Command API operations | Core SemPKM dependency |
| asyncio | stdlib | Background thread execution, SSE broadcast | Existing pattern from scanner |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| ScanBroadcast / SSEEvent | (existing) | SSE progress fan-out | Reuse for import progress streaming |
| EventStore | (existing) | Atomic triple commits | Each batch committed via EventStore.commit() |
| Command handlers | (existing) | handle_object_create, handle_body_set, handle_edge_create | Direct invocation, not HTTP |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Direct handler calls | HTTP POST to /api/commands | HTTP adds overhead, auth complexity, and cookie forwarding; direct calls are simpler and faster |
| Per-object transactions | Single giant transaction | Giant transactions risk timeout; per-object or small-batch keeps progress granular and errors isolated |

## Architecture Patterns

### Recommended Project Structure
```
backend/app/obsidian/
    executor.py        # NEW: ImportExecutor class
    router.py          # ADD: import trigger + stream + summary endpoints
    broadcast.py       # REUSE: ScanBroadcast / SSEEvent (as-is or rename to ImportBroadcast)
    models.py          # ADD: ImportResult dataclass
    scanner.py         # EXISTING: no changes
```

### Pattern 1: Direct Command Handler Invocation
**What:** Call command handlers directly instead of going through the HTTP API
**When to use:** Server-side batch operations that already have an authenticated user context
**Example:**
```python
from app.commands.handlers.object_create import handle_object_create
from app.commands.handlers.body_set import handle_body_set
from app.commands.handlers.edge_create import handle_edge_create
from app.commands.schemas import ObjectCreateParams, BodySetParams, EdgeCreateParams
from app.events.store import EventStore, Operation
from app.config import settings

# Create object + set body in one atomic batch
ops: list[Operation] = []

create_op = await handle_object_create(
    ObjectCreateParams(
        type=type_iri,
        slug=slug,
        properties={"dcterms:title": title, "schema:keywords": tag_value, "sempkm:importSource": vault_path},
    ),
    settings.base_namespace,
)
ops.append(create_op)
object_iri = create_op.affected_iris[0]

if body_text.strip():
    body_op = await handle_body_set(
        BodySetParams(iri=object_iri, body=body_text),
        settings.base_namespace,
    )
    ops.append(body_op)

event_store = EventStore(client)
user_iri = URIRef(f"urn:sempkm:user:{user.id}")
await event_store.commit(ops, performed_by=user_iri, performed_by_role=user.role)
```

### Pattern 2: Two-Pass Import (Objects then Edges)
**What:** First pass creates all objects and builds a filename-to-IRI lookup table. Second pass creates wiki-link edges using the lookup table.
**When to use:** Always -- edges require both source and target objects to exist first.
**Example:**
```python
# Pass 1: Create objects, build lookup
filename_to_iri: dict[str, str] = {}  # lowercase stem -> object IRI

for note in notes:
    stem = Path(note.path).stem.lower()
    # ... create object via handler ...
    filename_to_iri[stem] = object_iri

# Pass 2: Create edges for wiki-links
for note in notes:
    source_iri = filename_to_iri[Path(note.path).stem.lower()]
    for link_target, alias in note.wiki_links:
        target_stem = link_target.lower()
        if target_stem in filename_to_iri:
            target_iri = filename_to_iri[target_stem]
            edge_props = {}
            if alias:
                edge_props["rdfs:label"] = alias
            edge_op = await handle_edge_create(
                EdgeCreateParams(
                    source=source_iri,
                    target=target_iri,
                    predicate="dcterms:references",
                    properties=edge_props,
                ),
                settings.base_namespace,
            )
            # ... commit edge batch ...
        else:
            unresolved_links.append((note.path, link_target))
```

### Pattern 3: SSE Progress Reuse (Scan Pattern)
**What:** Reuse the `ScanBroadcast` / `stream_sse` pattern for import progress
**When to use:** For the import progress streaming
**Example:**
```python
# Terminal events for import (extend stream_sse or use separate terminal events)
# Recommended terminal events: "import_complete", "import_error"
# Progress events: "import_progress"

broadcast.publish(SSEEvent(
    event="import_progress",
    data={
        "phase": "objects",  # or "edges"
        "current": i,
        "total": total_notes,
        "current_file": note_path,
    },
))
```

### Pattern 4: Multi-valued Properties for Tags
**What:** The `properties` dict in `ObjectCreateParams` accepts single values. For multi-valued `schema:keywords`, need to create multiple triples manually or extend the approach.
**When to use:** When a note has multiple tags
**Important detail:** The `handle_object_create` handler calls `_to_rdf_value(value)` for each property entry. For multi-valued properties, the executor should add tag triples directly to the Operation rather than going through the properties dict, OR iterate and add one property per tag to the operation's triples list.
**Example:**
```python
# Option A: Build triples manually for multi-valued properties
from app.commands.handlers.object_create import _resolve_predicate, _to_rdf_value

create_op = await handle_object_create(
    ObjectCreateParams(type=type_iri, slug=slug, properties=base_props),
    settings.base_namespace,
)
# Add extra tag triples
subject = URIRef(create_op.affected_iris[0])
keywords_pred = _resolve_predicate("schema:keywords")
for tag in tags:
    triple = (subject, keywords_pred, Literal(tag))
    create_op.data_triples.append(triple)
    create_op.materialize_inserts.append(triple)
```

### Anti-Patterns to Avoid
- **HTTP round-trips for batch import:** Do NOT call POST /api/commands in a loop from the backend. Use direct handler invocation.
- **Single giant transaction:** Do NOT batch all objects into one EventStore.commit() call. RDF4J transactions can timeout. Batch 5-10 objects per commit.
- **Blocking the event loop:** The import executor MUST run in a background thread (via `asyncio.to_thread`), same as the scanner. Handler calls are async, so use `asyncio.run_coroutine_threadsafe()` or structure as an async function.
- **Forgetting validation queue:** Each EventStore.commit() normally triggers async SHACL validation. For bulk import, consider whether to enqueue validation per-batch or skip during import and validate once afterward. The current command router enqueues per commit -- the executor should do the same for consistency.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Object IRI minting | Custom IRI generation | `mint_object_iri()` from `app.rdf.iri` | Handles slug encoding, UUID fallback, namespace prefixing |
| Edge IRI minting | Custom edge IDs | `mint_edge_iri()` from `app.rdf.iri` | Consistent UUID-based edge IRIs |
| Predicate resolution | Manual IRI expansion | `_resolve_predicate()` from object_create handler | Handles compact IRIs, full IRIs, local names |
| RDF value conversion | Type-specific literal building | `_to_rdf_value()` from object_create handler | Handles strings, numbers, booleans, URIs, dateTime detection |
| SSE broadcasting | Custom WebSocket impl | `ScanBroadcast` + `stream_sse()` | Thread-safe fan-out, keepalive, terminal events |
| Frontmatter parsing | Custom YAML extraction | `python-frontmatter` library | Already used by scanner, handles edge cases |
| Wiki-link extraction | Custom regex | `WIKILINK_RE` from scanner.py | Already tested, handles aliases, headings, excludes embeds |
| Tag extraction | Custom regex | `TAG_RE` from scanner.py | Handles inline tags, already tested |
| Code block stripping | Custom approach | `CODE_BLOCK_RE` from scanner.py | Prevents false matches inside code blocks |

**Key insight:** Almost every low-level operation needed for import already exists in the codebase. The executor is primarily orchestration and data flow, not new primitives.

## Common Pitfalls

### Pitfall 1: Async/Thread Boundary
**What goes wrong:** The import executor needs to run potentially long operations, but command handlers are async. Running `asyncio.to_thread()` for the whole import then trying to call async handlers from a sync thread fails.
**Why it happens:** Python async/sync boundary confusion.
**How to avoid:** Keep the executor as an async function. Use `asyncio.to_thread()` only for synchronous I/O (file reading with python-frontmatter). The async event loop handles the EventStore commits directly. The broadcast.publish() is already thread-safe.
**Warning signs:** `RuntimeError: no running event loop` errors.

### Pitfall 2: Wiki-Link Regex Needs Alias Extraction
**What goes wrong:** The scanner's `WIKILINK_RE` captures only the target name (group 1), not the alias text. The import executor needs both target AND alias for edge annotations.
**Why it happens:** Scanner only needed target names for counting; import needs the full match.
**How to avoid:** Create an enhanced regex or use a separate regex for import that captures both groups: `(?<!!)\[\[([^\]\|#]+)(?:#[^\]\|]*)?\s*(?:\|([^\]]*))?\]\]` (group 1 = target, group 2 = alias).
**Warning signs:** Alias always None, no `rdfs:label` on edges.

### Pitfall 3: ObjectCreateParams Properties Dict is Single-Valued
**What goes wrong:** `properties: dict[str, Any]` maps predicate -> single value. Tags need multiple values for `schema:keywords`.
**Why it happens:** The Command API was designed for form-based single-value property setting.
**How to avoid:** Either (a) accept a list value and extend handle_object_create to iterate, or (b) add tag triples directly to the Operation's triple lists after handler call. Option (b) is simpler and avoids modifying the general-purpose handler.
**Warning signs:** Only the last tag appears on imported objects.

### Pitfall 4: Slug Collisions on Re-import
**What goes wrong:** If notes have identical filenames across different folders, slug-based IRI minting could collide.
**Why it happens:** `mint_object_iri()` uses the slug directly -- two notes named "README.md" in different folders get the same slug.
**How to avoid:** Use the full relative vault path (with `/` replaced by `-`) as the slug, or let the slug be None (UUID fallback) and only use the `sempkm:importSource` property for deduplication.
**Warning signs:** 409 Conflict errors or objects overwriting each other.

### Pitfall 5: Large SPARQL Strings with Body Content
**What goes wrong:** Markdown bodies can contain special characters (`"`, `\`, newlines) that break SPARQL INSERT DATA statements.
**Why it happens:** Body content passed through `_serialize_rdf_term()` which escapes these, but very large bodies (>100KB) can hit RDF4J request size limits.
**How to avoid:** The existing `_serialize_rdf_term()` handles escaping correctly. For very large bodies, the per-object batching keeps each SPARQL statement to a single body's worth of data, which is manageable. No special handling needed unless vaults contain extremely large notes.
**Warning signs:** HTTP 413 or timeout errors on specific notes.

### Pitfall 6: Deduplication Query Performance
**What goes wrong:** On re-import, querying for all objects with `sempkm:importSource` matching any vault path could be slow with large existing datasets.
**Why it happens:** SPARQL FILTER with IN clause over hundreds of values.
**How to avoid:** Query once before import for ALL objects with `sempkm:importSource` values, build a set in Python. Single SPARQL query: `SELECT ?s ?path WHERE { GRAPH <urn:sempkm:current> { ?s <urn:sempkm:importSource> ?path } }`. Filter in Python.
**Warning signs:** Import start takes unexpectedly long.

## Code Examples

### Reading a Note and Building Commands
```python
import frontmatter as fm_lib
from pathlib import Path

def read_note(vault_root: Path, rel_path: str) -> tuple[dict, str, list[tuple[str, str|None]], list[str]]:
    """Read a note and extract metadata, body, wiki-links, and tags.

    Returns: (frontmatter_dict, body_text, wiki_links[(target, alias)], tags[str])
    """
    full_path = vault_root / rel_path
    post = fm_lib.load(str(full_path))
    meta = post.metadata or {}
    body = post.content or ""

    # Strip code blocks before extracting links/tags
    clean_body = CODE_BLOCK_RE.sub("", body)

    # Enhanced wiki-link regex capturing alias
    WIKILINK_FULL_RE = re.compile(r"(?<!!)\[\[([^\]\|#]+)(?:#[^\]\|]*)?\s*(?:\|([^\]]*))?\]\]")
    wiki_links = []
    for m in WIKILINK_FULL_RE.finditer(clean_body):
        target = m.group(1).strip()
        alias = m.group(2).strip() if m.group(2) else None
        if target:
            wiki_links.append((target, alias))

    # Tags from body
    tags = [m.group(1) for m in TAG_RE.finditer(clean_body)]

    # Tags from frontmatter
    fm_tags = meta.get("tags") or meta.get("tag")
    if fm_tags:
        if isinstance(fm_tags, str):
            fm_tags = [t.strip() for t in fm_tags.split(",") if t.strip()]
        if isinstance(fm_tags, list):
            for tag in fm_tags:
                tag_str = str(tag).strip().lstrip("#")
                if tag_str and tag_str not in tags:
                    tags.append(tag_str)

    return meta, body, wiki_links, tags
```

### Deduplication Query
```python
async def get_existing_import_sources(client: TriplestoreClient) -> set[str]:
    """Query all existing sempkm:importSource values for deduplication."""
    sparql = """
    SELECT ?path WHERE {
        GRAPH <urn:sempkm:current> {
            ?s <urn:sempkm:importSource> ?path .
        }
    }
    """
    results = await client.query(sparql)
    return {row["path"]["value"] for row in results.get("results", {}).get("bindings", [])}
```

### Import Summary Dataclass
```python
@dataclass
class ImportResult:
    """Summary of a completed import execution."""
    created: int = 0
    skipped_existing: int = 0
    skipped_errors: int = 0
    edges_created: int = 0
    unresolved_links: list[tuple[str, str]] = field(default_factory=list)  # (source_path, target_name)
    errors: list[tuple[str, str]] = field(default_factory=list)  # (path, error_message)
    duration_seconds: float = 0.0
```

### SSE Terminal Event Extension
```python
# In stream_sse() or a new import_stream_sse(), add terminal events:
# The existing stream_sse checks for "scan_complete" and "scan_error".
# For import, either:
# (a) Generalize: check for events ending in "_complete" or "_error"
# (b) Create a separate stream function for import with its own terminal events

async def stream_import_sse(queue: asyncio.Queue[SSEEvent]) -> AsyncGenerator[str, None]:
    """Like stream_sse but with import-specific terminal events."""
    while True:
        try:
            event = await asyncio.wait_for(queue.get(), timeout=30.0)
            yield event.format()
            if event.event in ("import_complete", "import_error"):
                break
        except asyncio.TimeoutError:
            yield ": keepalive\n\n"
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| HTTP API calls in loop | Direct handler invocation | Phase 47 design | Eliminates HTTP overhead for internal operations |
| Single-pass import | Two-pass (objects then edges) | Phase 47 design | Enables wiki-link resolution against known IRIs |

## Open Questions

1. **Validation Queue During Import**
   - What we know: The command router enqueues SHACL validation after each commit. The executor should likely do the same.
   - What's unclear: For a 500-note import, that's 50-100 validation queue entries. Should we throttle or batch validation differently?
   - Recommendation: Enqueue validation per batch commit (same as command router). The validation queue is async and non-blocking. If performance is an issue, it can be optimized later.

2. **"Browse Imported Objects" Button Behavior**
   - What we know: User wants to verify imports immediately. SemPKM has nav tree sidebar and workspace tabs.
   - What's unclear: Best UX for "browse all imported objects"
   - Recommendation: Navigate to the workspace with a nav tree refresh trigger. The imported objects will appear in the tree under their types. Add an `HX-Trigger: sempkm:nav-refresh` response header on the summary page load, or include a JS snippet that dispatches a custom event to reload the nav tree.

3. **Batch Size for Object Creation**
   - What we know: Each EventStore.commit() opens an RDF4J transaction. Too many operations per batch = large SPARQL. Too few = many round-trips.
   - Recommendation: 1 object per commit (object.create + body.set + property triples). This keeps error isolation clean (skip failures continue) and matches the "per-object batch" decision. For edges, batch 10-20 per commit since they're smaller.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | Playwright (e2e) |
| Config file | `e2e/playwright.config.ts` |
| Quick run command | `cd /home/james/Code/SemPKM/e2e && npx playwright test --project=chromium tests/14-obsidian-import/` |
| Full suite command | `cd /home/james/Code/SemPKM/e2e && npx playwright test --project=chromium` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| OBSI-06 | Import creates objects with bodies, properties via Command API | e2e | `npx playwright test --project=chromium tests/14-obsidian-import/batch-import.spec.ts` | No -- Wave 0 |
| OBSI-07 | Wiki-links resolved to dcterms:references edges, tags to schema:keywords | e2e | `npx playwright test --project=chromium tests/14-obsidian-import/batch-import.spec.ts` | No -- Wave 0 |

### Sampling Rate
- **Per task commit:** Manual verification via UI (upload vault, run import, check objects)
- **Per wave merge:** `cd /home/james/Code/SemPKM/e2e && npx playwright test --project=chromium tests/14-obsidian-import/`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `e2e/tests/14-obsidian-import/batch-import.spec.ts` -- covers OBSI-06, OBSI-07 (import execution, object creation, edge creation, tag resolution, summary display)
- [ ] Test vault ZIP with known wiki-links and tags for deterministic assertions

## Sources

### Primary (HIGH confidence)
- Codebase inspection: `backend/app/obsidian/router.py`, `scanner.py`, `models.py`, `broadcast.py` -- existing Phase 45-46 implementation
- Codebase inspection: `backend/app/commands/` -- schemas, dispatcher, handlers (object_create, body_set, edge_create)
- Codebase inspection: `backend/app/events/store.py` -- EventStore.commit() transaction semantics
- Codebase inspection: `backend/app/rdf/iri.py` -- IRI minting functions
- Codebase inspection: `backend/app/templates/obsidian/partials/preview.html` -- disabled Import button to wire up

### Secondary (MEDIUM confidence)
- Codebase inspection: `backend/app/rdf/namespaces.py` -- COMMON_PREFIXES for compact IRI resolution (dcterms, schema, rdfs all present)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - all libraries and patterns already exist in the codebase
- Architecture: HIGH - two-pass import with direct handler calls is a natural extension of existing patterns
- Pitfalls: HIGH - identified from direct code reading (regex groups, multi-valued properties, async boundaries)

**Research date:** 2026-03-08
**Valid until:** 2026-04-08 (stable -- internal codebase patterns)
