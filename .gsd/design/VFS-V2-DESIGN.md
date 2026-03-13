# VFS Mount Spec v2 — Design Notes

> Status: **Draft** — discussion document for next milestone planning
> Date: 2026-03-13

## Current State (v1)

Each mount has:
- **One strategy** — `flat | by-type | by-date | by-tag | by-property`
- **One scope** — `"all"` or a raw SPARQL WHERE fragment (`sparql_scope`)
- **saved_query_id** — stored but not wired (dead field)
- Strategy produces 1 level of folders (except `by-date` → year/month)

**What works well:**
- Simple mental model: pick a strategy, get a folder structure
- WebDAV clients see it immediately
- Scope filtering via raw SPARQL is powerful for advanced users

**What's missing:**
- Saved queries can't drive mount scope (the plumbing exists but is disconnected)
- No way to compose strategies (e.g. by-tag → by-date within each tag)
- No way to filter to "just my Notes tagged #project-x" without writing SPARQL
- Mount preview is flat — doesn't show what the tree will actually look like

---

## Proposed Changes

### 1. Saved Query as Scope Source

**Problem:** `saved_query_id` is stored on the mount but `build_scope_filter()` 
only reads `sparql_scope`. Users who create saved queries in the SPARQL console 
can't reference them from mount creation.

**Design:** When `saved_query_id` is set, resolve it at mount evaluation time:
1. Look up `SavedSparqlQuery` by ID
2. Extract `query_text` 
3. Wrap it as a scope sub-select: `{ SELECT ?iri WHERE { <query_text> } }`
4. If both `saved_query_id` and `sparql_scope` are set, `saved_query_id` wins
   (or AND them together — TBD)

**UI change:** The mount form Scope dropdown should list saved queries alongside 
the "All objects" option. Selecting one populates `saved_query_id`.

**Complexity:** Low — wiring existing fields, no schema change.

### 2. Composable Strategy Chains (Multi-Level Folders)

**Problem:** Users want `by-tag/by-date` or `by-type/flat` hierarchies. 
Currently stuck with one level.

**Design option A — Strategy chain as ordered list:**
```json
{
  "strategy": ["by-tag", "by-date"],
  "group_by_property": "urn:sempkm:tag",
  "date_property": "http://purl.org/dc/terms/created"
}
```
Produces: `/mount/machine-learning/2025/03-March/my-note.md`

Each level in the chain narrows the object set. The final level produces files.
Intermediate levels produce folders.

**Design option B — Nested strategy definition:**
```json
{
  "strategy": "by-tag",
  "group_by_property": "urn:sempkm:tag",
  "sub_strategy": {
    "strategy": "by-date",
    "date_property": "http://purl.org/dc/terms/created"
  }
}
```

**Recommendation:** Option A (flat list) is simpler to serialize, validate, and 
build UI for. Max depth of 3 levels should be enforced to keep WebDAV paths sane.

**Implementation approach:**
- `strategy` field becomes `string | string[]` (backward compatible: single 
  string = current behavior, array = chain)
- `StrategyFolderCollection` already has `parent_folder_value` for by-date's 
  year→month nesting — generalize this pattern
- Each level filters the object set further before passing to the next level

**Complexity:** Medium — requires generalized folder nesting in WebDAV 
collections + UI for chain building.

### 3. Type Filter (No SPARQL Required)

**Problem:** Filtering to "just Notes" or "just Notes + Concepts" requires 
writing `?iri a <urn:...Note>` in raw SPARQL. Most users won't do this.

**Design:** Add a `type_filter` field — list of type IRIs or local names. If 
set, only objects of those types appear in the mount.

```json
{
  "type_filter": ["Note", "Concept"],
  "strategy": "by-tag"
}
```

The UI shows a multi-select of available types (already queryable from shapes).
This covers the most common scope need without SPARQL knowledge.

**Complexity:** Low — add field, extend `build_scope_filter()`.

### 4. Preview Improvements

**Problem:** Current preview is a flat list of paths. Doesn't show the actual 
tree structure or give a sense of how many files land in each folder.

**Design:** Return preview as a nested tree with file counts per folder:
```json
{
  "tree": [
    {"name": "machine-learning", "count": 42, "children": [
      {"name": "2025", "count": 15, "children": [
        {"name": "03-March", "count": 8}
      ]}
    ]}
  ],
  "total_files": 120,
  "truncated": false
}
```

**Complexity:** Low-medium — reuse existing strategy queries with COUNT.

### 5. File Naming Control

**Problem:** Filenames are always `slugified-title.md`. Some users might want 
IRI-based names, date-prefixed names, or custom patterns.

**Design:** Add optional `filename_template` field:
- `"{title}"` (default) → `my-great-note.md`
- `"{date}-{title}"` → `2025-03-13-my-great-note.md`  
- `"{type}-{title}"` → `note-my-great-note.md`

Available variables: `{title}`, `{date}`, `{type}`, `{id}` (IRI hash)

**Complexity:** Low — template expansion in `_build_file_map_from_bindings()`.

### 6. Write Support (Future — Bigger Lift)

**Problem:** All mounts are currently read-only. External editors can read .md 
files but can't save back. This limits the Obsidian/VS Code integration story.

**Design considerations:**
- Write to what? Object's `dcterms:description` or full property serialization?
- Conflict resolution: what if the object was edited in the browser too?
- Filename-to-IRI mapping: mount must maintain a stable reverse index
- New file creation: which type? which graph? what properties?

**Recommendation:** Defer to a dedicated milestone. The read-only projection is 
already very useful for external tool integration, and write support has complex 
edge cases that deserve focused design.

---

## Priority Order

| # | Feature | Effort | Impact | Depends On |
|---|---------|--------|--------|------------|
| 1 | Saved query as scope | Low | High | — |
| 2 | Type filter | Low | High | — |
| 3 | Composable strategies | Medium | Medium | — |
| 4 | Preview tree | Low-Med | Medium | — |
| 5 | Filename templates | Low | Low | — |
| 6 | Write support | High | High | Separate milestone |

Items 1-2 are quick wins that dramatically improve usability without SPARQL.
Item 3 is the architectural change. Items 4-5 are polish. Item 6 is future.

---

## Open Questions

- Should strategy chains allow repeats? (e.g. `by-property/by-property` with 
  different properties at each level)
- Should `type_filter` and `saved_query_id` compose (AND) or be mutually 
  exclusive?
- For strategy chains, does the UI show a "+" to add levels, or predefined 
  combos like "By Tag, then By Date"?
- Should mounts support an "auto-refresh" interval or always use cache 
  invalidation via the event bus?
