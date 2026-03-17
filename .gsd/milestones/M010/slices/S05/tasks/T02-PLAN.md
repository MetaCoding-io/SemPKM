---
estimated_steps: 7
estimated_files: 5
---

# T02: Wire OPML import route + template into app with integration tests

**Slice:** S05 — OPML import + app settings
**Milestone:** M010

## Description

Wire the OPML parser (from T01) into the RSS Reader app with a file upload route, htmx template, and integration tests. This delivers requirement **RSS-05** (OPML import for feed subscriptions). The user clicks "Import OPML" in the feed sidebar, uploads an `.opml` file, and sees a summary of created/duplicate/failed subscriptions.

The import route reads the uploaded file, calls `parse_opml()`, then calls `FeedService.subscribe()` sequentially for each feed. Categories from the OPML file are preserved by patching `bpkm:tags` onto the created subscription.

**Relevant skill:** `test` (for test patterns)

## Steps

1. **Add import fallback for `opml_parser` in `apps/rss-reader/app.py`** — follow the same `try/except ImportError` pattern already used for `feed_service`:
   ```python
   try:
       from services.opml_parser import parse_opml
   except ImportError:
       import importlib.util as _ilu
       from pathlib import Path as _P
       _op_path = str(_P(__file__).resolve().parent / "services" / "opml_parser.py")
       _op_spec = _ilu.spec_from_file_location("opml_parser", _op_path)
       _op_mod = _ilu.module_from_spec(_op_spec)
       _op_spec.loader.exec_module(_op_mod)
       parse_opml = _op_mod.parse_opml
   ```

2. **Create GET `/_fragments/opml-import-dialog` route** in `app.py`:
   - Renders `opml-import.html` template via `ctx.render_template()`
   - Simple: just returns the upload form

3. **Create POST `/_fragments/import-opml` route** in `app.py`:
   - Read uploaded file via `form = await request.form(); opml_file = form.get("opml_file")`
   - If no file or empty → return `<div class="rss-error">No OPML file uploaded</div>`
   - Read file content: `content = await opml_file.read()`
   - Call `parse_opml(content)` — if returns empty list → return error div ("No feeds found in OPML file" or "Invalid OPML file")
   - For each feed entry, call `await subscribe(ctx, entry["url"], entry["title"])` sequentially (not gather — avoid overwhelming SDK). Track counts: created, duplicate, error.
   - If feed has a `category` value, and the subscribe returned `"created"`, patch `bpkm:tags` onto the subscription IRI: `await ctx.commands.execute("object.patch", {"iri": result["iri"], "properties": {"https://bpkm.org/ontology/tags": entry["category"]}})`
   - Return HTML summary div with CSS class `rss-success`: "Imported N feeds (M already subscribed, K errors)"
   - Set response header `HX-Trigger: feedsChanged` so sidebar refreshes

4. **Create `apps/rss-reader/frontend/templates/opml-import.html`**:
   ```html
   <div id="rss-opml-import" class="rss-subscribe-form">
     <h3>Import OPML</h3>
     <p>Upload an OPML file to import feed subscriptions.</p>
     <form hx-post="/_fragments/import-opml"
           hx-target="#opml-import-result"
           hx-swap="innerHTML"
           hx-encoding="multipart/form-data">
       <div class="form-group">
         <input type="file" name="opml_file" accept=".opml,.xml" required class="form-input">
       </div>
       <div class="form-actions">
         <button type="submit" class="btn btn-primary">Import</button>
       </div>
     </form>
     <div id="opml-import-result"></div>
   </div>
   ```

5. **Add "Import OPML" button to `feed-sidebar.html`** — add below the existing Subscribe button:
   ```html
   <button class="rss-subscribe-btn"
           hx-get="/_fragments/opml-import-dialog"
           hx-target="#rss-reading-pane"
           hx-swap="innerHTML">
     <i data-lucide="upload"></i> Import OPML
   </button>
   ```
   This goes in both the feeds-present block (after Subscribe button) and the empty-state block.

