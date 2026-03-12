# S56: Vfs Mountspec

**Goal:** Create the MountSpec RDF vocabulary, a MountService for CRUD operations on mount definitions, and REST API endpoints for the settings UI to consume.
**Demo:** Create the MountSpec RDF vocabulary, a MountService for CRUD operations on mount definitions, and REST API endpoints for the settings UI to consume.

## Must-Haves


## Tasks

- [x] **T01: 56-vfs-mountspec 01** `est:4min`
  - Create the MountSpec RDF vocabulary, a MountService for CRUD operations on mount definitions, and REST API endpoints for the settings UI to consume.

Purpose: Foundation layer -- all other plans depend on mount definitions existing and being manageable. The RDF vocabulary defines the MountSpec schema, the service handles reading/writing to the triplestore, and the API endpoints expose mount management to the frontend.

Output: mount_service.py (sync CRUD), mount_router.py (REST API), updated cache.py (mount cache invalidation)
- [x] **T02: 56-vfs-mountspec 02** `est:5min`
  - Build the WebDAV directory strategy collections, extend the provider for mount dispatch, and create MountedResourceFile with SHACL-aware frontmatter rendering and property write-back.

Purpose: This is the core VFS extension -- it makes custom mounts browseable via WebDAV and enables full property editing through frontmatter. Users can mount objects organized by type, date, tag, property, or flat, and edit properties directly in their text editor.

Output: mount_collections.py (strategy collections), strategies.py (query builders), mount_resource.py (SHACL resource), extended provider.py, extended write.py
- [x] **T03: 56-vfs-mountspec 03** `est:3min`
  - Build the mount management UI in the Settings page for creating, editing, and deleting custom VFS mounts.

Purpose: This is the user-facing surface for VFS-05 -- users need a way to create and manage their custom mount configurations. The UI follows the existing VFS settings pattern (inline form with token management) and adds strategy-specific dynamic fields, a live directory preview, and a mount list.

Output: Extended _vfs_settings.html template, CSS for mount form, JS for interactions

## Files Likely Touched

- `backend/app/vfs/mount_service.py`
- `backend/app/vfs/mount_router.py`
- `backend/app/vfs/cache.py`
- `backend/app/vfs/mount_collections.py`
- `backend/app/vfs/strategies.py`
- `backend/app/vfs/mount_resource.py`
- `backend/app/vfs/provider.py`
- `backend/app/vfs/collections.py`
- `backend/app/vfs/write.py`
- `backend/app/templates/browser/_vfs_settings.html`
- `frontend/static/css/workspace.css`
- `frontend/static/js/workspace.js`
