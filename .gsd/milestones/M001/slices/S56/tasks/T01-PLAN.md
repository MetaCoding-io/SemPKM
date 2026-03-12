# T01: 56-vfs-mountspec 01

**Slice:** S56 — **Milestone:** M001

## Description

Create the MountSpec RDF vocabulary, a MountService for CRUD operations on mount definitions, and REST API endpoints for the settings UI to consume.

Purpose: Foundation layer -- all other plans depend on mount definitions existing and being manageable. The RDF vocabulary defines the MountSpec schema, the service handles reading/writing to the triplestore, and the API endpoints expose mount management to the frontend.

Output: mount_service.py (sync CRUD), mount_router.py (REST API), updated cache.py (mount cache invalidation)

## Must-Haves

- [ ] "MountSpec definitions can be created, read, updated, and deleted via API"
- [ ] "Mount definitions are persisted as RDF triples in urn:sempkm:mounts named graph"
- [ ] "Mount path prefixes are validated to avoid conflicts with installed model IDs"
- [ ] "Personal mounts are visible only to their creator; shared mounts visible to all"
- [ ] "Mount preview endpoint returns a directory tree structure for a given configuration"

## Files

- `backend/app/vfs/mount_service.py`
- `backend/app/vfs/mount_router.py`
- `backend/app/vfs/cache.py`
