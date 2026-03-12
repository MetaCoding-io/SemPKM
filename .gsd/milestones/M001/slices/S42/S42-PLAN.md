# S42: Vfs Browser Fix

**Goal:** Fix three bugs preventing the VFS browser from functioning: (1) wrong LabelService method name causing 500 errors on object listing, (2) wrong SPARQL predicate causing model names to fall back to IDs, (3) htmx `revealed` trigger without `once` causing infinite retry loops on error.
**Demo:** Fix three bugs preventing the VFS browser from functioning: (1) wrong LabelService method name causing 500 errors on object listing, (2) wrong SPARQL predicate causing model names to fall back to IDs, (3) htmx `revealed` trigger without `once` causing infinite retry loops on error.

## Must-Haves


## Tasks

- [x] **T01: 42-vfs-browser-fix 01** `est:1min`
  - Fix three bugs preventing the VFS browser from functioning: (1) wrong LabelService method name causing 500 errors on object listing, (2) wrong SPARQL predicate causing model names to fall back to IDs, (3) htmx `revealed` trigger without `once` causing infinite retry loops on error.

Purpose: Close VFS-01 gap from v2.4 milestone audit -- VFS browser tab must be fully functional.
Output: Working VFS browser tree that loads models, types, and objects without errors.

## Files Likely Touched

- `backend/app/browser/router.py`
- `backend/app/templates/browser/vfs_browser.html`
- `backend/app/templates/browser/_vfs_types.html`
