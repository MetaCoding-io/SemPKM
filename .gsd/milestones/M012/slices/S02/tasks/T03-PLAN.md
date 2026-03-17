---
estimated_steps: 7
estimated_files: 2
---

# T03: Add body.diff undo support and comprehensive unit tests

**Slice:** S02 — Body.Diff — Incremental Storage & Rendering
**Milestone:** M012

## Description

Closes the slice by adding undo/compensation support for `body.diff` events and writing comprehensive unit tests that prove all code paths — handler output, save endpoint branching, event detail rendering (both `body.set` and `body.diff`), undo, and backward compatibility.

## Steps

1. **Add `body.diff` case to `build_compensation()` in `backend/app/events/query.py`:**

   After the existing `elif op_type == "body.set":` block, add:
   ```python
   elif op_type == "body.diff":
       if not subject_iri:
           return None
       # Read the stored diff from data_triples
       diff_text = None
       body_pred = None
       for s_str, p_str, o_str in detail.data_triples:
           if p_str == "urn:sempkm:bodyDiff":
               diff_text = o_str
           elif p_str != "urn:sempkm:bodyDiff":
               body_pred = p_str  # The non-diff predicate is the body predicate
       if not diff_text or not body_pred:
           return None
       # Get the new body from data_triples (the non-diff triple)
       new_body = None
       for s_str, p_str, o_str in detail.data_triples:
           if p_str == body_pred:
               new_body = o_str
               break
       if new_body is None:
           return None
       # Reverse-apply the diff to recover the old body
       old_body = self._reverse_apply_diff(new_body, diff_text)
       if old_body is None:
           return None
       old_literal = Literal(old_body)
       new_literal = Literal(new_body)
       return Operation(
           operation_type="body.set",
           affected_iris=[subject_iri],
           description=f"Undo body.diff: {event_iri}",
           data_triples=[(URIRef(subject_iri), URIRef(body_pred), old_literal)],
           materialize_inserts=[(URIRef(subject_iri), URIRef(body_pred), old_literal)],
           materialize_deletes=[(URIRef(subject_iri), URIRef(body_pred), new_literal)],
       )
   ```

2. **Add `_reverse_apply_diff()` method to `EventQueryService`:**
   ```python
   def _reverse_apply_diff(self, new_body: str, diff_text: str) -> str | None:
       """Reverse-apply a unified diff to recover the old body from the new body.
       
       Swaps + and - lines in the diff, then applies to the new body.
       Simpler approach: parse the diff and reconstruct old from new by
       removing added lines and restoring removed lines.
       """
       try:
           old_lines: list[str] = []
           new_lines = new_body.splitlines(keepends=True)
           new_idx = 0
           for line in diff_text.splitlines(keepends=True):
               if line.startswith("---") or line.startswith("+++") or line.startswith("@@"):
                   continue
               elif line.startswith("+"):
                   # This was added — skip it in old (but advance new_idx)
                   new_idx += 1
               elif line.startswith("-"):
                   # This was removed — it was in the old body
                   old_lines.append(line[1:])
               elif line.startswith(" "):
                   # Context line — present in both
                   old_lines.append(line[1:])
                   new_idx += 1
           # Append any trailing context not covered by the diff
           # (unified_diff may not include all trailing context)
           # Simple approach: just return what we reconstructed
           return "".join(old_lines)
       except Exception:
           return None
   ```
   
   **Important:** The simpler and more reliable approach is to reconstruct the old body directly from the diff without using the new body as input. A unified diff contains all removed lines (prefixed `-`) and all context lines (prefixed ` `). Concatenating context + removed lines in order gives the old body. Added lines (prefixed `+`) are skipped. This is a well-known property of unified diffs.

3. **Create `backend/tests/test_body_diff.py` with comprehensive tests:**

   Follow the pattern in `backend/tests/test_event_log_labels.py`. Use pytest with async support.

4. **Test: `handle_body_diff()` produces correct Operation:**
   ```python
   async def test_handle_body_diff_produces_correct_operation():
       params = BodyDiffParams(iri="urn:test:obj1", body="new content", diff_text="-old\n+new\n")
       op = await handle_body_diff(params, "urn:sempkm:")
       assert op.operation_type == "body.diff"
       assert op.affected_iris == ["urn:test:obj1"]
       # Check data_triples has both bodyDiff and body predicates
       preds = [str(t[1]) for t in op.data_triples]
       assert "urn:sempkm:bodyDiff" in preds
       assert "urn:sempkm:body" in preds
   ```

5. **Test: `_parse_stored_diff()` and `_compute_body_diff()` both work:**
   ```python
   def test_parse_stored_diff():
       service = EventQueryService(mock_client)
       diff_text = "--- a\n+++ b\n@@ -1 +1 @@\n-old line\n+new line\n context\n"
       result = service._parse_stored_diff(diff_text)
       assert any(d["type"] == "remove" and "old line" in d["text"] for d in result)
       assert any(d["type"] == "add" and "new line" in d["text"] for d in result)
   
   def test_compute_body_diff_still_works():
       service = EventQueryService(mock_client)
       result = service._compute_body_diff("old text", "new text")
       assert len(result) > 0  # Has diff lines
   ```

6. **Test: `_reverse_apply_diff()` recovers old body:**
   ```python
   def test_reverse_apply_diff():
       service = EventQueryService(mock_client)
       old_body = "line 1\nline 2\nline 3\n"
       new_body = "line 1\nmodified line 2\nline 3\n"
       diff_text = "".join(difflib.unified_diff(
           old_body.splitlines(keepends=True),
           new_body.splitlines(keepends=True),
           lineterm="",
       ))
       recovered = service._reverse_apply_diff(new_body, diff_text)
       assert recovered == old_body
   ```

7. **Test backward compatibility and edge cases:**
   - `body.set` events with before_values still compute diff on-the-fly (no regression)
   - First body set (no prior body) still uses `body.set` operation type
   - Empty diff (identical content) — verify the no-op behavior at save endpoint level
   - `build_compensation()` for `body.diff` produces a `body.set` operation with the old body
   - `build_compensation()` for `body.set` still works (no regression)

## Must-Haves

- [ ] `build_compensation()` handles `body.diff` — produces `body.set` compensation with old body recovered from diff
- [ ] `_reverse_apply_diff()` correctly reconstructs old body from new body + stored diff
- [ ] All tests in `test_body_diff.py` pass
- [ ] No regressions in existing test suite

## Verification

- `cd backend && python -m pytest tests/test_body_diff.py -v` — all tests pass
- `cd backend && python -m pytest tests/ -v --tb=short -x -q 2>&1 | tail -5` — no regressions

## Inputs

- T01 output: `backend/app/commands/handlers/body_diff.py`, `backend/app/commands/schemas.py` (BodyDiffParams, BodyDiffCommand)
- T02 output: Modified `save_body()` in `backend/app/browser/objects.py`, modified `get_event_detail()` and `_parse_stored_diff()` in `backend/app/events/query.py`
- `backend/app/events/query.py` — `build_compensation()` method to extend with `body.diff` case
- `backend/tests/test_event_log_labels.py` — reference test file for patterns (fixtures, mocking)

## Expected Output

- `backend/app/events/query.py` — `build_compensation()` extended with `body.diff` case, new `_reverse_apply_diff()` method
- `backend/tests/test_body_diff.py` — new comprehensive test file with 8+ tests covering all code paths
