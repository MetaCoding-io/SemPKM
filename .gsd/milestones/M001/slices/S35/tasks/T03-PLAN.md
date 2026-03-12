# T03: 35-owl2-rl-inference 03

**Slice:** S35 — **Milestone:** M001

## Description

Build the Inference bottom panel tab — the user's control center for inference. Contains a Refresh button to trigger inference, a global list of all inferred triples, filters (object type, date range), grouping options, and per-triple dismiss/promote actions.

Purpose: This is the primary user interface for interacting with inference. Users trigger inference here, review results, and manage individual triples.
Output: New Inference tab in bottom panel with full interactive triple management via htmx.

## Must-Haves

- [ ] "New 'Inference' tab appears in the bottom panel alongside SPARQL, Event Log, AI Copilot"
- [ ] "Clicking 'Refresh' button triggers POST /api/inference/run and updates the triple list"
- [ ] "Panel shows a global list of all inferred triples with subject, predicate, object, entailment type"
- [ ] "User can filter triples by object type and date range"
- [ ] "User can group triples by time, object type, or property type"
- [ ] "User can dismiss individual triples (removes from view and inferred graph)"
- [ ] "User can promote individual triples to permanent user-created triples"
- [ ] "Loading spinner shows during inference run"
- [ ] "Last run timestamp displayed in panel header"

## Files

- `backend/app/templates/browser/workspace.html`
- `backend/app/templates/browser/inference_panel.html`
- `backend/app/templates/browser/inference_triple_row.html`
- `frontend/static/css/workspace.css`
- `frontend/static/js/workspace-layout.js`
