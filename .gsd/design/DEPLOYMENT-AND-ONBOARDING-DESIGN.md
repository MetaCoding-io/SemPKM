# SemPKM Deployment & Onboarding Redesign

**Date:** 2026-03-21
**Status:** Approved — ready for implementation
**Supersedes:** D277 (QUIC/HTTP/3 deferral)
**Depends on:** M025 (Hosted Demo — Caddy already proven), M029 (Frontend Performance)

---

## Table of Contents

1. [Motivation](#1-motivation)
2. [Deployment Personas](#2-deployment-personas)
3. [Proposal 1 — Setup Wizard Domain Configuration](#3-proposal-1--setup-wizard-domain-configuration)
4. [Proposal 2 — Caddy Cloud Profile](#4-proposal-2--caddy-cloud-profile)
5. [Proposal 3 — Local TLS via mkcert](#5-proposal-3--local-tls-via-mkcert)
6. [BASE_NAMESPACE Strategy](#6-base_namespace-strategy)
7. [HTTP/3 — Resolution of D277](#7-http3--resolution-of-d277)
8. [Implementation Plan](#8-implementation-plan)
9. [Files Changed](#9-files-changed)
10. [Decisions](#10-decisions)

---

## 1. Motivation

SemPKM currently assumes a single deployment model: local Docker on `localhost:3000` with an optional reverse proxy bolted on by the operator. The setup wizard collects only a setup token and email — it never asks about the domain, BASE_NAMESPACE, or TLS. This creates three problems:

1. **Dangerous default IRI prefix.** `BASE_NAMESPACE=https://example.org/data/` is shared by every SemPKM instance worldwide. Two users who both forget to change it will create objects with identical IRIs, breaking federation and data portability. The setup wizard does not surface this.

2. **Cloud deployment is undocumented friction.** Self-hosted cloud users must manually configure Caddy/Traefik, set env vars, and understand the `Caddy → nginx → FastAPI` three-layer stack. There's no compose profile, no guided flow, and the production docs show an nginx TLS example that duplicates the internal nginx.

3. **HTTP/3 was deferred (D277) because `nginx:stable-alpine` lacks the module.** But cloud-hosted users would benefit from QUIC's multiplexing and 0-RTT, and Caddy — already proven in M025 for the demo instance — enables HTTP/3 by default with zero configuration.

---

## 2. Deployment Personas

| Persona | Example | Domain | TLS | BASE_NAMESPACE strategy |
|---------|---------|--------|-----|------------------------|
| **Local-only** | Developer on laptop, personal notes | `localhost:3000` | None needed | `urn:sempkm:{instance-uuid}/` — globally unique without a domain |
| **Self-hosted cloud** | VPS on Hetzner, home NAS with DDNS | `sempkm.example.com` | Let's Encrypt via Caddy (automatic) | `https://sempkm.example.com/data/` |
| **Platform-hosted** | `james.sempkm.app` (future) | Platform-assigned subdomain | Platform manages certs | `https://james.sempkm.app/data/` |

The current setup serves none of these well. The redesign gives each persona a clean path.

---

## 3. Proposal 1 — Setup Wizard Domain Configuration

### Problem

The setup wizard (`frontend/static/setup.html` → `POST /api/auth/setup`) only collects a setup token and email. The single most consequential decision — what IRI prefix all data will use forever — is buried in an env var that defaults to `example.org`.

### Design

Add a **deployment mode step** before account creation. The setup wizard becomes a two-step flow:

#### Step 1: Deployment Mode (new)

```
How will you access SemPKM?

○ Local only (http://localhost:3000)
  Data stays on this machine. Uses a UUID-based namespace
  so your data is portable if you add a domain later.

○ Custom domain (e.g., sempkm.example.com)
  For cloud hosting or LAN access. Enables federation
  and resolvable Linked Data URIs.

  [ Domain: _________________________ ]

○ I'll configure this later (advanced)
  Uses the UUID namespace. You can set BASE_NAMESPACE
  and APP_BASE_URL in .env at any time before creating data.
```

#### Step 2: Account Creation (existing, unchanged)

```
Enter the setup token shown in your terminal to claim this instance.

[ Setup Token: _____________________ ]
[ Email (optional): ________________ ]

[Claim Instance]
```

### Backend Changes

**New endpoint:** `POST /api/setup/configure-instance`

Called before `POST /api/auth/setup`. Accepts:

```json
{
  "mode": "local" | "domain" | "later",
  "domain": "sempkm.example.com"  // only when mode=domain
}
```

Behavior:
- **`local`**: Sets `BASE_NAMESPACE=urn:sempkm:{uuid}/` and `APP_BASE_URL=http://localhost:3000` in a persistent instance config file (`data/.instance-config.json`).
- **`domain`**: Validates the domain (DNS resolution check, no protocol prefix). Sets `BASE_NAMESPACE=https://{domain}/data/` and `APP_BASE_URL=https://{domain}`.
- **`later`**: Sets `BASE_NAMESPACE=urn:sempkm:{uuid}/` and `APP_BASE_URL=""` (derive from headers).

The endpoint writes to `data/.instance-config.json`, which is loaded by `config.py` at startup with higher priority than env vars but lower priority than explicit env var overrides. This way:
- First-time users get guided through the wizard
- Operators who set env vars explicitly still override everything
- The config persists across container rebuilds (volume-mounted `data/`)

**Guard rail:** If `BASE_NAMESPACE` is still `https://example.org/data/` and `data/.instance-config.json` does not exist, the API returns `setup_mode=true` even if an owner account exists, forcing the user through the deployment mode step. This catches existing instances that never configured their namespace.

**One-way door warning:** The wizard UI must clearly state that BASE_NAMESPACE cannot be changed after objects are created without a migration. If the triplestore already contains user data (objects in `urn:sempkm:current`), the endpoint should refuse to change the namespace and show a warning.

### Instance Config File

```json
// data/.instance-config.json
{
  "instance_id": "a1b2c3d4-...",
  "deployment_mode": "local",
  "base_namespace": "urn:sempkm:a1b2c3d4-.../",
  "app_base_url": "http://localhost:3000",
  "configured_at": "2026-03-21T14:30:00Z"
}
```

### Config Loading Priority (highest wins)

1. Explicit environment variables (`BASE_NAMESPACE=...` in `.env` or docker-compose)
2. Instance config file (`data/.instance-config.json`)
3. Pydantic defaults in `config.py`

This means: if an operator sets `BASE_NAMESPACE` in `.env`, the wizard choice is overridden. The wizard should detect this and skip the deployment mode step.

---

## 4. Proposal 2 — Caddy Cloud Profile

### Problem

Cloud users face a three-layer stack (`Caddy → nginx → FastAPI`) where Caddy and nginx both reverse-proxy. This is redundant — Caddy can serve static files, reverse-proxy to FastAPI, and terminate TLS in a single process.

### Design

Provide a **docker compose profile** that replaces nginx with Caddy for cloud deployments:

```
# Local development (default — no profile flag)
docker compose up

# Cloud deployment with automatic TLS
docker compose --profile cloud up
```

#### docker-compose.cloud.yml (compose override)

```yaml
services:
  # Override the frontend service to use Caddy instead of nginx
  frontend:
    image: caddy:2-alpine
    ports:
      - "443:443"
      - "80:80"      # Caddy auto-redirects HTTP → HTTPS
    volumes:
      - ./Caddyfile.cloud:/etc/caddy/Caddyfile
      - caddy_data:/data          # certificate storage
      - caddy_config:/config      # Caddy runtime config
      - ./frontend/static:/srv/static:ro
      - frontend_assets:/srv/built-assets:ro
    profiles:
      - cloud
    depends_on:
      api:
        condition: service_healthy
    networks:
      - sempkm

volumes:
  caddy_data:
  caddy_config:
```

#### Caddyfile.cloud (template)

```caddyfile
{$SEMPKM_DOMAIN:localhost} {
    # Static files — equivalent to nginx static serving
    handle /static/* {
        root * /srv
        file_server
        header Cache-Control "public, max-age=31536000, immutable"
    }

    # Built assets (content-hashed)
    handle /assets/* {
        root * /srv/built-assets
        file_server
        header Cache-Control "public, max-age=31536000, immutable"
    }

    # Auth pages — no cache
    handle /login.html {
        root * /srv/static
        file_server
        header Cache-Control "no-cache"
    }
    handle /setup.html {
        root * /srv/static
        file_server
        header Cache-Control "no-cache"
    }

    # API and everything else → FastAPI
    handle {
        reverse_proxy api:8000

        # Preserve merge_slashes behavior — Caddy does not
        # merge slashes by default, so no special config needed.
        # (nginx required merge_slashes off; Caddy is correct by default)
    }

    # Encode responses
    encode gzip
}
```

### What Caddy Gives Us For Free

| Feature | nginx (current) | Caddy (cloud profile) |
|---------|-----------------|----------------------|
| TLS certificates | Manual or external Caddy | Automatic Let's Encrypt + auto-renewal |
| HTTP/2 | Requires explicit config | Enabled by default |
| HTTP/3 (QUIC) | Not supported in stable-alpine | Enabled by default |
| Gzip | Configured manually | `encode gzip` directive |
| HTTP→HTTPS redirect | Separate server block | Automatic |
| OCSP stapling | Manual config | Automatic |
| Slash handling | `merge_slashes off` needed | Correct by default (no merging) |

### Key Concerns and Mitigations

**Concern: Caddy static file performance vs nginx.**
Caddy's file server is production-grade and handles the scale of a single-user/small-team PKM tool without issue. nginx's raw throughput advantage only matters at thousands of req/s, which is irrelevant here.

**Concern: `merge_slashes` equivalent.**
Caddy does not merge slashes by default — this is actually better than nginx, where we had to explicitly disable it (`merge_slashes off` was a bug fix in M002). No action needed.

**Concern: CORS headers.**
The current nginx config adds CORS headers for `/api/` and `/.well-known/sempkm`. In the Caddy cloud profile, these move to the FastAPI middleware (which already has CORS configured via `CORSMiddleware`). The nginx CORS headers were belt-and-suspenders; FastAPI's are sufficient. Verify during implementation.

**Concern: The existing `Caddyfile` at project root (for demo).**
Rename to `Caddyfile.demo` to avoid confusion. `Caddyfile.cloud` is the new template for self-hosted cloud. The demo instance keeps its own compose file (`docker-compose.demo.yml`) and Caddy config.

### Environment Variable for Domain

The cloud Caddyfile uses `{$SEMPKM_DOMAIN}` so the domain is set once in `.env`:

```bash
# .env for cloud deployment
SEMPKM_DOMAIN=sempkm.example.com
BASE_NAMESPACE=https://sempkm.example.com/data/
APP_BASE_URL=https://sempkm.example.com
COOKIE_SECURE=true
```

The setup wizard (Proposal 1) can generate this `.env` block for the user to copy.

---

## 5. Proposal 3 — Local TLS via mkcert

### Problem

Let's Encrypt requires a publicly reachable domain — it cannot issue certificates for `localhost`. But local TLS is useful for:
- Testing the HTTPS code path before deploying to cloud
- WebAuthn (requires secure context)
- Developing against `COOKIE_SECURE=true`

### Design

Provide a `docker compose --profile local-tls` profile that uses pre-generated mkcert certificates.

**User workflow:**

```bash
# One-time setup (requires mkcert installed on host)
mkcert -install                    # installs local CA into OS/browser trust stores
mkcert -cert-file certs/local.pem \
       -key-file certs/local-key.pem \
       localhost 127.0.0.1 ::1

# Then start with local TLS
docker compose --profile local-tls up
# Access at https://localhost
```

#### docker-compose.local-tls.yml

```yaml
services:
  frontend:
    image: caddy:2-alpine
    ports:
      - "443:443"
      - "80:80"
    volumes:
      - ./Caddyfile.local-tls:/etc/caddy/Caddyfile
      - ./certs:/etc/caddy/certs:ro
      - ./frontend/static:/srv/static:ro
      - frontend_assets:/srv/built-assets:ro
    profiles:
      - local-tls
    depends_on:
      api:
        condition: service_healthy
    networks:
      - sempkm
```

#### Caddyfile.local-tls

```caddyfile
localhost {
    tls /etc/caddy/certs/local.pem /etc/caddy/certs/local-key.pem

    # Same static/API routing as Caddyfile.cloud
    handle /static/* {
        root * /srv
        file_server
    }
    handle /assets/* {
        root * /srv/built-assets
        file_server
    }
    handle {
        reverse_proxy api:8000
    }
    encode gzip
}
```

### Priority

This is a **nice-to-have**. Implement after Proposals 1 and 2 are done. Most users will not need local TLS. The primary value is testing the production path.

### .gitignore

Add `certs/` to `.gitignore` — mkcert private keys must never be committed.

---

## 6. BASE_NAMESPACE Strategy

### The Problem with `https://example.org/data/`

RDF IRIs are **permanent identifiers**, not just URLs. The current default means:
- Every SemPKM instance in the world creates objects with the same IRI prefix
- Two users federating will have colliding IRIs
- `example.org` is an IANA-reserved domain — using it in production data is semantically wrong

### New Strategy

| Deployment mode | BASE_NAMESPACE | Rationale |
|----------------|---------------|-----------|
| **Local-only** | `urn:sempkm:{instance-uuid}/` | Valid IRI, globally unique (UUID), no domain needed. Tools like Protégé use this pattern. Data is portable — the URN is just a name, not a locator. |
| **Custom domain** | `https://{domain}/data/` | Resolvable, federable, proper Linked Data. The `{domain}` portion makes it globally unique. |
| **Platform-hosted** | `https://{subdomain}.sempkm.app/data/` | Platform assigns subdomain at provisioning time. |

### UUID-based URN Format

```
urn:sempkm:a1b2c3d4-e5f6-7890-abcd-ef1234567890/
```

- `urn:` — standard URN scheme (RFC 8141)
- `sempkm:` — namespace identifier (NID). Informal NID, acceptable for application-scoped use. If SemPKM grows to need a formal NID, register with IANA.
- UUID v4 — generated once at instance creation, stored in `data/.instance-config.json`
- Trailing `/` — so object IRIs are `urn:sempkm:{uuid}/{object-id}`

### Migration Path: Local → Domain

If a local user later gets a domain and wants resolvable Linked Data URIs:

1. **CLI command:** `sempkm migrate-namespace --from urn:sempkm:{uuid}/ --to https://example.com/data/`
2. **Implementation:** SPARQL `DELETE/INSERT` rewriting all subjects, predicates, objects, and graph names that start with the old prefix
3. **Scope:** Rewrites `urn:sempkm:current`, all event graphs, and the named-graph catalog
4. **Safety:** Creates a full RDF4J backup before starting, rolls back on failure
5. **When:** This is a future feature — document its existence in the setup wizard as "you can upgrade later" but don't build it in the first pass

### Validation at Startup

Add to `main.py` lifespan:

```python
if settings.base_namespace == "https://example.org/data/":
    if not Path("data/.instance-config.json").exists():
        logger.warning(
            "BASE_NAMESPACE is set to the default 'https://example.org/data/'. "
            "This will cause IRI collisions with other SemPKM instances. "
            "Run the setup wizard or set BASE_NAMESPACE in your .env file."
        )
```

---

## 7. HTTP/3 — Resolution of D277

D277 deferred HTTP/3 because `nginx:stable-alpine` doesn't include the `http_v3_module`. With the Caddy cloud profile (Proposal 2), this resolves naturally:

| Deployment | Protocol | How |
|-----------|----------|-----|
| Local dev (nginx) | HTTP/1.1 | Fine for localhost — no multiplexing benefit |
| Cloud (Caddy) | HTTP/2 + HTTP/3 | Caddy enables both by default, zero config |
| Demo (Caddy) | HTTP/2 + HTTP/3 | Already using Caddy since M025 |

**No nginx changes needed.** The local dev stack stays on `nginx:stable-alpine` serving HTTP/1.1. Cloud users who opt into the Caddy profile get HTTP/3 for free.

**Updated decision (replaces D277):**
> HTTP/3 is available automatically for cloud deployments via the Caddy compose profile. No nginx changes. Local dev stays HTTP/1.1 — multiplexing and 0-RTT provide no benefit over localhost.

---

## 8. Implementation Plan

### Phase 1: Instance Config & Namespace Strategy (backend)

**Goal:** Eliminate the `example.org` default and provide a safe fallback.

1. Create `backend/app/instance_config.py`:
   - `InstanceConfig` Pydantic model with `instance_id`, `deployment_mode`, `base_namespace`, `app_base_url`, `configured_at`
   - `load_instance_config()` — reads `data/.instance-config.json`, returns `None` if absent
   - `save_instance_config(config)` — writes atomically (write to `.tmp`, rename)
   - `generate_instance_id()` — `uuid.uuid4()`

2. Modify `backend/app/config.py`:
   - On import, check for `data/.instance-config.json`
   - If found and env var is not explicitly set, use instance config values for `base_namespace` and `app_base_url`
   - Priority: explicit env var > instance config > Pydantic default

3. Add startup validation in `main.py`:
   - Warn if `base_namespace` is still `example.org` and no instance config exists
   - If instance config exists but `base_namespace` was overridden by env var, log which value won

4. Create `POST /api/setup/configure-instance` endpoint:
   - Accepts `{mode, domain?}`
   - Validates domain (regex + optional DNS check)
   - Generates instance ID if not already set
   - Writes `data/.instance-config.json`
   - Returns the derived `base_namespace` and `app_base_url`
   - Refuses to change if user data already exists in triplestore

### Phase 2: Setup Wizard UI (frontend)

**Goal:** Guide first-time users through deployment mode selection.

1. Redesign `frontend/static/setup.html`:
   - Two-step flow: deployment mode → account creation
   - Step 1 shows three radio options (local / domain / later)
   - Domain input with inline validation (no protocol prefix, valid hostname)
   - "This cannot be changed after you create data" warning
   - Step 2 is the existing token + email form

2. Update `frontend/static/js/auth.js`:
   - `handleSetupForm()` becomes a multi-step flow
   - Step 1 calls `POST /api/setup/configure-instance`
   - Step 2 calls `POST /api/auth/setup` (unchanged)

3. Update `GET /api/auth/status`:
   - Add `instance_configured: bool` to response
   - If `false`, frontend shows Step 1; if `true`, shows Step 2

### Phase 3: Caddy Cloud Profile (infrastructure)

**Goal:** One-command cloud deployment with automatic TLS.

1. Create `Caddyfile.cloud` — template using `{$SEMPKM_DOMAIN}`
2. Create `docker-compose.cloud.yml` — override that replaces nginx with Caddy
3. Rename `Caddyfile` → `Caddyfile.demo`
4. Update `docker-compose.demo.yml` to reference `Caddyfile.demo`
5. Create `.env.cloud.example` with all required cloud vars
6. Verify CORS works without nginx headers (FastAPI `CORSMiddleware` only)
7. Test: `docker compose -f docker-compose.yml -f docker-compose.cloud.yml up`

### Phase 4: Local TLS Profile (infrastructure, nice-to-have)

**Goal:** mkcert-based local HTTPS for testing.

1. Create `Caddyfile.local-tls`
2. Create `docker-compose.local-tls.yml`
3. Add `certs/` to `.gitignore`
4. Document mkcert setup in user guide

### Phase 5: Documentation & Migration

**Goal:** Update all affected docs and ship.

1. Update `docs/guide/20-production-deployment.md`:
   - Add Caddy cloud profile section
   - Update architecture diagram
   - Add cloud deployment quick-start
2. Update `docs/guide/03-installation-and-setup.md`:
   - Document the new setup wizard flow
   - Explain deployment modes
3. Create `docs/guide/21-cloud-deployment.md`:
   - Step-by-step Caddy cloud guide
   - DNS, firewall, `.env` configuration
   - Backup and monitoring
4. Update `docs/guide/appendix-a-environment-variables.md`:
   - Add `SEMPKM_DOMAIN`
   - Document instance config file
5. Update `.gsd/DECISIONS.md`:
   - Close D277 with reference to this design
   - Add new decisions for namespace strategy and Caddy cloud profile

---

## 9. Files Changed

### New Files

| File | Purpose |
|------|---------|
| `backend/app/instance_config.py` | Instance config model and I/O |
| `backend/app/api/setup_routes.py` | `POST /api/setup/configure-instance` |
| `Caddyfile.cloud` | Cloud deployment Caddy template |
| `docker-compose.cloud.yml` | Cloud compose override |
| `.env.cloud.example` | Example cloud environment variables |
| `Caddyfile.local-tls` | Local TLS Caddy config (Phase 4) |
| `docker-compose.local-tls.yml` | Local TLS compose override (Phase 4) |
| `docs/guide/21-cloud-deployment.md` | Cloud deployment guide |

### Modified Files

| File | Change |
|------|--------|
| `backend/app/config.py` | Load instance config, priority chain |
| `backend/app/main.py` | Startup namespace validation, `instance_configured` in auth status |
| `backend/app/auth/router.py` | Add `instance_configured` to `GET /api/auth/status` |
| `frontend/static/setup.html` | Two-step wizard UI |
| `frontend/static/js/auth.js` | Multi-step setup flow logic |
| `frontend/static/css/style.css` | Setup wizard step styling |
| `.env` | Change default `BASE_NAMESPACE` comment |
| `.gitignore` | Add `certs/` |
| `Caddyfile` → `Caddyfile.demo` | Rename |
| `docker-compose.demo.yml` | Reference `Caddyfile.demo` |
| `docs/guide/20-production-deployment.md` | Caddy profile, updated architecture |
| `docs/guide/03-installation-and-setup.md` | New setup wizard flow |
| `docs/guide/appendix-a-environment-variables.md` | New vars |
| `.gsd/DECISIONS.md` | D277 closure, new decisions |

---

## 10. Decisions

| ID | Decision | Rationale |
|----|----------|-----------|
| D278 | Setup wizard collects deployment mode (local/domain/later) before account creation | BASE_NAMESPACE is a one-way door; the current `example.org` default is actively harmful. Users must make this choice explicitly. |
| D279 | Local-only instances use `urn:sempkm:{uuid}/` as BASE_NAMESPACE | Globally unique without needing a domain. Valid IRI per RFC 8141. Data is portable — UUID ensures no collisions. Standard pattern used by Protégé and other RDF tools. |
| D280 | Caddy replaces nginx for cloud deployments via compose profile | Eliminates redundant proxy layer. Automatic TLS, HTTP/2, HTTP/3 with zero configuration. Proven in M025 demo instance. nginx remains for local dev (simpler, no TLS overhead). |
| D281 | Instance configuration persists in `data/.instance-config.json` | Survives container rebuilds (Docker volume). Lower priority than env vars (operators can still override). Higher priority than Pydantic defaults (wizard choice beats `example.org`). |
| D282 | HTTP/3 available via Caddy cloud profile (closes D277) | No nginx changes needed. Cloud users get HTTP/3 automatically. Local dev stays HTTP/1.1 — no benefit from QUIC over localhost. |
| D283 | Local TLS via mkcert as optional compose profile (nice-to-have) | Let's Encrypt requires public domain. mkcert generates locally-trusted certs for `localhost`. Useful for testing HTTPS code path, WebAuthn, secure cookies. |
| D284 | Namespace migration CLI deferred — document as future escape hatch | SPARQL DELETE/INSERT across all graphs is feasible but expensive. First pass focuses on getting the namespace right from the start. Document the migration path so users know it's possible. |
