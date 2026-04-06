# M053 Research: Model Marketplace

## 1. Current State Analysis

### Install Flow (what exists)

The install pipeline is fully directory-based:

1. **Admin UI** — `models.html` shows a text input for filesystem path (e.g., `/app/models/basic-pkm`)
2. **Admin router** — `POST /admin/models/install` takes `path: str = Form(...)`, creates `Path(path)`, calls `model_service.install()`
3. **API router** — `POST /api/models/install` takes `InstallRequest(path=str)`, same flow
4. **ModelService.install()** — takes `model_dir: Path`, calls `parse_manifest(model_dir)` → `load_archive(model_dir, manifest)` → `validate_archive()` → transactional SPARQL writes → seed materialization → TBox surface creation → prefix registration
5. **Startup** — `ensure_starter_model()` auto-installs `basic-pkm` from `/app/models/basic-pkm` on first run

The loader (`load_archive()`) reads JSON-LD/Turtle files from subdirectories. The validator (`validate_archive()`) checks IRI namespacing and cross-file reference integrity.

### Model Archive Structure

Each model is a directory with standard layout:
```
manifest.yaml          # Pydantic-validated schema
ontology/{modelId}.jsonld
shapes/{modelId}.jsonld
views/{modelId}.jsonld
seed/{modelId}.jsonld   # optional
rules/{modelId}.ttl     # optional
dashboards/{modelId}.json  # optional, v2 manifest
workflows/{modelId}.json   # optional, v2 manifest
```

Sizes: 40-264KB per model (8 models total, ~1MB combined). Small enough for direct HTTP download without streaming concerns.

### Docker Volume Layout

- `./models:/app/models:ro` — bundled models, **read-only** in container
- `sempkm_data:/app/data` — persistent writable volume for SQLite, secrets, etc.
- Downloaded marketplace models must go to `/app/data/models/` (writable, persisted across restarts)
- `ensure_starter_model()` currently hardcodes `/app/models/basic-pkm` — needs to also check `/app/data/models/`

### Existing Security Infrastructure

- **SSRF guard** (`app.security.ssrf.validate_outbound_url`) — blocks loopback/private/reserved IPs. Must be used for all registry HTTP calls.
- **ZIP validator** (`app.security.zip_validator.validate_zip_contents`) — checks uncompressed size (2GB), file count (50K), compression ratio (100:1). Must be used for downloaded model archives.
- **httpx** — async HTTP client already in dependencies, used by triplestore client. Reuse for registry fetches.

### Registry Data in Triplestore

Model metadata is stored in `GRAPH <urn:sempkm:models>` with these properties:
- `sempkm:modelId`, `sempkm:version`, `dcterms:title`, `dcterms:description`, `sempkm:namespace`, `sempkm:installedAt`

No `sempkm:registryUrl`, `sempkm:remoteVersion`, or update-tracking properties exist yet.

## 2. Architecture Decisions

### Registry Hosting: Static JSON on GitHub Pages

**Recommendation:** Use a static JSON registry served from GitHub Pages (or any static hosting).

**Why:**
- Model archives are tiny (40-264KB) — no need for a CDN or object storage
- A simple `registry.json` index + `.tar.gz` archives in a GitHub repo can be served at zero cost
- GitHub Pages provides HTTPS, global CDN, and high availability
- No backend server to maintain, no API keys to manage
- Users can fork the registry to host private/custom models
- The SemPKM backend just needs to `GET` a JSON file and download `.tar.gz` archives

**Registry API contract (static files):**
```
https://registry.sempkm.org/                     (or GitHub Pages URL)
  registry.json                                    # catalog index
  archives/
    basic-pkm-2.2.0.tar.gz                       # model archives
    business-planning-1.0.0.tar.gz
```

**`registry.json` schema:**
```json
{
  "version": "1",
  "updated": "2026-04-05T12:00:00Z",
  "models": [
    {
      "modelId": "basic-pkm",
      "name": "Basic PKM",
      "description": "Personal knowledge management...",
      "version": "2.2.0",
      "author": "SemPKM",
      "archive_url": "archives/basic-pkm-2.2.0.tar.gz",
      "archive_sha256": "abc123...",
      "size_bytes": 42000,
      "tags": ["pkm", "notes", "tasks"],
      "icon": "notebook",
      "screenshots": [],
      "min_app_version": "2.0.0",
      "created": "2025-01-01",
      "updated": "2026-04-01"
    }
  ]
}
```