6. **Add ≥8 integration tests to `backend/tests/test_opml_import.py`** (appending to the file from T01):
   - Use the `_make_mock_ctx()` pattern from `test_feed_service.py`. The mock ctx needs: `ctx.render_template` returning a string, `ctx.commands.execute` as AsyncMock, `ctx.graph.query` as AsyncMock.
   - Import the route handler via `importlib.util.spec_from_file_location` to get `rss_reader_app` or individual functions.
   - **Alternative approach (simpler):** Since the import route is essentially `parse_opml()` + `subscribe()` calls, test the integration logic as a helper function. Extract the core logic into a testable async function `process_opml_import(ctx, xml_bytes)` that returns `{"created": N, "duplicate": M, "errors": K, "feeds": [...]}`, and test that function with mock ctx.
   - Test cases:
     - Successful import with 3 feeds → subscribe called 3 times, returns created=3
     - Import with some duplicates → subscribe returns "duplicate" for 2, created=1, duplicate=2
     - Empty OPML (no feeds) → returns created=0 with appropriate message
     - Invalid XML → returns error
     - Feed with category → object.patch called with bpkm:tags
     - Feed without category → no object.patch call
     - Subscribe raises exception for one feed → error count incremented, others still processed
     - All feeds are duplicates → duplicate count correct

7. **Verify everything:**
   ```bash
   cd backend && .venv/bin/python -m pytest tests/test_opml_import.py -v
   python3 -c "import ast; ast.parse(open('../apps/rss-reader/app.py').read())"
   cd backend && .venv/bin/python -m pytest tests/test_rss_feed_parser.py tests/test_feed_service.py -v
   ```

## Must-Haves

- [ ] POST `/_fragments/import-opml` route accepts multipart file upload
- [ ] Route calls `parse_opml()` then `subscribe()` per feed sequentially
- [ ] Categories from OPML patched as `bpkm:tags` on created subscriptions
- [ ] Error cases (no file, empty, invalid XML, subscribe failures) handled gracefully with user-friendly messages
- [ ] `HX-Trigger: feedsChanged` emitted on successful import
- [ ] "Import OPML" button added to feed sidebar
- [ ] ≥8 import route/integration tests pass
- [ ] Zero regressions in existing test suites

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_opml_import.py -v` — ≥20 total tests (12 parser + 8 route)
- `python3 -c "import ast; ast.parse(open('apps/rss-reader/app.py').read())"` — syntax OK
- `cd backend && .venv/bin/python -m pytest tests/test_rss_feed_parser.py tests/test_feed_service.py -v` — zero regressions

## Inputs

- `apps/rss-reader/services/opml_parser.py` — T01's pure `parse_opml()` function
- `apps/rss-reader/services/feed_service.py` — `subscribe(ctx, feed_url, title)` returns `{"status": "created"|"duplicate", "iri": ...}`
- `apps/rss-reader/app.py` — existing route patterns, import fallback patterns
- `apps/rss-reader/frontend/templates/subscribe-dialog.html` — reference for form/htmx patterns
- `apps/rss-reader/frontend/templates/feed-sidebar.html` — must add Import OPML button
- `backend/tests/test_feed_service.py` — reference for mock ctx patterns (`_make_mock_ctx()`, `_make_mock_http_client()`)

## Expected Output

- `apps/rss-reader/app.py` — modified with import fallback + 2 new routes (GET dialog + POST import)
- `apps/rss-reader/frontend/templates/opml-import.html` — new file upload template
- `apps/rss-reader/frontend/templates/feed-sidebar.html` — modified with Import OPML button
- `backend/tests/test_opml_import.py` — expanded with ≥8 route/integration tests (≥20 total)

## Observability Impact

- **Import route summary div:** POST `/_fragments/import-opml` returns `<div class="rss-success" data-created="N" data-duplicates="M" data-errors="K">` with structured data attributes — inspectable via `browser_find` or `curl`.
- **Error divs:** All error paths (no file, empty file, invalid XML, subscribe failures) return `<div class="rss-error">` with user-visible messages — never silent failures.
- **HX-Trigger header:** Successful imports emit `HX-Trigger: feedsChanged` — observable via network logs to confirm sidebar refresh was triggered.
- **Logger warnings:** `process_opml_import()` logs subscribe failures and tag-patch failures via `logger.warning(...)` — check app logs for `OPML import subscribe error` or `Failed to patch tags` prefixes.
- **Test verification:** `cd backend && .venv/bin/python -m pytest tests/test_opml_import.py -v` — ≥27 tests covering parser + route integration.
