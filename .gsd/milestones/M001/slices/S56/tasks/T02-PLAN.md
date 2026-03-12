# T02: 56-vfs-mountspec 02

**Slice:** S56 — **Milestone:** M001

## Description

Build the WebDAV directory strategy collections, extend the provider for mount dispatch, and create MountedResourceFile with SHACL-aware frontmatter rendering and property write-back.

Purpose: This is the core VFS extension -- it makes custom mounts browseable via WebDAV and enables full property editing through frontmatter. Users can mount objects organized by type, date, tag, property, or flat, and edit properties directly in their text editor.

Output: mount_collections.py (strategy collections), strategies.py (query builders), mount_resource.py (SHACL resource), extended provider.py, extended write.py

## Must-Haves

- [ ] "WebDAV root lists custom mount directories alongside model directories"
- [ ] "Navigating into a mount path dispatches to the correct strategy collection"
- [ ] "Each of 5 strategies (flat, by-type, by-date, by-tag, by-property) produces correct subdirectory structure"
- [ ] "Files within mounted directories render SHACL-aware frontmatter with human-readable property names"
- [ ] "Editing frontmatter via WebDAV PUT writes changed properties back to RDF via object.patch"
- [ ] "Objects missing the grouping property appear in _uncategorized folder"
- [ ] "Multi-valued grouping properties produce duplicate files in each relevant folder"
- [ ] "All duplicate files share the same ETag derived from object IRI (not content)"

## Files

- `backend/app/vfs/mount_collections.py`
- `backend/app/vfs/strategies.py`
- `backend/app/vfs/mount_resource.py`
- `backend/app/vfs/provider.py`
- `backend/app/vfs/collections.py`
- `backend/app/vfs/write.py`
