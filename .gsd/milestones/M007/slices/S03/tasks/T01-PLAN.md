---
estimated_steps: 6
estimated_files: 4
---

# T01: Filename templates — backend + tests

**Slice:** S03 — VFS Composable Chains & Filename Templates
**Milestone:** M007

## Description

Add `filename_template` field to `MountDefinition` and implement template variable expansion in `_build_file_map_from_bindings()`. This is an isolated feature — no dependency on the chain work in T02-T04. The template system supports `{title}`, `{date}`, `{type}`, `{id}` variables that expand before slugification, with the existing dedup suffix still applying.

## Steps

1. **Add `filename_template` to data model** — In `backend/app/vfs/mount_service.py`:
   - Add `FILENAME_TEMPLATE = f"{NS_SEMPKM}filenameTemplate"` constant near the other predicate constants
   - Add `filename_template: str | None = None` field to `MountDefinition` dataclass (after `type_filter`)
   - Add `"filename_template": self.filename_template` to `to_dict()`
   - In `SyncMountService.get_by_id()`: add `<{FILENAME_TEMPLATE}>` to SELECT and parse it from bindings (OPTIONAL in SPARQL)
   - In `SyncMountService.get_by_prefix()`: same — add OPTIONAL for filename_template
   - In `SyncMountService.create()`: if `mount.filename_template`, add triple `<{mount_iri}> <{FILENAME_TEMPLATE}> "{escaped_value}"` to INSERT DATA
   - In `SyncMountService.update()`: handle `filename_template` in updates dict — update field on existing object

2. **Add `filename_template` to async router** — In `backend/app/vfs/mount_router.py`:
   - Add `filename_template: str | None = None` to `MountCreateRequest`, `MountUpdateRequest`, and `MountPreviewRequest` Pydantic models
   - In `_get_mount_by_id_async()`: add OPTIONAL for filename_template in SELECT, parse from bindings
   - In `_get_mount_list_async()`: same — add OPTIONAL, parse from bindings
   - In `create_mount()`: add filename_template triple to INSERT DATA if present. Pass to MountDefinition constructor.
   - In `update_mount()`: handle filename_template in update logic — delete old triple, insert new if present
   - In `preview_mount()`: pass `filename_template` to temp MountDefinition (for future use, no preview change needed yet)

3. **Implement template expansion in file map builder** — In `backend/app/vfs/mount_collections.py`:
   - Change `_build_file_map_from_bindings()` signature to accept optional `filename_template: str | None = None` and `type_labels: dict[str, str] | None = None`
   - Before the existing `slug = _slugify(label)` line, add template expansion logic:
     ```python
     if filename_template:
         expanded = filename_template
         expanded = expanded.replace("{title}", label)
         expanded = expanded.replace("{id}", hashlib.sha256(iri.encode()).hexdigest()[:8])
         if "{date}" in expanded:
             date_val = b.get("created", {}).get("value", "")
             date_str = date_val[:10] if date_val else "undated"
             expanded = expanded.replace("{date}", date_str)
         if "{type}" in expanded:
             type_label = ""
             if type_labels and type_iri:
                 type_label = type_labels.get(type_iri, "")
             if not type_label and type_iri:
                 type_label = type_iri.rsplit("/", 1)[-1].rsplit("#", 1)[-1].rsplit(":", 1)[-1]
             expanded = expanded.replace("{type}", type_label or "unknown")
         slug = _slugify(expanded)
     else:
         slug = _slugify(label)
     ```
   - The `{date}` variable requires `dcterms:created` in SPARQL bindings. The SPARQL key is `created` — check if the binding has it.

4. **Thread `filename_template` through collection classes** — In `backend/app/vfs/mount_collections.py`:
   - In `MountRootCollection._get_flat_file_map()`: pass `filename_template=self._mount.filename_template` to `_build_file_map_from_bindings()`
   - In `StrategyFolderCollection._build_file_map()`: same — pass `filename_template=self._mount.filename_template`
   - For `{date}` support: the SPARQL queries that feed `_build_file_map_from_bindings()` need an OPTIONAL for `dcterms:created`. Check which strategy query builders (`query_flat_objects`, `query_objects_by_type`, `query_objects_by_tag`, `query_objects_by_date`, `query_objects_by_property`, `query_uncategorized_objects`) already include a `?created` variable. If not present, they need: `OPTIONAL { ?iri <http://purl.org/dc/terms/created> ?created }`
   - Check `backend/app/vfs/strategies.py` for each query function and add the OPTIONAL if missing. The binding key must be `created` to match the expansion code.

