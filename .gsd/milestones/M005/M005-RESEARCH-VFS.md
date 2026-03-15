# M005 S07: VFS v2 — Research Notes

**Date:** 2026-03-14  
**Status:** Discussion captured, refines `.gsd/design/VFS-V2-DESIGN.md`

## Refined Mental Model

The VFS v2 mount model is cleaner than v1. Three concerns, fully separated:

```
Mount = Scope + Strategy + Prefix

Scope    → saved query (or "all") → yields a set of objects
Strategy → ordered chain of path segments → computes a filesystem path per object
Prefix   → mount name → root directory in WebDAV
```

### Scope (What Objects)

- A saved query defines the universe of objects in the mount
- "All objects" is the default (no query)
- Type filter is convenience sugar on top (ANDed with saved query)
- The scope is a **filter** — it decides which objects appear at all

### Strategy (How to Organize)

- An ordered chain of property-based path segment builders
- Each level extracts a value from the object and creates a folder level
- The strategy does NOT filter — every object in the scope MUST get a path
- Catch-all folder (e.g. `_uncategorized/`) for objects missing the expected property
- Max 3 levels enforced

Example:
```
scope:    saved query "all Notes tagged #research"
strategy: [by-tag, by-date-year]  
prefix:   /research-notes

Result:   /research-notes/machine-learning/2025/attention-paper.md
          /research-notes/physics/2024/quantum-review.md
          /research-notes/_untagged/random-thought.md   ← catch-all
```

### Prefix (Where in WebDAV)

- Mount name becomes the root directory
- Already works this way in v1

## Bidirectional Path ↔ Properties (Write Support)

**Key insight from discussion:** The strategy chain is bidirectional.

**Read direction:** object properties → path segments  
**Write direction:** path segments → object properties on new objects

```
Strategy: [by-type, by-tag]
Mount:    /knowledge

Read:   Object(type=Note, tag=physics) → /knowledge/Note/physics/my-notes.md
Write:  Create /knowledge/Note/physics/new-paper.md
        → new Object with:
           type = Note        (from path segment 1, via by-type strategy)
           tag  = physics     (from path segment 2, via by-tag strategy)
           title = new-paper  (from filename)
           body = <file content after frontmatter>
```

The frontmatter in the `.md` file fills in everything the path doesn't cover:

```yaml
---
status: active
priority: high
references: ["https://arxiv.org/..."]
---
# New Paper
Body content becomes the object's body property.
```

**This makes the strategy definition a schema contract:**
- Objects HERE have THESE properties set by their position in the tree
- Objects HERE have THESE properties set by their frontmatter
- The catch-all folder means "this property is unset on the object"
- Creating a file in catch-all omits that property

**Impact on VFS v2 design doc:**
- "Write Support (Future — Bigger Lift)" becomes much more tractable
- The strategy chain IS the write schema — no separate mapping needed
- "What type should a new file be?" → the path tells you (if strategy includes by-type)
- Still complex edge cases (filename-to-IRI mapping, conflict resolution), but the conceptual model is clean

## Immediate Implementation Priorities (from existing design doc)

| # | Feature | Effort | Status |
|---|---------|--------|--------|
| 1 | Saved query as scope | Low | `saved_query_id` already stored, just wire `build_scope_filter()` |
| 2 | Type filter | Low | Add field, extend scope builder |
| 3 | Composable strategies | Medium | Generalize `StrategyFolderCollection` parent_folder_value pattern |
| 4 | Preview tree | Low-Med | Nested tree with counts, reuse strategy queries |
| 5 | Filename templates | Low | Template expansion in `_build_file_map_from_bindings()` |
| 6 | Write support | High | Now better understood but still its own milestone |

## Design Decisions Crystallized

1. **`type_filter` and `saved_query_id` compose (AND)**  
   Saved query scopes the universe; type filter narrows within it. Same pattern as views.

2. **Strategy chains use flat list (Option A from design doc)**  
   `"strategy": ["by-tag", "by-date"]` — simpler to serialize, validate, UI.

3. **Every object gets a path — no filtering at strategy level**  
   Catch-all folders for missing properties. Strategy is a path function, not a filter.

4. **Shared scoping primitive with views**  
   Saved queries are the universal scope mechanism. Design once for VFS, reuse for views.

5. **Strategy chain repeats allowed**  
   `by-property/by-property` with different property IRIs at each level is valid.

## Connection to Views Rethink (S06)

Both VFS mounts and views need the same "scope an object set" primitive:
- VFS: scope → strategy → filesystem paths
- Views: scope → renderer → table/cards/graph display

The saved query is the shared input. If we design the scoping well for VFS v2, views get it for free.

## Open Questions Remaining

- **Catch-all folder naming:** `_uncategorized/`, `_untagged/`, `_other/`? Should it be configurable?
- **Write support: conflict resolution** — what if object edited in browser AND via VFS file?
- **Write support: new file type inference** — if strategy doesn't include by-type, what type is a new file? Default type per mount config?
- **Strategy chain UI:** "+" button to add levels, or predefined combos? Predefined is simpler for v1.

## Key Files

- `.gsd/design/VFS-V2-DESIGN.md` — original design draft (to be updated by S07)
- `backend/app/vfs/mount_service.py` — MountSpec dataclass, `saved_query_id` field
- `backend/app/vfs/mount_collections.py` — StrategyFolderCollection, existing nesting
- `backend/app/vfs/strategies.py` — strategy implementations
- `backend/app/vfs/provider.py` — DAVProvider, `build_scope_filter()`
- `backend/app/vfs/mount_router.py` — mount CRUD endpoints
