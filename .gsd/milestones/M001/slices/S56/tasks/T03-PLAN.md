# T03: 56-vfs-mountspec 03

**Slice:** S56 — **Milestone:** M001

## Description

Build the mount management UI in the Settings page for creating, editing, and deleting custom VFS mounts.

Purpose: This is the user-facing surface for VFS-05 -- users need a way to create and manage their custom mount configurations. The UI follows the existing VFS settings pattern (inline form with token management) and adds strategy-specific dynamic fields, a live directory preview, and a mount list.

Output: Extended _vfs_settings.html template, CSS for mount form, JS for interactions

## Must-Haves

- [ ] "Settings page shows mount management section below existing VFS token section"
- [ ] "User can fill in mount name, path prefix, strategy, and strategy-specific fields"
- [ ] "Strategy-specific fields appear dynamically when strategy is selected"
- [ ] "Scope dropdown lists 'All objects', saved queries by name, and 'Custom SPARQL...' option"
- [ ] "Live preview shows directory tree structure before saving"
- [ ] "Active mounts are listed below the form with Edit and Delete actions"
- [ ] "Creating a mount sends POST to /api/vfs/mounts and updates the mount list"
- [ ] "Deleting a mount removes it from the list after confirmation"

## Files

- `backend/app/templates/browser/_vfs_settings.html`
- `frontend/static/css/workspace.css`
- `frontend/static/js/workspace.js`
