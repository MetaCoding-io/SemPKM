# T01: 42-vfs-browser-fix 01

**Slice:** S42 — **Milestone:** M001

## Description

Fix three bugs preventing the VFS browser from functioning: (1) wrong LabelService method name causing 500 errors on object listing, (2) wrong SPARQL predicate causing model names to fall back to IDs, (3) htmx `revealed` trigger without `once` causing infinite retry loops on error.

Purpose: Close VFS-01 gap from v2.4 milestone audit -- VFS browser tab must be fully functional.
Output: Working VFS browser tree that loads models, types, and objects without errors.

## Must-Haves

- [ ] "VFS tree loads installed models with human-readable names (not IDs)"
- [ ] "Expanding a type folder loads and displays objects without 500 errors"
- [ ] "Failed htmx requests do not cause infinite retry loops"
- [ ] "Clicking an object in the VFS tree opens it in a workspace tab"

## Files

- `backend/app/browser/router.py`
- `backend/app/templates/browser/vfs_browser.html`
- `backend/app/templates/browser/_vfs_types.html`