### Model Archive Format: .tar.gz

**Why `.tar.gz` over `.zip`:**
- Model directories have a flat structure (manifest.yaml + subdirs) — tar.gz preserves this exactly
- Python's `tarfile` module is stdlib, no extra dependencies
- Consistent with how Python packages and most Linux archives work
- The existing `zipfile` validator can be adapted for tarfile (size/count/ratio checks)

**Safety:** Extract to a temp directory first, validate manifest + contents, then move to `/app/data/models/{modelId}/`. Never extract directly to the install location.

### Download + Install Flow

```
User clicks "Install" in marketplace UI
  → Frontend: POST /admin/models/marketplace-install {modelId: "basic-pkm"}
  → Backend:
    1. Fetch registry.json (cached, TTL ~1 hour)
    2. Find model entry by modelId
    3. Download archive from archive_url
    4. Verify SHA-256 hash
    5. Validate archive (tarfile bomb protection)
    6. Extract to tempdir
    7. validate_outbound_url() on the registry URL (SSRF check)
    8. Run existing install pipeline: parse_manifest → load_archive → validate_archive → install
    9. Clean up tempdir
```

### Writable Model Directory

Add `/app/data/models/` as a secondary model directory. The `ensure_starter_model()` and `refresh_artifacts()` functions that currently hardcode `/app/models/{model_id}` need to search both directories.

Configuration: add `MARKETPLACE_MODELS_DIR` setting (default: `/app/data/models`).

## 3. Key Design Boundaries

### Boundary 1: Auto-Discovery of Bundled Models (S01, low risk)

Currently the install UI requires typing `/app/models/basic-pkm`. The admin page should scan `/app/models/` and show installable models as clickable buttons.

**Scope:** Backend scans `models_dir` for directories with `manifest.yaml`, frontend shows a "Available Models" section above the text input. No registry, no network — pure filesystem.

**Contract:** `GET /admin/models/available` returns `[{modelId, name, description, version, path, installed: bool}]`

### Boundary 2: Registry Client + Download Service (S02, medium risk)

Backend service to fetch `registry.json`, cache it, download archives, verify hashes, extract to tempdir.

**Contract:** `RegistryService.fetch_catalog()` → cached model list. `RegistryService.download_model(modelId)` → `Path` to extracted directory.

**Risk:** Network failures, corrupted downloads, hash mismatches, registry unavailability. All must be handled gracefully.

### Boundary 3: Install-from-Registry API + UI (S03, medium risk)

Wire the marketplace install flow end-to-end: browse catalog in UI, click install, show progress, handle errors.

**Contract:** `POST /admin/models/marketplace-install` → triggers download + install pipeline. UI shows progress via htmx polling or SSE.

### Boundary 4: Version Checking + Update Notifications (S04, low risk)

Compare installed model versions against registry versions. Show "Update available" badges.

**Contract:** `GET /admin/models/updates` → `[{modelId, installed_version, latest_version, changelog}]`

### Boundary 5: Marketplace Browse UI (S05, low risk)

Rich catalog browsing with descriptions, tags, version info. Card-based layout. This is the user-facing "Browse Marketplace" experience.

**Depends on:** S02 (registry client) and S03 (install flow).

## 4. Constraints from Existing Codebase

### ModelService.install() takes Path, not URL
The entire install pipeline is synchronous-on-disk. The marketplace flow must download + extract before calling install(). Do NOT try to make install() accept URLs — keep the boundary clean: download service handles network, install service handles disk.

### Read-only bundled models
`/app/models` is mounted `:ro`. Downloaded models go to `/app/data/models/`. The `refresh_artifacts()` method hardcodes `Path(f"/app/models/{model_id}")` — this must search both directories.

### Security: SHACL-AF rules are executable
Models containing `rules/*.ttl` files include SHACL-AF rules that execute SPARQL queries at validation time. A malicious model could craft rules that exfiltrate data or cause DoS. For M053, trust is established by SHA-256 hash verification against the registry. Model signing (GPG/Sigstore) is a future enhancement.

### Manifest version constraint
`ManifestSchema.namespace` must match `urn:sempkm:model:{modelId}:`. This prevents namespace collisions. Downloaded models go through the same validation as filesystem-installed models.

