# T01: 41-gap-closure-rules-flip-vfs 01

**Slice:** S41 — **Milestone:** M001

## Description

Wire the rules graph into model install and add validation enqueue after promote_triple.

Purpose: Close two INF-02 gaps -- (1) rules graph triples are loaded by the archive loader but never written to the triplestore during install_model, and (2) promoting an inferred triple commits to EventStore but never triggers re-validation.
Output: Two surgical code changes in models.py and inference/router.py.

## Must-Haves

- [ ] "Rules graph triples are written to triplestore during model install"
- [ ] "promote_triple enqueues validation after committing to EventStore"

## Files

- `backend/app/services/models.py`
- `backend/app/inference/router.py`
