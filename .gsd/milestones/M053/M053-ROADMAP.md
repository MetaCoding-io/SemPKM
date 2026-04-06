# M053: Model Marketplace

## Vision
Cloud-hosted model registry so users can discover, browse, and install Mental Models from an in-app marketplace without filesystem access. Replaces the current path-based install flow with a browsable catalog backed by a static JSON registry and downloadable .tar.gz archives.

## Slice Overview
| ID | Slice | Risk | Depends | Done | After this |
|----|-------|------|---------|------|------------|
| S01 | Auto-Discover Bundled Models | low | — | ✅ | Admin → Mental Models shows available bundled models as clickable cards. Click Install on one → model installs without typing a path. |
| S02 | Marketplace Registry + Install-from-Cloud | high | S01 | ✅ | Admin → Mental Models shows a Browse Marketplace section with models from a remote registry. Click Install on a marketplace model → download + verify + extract + install → model types appear in explorer. |
| S03 | Version Checking + Update Notifications | low | S02 | ✅ | Admin → Mental Models shows 'Up to date' or 'Update available' badges on installed model cards. Click Update to re-download and reinstall the latest version. |