### No Python tarfile in dependencies
`tarfile` is stdlib — no pyproject.toml change needed. `hashlib` for SHA-256 is also stdlib.

## 5. Risk Assessment

### High Risk
- **Network reliability during install** — download could fail mid-stream, leaving partial state. Mitigation: download to tempdir, atomic move to install dir.
- **Archive extraction security** — tarfile path traversal (../../etc/passwd). Mitigation: validate all member paths are relative and within expected structure before extraction.

### Medium Risk  
- **Registry format stability** — if registry.json schema changes, old clients break. Mitigation: version field in registry, client validates version before parsing.
- **Offline mode** — app must work when registry is unreachable. Mitigation: cache registry.json locally, all UI gracefully handles fetch failures.
- **Concurrent installs** — two users clicking "Install" on the same model simultaneously. Mitigation: ModelService.install() already checks for duplicates.

### Low Risk
- **Model size limits** — current models are 40-264KB. Even 10x wouldn't stress the download pipeline.
- **Compatibility** — min_app_version field in registry handles version skew.

## 6. Recommended Slice Ordering

1. **S01: Auto-Discover Bundled Models** (low risk, immediate UX win)
   — Scan `/app/models/` on the admin page, show installable models. Zero network dependency.

2. **S02: Registry Client + Download Infrastructure** (highest technical risk, prove first)
   — Registry service, archive download, hash verification, tarfile extraction, SSRF guard, bomb protection. This is the core technical uncertainty.

3. **S03: Install-from-Registry Flow** (medium risk)
   — Wire download → install, handle writable model directory, update refresh_artifacts() path resolution, admin UI for marketplace install.

4. **S04: Marketplace Browse UI** (low risk)
   — Card-based catalog browser, search/filter by tag, model detail view with descriptions.

5. **S05: Version Checking + Updates** (low risk)
   — Compare installed vs registry versions, show update badges, update flow.

## 7. Existing Patterns to Reuse

| Pattern | Where | Reuse |
|---------|-------|-------|
| `validate_outbound_url()` | `app.security.ssrf` | All registry HTTP calls |
| `validate_zip_contents()` pattern | `app.security.zip_validator` | Adapt for tarfile bomb protection |
| htmx partial rendering | All admin templates | Marketplace UI |
| `ModelService.install(Path)` | `app.services.models` | Called after download+extract |
| `parse_manifest()` | `app.models.manifest` | Validate downloaded model before install |
| `ensure_starter_model()` | `app.services.models` | Pattern for auto-upgrade from registry |
| `httpx.AsyncClient` | `app.triplestore.client` | Reuse for registry fetches |
| `hx-indicator` loading pattern | `admin/models.html` | Install progress UX |

## 8. Candidate Requirements

These are surfaced for the planner to consider, not auto-binding:

| Candidate | Type | Rationale |
|-----------|------|-----------|
| **R-MP-01: Registry fetch must use SSRF guard** | security | Prevents SSRF via crafted registry URLs |
| **R-MP-02: Archive downloads verified by SHA-256** | security | Prevents tampered model injection |
| **R-MP-03: Tarfile extraction must validate paths** | security | Prevents path traversal attacks |
| **R-MP-04: App must function when registry unreachable** | operational | Network failures shouldn't break the app |
| **R-MP-05: Downloaded models persist across container restarts** | operational | Models stored in persistent volume |
| **R-MP-06: Install progress visible in UI** | functional | User knows download is happening, not frozen |
| **R-MP-07: Duplicate install prevented** | functional | Already exists in ModelService — verify it works for registry installs too |

## 9. Open Questions (Resolved)

**Q: Where to host the registry?**
→ GitHub Pages (simplest, zero cost, globally cached). A GitHub repo with `registry.json` + `archives/` directory. GitHub Actions can build archives from model source directories.

**Q: Should models be signed/verified for integrity?**  
→ SHA-256 hash verification for M053. Model signing (GPG/Sigstore) is future scope — adds significant complexity for marginal security gain when the registry is first-party.

**Q: Archive format?**  
→ `.tar.gz`. Model directories map naturally to tar archives. Python stdlib, no new dependencies.

## 10. Out of Scope Confirmation

Per the context document, these are confirmed out of scope:
- Community model submissions
- Model authoring tools
- Paid models or licensing
- Model dependency resolution (model A requires model B)
- Model signing/GPG verification (SHA-256 hash is sufficient for M053)
