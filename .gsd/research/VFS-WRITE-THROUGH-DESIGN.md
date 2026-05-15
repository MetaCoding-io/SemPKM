# VFS Write-Through, Multi-Subtree Mounts & Blob Storage

> **Status:** Design — agreed
> **Date:** 2026-05-15
> **Context:** Design conversation following review of VFS v2 (M007) and the deferred write-support work. Captures the agreed model for full read/write VFS, multi-subtree mounts, blob storage with type promotion, wiki-link sync, and rename-safe path↔IRI binding.

---

## Motivation

The VFS today is a read-only graph projection. Edits to existing markdown files work (PUT round-trips through `mount_resource.py` → event store), but:

- Create new file → 403
- Create folder → 403
- Delete → 403
- Move / rename → 403
- Non-markdown files → no path at all

This blocks the use case of "make the mount usable as an Obsidian vault" — and any tooling that wants to operate on it like a real filesystem (Quarto for static-site generation, Pandoc, Git, anything that wants to drop assets alongside markdown).

The other current limitation: one-strategy-per-mount means users who want a vault-like structure must create N separate mounts (one for tasks, one for daily notes, one for projects, etc.). The mental model breaks.

---

## The agreed model

### One-line summary

> *A subtree is a filter + a creation rule. An object appears wherever it matches. Edits write to the object, not the path.*

### Mount → subtree spec

A `MountSpec` is:

- `name` — display label
- `root_path` — WebDAV mount root
- `subtrees` — ordered list of `SubtreeSpec`

A `SubtreeSpec` is:

- `path_pattern` — e.g. `/Tasks/`, `/DailyNotes/{YYYY-MM-DD}/`, `/ByTag/{tag}/`
- `filter` — SPARQL fragment OR property-set predicate (`type=Task AND priority=high`)
- `default_type` — type IRI assigned on creation
- `accepts` — one of `["markdown"]`, `["blob"]`, `["markdown","blob"]`
- `frontmatter_mode` — `strict` | `passthrough` (default) | `promote`

Example mount:

```
MountSpec "My Vault" rooted at /vault
  Subtree "Tasks"        path=/Tasks/{...}             filter: type=Task              default=Task     accepts=[md]    fm=passthrough
  Subtree "Daily"        path=/Daily/{YYYY}/{MM}/      filter: type=DailyNote         default=DailyNote accepts=[md]    fm=strict
  Subtree "Notes"        path=/Notes/{tag}/            filter: type=Note              default=Note     accepts=[md,blob] fm=passthrough
  Subtree "Attachments"  path=/Attachments/{ext}/      filter: type=File              default=File     accepts=[blob]  fm=passthrough
  Subtree "AllTasks"     path=/Views/AllTasks/         filter: type=Task              (read-only)
  Subtree "HighPriority" path=/Views/HighPriority/     filter: type=Task,priority=high (read-only)
  Subtree "Other"        path=/Other/                  filter: *                      default=Note     accepts=[md,blob] fm=passthrough
```

### Multi-path is the default

An object appears in **every subtree whose filter it matches**, simultaneously. Same `ETag` (already designed-in: `mount_resource.py:296-302` — *"ETag derived from object IRI (not content). All paths to the same object share the same ETag, enabling cross-path concurrency control for multi-folder objects."*)

- Edits at any path commit to the same IRI
- Stale views recover on refresh (same as Obsidian-vs-Git today)
- DELETE from any path = delete the object globally
- Cross-subtree MOVE is **blocked** — users change semantics via the workspace UI, not by dragging files

### Filter satisfiability gates creation

Whether a subtree supports PUT-create is determined by whether its filter is **satisfiable by property assignment**:

| Filter | Satisfiable? | Creation behavior |
|---|---|---|
| `type=Task` | ✅ | Sets `rdf:type=Task` on create |
| `type=Task AND priority=high` | ✅ | Sets both |
| `tag=urgent` | ✅ | Adds tag on create |
| `modified within 7d` | ❌ | PUT-create → 403; reads/edits still work |
| `body matches regex X` | ❌ | Same |

No virtual/primary flag needed. The filter itself answers the question.

### Path↔IRI binding

- **IRI:** UUID-based (`urn:sempkm:obj:<uuid>`), stable across renames
- **Filename:** slug derived from `dcterms:title`, freely renameable
- **Rename safe** because edges point to IRIs, not titles — survives rename for free
- Body text needs rewrite-on-rename (see Wiki-link sync below)

