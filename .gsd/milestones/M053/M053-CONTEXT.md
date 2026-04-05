---
depends_on: [M048]
---

# M053: Model Marketplace

**Gathered:** 2026-04-05
**Status:** Ready for planning

## Project Description

Cloud-hosted model registry so users can discover, browse, and install Mental Models without filesystem access. The current install flow requires typing a filesystem path (`/app/models/basic-pkm`) which is a deployment dead end — users of a Docker image have no way to add models beyond what's bundled.

## Why This Milestone

Mental Models are SemPKM's core value proposition ("Install a Mental Model and immediately create, browse, and explore structured knowledge"). But discovering and installing models requires filesystem access inside the Docker container. This blocks adoption — no one outside the developer can install new models.

## User-Visible Outcome

### When this milestone is complete, the user can:

- Open Admin → Mental Models and see a "Browse Marketplace" button
- Browse available models in an in-app catalog with descriptions, screenshots, version info
- Click "Install" on any model to download and install it from the cloud registry
- See update notifications when installed models have newer versions available
- Auto-discover models from `/app/models/` on the Install page (as an interim improvement)

### Entry point / environment

- Entry point: http://localhost:4000/admin/models + cloud registry API
- Environment: Docker Compose + cloud-hosted registry (simple static API or S3 + CloudFront)
- Live dependencies involved: cloud registry HTTP endpoint

## Completion Class

- Contract complete means: registry API serves model metadata, in-app UI fetches and displays catalog, install-from-URL works
- Integration complete means: full flow from browse → install → use model works
- Operational complete means: registry hosted and accessible, model archives served via HTTPS

## Final Integrated Acceptance

To call this milestone complete, we must prove:

- Fresh SemPKM instance → Admin → Mental Models → Browse Marketplace → see available models
- Click Install on a model → download + install succeeds → model types appear in explorer
- Installed model shows "Up to date" or "Update available" badge

## Risks and Unknowns

- **Registry hosting** — need to decide: static JSON on GitHub Pages, S3 + CloudFront, or a simple API server
- **Model archive format** — currently a directory. May need to support .tar.gz or .zip for HTTP download.
- **Versioning** — how to handle model version upgrades when user has existing data
- **Security** — models contain executable SHACL-AF rules. Need to trust the source.
- **Offline fallback** — app should still work when registry is unreachable

## Existing Codebase / Prior Art

- `backend/app/services/models.py` — ModelService.install() takes a directory path. Needs to accept URL or downloaded archive.
- `backend/app/models/loader.py` — load_archive() parses from directory. Needs archive extraction step.
- `backend/app/admin/router.py` — admin_models_install() currently takes a path string from form input.
- `backend/app/templates/admin/models.html` — install UI with text input field.

## Scope

### In Scope

- Auto-discover installable models from `/app/models/` directory (interim improvement)
- Cloud registry API design and hosting (static JSON + model archives)
- In-app marketplace browse UI
- Install-from-registry flow (download → extract → install)
- Version checking and update notifications
- Model metadata schema (name, description, version, author, screenshots, dependencies)

### Out of Scope / Non-Goals

- Community model submissions (later phase)
- Model authoring tools
- Paid models or licensing
- Model dependency resolution (install model A which requires model B)

## Open Questions

- Where to host the registry? GitHub Pages (simplest), S3 (scalable), or custom API?
- Should models be signed/verified for integrity?
