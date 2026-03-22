---
estimated_steps: 5
estimated_files: 2
skills_used: []
---

# T04: SPARQL console Mirror button and endpoint picker

**Slice:** S01 — Federated SPARQL & Mirrored Triples
**Milestone:** M033

## Description

Add the user-facing mirror capability to the SPARQL console. When a user executes a query containing a SERVICE clause, a "Mirror Results" button appears in the results info bar. Clicking it sends the query and detected endpoint URL to the mirror API, stores the federated results as mirrored triples, and shows success/failure feedback. The button also indicates whether the detected endpoint is in the allowlist.

The SPARQL console is a 1500-line ES module at `frontend/static/js/sparql-console.js` using CodeMirror 6 for the editor. Results render in a table below the editor. The info bar (element `#sparql-results-info`) already shows row count and execution time, and conditionally shows a "Save as View" button for saved queries. The mirror button follows the same pattern.

## Steps

1. **Add SERVICE clause detection function:**
   - Add `function detectServiceEndpoints(queryText)` that scans the query text for `SERVICE\s+<([^>]+)>` patterns (respecting string literals via the existing stripped-query approach — reuse the `KNOWN_VOCAB_PREFIXES` skip pattern or a simpler regex on non-string content). Returns an array of endpoint URL strings found, or empty array if no SERVICE clauses detected.
   - Also detect `SERVICE SILENT <url>` variant.

2. **Add Mirror Results button to the result info bar:**
   - In the result rendering section (near line ~300, where `infoEl` content is built after successful query execution), after the existing "Save as View" button conditional:
   - Call `detectServiceEndpoints(queryText)`. If endpoints found, create a "Mirror Results" button with class `sparql-mirror-btn`.
   - Include the first detected endpoint URL as a data attribute (`data-endpoint`).
   - Add a Lucide `database` icon in the button.

3. **Implement mirror button click handler:**
   - On click, call `POST /api/sparql/mirror` with `{query: queryText, endpoint_url: endpointUrl}`.
   - While pending, disable the button and show "Mirroring..." text.
   - On success (200), update button text to "✓ Mirrored {count} triples" and disable it.
   - On 403 (endpoint not in allowlist), show an inline error: "Endpoint not allowed. Ask an admin to add it to the federation allowlist."
   - On other errors, show the error message from the response.

4. **Add endpoint allowlist check:**
   - On page load (or lazily on first SERVICE query), fetch `GET /api/sparql/mirror/endpoints` to get the allowlist.
   - Cache the result in module state.
   - When building the mirror button, check if the detected endpoint is in the cached allowlist. If not, add a warning icon and title tooltip: "This endpoint is not in the allowlist — mirroring may be blocked."

5. **Add CSS styling for mirror button in `frontend/static/css/workspace.css`:**
   - Add `.sparql-mirror-btn` styling — teal accent color matching the mirrored badge, similar button shape to `.sparql-save-view-btn`.
   - Add `.sparql-mirror-btn:disabled` state (muted, no pointer).
   - Add `.sparql-mirror-btn.mirror-warning` variant with amber/orange border for unallowed endpoints.
   - Add `.sparql-mirror-success` for the success state text.

## Must-Haves

- [ ] SERVICE endpoint detection works for `SERVICE <url>` and `SERVICE SILENT <url>` patterns
- [ ] Mirror button appears only when query contains SERVICE clauses
- [ ] Mirror button calls POST /api/sparql/mirror with correct payload
- [ ] Success feedback shows mirrored triple count
- [ ] Error feedback shows meaningful message for blocked endpoints
- [ ] Endpoint allowlist is fetched and used to show warning indicator
- [ ] Button styling matches existing SPARQL console design

## Verification

- `rg "detectServiceEndpoints\|sparql-mirror-btn\|mirror" frontend/static/js/sparql-console.js` — SERVICE detection and mirror button code present
- `rg "sparql-mirror-btn" frontend/static/css/workspace.css` — button styling exists

## Inputs

- `frontend/static/js/sparql-console.js` — existing SPARQL console module (1517 lines) with result rendering, info bar, and "Save as View" button pattern
- `frontend/static/css/workspace.css` — existing styles with `.sparql-save-view-btn` pattern to follow
- `backend/app/sparql/mirror_router.py` — mirror API endpoints created in T02 (POST /api/sparql/mirror, GET /api/sparql/mirror/endpoints)

## Expected Output

- `frontend/static/js/sparql-console.js` — with detectServiceEndpoints(), mirror button rendering, click handler, allowlist check
- `frontend/static/css/workspace.css` — with `.sparql-mirror-btn` and related styling
