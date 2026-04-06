---
estimated_steps: 22
estimated_files: 3
skills_used: []
---

# T01: Strip Shape suffix, fix event log placeholder, and add model titles to VFS mount SPARQL

Three small backend/template fixes:

1. **Strip ' Shape' suffix from type labels** (D391): In `backend/app/services/shapes.py` `get_types()` method (line 556), add `.removesuffix(' Shape')` to the label when building the types list. Do NOT modify `_resolve_label()` — PropertyGroup labels like 'Relationships' don't have ' Shape'. The existing client-side strip in `workspace.js` line 2094-2095 (`typeLabel.replace(/\s+Shape$/, '')`) becomes redundant but leave it as a harmless no-op.

2. **Fix event log placeholder text**: In `backend/app/templates/browser/workspace.html` line 183, change `Event Log Explorer — coming in Phase 16` to `Loading event log...`. The lazy-load handler in workspace.js already replaces this content via htmx GET to `/browser/events` on first panel open.

3. **Add `dcterms:title` to VFS mount SPARQL**: In `backend/app/vfs/mount_router.py` `list_mounts()` function (around line 269), modify the model mounts SPARQL query to also fetch `dcterms:title`:
```sparql
SELECT DISTINCT ?modelId ?title FROM <urn:sempkm:models>
WHERE {
  ?model a <urn:sempkm:MentalModel> ;
         <urn:sempkm:modelId> ?modelId .
  OPTIONAL { ?model <http://purl.org/dc/terms/title> ?title }
}
ORDER BY ?modelId
```
Then in the dict construction (around line 282), use `title` with `model_id` as fallback:
```python
title = b.get('title', {}).get('value', '')
mounts.append({
    ...
    'name': title if title else model_id,
    ...
})
```

## Inputs

- ``backend/app/services/shapes.py` — get_types() method at line 556`
- ``backend/app/templates/browser/workspace.html` — event log placeholder at line 183`
- ``backend/app/vfs/mount_router.py` — list_mounts() SPARQL at line 269`

## Expected Output

- ``backend/app/services/shapes.py` — get_types() strips ' Shape' suffix from labels`
- ``backend/app/templates/browser/workspace.html` — placeholder says 'Loading event log...'`
- ``backend/app/vfs/mount_router.py` — model mounts include dcterms:title with fallback to modelId`

## Verification

cd backend && .venv/bin/python -m pytest tests/ -x -q --timeout=30 2>&1 | tail -5
