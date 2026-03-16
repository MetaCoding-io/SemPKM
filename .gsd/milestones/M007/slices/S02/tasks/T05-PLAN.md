---
estimated_steps: 5
estimated_files: 3
---

# T05: Path contract documentation and slug/dedup tests

**Slice:** S02 — VFS Quick Wins — Type Filter, Query IRI, Preview
**Milestone:** M007

## Description

Document the bidirectional VFS path contract (IRI → filename, filename → IRI) and write unit tests for slug generation edge cases and collision dedup logic. This covers VFS-10.

The path contract is implicit in mount_collections.py — the `_slugify_label()` function (or equivalent) generates filenames from RDF labels, and `_build_file_map_from_bindings()` (or equivalent) handles collision dedup by appending numeric suffixes. These functions need to be identified, documented, and tested.

## Steps

1. **Identify the slug/dedup functions:**
   - Search `mount_collections.py` for the function(s) that convert RDF labels to filenames and handle collisions. Look for slug, sanitize, file_map patterns. Also check `mount_resource.py` and `strategies.py`.
   - Document the actual function names and their signatures.

2. **Write unit tests in `backend/tests/test_vfs_path_contract.py`:**
   - Import the slug/sanitize function directly
   - Test cases for slug generation:
     - Normal label: `"My Research Note"` → `"my-research-note.md"` (or whatever the actual output is)
     - Unicode: `"Über Données"` → ASCII-safe slug
     - Special characters: `"Hello/World: A <Test>"` → safe filename
     - Empty label: falls back to IRI fragment or ID
     - Very long label: truncated to reasonable length
     - Already-slugified: idempotent
   - Test cases for collision dedup:
     - Two objects with same label → one gets suffix (e.g., `note.md`, `note-2.md`)
     - Three-way collision → sequential suffixes
     - No collision → no suffix

3. **Add path contract section to `docs/guide/23-vfs.md`:**
   - Add a "## Path Contract" section (or similar) documenting:
     - **Forward mapping (IRI → path):** RDF label → slugified filename → dedup suffix if collision
     - **Reverse mapping (path → IRI):** file_map lookup table built per-request; no persistent index
     - **Filename instability caveat:** if an object's label changes, its filename changes. No stable filenames across label edits. Tools that cache paths (e.g., Obsidian vault indexing) may break.
     - **Dedup behavior:** when two objects have the same label, second gets `-2` suffix, third gets `-3`, etc.
     - **Extension:** always `.md` for knowledge objects
   - Keep it concise — this is developer/power-user documentation, not a tutorial

4. **If slug functions are private/inline, consider extracting:**
   - If the slug logic is deeply embedded in a class method, extract it to a module-level function in `strategies.py` or `mount_collections.py` so it's importable for testing
   - Keep the extraction minimal — don't refactor beyond what's needed for testability

5. Run tests.

## Must-Haves

- [ ] Unit tests for slug generation edge cases (unicode, special chars, empty, long)
- [ ] Unit tests for collision dedup (2-way, 3-way, no collision)
- [ ] Path contract documented in docs/guide/23-vfs.md with forward/reverse examples
- [ ] Filename instability caveat documented

## Verification

- `cd backend && python -m pytest tests/test_vfs_path_contract.py -v` — all tests pass
- `docs/guide/23-vfs.md` contains "Path Contract" section with examples
- Forward and reverse mapping are both explained

## Inputs

- `backend/app/vfs/mount_collections.py` — slug/dedup functions (need to identify exact names)
- `backend/app/vfs/mount_resource.py` — may contain slug logic
- `docs/guide/23-vfs.md` — existing VFS documentation

## Expected Output

- `backend/tests/test_vfs_path_contract.py` (new) — slug and dedup unit tests
- `docs/guide/23-vfs.md` — updated with path contract section
- Possibly: extracted slug function if currently not importable

## Observability Impact

This task is documentation and tests only — no runtime behavior changes.

- **No new runtime signals:** no new log lines, metrics, or error surfaces added
- **Test diagnostic:** `python -m pytest tests/test_vfs_path_contract.py -v` shows slug/dedup contract verification
- **Documentation:** `docs/guide/23-vfs.md` "Path Contract" section is the reference for how filenames are derived from IRIs/labels and how collisions are resolved