5. **Write unit tests** — In `backend/tests/test_vfs_path_contract.py`, add a new test class:
   ```python
   class TestFilenameTemplates:
       """Filename template expansion in _build_file_map_from_bindings."""

       def _make_binding(self, iri, label, type_iri="", created=""):
           b = {"iri": {"value": iri}, "label": {"value": label}, "typeIri": {"value": type_iri}}
           if created:
               b["created"] = {"value": created}
           return b

       def test_title_only(self):
           """Template with just {title} — same as no template."""
           bindings = [self._make_binding("urn:x:1", "My Note")]
           result = _build_file_map_from_bindings(bindings, filename_template="{title}")
           assert "my-note.md" in result

       def test_date_title(self):
           """Template {date}-{title} produces date-prefixed slug."""
           bindings = [self._make_binding("urn:x:1", "My Note", created="2024-01-15T10:00:00Z")]
           result = _build_file_map_from_bindings(bindings, filename_template="{date}-{title}")
           assert "2024-01-15-my-note.md" in result

       def test_type_title(self):
           bindings = [self._make_binding("urn:x:1", "My Note", type_iri="http://example.org/Note")]
           result = _build_file_map_from_bindings(bindings, filename_template="{type}-{title}")
           assert "note-my-note.md" in result

       def test_id_suffix(self):
           bindings = [self._make_binding("urn:x:1", "My Note")]
           result = _build_file_map_from_bindings(bindings, filename_template="{title}-{id}")
           keys = list(result.keys())
           assert len(keys) == 1
           # Should have hash suffix in the slug
           assert keys[0].startswith("my-note-")
           assert keys[0].endswith(".md")

       def test_missing_date_uses_undated(self):
           bindings = [self._make_binding("urn:x:1", "My Note")]
           result = _build_file_map_from_bindings(bindings, filename_template="{date}-{title}")
           assert "undated-my-note.md" in result

       def test_no_template_unchanged(self):
           """No template = existing behavior (slug from label only)."""
           bindings = [self._make_binding("urn:x:1", "My Note")]
           result = _build_file_map_from_bindings(bindings)
           assert "my-note.md" in result

       def test_dedup_with_template(self):
           """Dedup still works when templates produce same slug."""
           bindings = [
               self._make_binding("urn:x:1", "Note A", created="2024-01-15T00:00:00Z"),
               self._make_binding("urn:x:2", "Note A", created="2024-01-15T00:00:00Z"),
           ]
           result = _build_file_map_from_bindings(bindings, filename_template="{date}-{title}")
           assert len(result) == 2
           # Both files should exist with hash suffixes
           for fname in result:
               assert fname.endswith(".md")
   ```

6. **Verify backward compatibility** — Run the full existing test suites to confirm no regressions:
   - `cd backend && python -m pytest tests/test_vfs_path_contract.py tests/test_vfs_scope.py -v`

## Must-Haves

- [ ] `filename_template` field on `MountDefinition` with SPARQL read/write in both sync and async paths
- [ ] Template expansion in `_build_file_map_from_bindings()` before `_slugify()`
- [ ] `{title}`, `{date}`, `{type}`, `{id}` variables all functional
- [ ] Missing `{date}` falls back to "undated"
- [ ] No template = existing behavior (backward compat)
- [ ] Dedup suffix still works with templates
- [ ] Unit tests covering all template variables and edge cases

## Verification

- `cd backend && python -m pytest tests/test_vfs_path_contract.py -v` — all existing 26 tests + new template tests pass
- `cd backend && python -m pytest tests/test_vfs_scope.py -v` — no regressions (21 tests)

## Observability Impact

- **New signal:** DEBUG log emitted in `_build_file_map_from_bindings()` when a filename template is expanded, including the template string and resulting slug. Enables diagnosing unexpected filenames.
- **Inspection:** `MountDefinition.to_dict()` includes `filename_template` — visible in mount API responses and useful for verifying persistence round-trips.
- **Failure shape:** Unknown template variables (e.g., `{bogus}`) are left as-is and slugified — they don't raise errors. This is observable as literal text in the filename, not a crash.
- **No breaking changes:** When `filename_template` is `None`, `_build_file_map_from_bindings()` follows the exact existing code path — no new log lines, no behavioral difference.

## Inputs

- `backend/app/vfs/mount_service.py` — existing `MountDefinition` with `type_filter` field (from S02)
- `backend/app/vfs/mount_collections.py` — existing `_build_file_map_from_bindings()` and `_slugify()`
- `backend/app/vfs/mount_router.py` — existing Pydantic models with `type_filter`
- `backend/app/vfs/strategies.py` — existing SPARQL query builders (may need `dcterms:created` OPTIONAL)
- `backend/tests/test_vfs_path_contract.py` — existing 26 tests for slug/dedup

## Expected Output

- `backend/app/vfs/mount_service.py` — `FILENAME_TEMPLATE` constant, `filename_template` field on `MountDefinition`, SPARQL read/write
- `backend/app/vfs/mount_router.py` — `filename_template` in Pydantic models and async CRUD
- `backend/app/vfs/mount_collections.py` — template expansion in `_build_file_map_from_bindings()`
- `backend/app/vfs/strategies.py` — `dcterms:created` OPTIONAL added to query builders if missing
- `backend/tests/test_vfs_path_contract.py` — new `TestFilenameTemplates` class with 7+ tests
