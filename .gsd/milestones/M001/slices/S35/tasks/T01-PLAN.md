# T01: 35-owl2-rl-inference 01

**Slice:** S35 — **Milestone:** M001

## Description

Build the complete backend inference engine: owlrl dependency, InferenceService with selective entailment filtering, API endpoints for triggering inference and managing inferred triples (list, dismiss, promote), SQLite metadata table for per-triple state, and event log integration.

Purpose: This is the core backend that makes OWL 2 RL inference work. Without it, no inferred triples exist. All other plans depend on data this produces.
Output: Working `/api/inference/run` endpoint that materializes owl:inverseOf (and other enabled entailment) triples into `urn:sempkm:inferred`, plus CRUD endpoints for triple management.

## Must-Haves

- [ ] "owlrl is installed and importable in the backend container"
- [ ] "POST /api/inference/run triggers OWL 2 RL inference, materializes owl:inverseOf triples, and stores them in urn:sempkm:inferred named graph"
- [ ] "Inferred triples that already exist in urn:sempkm:current are filtered out (no duplicates)"
- [ ] "Blank-node triples from owlrl expansion are filtered out before storage"
- [ ] "Each inference run creates an event log entry for auditability"
- [ ] "GET /api/inference/triples returns all inferred triples with metadata (source entailment type)"
- [ ] "POST /api/inference/triples/{hash}/dismiss marks a triple as dismissed; POST /api/inference/triples/{hash}/promote copies it to urn:sempkm:current via EventStore"
- [ ] "Selective entailment filtering: only enabled entailment types produce stored triples"
- [ ] "SQLite table inference_triple_state tracks per-triple dismiss/promote state"
- [ ] "basic-pkm manifest includes entailment_defaults section"

## Files

- `backend/pyproject.toml`
- `backend/app/inference/__init__.py`
- `backend/app/inference/service.py`
- `backend/app/inference/entailments.py`
- `backend/app/inference/models.py`
- `backend/app/inference/router.py`
- `backend/app/main.py`
- `backend/app/db/base.py`
- `models/basic-pkm/manifest.yaml`
