---
estimated_steps: 7
estimated_files: 3
---

# T02: Modify save endpoint to emit body.diff and update event detail rendering

**Slice:** S02 — Body.Diff — Incremental Storage & Rendering
**Milestone:** M012

## Description

The core behavior change of S02. Modifies `save_body()` in the browser router to detect whether an existing body exists before saving — if it does and content differs, compute a unified diff and emit `body.diff`; if content is identical, return early as a no-op; if no prior body exists, emit `body.set` as before (D157). Also updates the event detail query service to read stored diffs for `body.diff` events and updates the template to render both operation types.

## Steps

1. **Modify `save_body()` in `backend/app/browser/objects.py` to query existing body:**

   After decoding the IRI and reading body content, before building params, add a SPARQL query to check the current body in `urn:sempkm:current`:
   ```python
   predicate_iri = predicate if predicate else "urn:sempkm:body"
   body_sparql = f"""SELECT ?body WHERE {{
     GRAPH <urn:sempkm:current> {{ <{decoded_iri}> <{predicate_iri}> ?body }}
   }}"""
   result = await client.query(body_sparql)
   rows = result.get("results", {}).get("bindings", [])
   existing_body = rows[0]["body"]["value"] if rows else None
   ```

2. **Add no-op check:**
   ```python
   if existing_body is not None and existing_body == body_content:
       return HTMLResponse(content='<span class="save-ok">Saved</span>', status_code=200)
   ```

3. **Branch on existing body to choose operation type:**
   ```python
   if existing_body is not None:
       # Existing body — compute diff and emit body.diff
       import difflib
       old_lines = existing_body.splitlines(keepends=True)
       new_lines = body_content.splitlines(keepends=True)
       diff_text = "".join(difflib.unified_diff(old_lines, new_lines, lineterm=""))
       
       from app.commands.handlers.body_diff import handle_body_diff
       from app.commands.schemas import BodyDiffParams
       params = BodyDiffParams(
           iri=decoded_iri,
           body=body_content,
           diff_text=diff_text,
           predicate=predicate if predicate else None,
       )
       operation = await handle_body_diff(params, settings.base_namespace)
   else:
       # No existing body — first body set
       from app.commands.handlers.body_set import handle_body_set
       from app.commands.schemas import BodySetParams
       params = BodySetParams(
           iri=decoded_iri,
           body=body_content,
           predicate=predicate if predicate else None,
       )
       operation = await handle_body_set(params, settings.base_namespace)
   ```
   The rest of the function (dcterms:modified timestamp, commit, validation queue) stays unchanged — it already operates on the generic `operation` variable.

4. **Add `"body.diff"` to `_OP_PRIORITY` in `backend/app/events/query.py`:**
   Add it right after `"body.set"`:
   ```python
   _OP_PRIORITY = [
       "object.create",
       "object.patch",
       "body.set",
       "body.diff",  # <-- add this
       "edge.create",
       "edge.patch",
       "edge.create.undo",
   ]
   ```

5. **Update `get_event_detail()` in `backend/app/events/query.py` to handle `body.diff`:**

   The existing code computes `body_diff` for `body.set` events by comparing before/after values. For `body.diff` events, the diff is stored directly in the event graph as a `sempkm:bodyDiff` data triple.

   Modify the body_diff computation block (around line 268):
   ```python
   body_diff: list[dict] | None = None
   if "body.diff" in op_type:
       # Stored diff — read directly from data_triples
       diff_text = None
       for s, p, o in data_triples:
           if p == "urn:sempkm:bodyDiff":
               diff_text = o
               break
       if diff_text:
           body_diff = self._parse_stored_diff(diff_text)
   elif "body.set" in op_type and new_values and before_values:
       # Legacy computed diff — compute on the fly
       body_pred = next(iter(new_values), None)
       if body_pred:
           old_body = before_values.get(body_pred, "")
           new_body = new_values.get(body_pred, "")
           body_diff = self._compute_body_diff(old_body, new_body)
   ```

6. **Add `_parse_stored_diff()` method to `EventQueryService`:**
   ```python
   def _parse_stored_diff(self, diff_text: str) -> list[dict]:
       """Parse a stored unified diff string into display format."""
       diff_lines: list[dict] = []
       for line in diff_text.splitlines():
           if line.startswith("+++") or line.startswith("---") or line.startswith("@@"):
               continue
           elif line.startswith("+"):
               diff_lines.append({"type": "add", "text": line[1:]})
           elif line.startswith("-"):
               diff_lines.append({"type": "remove", "text": line[1:]})
           else:
               diff_lines.append({"type": "context", "text": line[1:] if line.startswith(" ") else line})
       return diff_lines if diff_lines else [{"type": "context", "text": "(no changes)"}]
   ```
   Note: This is nearly identical to `_compute_body_diff()` parsing — it parses the same unified diff format, just from a stored string instead of computing it fresh.

7. **Update `backend/app/templates/browser/event_detail.html` template condition:**

   Change line 3 from:
   ```jinja
   {% if 'body.set' in detail.summary.operation_type and detail.body_diff %}
   ```
   to:
   ```jinja
   {% if ('body.set' in detail.summary.operation_type or 'body.diff' in detail.summary.operation_type) and detail.body_diff %}
   ```

## Must-Haves

- [ ] `save_body()` queries `urn:sempkm:current` for existing body before choosing operation type
- [ ] When existing body differs → emits `body.diff` with computed unified diff
- [ ] When no existing body → emits `body.set` (first body creation, per D157)
- [ ] When body content is unchanged → returns early with no event (no-op)
- [ ] `_OP_PRIORITY` includes `"body.diff"` after `"body.set"`
- [ ] `get_event_detail()` reads stored diff from data_triples for `body.diff` events
- [ ] `get_event_detail()` still computes diff on-the-fly for old `body.set` events (backward compat)
- [ ] Template renders both `body.set` and `body.diff` with diff highlighting

## Verification

- LSP diagnostics: `lsp diagnostics backend/app/browser/objects.py` and `lsp diagnostics backend/app/events/query.py` — no errors
- `cd backend && python -m pytest tests/ -v --tb=short -x -q 2>&1 | tail -5` — no regressions
- Manual code review: the `save_body()` branching logic is correct for all three cases (new body, changed body, unchanged body)

## Inputs

- T01 output: `backend/app/commands/handlers/body_diff.py` (importable `handle_body_diff`), `backend/app/commands/schemas.py` (importable `BodyDiffParams`)
- `backend/app/browser/objects.py` — current `save_body()` function at line 363
- `backend/app/events/query.py` — current `get_event_detail()` and `_compute_body_diff()` methods
- `backend/app/templates/browser/event_detail.html` — current template with `body.set` condition

## Expected Output

- `backend/app/browser/objects.py` — `save_body()` modified with existing-body query, branching logic, and no-op check
- `backend/app/events/query.py` — `_OP_PRIORITY` updated, `get_event_detail()` handles `body.diff`, new `_parse_stored_diff()` method
- `backend/app/templates/browser/event_detail.html` — condition extended to match `body.diff`