---

## Wiki-link sync on save

Today's behavior is inconsistent:

- **Obsidian importer** (one-shot): extracts `[[…]]`, creates `dcterms:references` edges
- **Canvas** (live render): resolves at render time via `/api/canvas/resolve-wikilinks`, creates ghost nodes
- **Workspace editor / VFS edits**: `[[…]]` round-trips as plain text; no edge, no resolution

This means backlinks only work for imported content. Live-edited wiki-links are invisible to the graph. We fix this by running sync on every save.

### Sync pipeline (on every body-mutating PUT)

1. **Extract** — Reuse `WIKILINK_FULL_RE` from `obsidian/scanner.py` (handles `[[target]]`, `[[target|alias]]`, `[[target#heading]]`, excludes `![[embeds]]`)
2. **Resolve** — Batch SPARQL query on title/label/prefLabel/name/foaf:name (reuse the pattern from `canvas/router.py:434` `resolve_wikilinks`)
3. **Reconcile** — Diff existing `dcterms:references` edges (from this source) vs resolved targets. Create added edges. Remove deleted edges. Multi-occurrence collapses (`[[Foo]]` × 5 = 1 edge, Obsidian semantics).
4. **Park unresolved** — Each `[[Foo]]` that didn't match anything → append literal to `bpkm:unresolvedRef` multi-valued property on source

### Late reconciliation

On `object_create`, scan the `bpkm:unresolvedRef` index for matches against the new object's title/labels. For each match: remove the literal, create the edge. This makes forward-references (you wrote `[[Future]]` before Future existed) eventually consistent.

### Embeds (`![[image.png]]`)

Distinct predicate from links:

- `bpkm:embeds` — general embeds
- `foaf:depiction` — image embeds specifically

Same extraction pipeline, separate regex (the existing scanner regex excludes embeds; we'd add a sibling regex that matches them).

### Performance budget

- Regex over body: O(body size), ~µs for typical notes
- One SPARQL resolve query: O(unique targets), typically <50 unique per note
- Edge diff writes: O(diff size), usually 0-3

Target: <100ms p95 added to PUT latency.

---

## Rename propagation

When `dcterms:title` is patched on an object (Foo → Bar):

1. Patch lands via `object.patch`
2. Query `?s dcterms:references <X>` — gives every source IRI that links to X
3. For each source: fetch body, regex-replace `[[Foo]]` and `[[Foo|alias]]` → `[[Bar]]` and `[[Bar|alias]]`, commit via `body.set` (provenance: "auto: title rename")
4. `bpkm:unresolvedRef` literals matching "Foo" are either rewritten to "Bar" or left for next-save reconciliation

The work is bounded by edge count (not graph size), so it's tractable even for heavily-linked objects.

---

## Blob storage

### Storage: content-addressed disk

- Layout: `/data/blobs/<sha256[0:2]>/<sha256>`
- Git-style sharding, free deduplication
- Backups: include the `/data/blobs/` directory
- RDF stays the source of truth for *what exists*; bytes are a side-effect

### RDF representation

A blob object has type `bpkm:File` with:

- `nfo:fileName` — original filename
- `dcterms:format` — MIME type
- `nfo:fileSize` — bytes
- `nfo:hasHash` — SHA-256 hex
- `bpkm:blobRef` — pointer to the on-disk file (could be just the hash)

### Sprinkled everywhere, never auto-promoted by path

A blob can land in any subtree whose `accepts` includes `"blob"`. It is **always** created as `bpkm:File` only — never auto-typed to the subtree's `default_type`.

| Subtree config | What happens when user drops `paper.pdf` |
|---|---|
| `accepts=["markdown"]` | 415 Unsupported (e.g. strict DailyNotes subtree) |
| `accepts=["markdown","blob"]` | Created as `bpkm:File`, appears in subtree if filter matches |
| `accepts=["blob"]` | Created as `bpkm:File` |

The "PDF in DailyNotes folder" case resolves cleanly: if DailyNotes is markdown-only, the OS gets a "can't copy here" dialog; if it's mixed, the PDF lands as a plain file with no daily-note magic.

### Type promotion

Right-click in workspace → "Promote to type…" → picks higher-order type (e.g. `bpkm:ResearchArticle`).

- **Promotion adds a type, never replaces.** `rdf:type bpkm:File, bpkm:ResearchArticle` — both apply.
- SHACL form for the new type appears with empty required fields
- Blob plumbing (download, preview, file size) stays intact
- Demotion = remove the higher type, keep `bpkm:File`

A promoted PDF appears in both its blob subtree (still a `bpkm:File`) and any subtree filtering on the new type.

---

## Frontmatter drift modes

Per-subtree config — what to do when user adds YAML frontmatter keys we don't recognize:

- **`strict`** — Write fails with 422-equivalent WebDAV error. Best for disciplined subtrees (DailyNotes with fixed schema).
- **`passthrough`** *(default)* — Unknown keys stored as `bpkm:extraFrontmatter` (single JSON literal). Round-trip on read. Graph doesn't gain properties, but user intent preserved.
- **`promote`** — Unknown keys auto-create properties (`bpkm:<camelCaseKey>`). SHACL doesn't reject. Most Obsidian-like; riskiest for schema cleanliness.

Orthogonal flag: `allow_arbitrary_typing` — whether user can set `type:` in frontmatter outside subtree's allowed types. Default off (subtree rule wins); on for power users.

---

## WebDAV write surface

### Allowed operations

| Op | Behavior |
|---|---|
| `PUT` (existing path) | Edit underlying object (works today) |
| `PUT` (new path, satisfiable filter) | Create object, set `default_type` + filter-derived properties |
| `PUT` (new path, non-satisfiable filter) | 403 with explanatory body |
| `PUT` (non-markdown content, `accepts` includes blob) | Hash, store on disk, create `bpkm:File` |
| `MKCOL` | Allowed for date-strategy subtrees (year/month folders); otherwise 403 |
| `DELETE` (any path) | Delete the underlying object globally |
| `MOVE` (within subtree) | Allowed (e.g. date reclassification, slug change) |
| `MOVE` (cross-subtree) | 403 with explanatory body — change semantics via UI |
| `COPY` | 403 — copying objects is a semantic op, not a filesystem op |

### Custom PROPFIND properties

In a `sempkm:` namespace, returned on every resource:

- `sempkm:objectIri` — canonical IRI (lets tooling deduplicate multi-path resources)
- `sempkm:type` — list of `rdf:type` values
- `sempkm:tags` — current tags
- `sempkm:appearsAt` — list of sibling paths this object projects to
- `sempkm:backlinkCount` — incoming `dcterms:references` count
- `sempkm:isBlob` — boolean
- `sempkm:promotedTypes` — types beyond `bpkm:File` (for promoted blobs)

Clients that don't know these properties ignore them silently. Future tooling (Obsidian plugin, CLI, Quarto plugin) can read them.

### Other WebDAV features worth shipping

- **DAV:displayname with type-icon prefix** — `"📋 My Task"` vs `"📝 My Note"`. macOS Finder and Cyberduck honor this; Windows Explorer mostly ignores. Mixed but free win.
- **WebDAV LOCK** — maps to event-store optimistic concurrency (ETag-based). Prevents concurrent-edit corruption in collaborative use. Obsidian doesn't use it, but VSCode-via-WebDAV and Office do.
- **WebDAV SEARCH (RFC 5323)** — expose SPARQL queries via the search verb. Niche but cheap if we wrap existing endpoints.
- **DAV:quota** — for cloud deployments with storage caps once blobs land.

### Deliberately not shipping

- **DAV:bind (RFC 5842)** — protocol-correct way to expose multiple paths to same resource, but ~zero client support (Finder/Explorer/Nautilus/Obsidian all ignore). Not worth the implementation cost.
- **DAV:redirectref (RFC 4437)** — kludgier symlink, same client support problem.
- **DELTA-V versioning (RFC 3253)** — heavy implementation; event store already exposes versioning via the workspace.

---

## Workspace UI

The biggest UX wins live in the workspace, not in WebDAV.

### Mount config UI

Subtree-by-subtree builder with **live preview** as the user types each filter:

- **Filter satisfiability indicator** inline:
  - `type=Task` → ✅ "Creation enabled — new files get type Task"
  - `modified within 7d` → ⚠️ "Read-only subtree (filter not a property assignment)" with a "why?" tooltip
- **"What matches" sample** — 5-10 objects matching the current filter, updating live
- **Subtree overlap chip** — "this filter overlaps with 'High Priority' in 12 objects" so users understand multi-path before it surprises them
- **Slug collision preview** — flag titles that produce identical paths with the planned `-2`, `-3` suffix
- **Path preview tree** — show how files will arrange across all subtrees as the user builds the spec

### "Where does this appear?" inspector

Pane in the workspace: for any selected object, show:

- IRI (with copy button)
- All current `rdf:type` values
- List of every VFS path it currently projects to (across all mounts)
- For blob-promoted objects: blob ref + download link
- Link to "test in mount config" to see how the subtree filter resolves

This is the answer to *"wait, where does this thing actually live?"* — it makes the file/semantic-object distinction tangible exactly when the user is curious.

---

## What this enables

- **Obsidian-compatible vault** — user opens the mount in Obsidian, edits notes, wiki-links sync, backlinks update, renames propagate
- **Quarto / static-site generation** — point Quarto at the mount root, render markdown → HTML, save HTML and CSS back into the mount as blobs; resulting vault is a complete static site
- **Mixed-content workflows** — drop PDFs, images, mind-map files, anything; they all live alongside notes; promote to higher types when needed
- **Cross-cutting access** — virtual-feeling subtrees (`/Views/HighPriority/`, `/ByTag/urgent/`) provide multi-axis browsing without proliferating mounts
- **One vault, one mental model** — replacing N mounts with one mount + N subtrees

---

## Implementation slicing (rough)

Six independent-ish slices, dependencies noted:

1. **Mount/subtree schema redesign** *(risk:high)* — `MountSpec` with ordered `SubtreeSpec` list, filter satisfiability checker, backward-compat migration
2. **Wiki-link sync on save & embeds** *(risk:medium)* — extract/resolve/reconcile + `bpkm:unresolvedRef` + embed predicate convention
3. **WebDAV write surface** *(risk:high, depends 1)* — PUT-create, DELETE, MKCOL where appropriate, MOVE-within
4. **Blob storage & multi-type promotion** *(risk:medium, depends 1, 3)* — content-addressed disk, `bpkm:File`, promotion UI
5. **Rename propagation** *(risk:medium, depends 2)* — title patch → find sources via edges → rewrite bodies
6. **Mount config UI, VFS inspector & WebDAV polish** *(risk:medium, depends 1, 3, 4)* — live preview, satisfiability indicator, "appears at" pane, PROPFIND custom props, LOCK, displayname

---

## Open questions / explicit deferrals

- **Blob garbage collection** — event-sourcing means deletions are logical, not physical. Defer to a future maintenance milestone.
- **Live filesystem notifications** — no inotify push from server to WebDAV clients. Clients poll. Defer indefinitely (clients don't reliably honor server-push WebDAV extensions anyway).
- **WebDAV SEARCH** — listed above as worth shipping, but lowest priority; could move to a follow-up milestone if scope tightens.
- **Federation interaction with blobs** — federation patches today are RDF-only. Do we exclude blob bytes from federation, or include them via a separate channel? Decision deferred until federation use cases stabilize.
- **Multi-type SHACL form rendering** — when an object has both `bpkm:File` and `bpkm:ResearchArticle`, the workspace edit form needs to merge SHACL shapes from both types. The merge rule (union of properties, last-write-wins on conflicts?) should be settled before S04 ships.

---

## References

- Existing VFS v1 design: `.gsd/design/VFS-V2-DESIGN.md`
- Path contract documentation: `docs/guide/23-vfs.md`
- Existing import wiki-link pipeline: `backend/app/obsidian/executor.py` (Pass 2), `backend/app/obsidian/scanner.py` (`WIKILINK_RE`)
- Live wiki-link resolution endpoint: `backend/app/canvas/router.py:434` (`resolve_wikilinks`)
- Current write path (markdown edit): `backend/app/vfs/mount_resource.py:312-398` (`begin_write`/`end_write`)
- WebDAV write helpers: `backend/app/vfs/write.py`
- Read-only enforcement to remove: `backend/app/vfs/mount_collections.py:274-289, 743-756`, `backend/app/vfs/collections.py:95-181, 320-331`
- ETag-by-IRI (multi-path correctness already designed): `backend/app/vfs/mount_resource.py:296-302`
- Original FUSE rejection: `DEC-03` (v2.1) — "Docker-compatible, HTTP-only, FUSE requires SYS_ADMIN (rejected)"
- Auto-refresh deferral: `D102` (M005) — "Defer auto-refresh for VFS… Revisit when write-support lands"
