# SemPKM App Platform — Architecture Design

**Date:** 2026-03-16
**Status:** Draft
**Depends on:** Mental Model system (M001), Event Sourcing (M002), Workspace UI (M003-M006)
**First app:** RSS Reader + Hypothesis Integration (see `docs/research/rss-reader-hypothesis-integration.md`)

---

## Table of Contents

1. [Design Philosophy](#1-design-philosophy)
2. [App vs Mental Model](#2-app-vs-mental-model)
3. [AppManifest Specification](#3-appmanifest-specification)
4. [Graph & Data Architecture](#4-graph--data-architecture)
5. [Process Architecture & Sandboxing](#5-process-architecture--sandboxing)
6. [App SDK](#6-app-sdk)
7. [Frontend Integration — Three Levels](#7-frontend-integration--three-levels)
8. [Scheduler & Background Tasks](#8-scheduler--background-tasks)
9. [Permissions & Enforcement](#9-permissions--enforcement)
10. [Lifecycle Management](#10-lifecycle-management)
11. [Admin Portal — App Monitoring](#11-admin-portal--app-monitoring)
12. [Bulk EventStore Extension](#12-bulk-eventstore-extension)
13. [Concrete Example: RSS Reader Manifest](#13-concrete-example-rss-reader-manifest)
14. [Pydantic Schema](#14-pydantic-schema)
15. [Disk Layout](#15-disk-layout)
16. [Migration & Upgrade](#16-migration--upgrade)
17. [Future Work](#17-future-work)

---

## 1. Design Philosophy

### Core principles

1. **Mental models are always shared.** An app never bundles its own model. Models are published independently to the marketplace, versioned on their own timeline, and reusable by any number of apps. The model defines the data contract; the app provides behavior.

2. **App data lives in `urn:sempkm:current`.** Apps produce data into the same graph as everything else. Data typed by shared models is first-class — browsable, queryable, linkable. Apps are data producers/consumers, not data owners.

3. **Apps are sandboxed from day one.** Each app runs in its own subprocess with its own virtual environment. Communication with the platform is via a well-defined IPC protocol over a unix socket. Apps cannot access platform internals directly.

4. **The platform owns scheduling.** Apps declare tasks; the platform runs them on schedule. This gives the admin full visibility and control over all background work.

5. **All app UI is fragments.** The platform controls the page shell (chrome, navigation, theming). Apps return HTML fragments loaded via htmx. This ensures consistent UX and prevents apps from breaking platform navigation.

6. **Models declare browser visibility.** Each type in a mental model declares `browserVisible: true|false`. Types marked `false` are hidden from the object browser but remain queryable via SPARQL and linkable via edges. This keeps the object browser clean of internal plumbing types.

---

## 2. App vs Mental Model

| Concern | Mental Model | App |
|---------|-------------|-----|
| **What it is** | Data schema: OWL classes, SHACL shapes, ViewSpecs, seed data | Interactive feature: UI, backend logic, external API integration |
| **Versioning** | Independent semver (e.g., `rss-feeds v1.2.0`) | Independent semver (e.g., `rss-reader v0.3.0`) |
| **Lifecycle** | Install → upgrade → uninstall | Install → start → stop → upgrade → uninstall |
| **Runs code** | No (declarative RDF artifacts only) | Yes (Python subprocess + HTML/JS/CSS fragments) |
| **Data** | Defines types; does not produce instances | Produces instances typed by model schemas |
| **Dependencies** | Other models (e.g., gist upper ontology) | Models (required + optional) and potentially other apps (future) |
| **Marketplace** | Published to model marketplace | Published to app marketplace |
| **Survives the other's removal** | Yes — data remains valid if app is removed | Yes — app can run without models if they're optional |

### Dependency relationship

```
App: rss-reader v0.3.0
  ├── requires: rss-feeds model >=1.0.0
  ├── requires: web-annotations model >=1.0.0
  └── optional: basic-pkm model >=1.0.0 (enables concept linking)

Model: rss-feeds v1.2.0
  ├── anchors to: gist upper ontology
  ├── uses vocabs: schema.org, dcterms, sioc
  └── no app dependency (models never depend on apps)
```

An app declares model dependencies with semver ranges. At install time, the platform checks that required models are installed and satisfy the version constraint. Missing models block installation with a clear error.

---

## 3. AppManifest Specification

The `manifest.yaml` file is the single source of truth for everything an app declares. The platform reads it at install time and again at each startup.

### Field naming convention

Follows the existing Mental Model ManifestSchema: **camelCase** for all fields. This matches YAML field names directly to Pydantic model fields.

### Complete field reference

```yaml
# ─────────────────────────────────────────────
# IDENTITY
# ─────────────────────────────────────────────

# Unique identifier. Lowercase alphanumeric + hyphens.
# Pattern: ^[a-z][a-z0-9-]*$, length 2-64
# Used in: IRI prefixes, URL paths, named graphs, filesystem paths
appId: "rss-reader"

# Semantic version (X.Y.Z)
version: "0.1.0"

# Human-readable display name (1-200 chars)
name: "RSS Reader"

# Description shown in admin/marketplace (0-2000 chars)
description: "Subscribe to RSS/Atom feeds, read articles in a clean reader interface, and sync annotations from Hypothesis."

# Author information
author:
  name: "SemPKM Contributors"
  url: "https://github.com/sempkm"     # optional

# License identifier (SPDX)
license: "MIT"

# ─────────────────────────────────────────────
# DEPENDENCIES
# ─────────────────────────────────────────────

dependencies:
  # Mental model dependencies (checked at install time)
  models:
    - id: "rss-feeds"
      version: ">=1.0.0"               # semver range
      optional: false                   # default: false
    - id: "web-annotations"
      version: ">=1.0.0"
      optional: false
    - id: "basic-pkm"
      version: ">=1.0.0"
      optional: true                    # app works without it

  # Platform version requirement
  platform: ">=0.8.0"                  # minimum SemPKM version

# ─────────────────────────────────────────────
# PERMISSIONS
# ─────────────────────────────────────────────

permissions:
  # Command API access — which command types the app can execute
  commands:
    - "object.create"
    - "object.patch"
    - "edge.create"
    - "body.set"

  # SPARQL access to urn:sempkm:current
  sparql:
    read: true                          # query the user's graph
    # Apps NEVER get write access to urn:sempkm:current via raw SPARQL.
    # All writes go through the command pipeline.

  # Network access — which external domains the app can reach
  # Enforced by the platform's scoped HTTP client
  network:
    - "*.hypothes.is"                   # Hypothesis API
    - "*"                               # wildcard (RSS feeds can be anywhere)
    # Empty list = no network access

  # Background task scheduling
  backgroundTasks: true                 # default: false

  # Settings storage
  settings: true                        # default: false

# ─────────────────────────────────────────────
# BACKEND
# ─────────────────────────────────────────────

backend:
  # Python entrypoint — module path to the App class
  # Resolved relative to the app's root directory
  entrypoint: "backend.app:RSSReaderApp"

  # Additional Python dependencies (installed in app's venv)
  requirements: "requirements.txt"      # path relative to app root

# ─────────────────────────────────────────────
# SCHEDULED TASKS
# ─────────────────────────────────────────────

# Tasks the platform scheduler will invoke on the app subprocess.
# The app must expose handlers for each task ID.
tasks:
  - id: "poll-feeds"
    description: "Check subscribed feeds for new articles"
    interval: "5m"                      # default interval (ISO 8601 duration or shorthand)
    # Shorthand: "30s", "5m", "1h", "6h", "12h", "1d"
    # ISO 8601: "PT5M", "PT1H", "PT12H"
    configurable: true                  # user can adjust interval in settings
    retryPolicy:                        # optional, defaults shown
      maxRetries: 3
      backoffMultiplier: 2              # exponential: 1s, 2s, 4s
      maxBackoff: "5m"

  - id: "sync-hypothesis"
    description: "Sync annotations from Hypothesis"
    interval: "15m"
    configurable: true
    retryPolicy:
      maxRetries: 3

# ─────────────────────────────────────────────
# FRONTEND
# ─────────────────────────────────────────────

frontend:
  # Static assets copied to /app-static/{appId}/ at install time
  # Served directly by nginx (no proxy to app subprocess)
  staticDir: "frontend/static"          # path relative to app root

  # CSS files to include when app UI is active
  # Paths relative to staticDir
  css:
    - "css/reader.css"

  # JS files to include when app UI is active
  # Loaded with defer attribute
  js:
    - "js/reader.js"

# ─────────────────────────────────────────────
# UI INTEGRATION
# ─────────────────────────────────────────────

ui:
  # ── Level 1: Standalone pages ──
  # Full-page app experiences accessible via sidebar navigation.
  # Platform renders the shell; app provides the content fragment.
  pages:
    - id: "reader"
      path: "/"                         # URL: /app/rss-reader/
      label: "RSS Reader"
      icon: "rss"                       # Lucide icon name
      nav: "apps"                       # sidebar section: "apps" (default)
      fragment: "/_fragments/main"      # htmx-loaded content fragment

    - id: "settings"
      path: "/settings"                 # URL: /app/rss-reader/settings
      label: "Reader Settings"
      icon: "settings"
      nav: null                         # not shown in sidebar (accessed from within app)
      fragment: "/_fragments/settings"

  # ── Level 2: Workspace contributions ──
  contributions:
    # Right pane sections — shown alongside Relations, Lint, etc.
    rightPane:
      - id: "related-articles"
        label: "Related Articles"
        icon: "file-text"
        fragment: "/_fragments/pane/related-articles"   # receives ?iri= param
        context: "object"               # "object" | "view" | "always"
        targetTypes: ["*"]              # ["*"] = all types, or list specific type IRIs
        priority: 60                    # ordering: relations=10, lint=50

    # View contributions — appear in Views nav section as tabs
    views:
      - id: "unread-articles"
        label: "Unread Articles"
        icon: "inbox"
        fragment: "/_fragments/views/unread"
      - id: "starred"
        label: "Starred Articles"
        icon: "star"
        fragment: "/_fragments/views/starred"
      - id: "highlights"
        label: "Highlights"
        icon: "highlighter"
        fragment: "/_fragments/views/highlights"

    # Command palette entries — registered with ninja-keys
    commandPalette:
      - id: "subscribe-feed"
        label: "Subscribe to Feed..."
        keywords: ["rss", "feed", "subscribe", "add"]
        actionType: "dialog"            # "dialog" | "post" | "navigate"
        fragment: "/_fragments/dialogs/subscribe"
      - id: "mark-all-read"
        label: "Mark All as Read"
        keywords: ["read", "rss", "clear"]
        actionType: "post"
        endpoint: "/api/mark-all-read"
      - id: "open-reader"
        label: "Open RSS Reader"
        keywords: ["rss", "reader", "feeds"]
        actionType: "navigate"
        path: "/"                       # resolves to /app/rss-reader/

  # ── Level 3: Object renderer overrides ──
  # Replace the default SHACL form for specific types.
  # Per-mode: omitted modes fall back to the default SHACL form.
  objectRenderers:
    - type: "rss:Article"               # full IRI resolved via model prefixes
      modes:
        read: "/_fragments/renderers/article-read"      # receives ?iri= param
        # edit: omitted — uses default SHACL form
    - type: "oa:Annotation"
      modes:
        read: "/_fragments/renderers/annotation-read"

# ─────────────────────────────────────────────
# APP SETTINGS
# ─────────────────────────────────────────────

# Settings the app contributes to the platform settings UI.
# Stored in the app's state graph (urn:sempkm:app:{appId}:state).
# Accessed via ctx.get_setting() / ctx.set_setting() in the SDK.
settings:
  - key: "hypothesisApiToken"
    label: "Hypothesis API Token"
    description: "Bearer token from https://hypothes.is/account/developer"
    inputType: "password"               # "text" | "password" | "toggle" | "select" | "number"
    default: ""

  - key: "defaultPollInterval"
    label: "Default Poll Interval"
    description: "How often to check feeds for updates"
    inputType: "select"
    options: ["5m", "15m", "30m", "1h", "2h", "6h"]
    default: "15m"

  - key: "fetchFullContent"
    label: "Fetch Full Article Content"
    description: "Use reader mode to extract full article text when feeds provide only summaries"
    inputType: "toggle"
    default: true

  - key: "maxArticleAge"
    label: "Maximum Article Age"
    description: "Automatically skip articles older than this when first subscribing to a feed"
    inputType: "select"
    options: ["7d", "30d", "90d", "365d", "unlimited"]
    default: "30d"
```

### Field resolution and validation rules

| Field | Validation | Notes |
|-------|-----------|-------|
| `appId` | `^[a-z][a-z0-9-]*$`, len 2-64 | Same pattern as `modelId` |
| `version` | `^\d+\.\d+\.\d+$` | Strict semver |
| `dependencies.models[].version` | Valid semver range | Parsed by `packaging.specifiers.SpecifierSet` |
| `dependencies.platform` | Valid semver range | Checked against running platform version |
| `permissions.commands[]` | Must be registered command types | Validated against `HANDLER_REGISTRY` |
| `permissions.network[]` | Glob patterns | `*` = any, `*.example.com` = subdomain match |
| `tasks[].interval` | Duration shorthand or ISO 8601 | Floor: 30s, ceiling: 24h |
| `tasks[].retryPolicy.maxRetries` | 0-10 | 0 = no retry |
| `ui.contributions.rightPane[].priority` | 0-100 | Lower = higher in pane |
| `ui.objectRenderers[].type` | Resolvable via installed model prefixes | Validated at install time |
| `settings[].key` | `^[a-zA-Z][a-zA-Z0-9]*$`, len 1-64 | camelCase convention |
| `settings[].inputType` | enum | `text`, `password`, `toggle`, `select`, `number` |
| `frontend.staticDir` | Relative path, must exist | Validated at install time |

---

## 4. Graph & Data Architecture

### Named graph layout

```
urn:sempkm:current                          # ALL user + app-produced data
urn:sempkm:event:{uuid}                     # event log (all sources, including app writes)
urn:sempkm:inferred                         # OWL/SHACL derived facts
urn:sempkm:models                           # model registry

urn:sempkm:model:{modelId}:ontology         # shared model schema (read-only after install)
urn:sempkm:model:{modelId}:shapes           #   "
urn:sempkm:model:{modelId}:views            #   "
urn:sempkm:model:{modelId}:rules            #   "

urn:sempkm:app:{appId}:state                # app operational state (direct CRUD, NOT event-sourced)
```

### App data in `urn:sempkm:current`

Apps produce data into `current` through the standard EventStore (including bulk mode). Data is typed by shared model schemas and is first-class — browsable, queryable, linkable.

### IRI minting convention

Apps mint IRIs with a predictable prefix for traceability and cleanup:

```
urn:sempkm:app:{appId}:{typeLocalName}:{uuid}
```

Examples:
```
urn:sempkm:app:rss-reader:subscription:550e8400-e29b-41d4-a716-446655440000
urn:sempkm:app:rss-reader:article:661f9500-a3b2-4c1d-8e7f-123456789abc
urn:sempkm:app:rss-reader:activity-read:772a0611-b4c3-5d2e-9f80-234567890def
```

The platform enforces this prefix in the SDK — apps cannot mint arbitrary IRIs.

### App operational state graph

`urn:sempkm:app:{appId}:state` stores app-internal bookkeeping:

- Sync cursors (e.g., "last synced Hypothesis annotation ID")
- Per-feed polling metadata (ETag, Last-Modified, next poll time)
- Internal configuration not exposed as user settings
- Cache data

This graph is:
- **Direct CRUD** — not event-sourced (no undo, no audit trail)
- **Fully owned** by the app — platform does not query it
- **Cleaned up** on any uninstall option (always removed)

### Cross-linking

When a user creates an edge from a Concept (user data) to an Article (app data), both IRIs live in `urn:sempkm:current`. The edge triple also lives in `current`. This is a normal edge — no cross-graph complexity.

### Cleanup on uninstall

```sparql
-- "Remove app + data" option:
DELETE WHERE {
  GRAPH <urn:sempkm:current> {
    ?s ?p ?o
    FILTER(STRSTARTS(STR(?s), "urn:sempkm:app:rss-reader:"))
  }
};
-- Also removes edges pointing TO app-created IRIs:
DELETE WHERE {
  GRAPH <urn:sempkm:current> {
    ?s ?p ?o
    FILTER(STRSTARTS(STR(?o), "urn:sempkm:app:rss-reader:"))
  }
};
-- Always remove operational state:
CLEAR GRAPH <urn:sempkm:app:rss-reader:state>
```

---

## 5. Process Architecture & Sandboxing

### Subprocess model

Each app runs as a separate Python process with its own virtual environment:

```
┌─────────────────────────────────────────────────┐
│ Platform Process (FastAPI, PID 1)                │
│                                                  │
│  AppManager                                      │
│  ├── AppScheduler (triggers tasks via HTTP)      │
│  ├── AppProxy (routes /app/{id}/* to socket)     │
│  ├── AppMonitor (health checks, metrics, logs)   │
│  └── AppRegistry (manifest cache, permissions)   │
│                                                  │
│  EventStore, TriplestoreClient, AuthService ...  │
└──────────┬──────────────┬────────────────────────┘
           │ HTTP/UDS     │ HTTP/UDS
    ┌──────▼──────┐ ┌─────▼───────┐
    │ rss-reader  │ │ future-app  │
    │ venv + proc │ │ venv + proc │
    │ PID 4821    │ │ PID 4822    │
    │ socket:     │ │ socket:     │
    │ /tmp/sempkm │ │ /tmp/sempkm │
    │ -app-rss-   │ │ -app-future │
    │ reader.sock │ │ -app.sock   │
    └─────────────┘ └─────────────┘
```

### IPC via unix domain socket (HTTP)

Each app subprocess runs a small HTTP server on a unix domain socket:

```
/tmp/sempkm-app-{appId}.sock
```

The platform proxies all requests matching `/app/{appId}/*` to the corresponding socket. The app sees standard HTTP requests and returns HTML fragments or JSON.

**Why HTTP over unix socket:**
- Standard HTTP tooling works (`curl --unix-socket /tmp/... http://localhost/...`)
- Apps use FastAPI (same framework as platform) — low learning curve
- Debugging is straightforward
- Platform can add auth headers, rate limiting, timeouts at the proxy layer

### Virtual environment isolation

At install time, the platform creates a dedicated venv:

```
/app/data/apps/{appId}/venv/          # Python virtual environment
/app/data/apps/{appId}/venv/bin/python
```

The venv gets:
1. App's declared dependencies from `requirements.txt`
2. The `sempkm-app-sdk` package (injected by platform)
3. Nothing else — no access to platform's packages

### Process startup

```bash
/app/data/apps/{appId}/venv/bin/python \
    -m sempkm_app_sdk.runner \
    --app-dir /apps/{appId} \
    --socket /tmp/sempkm-app-{appId}.sock \
    --platform-url http://localhost:8000 \
    --app-token {per-app-scoped-jwt}
```

The `--platform-url` and `--app-token` allow the SDK to call back into the platform's API (scoped by permissions). The token is generated at startup, short-lived, and rotated periodically.

### Process supervision

| Event | Behavior |
|-------|----------|
| App process exits unexpectedly | Restart up to 3 times with exponential backoff (1s, 2s, 4s) |
| 3 consecutive failures | Mark app as `error`, stop restarting, surface in admin |
| Platform shutdown | Send SIGTERM to all app processes, wait 10s, SIGKILL |
| App install | Create venv, install deps, start process |
| App uninstall | Send SIGTERM, wait for shutdown, remove venv + state |
| App upgrade | Stop old process, update venv, start new process |

---

## 6. App SDK

### Overview

The `sempkm-app-sdk` is a small Python package that provides the developer-facing API. It handles IPC with the platform, permission enforcement, and common patterns.

### App class

```python
from sempkm_app_sdk import App, AppContext

app = App("rss-reader")

@app.on_install
async def install(ctx: AppContext):
    """Called once at install time. Initialize state graph, create defaults."""
    await ctx.state.set("hypothesis_sync_cursor", "")
    await ctx.state.set("last_full_sync", "")

@app.on_startup
async def startup(ctx: AppContext):
    """Called each time the app process starts."""
    pass

@app.on_shutdown
async def shutdown(ctx: AppContext):
    """Called before the app process stops."""
    pass

@app.on_uninstall
async def uninstall(ctx: AppContext):
    """Called before uninstall. Clean up external resources if needed."""
    pass
```

### AppContext — the scoped API surface

```python
class AppContext:
    """Passed to all app handlers. Enforces permissions at every call."""

    app_id: str

    # ── Data access ──

    commands: CommandClient
    # Execute commands against urn:sempkm:current.
    # Scoped: only permitted command types (from manifest) are allowed.
    # IRI minting enforced: all created IRIs use app prefix.
    #
    # Usage:
    #   result = await ctx.commands.execute("object.create", {
    #       "type": "rss:Article",
    #       "properties": {"dcterms:title": "..."}
    #   })
    #
    # Bulk mode:
    #   async with ctx.commands.bulk(summary="Ingested 50 articles") as batch:
    #       for article in articles:
    #           batch.add("object.create", {...})
    #           batch.add("body.set", {...})
    #   # committed atomically on exit

    graph: GraphClient
    # SPARQL query access.
    # Reads: urn:sempkm:current (if sparql.read permitted)
    # Platform auto-injects common prefixes.
    #
    # Usage:
    #   results = await ctx.graph.query("""
    #       SELECT ?article ?title WHERE {
    #           ?article a rss:Article ;
    #                    dcterms:title ?title .
    #       } LIMIT 50
    #   """)

    state: StateClient
    # Direct CRUD on urn:sempkm:app:{appId}:state.
    # Key-value style for simplicity.
    #
    # Usage:
    #   await ctx.state.set("hypothesis_sync_cursor", "2026-03-16T10:00:00Z")
    #   cursor = await ctx.state.get("hypothesis_sync_cursor")
    #
    # Also supports raw SPARQL on the state graph:
    #   await ctx.state.sparql_update("INSERT DATA { ... }")
    #   results = await ctx.state.sparql_query("SELECT ...")

    http: HttpClient
    # Scoped httpx.AsyncClient that enforces network permissions.
    # Requests to non-permitted domains raise PermissionDenied.
    #
    # Usage:
    #   response = await ctx.http.get("https://feeds.arstechnica.com/arstechnica/index")
    #   response = await ctx.http.get("https://hypothes.is/api/search", headers={...})

    settings: SettingsClient
    # Read/write app settings (declared in manifest).
    #
    # Usage:
    #   token = await ctx.settings.get("hypothesisApiToken")
    #   await ctx.settings.set("defaultPollInterval", "30m")

    # ── Utilities ──

    def render_template(self, template_name: str, context: dict) -> str:
        """Render a Jinja2 template from the app's frontend/templates/ directory."""

    @property
    def logger(self) -> logging.Logger:
        """Namespaced logger: sempkm.app.{appId}"""
```

### Task handlers

```python
@app.task("poll-feeds")
async def poll_feeds(ctx: AppContext):
    """Called by the platform scheduler at the configured interval."""
    feeds = await ctx.graph.query("""
        SELECT ?sub ?feedUrl ?etag ?lastModified WHERE {
            ?sub a rss:FeedSubscription ;
                 rss:feedUrl ?feedUrl .
            OPTIONAL { ?sub rss:etag ?etag }
            OPTIONAL { ?sub rss:lastModified ?lastModified }
        }
    """)

    for feed in feeds:
        try:
            new_articles = await fetch_and_parse_feed(ctx, feed)
            if new_articles:
                async with ctx.commands.bulk(
                    summary=f"Ingested {len(new_articles)} articles from {feed.feedUrl}"
                ) as batch:
                    for article in new_articles:
                        batch.add("object.create", {
                            "type": "rss:Article",
                            "properties": {
                                "dcterms:title": article.title,
                                "dcterms:creator": article.author,
                                "dcterms:issued": article.published,
                                "schema:url": article.link,
                                "dcterms:source": feed.sub,
                            }
                        })
                        batch.add("body.set", {
                            "iri": "$last",  # refers to IRI created by previous command
                            "body": article.content_markdown,
                            "format": "text/markdown",
                        })
        except Exception as e:
            ctx.logger.error(f"Failed to poll {feed.feedUrl}: {e}")
            # Platform handles retry based on retryPolicy in manifest
            raise  # re-raise so platform can track the failure
```

### Route handlers (for HTTP fragment serving)

```python
@app.route("/_fragments/main")
async def main_fragment(request: Request, ctx: AppContext):
    feeds = await ctx.graph.query("SELECT ...")
    unread_count = await ctx.graph.query("SELECT (COUNT(...) as ?c) ...")
    return ctx.render_template("reader.html", {
        "feeds": feeds,
        "unread_count": unread_count,
    })

@app.route("/_fragments/renderers/article-read")
async def article_renderer(request: Request, ctx: AppContext):
    iri = request.query_params["iri"]
    article = await ctx.graph.query(f"DESCRIBE <{iri}>")
    return ctx.render_template("article_read.html", {"article": article})

@app.route("/api/star/{article_id}")
async def star_article(request: Request, ctx: AppContext):
    article_iri = f"urn:sempkm:app:rss-reader:article:{request.path_params['article_id']}"
    await ctx.commands.execute("object.patch", {
        "iri": article_iri,
        "set": {"rss:starred": True},
    })
    return HTMLResponse('<i data-lucide="star" class="starred"></i>')
```

---

## 7. Frontend Integration — Three Levels

### Level 1: Standalone pages

The app's primary interface. Platform renders the shell; app provides the content fragment via htmx.

**Flow:**

```
1. User clicks "RSS Reader" in sidebar [Apps] section
2. Browser navigates to /app/rss-reader/
3. Platform app_shell route renders base template with sidebar + header
4. Template contains: <div hx-get="/app/rss-reader/_fragments/main" hx-trigger="load">
5. Platform proxies to app subprocess unix socket
6. App returns HTML fragment (reader UI)
7. htmx swaps fragment into content area
```

**Platform template (`app_shell.html`):**

```html
{% extends "base.html" %}

{% block head_extra %}
  {% for css in app_css %}
  <link rel="stylesheet" href="/app-static/{{ app_id }}/{{ css }}">
  {% endfor %}
{% endblock %}

{% block content %}
<div id="app-content"
     class="app-container"
     data-app-id="{{ app_id }}"
     hx-get="{{ fragment_url }}"
     hx-trigger="load"
     hx-swap="innerHTML"
     hx-headers='{"X-SemPKM-App": "{{ app_id }}"}'>
  <div class="app-loading">Loading {{ app_name }}...</div>
</div>
{% endblock %}

{% block scripts_extra %}
  {% for js in app_js %}
  <script src="/app-static/{{ app_id }}/{{ js }}" defer></script>
  {% endfor %}
{% endblock %}
```

**App internal navigation** uses htmx within its fragment — all URLs scoped to `/app/{appId}/`:

```html
<div class="article-item"
     hx-get="/app/rss-reader/_fragments/article/{{ article.id }}"
     hx-target="#reading-pane"
     hx-swap="innerHTML">
  {{ article.title }}
</div>
```

### Level 2: Workspace contributions

Apps inject fragments into the existing workspace without leaving it.

#### Right pane sections

Platform queries running apps for `rightPane` contributions matching the current object's type:

```python
def get_right_pane_sections(object_iri: str, object_types: list[str]) -> list[PaneSection]:
    sections = [
        PaneSection("relations", "/browser/relations", priority=10),
        PaneSection("lint", "/browser/lint", priority=50),
    ]
    for app in app_manager.running_apps():
        for contrib in app.manifest.ui.contributions.get("rightPane", []):
            if contrib.matches_types(object_types):
                sections.append(PaneSection(
                    id=f"app-{app.id}-{contrib.id}",
                    label=contrib.label,
                    icon=contrib.icon,
                    url=f"/app/{app.id}{contrib.fragment}?iri={object_iri}",
                    priority=contrib.priority,
                ))
    return sorted(sections, key=lambda s: s.priority)
```

Rendered as collapsible htmx-loaded blocks in the right pane:

```html
{% for section in sections %}
<details class="right-pane-section" {% if section.priority < 30 %}open{% endif %}>
  <summary>
    <i data-lucide="{{ section.icon }}"></i> {{ section.label }}
  </summary>
  <div hx-get="{{ section.url }}"
       hx-trigger="toggle from:closest details"
       hx-swap="innerHTML">
  </div>
</details>
{% endfor %}
```

#### View contributions

App-contributed views appear in the [Views] nav section. When clicked, the platform loads the app's fragment into the editor area as a tab:

```
Nav Tree:
  [Views]
    Projects Table           ← model ViewSpec (existing)
    Unread Articles          ← app view (rss-reader)
    Starred Articles         ← app view (rss-reader)
```

Platform renders a thin shell tab that htmx-loads the app's fragment:

```python
@router.get("/browser/app-view/{app_id}/{view_id}")
async def app_view(app_id: str, view_id: str):
    app = app_manager.get(app_id)
    contrib = app.manifest.get_view(view_id)
    return templates.TemplateResponse("app_view_tab.html", {
        "fragment_url": f"/app/{app_id}{contrib.fragment}",
        "label": contrib.label,
        "icon": contrib.icon,
        "app_id": app_id,
    })
```

#### Command palette entries

Platform registers app commands with ninja-keys at workspace load:

```javascript
// Platform fetches app commands and injects into ninja-keys
const appCommands = await fetch('/api/apps/commands').then(r => r.json());

for (const cmd of appCommands) {
  ninjaKeys.data.push({
    id: `${cmd.appId}:${cmd.id}`,
    title: cmd.label,
    keywords: cmd.keywords.join(' '),
    section: cmd.appName,
    handler: () => {
      switch (cmd.actionType) {
        case 'dialog':
          htmx.ajax('GET', `/app/${cmd.appId}${cmd.fragment}`, {target: '#modal-container'});
          break;
        case 'post':
          htmx.ajax('POST', `/app/${cmd.appId}${cmd.endpoint}`);
          break;
        case 'navigate':
          window.location.href = `/app/${cmd.appId}${cmd.path}`;
          break;
      }
    }
  });
}
```

### Level 3: Object renderer overrides

Apps replace the default SHACL form for specific types with a custom reading/editing experience.

**Resolution flow:**

```
1. User opens an rss:Article (from object browser or any link)
2. Platform's object tab route checks AppRegistry for renderer overrides
3. AppRegistry.get_renderer("rss:Article", "read") returns rss-reader's declaration
4. Platform renders object_tab_app.html instead of default object_tab.html
5. Tab loads app fragment via htmx: /app/rss-reader/_fragments/renderers/article-read?iri=...
6. App returns rich article reading view
```

**Renderer conflict resolution** (multiple apps register for the same type):

1. Check user preference in settings (`renderer:{typeIri}:{mode}` → `appId`)
2. If no preference, most recently installed app wins
3. Admin can view and change renderer assignments

**Object tab with app renderer:**

```html
<!-- object_tab_app.html -->
<div class="object-tab" data-iri="{{ iri }}">
  <div class="object-toolbar">
    <span class="object-type-badge">
      <i data-lucide="{{ type_icon }}"></i> {{ type_label }}
    </span>

    {% if has_custom_edit %}
    <button class="mode-toggle" onclick="toggleObjectMode(this)">
      <i data-lucide="pencil"></i>
    </button>
    {% else %}
    <button class="mode-toggle" onclick="toggleObjectMode(this)"
            title="Edit with standard form">
      <i data-lucide="pencil"></i>
    </button>
    {% endif %}

    <a href="/app/{{ app_id }}/" class="open-in-app-btn"
       title="Open in {{ app_name }}">
      <i data-lucide="external-link"></i>
    </a>
  </div>

  <!-- Read face: app-rendered -->
  <div class="object-face object-face-read"
       hx-get="{{ read_fragment_url }}"
       hx-trigger="load"
       hx-swap="innerHTML">
  </div>

  <!-- Edit face: default SHACL form unless app overrides edit too -->
  <div class="object-face object-face-edit face-hidden"
       hx-get="{{ edit_fragment_url }}"
       hx-trigger="revealed"
       hx-swap="innerHTML">
  </div>
</div>
```

---

## 8. Scheduler & Background Tasks

### Platform-owned scheduler

The platform's `AppScheduler` runs in the main process and triggers app tasks via HTTP calls to the app subprocess.

```
AppScheduler (platform)
  │
  ├── Every 60s: check which tasks are due
  │
  ├── Task due: POST /app/{appId}/_tasks/{taskId}
  │   └── Proxied to app subprocess unix socket
  │   └── App handles the task and returns 200/500
  │
  ├── Track: start time, duration, success/failure, error
  │
  └── Enforce: concurrency guard, retry policy, backoff
```

### Concurrency guard

The scheduler will not invoke a task if the previous invocation is still running. If a task consistently overruns its interval, the scheduler logs a warning and skips the invocation.

### User-adjustable intervals

When `configurable: true` is set on a task, the admin can adjust the interval:

```
Admin > Apps > RSS Reader > Tasks
  poll-feeds:     [5m ▾]   (manifest default: 5m)
  sync-hypothesis: [15m ▾]  (manifest default: 15m)
```

Overridden intervals are stored in SQLite `app_task_config` table.

### Task invocation protocol

```
Platform → POST /app/rss-reader/_tasks/poll-feeds
Headers:
  X-SemPKM-Task-Id: poll-feeds
  X-SemPKM-Task-Run: run-uuid-here
  X-SemPKM-App-Token: {jwt}
  Content-Type: application/json
Body: {}  (or task-specific parameters in future)

App → 200 OK
  {"status": "success", "summary": "Ingested 12 new articles"}

App → 500 Internal Server Error
  {"status": "error", "message": "Feed https://... returned 503"}
```

### Retry policy

Default retry behavior (overridable per-task in manifest):

| Attempt | Delay | Behavior |
|---------|-------|----------|
| 1st retry | 1s × backoffMultiplier^0 = 1s | Immediate-ish retry |
| 2nd retry | 1s × backoffMultiplier^1 = 2s | Short delay |
| 3rd retry | 1s × backoffMultiplier^2 = 4s | Medium delay |
| Max exceeded | — | Log error, wait for next scheduled invocation |

Persistent failures (e.g., 10 consecutive failed runs) trigger an admin notification.

---

## 9. Permissions & Enforcement

### Declaration

Permissions are declared in the manifest and approved by the user at install time.

### Install-time approval dialog

```
Install RSS Reader v0.1.0?

This app requests the following permissions:

  Commands:    object.create, object.patch, edge.create, body.set
  SPARQL:      Read access to your knowledge graph
  Network:     Access to any external URL (for RSS feeds)
               Access to *.hypothes.is (for annotation sync)
  Background:  Run scheduled tasks (poll-feeds, sync-hypothesis)
  Settings:    Store configuration (API tokens, preferences)

  [Cancel]  [Install]
```

### Enforcement layers

| Layer | What it enforces | How |
|-------|-----------------|-----|
| **CommandClient** | Only permitted command types | SDK checks `manifest.permissions.commands` before forwarding to platform API |
| **GraphClient** | Only `urn:sempkm:current` reads if `sparql.read` is true | Platform API validates `X-SemPKM-App-Token` scope |
| **HttpClient** | Only permitted network domains | SDK wraps httpx.AsyncClient, checks URL against `permissions.network` glob patterns |
| **IRI minting** | App prefix enforced on all created IRIs | CommandClient rejects IRIs not matching `urn:sempkm:app:{appId}:` |
| **State graph** | App can only access its own state graph | StateClient scoped to `urn:sempkm:app:{appId}:state` |
| **Task invocation** | Only platform can trigger tasks | App HTTP server rejects `/_tasks/*` requests without valid `X-SemPKM-Task-Run` header |

### App-scoped JWT token

Each running app receives a short-lived JWT that encodes its permissions:

```json
{
  "sub": "app:rss-reader",
  "permissions": {
    "commands": ["object.create", "object.patch", "edge.create", "body.set"],
    "sparql_read": true,
    "network": ["*"],
    "background_tasks": true
  },
  "iat": 1710590400,
  "exp": 1710594000
}
```

The platform API validates this token on every callback from the app subprocess. Tokens are rotated every hour; the SDK handles renewal transparently.

---

## 10. Lifecycle Management

### Install

```
1. Validate manifest.yaml
   ├── Check appId uniqueness
   ├── Parse and validate all fields
   └── Resolve type IRIs in objectRenderers against installed model prefixes

2. Check dependencies
   ├── Required models installed with satisfying versions?
   ├── Platform version satisfies constraint?
   └── Block with clear error if not

3. Show permission approval dialog to user

4. Create virtual environment
   └── python -m venv /app/data/apps/{appId}/venv
   └── pip install -r requirements.txt
   └── pip install sempkm-app-sdk

5. Copy static assets
   └── cp -r {appDir}/frontend/static/* /app/data/apps-static/{appId}/

6. Create app state graph
   └── Initialize urn:sempkm:app:{appId}:state

7. Register in SQLite
   └── INSERT INTO app_instances (app_id, status, installed_at, manifest_hash)

8. Start subprocess
   └── Launch with venv Python, pass socket path + platform URL + token

9. Call on_install hook
   └── POST /app/{appId}/_lifecycle/install

10. Register scheduled tasks in AppScheduler

11. Register UI contributions (views, right pane, renderers, commands)

12. Invalidate caches (ViewSpec, nav tree, command palette)
```

### Startup (platform boot or app restart)

```
1. For each installed app:
   ├── Read manifest.yaml
   ├── Check dependencies still satisfied
   ├── Start subprocess
   ├── Wait for health check: GET /app/{appId}/_health → 200
   ├── Call on_startup hook
   ├── Register scheduled tasks
   └── Mark status: running
```

### Shutdown

```
1. Call on_shutdown hook: POST /app/{appId}/_lifecycle/shutdown
2. Wait up to 10s for graceful completion
3. Send SIGTERM
4. Wait up to 5s
5. Send SIGKILL if still alive
6. Mark status: stopped
```

### Upgrade

```
1. Stop running instance (shutdown flow)
2. Validate new manifest
3. Check dependency compatibility
4. Update venv: pip install -r new-requirements.txt
5. Copy new static assets
6. Start new instance
7. Call on_startup (not on_install — this is an upgrade)
8. Re-register UI contributions
```

### Uninstall

```
User chooses one of three options:

Option A: "Remove app only"
  1. Shutdown flow
  2. Remove static assets
  3. Remove venv
  4. Clear urn:sempkm:app:{appId}:state
  5. Remove from app_instances table
  6. De-register UI contributions
  7. Data + models remain

Option B: "Remove app + data"
  1. Everything in Option A
  2. Call on_uninstall hook (cleanup external resources)
  3. DELETE WHERE { ?s ?p ?o FILTER(STRSTARTS(STR(?s), "urn:sempkm:app:{appId}:")) }
     on urn:sempkm:current
  4. DELETE WHERE { ?s ?p ?o FILTER(STRSTARTS(STR(?o), "urn:sempkm:app:{appId}:")) }
     on urn:sempkm:current (dangling edges)

Option C: "Remove app + data + models"
  1. Everything in Option B
  2. For each model dependency:
     └── If no other installed app depends on it:
         └── ModelService.remove(modelId)
     └── If other apps depend on it:
         └── Skip with note: "rss-feeds model kept (used by podcast-player)"
```

---

## 11. Admin Portal — App Monitoring

### App list view

```
Admin > Applications
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

RSS Reader  v0.1.0                        [Running ●]
  PID 4821 · Uptime 2h 15m · Memory 45MB
  Models: rss-feeds v1.0.0, web-annotations v1.0.0
  Data: 1,234 objects in urn:sempkm:current

  [View Details]  [Restart]  [Stop]  [Uninstall ▾]
```

### App detail view

```
Admin > Applications > RSS Reader
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Status:     Running (PID 4821)
Version:    0.1.0
Uptime:     2h 15m 32s
Memory:     45.2 MB
Socket:     /tmp/sempkm-app-rss-reader.sock

── Scheduled Tasks ──────────────────────────────

┌──────────────────┬──────────┬────────────┬──────────┬─────────┬─────────┐
│ Task             │ Interval │ Last Run   │ Duration │ Status  │ Next    │
├──────────────────┼──────────┼────────────┼──────────┼─────────┼─────────┤
│ poll-feeds       │ 5m  [▾]  │ 2m ago     │ 1.2s     │ success │ in 3m   │
│ sync-hypothesis  │ 15m [▾]  │ 8m ago     │ 0.4s     │ success │ in 7m   │
└──────────────────┴──────────┴────────────┴──────────┴─────────┴─────────┘

  [Trigger Now]  [Pause All]

── Task History (last 24h) ──────────────────────

  poll-feeds:       288 runs, 285 success, 3 errors (last error: 6h ago)
  sync-hypothesis:  96 runs, 96 success, 0 errors

── Permissions ──────────────────────────────────

  Commands:    object.create, object.patch, edge.create, body.set
  SPARQL:      Read
  Network:     * (any), *.hypothes.is
  Background:  Yes
  Settings:    Yes

── Data ─────────────────────────────────────────

  Objects created: 1,234 (prefix: urn:sempkm:app:rss-reader:)
  State graph:     42 triples (urn:sempkm:app:rss-reader:state)

── UI Contributions ─────────────────────────────

  Pages:     RSS Reader (/)
  Views:     Unread Articles, Starred Articles, Highlights
  Pane:      Related Articles (right pane, priority 60)
  Commands:  Subscribe to Feed..., Mark All as Read, Open RSS Reader
  Renderers: rss:Article (read), oa:Annotation (read)

── Logs (last 50 lines) ─────────────────────────

  [2026-03-16 10:14:32] INFO  poll-feeds: Checking 12 feeds
  [2026-03-16 10:14:33] INFO  poll-feeds: Ingested 3 new articles from Ars Technica
  [2026-03-16 10:14:33] INFO  poll-feeds: No new articles from Hacker News
  ...

  [View Full Logs]

── Renderers ────────────────────────────────────

  rss:Article (read)    → this app     [Default ▾]
  oa:Annotation (read)  → this app     [Default ▾]

── Actions ──────────────────────────────────────

  [Restart]  [Stop]  [Uninstall ▾]
```

### SQLite tables for app monitoring

```sql
-- App instance registry
CREATE TABLE app_instances (
    app_id TEXT PRIMARY KEY,
    version TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'stopped',   -- running | stopped | error | installing
    pid INTEGER,
    socket_path TEXT,
    started_at TIMESTAMP,
    installed_at TIMESTAMP NOT NULL,
    manifest_hash TEXT NOT NULL,              -- detect manifest changes
    error_message TEXT,
    restart_count INTEGER DEFAULT 0
);

-- Task execution history
CREATE TABLE app_task_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    app_id TEXT NOT NULL REFERENCES app_instances(app_id),
    task_id TEXT NOT NULL,
    run_id TEXT NOT NULL,                     -- UUID for this run
    started_at TIMESTAMP NOT NULL,
    finished_at TIMESTAMP,
    status TEXT NOT NULL DEFAULT 'running',   -- running | success | error
    duration_ms INTEGER,
    error_message TEXT,
    summary TEXT                              -- app-provided summary on success
);

-- Task interval overrides (user-adjusted)
CREATE TABLE app_task_config (
    app_id TEXT NOT NULL REFERENCES app_instances(app_id),
    task_id TEXT NOT NULL,
    interval_override TEXT,                   -- null = use manifest default
    paused BOOLEAN DEFAULT FALSE,
    PRIMARY KEY (app_id, task_id)
);

-- Renderer preference overrides
CREATE TABLE app_renderer_prefs (
    type_iri TEXT NOT NULL,
    mode TEXT NOT NULL,                       -- 'read' | 'edit'
    app_id TEXT NOT NULL REFERENCES app_instances(app_id),
    PRIMARY KEY (type_iri, mode)
);

-- Approved permissions snapshot (from install time)
CREATE TABLE app_permissions (
    app_id TEXT PRIMARY KEY REFERENCES app_instances(app_id),
    permissions_json TEXT NOT NULL,           -- JSON of approved permissions
    approved_at TIMESTAMP NOT NULL,
    approved_by TEXT NOT NULL                 -- user_id who approved
);
```

---

## 12. Bulk EventStore Extension

### Motivation

Feed polling can produce 50+ articles per update. At 3 commands per article (object.create + body.set + edge.create), that's 150 operations. The standard EventStore records per-operation metadata in the event graph, adding significant overhead for bulk ingestion.

### API

```python
class EventStore:
    async def commit(
        self,
        operations: list[Operation],
        *,
        actor: str | None = None,
    ) -> CommitResult:
        """Standard commit. Per-operation metadata in event graph. Individually undoable."""
        ...

    async def commit_bulk(
        self,
        operations: list[Operation],
        *,
        summary: str,
        source: str | None = None,       # e.g., "app:rss-reader:poll-feeds"
        actor: str | None = None,
    ) -> BulkCommitResult:
        """Bulk commit. Summary metadata only. All-or-nothing undo."""
        ...
```

### Event graph comparison

**Standard event** (current behavior):

```turtle
<urn:sempkm:event:{uuid}>
    a sempkm:Event ;
    sempkm:committedAt "2026-03-16T10:00:00Z"^^xsd:dateTime ;
    sempkm:actor <urn:sempkm:user:current> ;
    sempkm:operation [
        sempkm:type "object.create" ;
        sempkm:affected <urn:article:1> ;
        sempkm:description "Created Article: Understanding RDF"
    ] ;
    # ... N more operation nodes (5 metadata triples each)
    .
```

**Bulk event** (new):

```turtle
<urn:sempkm:event:{uuid}>
    a sempkm:BulkEvent ;
    sempkm:committedAt "2026-03-16T10:00:00Z"^^xsd:dateTime ;
    sempkm:actor <urn:sempkm:app:rss-reader> ;
    sempkm:summary "Ingested 50 articles from Ars Technica" ;
    sempkm:source "app:rss-reader:poll-feeds" ;
    sempkm:operationCount 150 ;
    sempkm:affectedCount 50 ;
    .
```

Both event types store the raw data triples (inserts/deletes) — that's how undo and replay work. The difference is metadata overhead: ~10 triples for bulk vs. ~5N triples for standard.

### SDK surface

```python
# Standard: fine-grained (individual undo)
await ctx.commands.execute("object.create", {...})

# Bulk: all-or-nothing undo
async with ctx.commands.bulk(summary="Ingested 50 articles from Ars Technica") as batch:
    for article in articles:
        batch.add("object.create", {...})
        batch.add("body.set", {...})
    # Atomic commit on context manager exit
    # If exception raised, nothing is committed
```

### Undo semantics

| Event type | Undo granularity |
|-----------|-----------------|
| Standard | Individual operation reversal |
| Bulk | Entire batch reversed as one unit |

The undo mechanism is the same: replay `materialize_deletes` as inserts and `materialize_inserts` as deletes. The difference is the unit of work.

### Guidance for app developers

| Scenario | Mode | Rationale |
|----------|------|-----------|
| User action (star, mark read, rename) | Standard | Individually undoable |
| Feed poll ingestion (10-100 articles) | Bulk | Performance, all-or-nothing is acceptable |
| Hypothesis sync (batch of annotations) | Bulk | Same rationale |
| User creates a single subscription | Standard | User-initiated, individual undo |

### Batch size limit

Platform enforces a maximum batch size (default: 1000 operations) to prevent memory exhaustion. If an app needs to ingest more, it should split into multiple bulk commits.

---

## 13. Concrete Example: RSS Reader Manifest

```yaml
# ─── Identity ───
appId: "rss-reader"
version: "0.1.0"
name: "RSS Reader"
description: >
  Subscribe to RSS, Atom, and JSON feeds. Read articles in a clean reader
  interface. Sync annotations from Hypothesis. Full-text search across your
  reading history.
author:
  name: "SemPKM Contributors"
  url: "https://github.com/sempkm"
license: "MIT"

# ─── Dependencies ───
dependencies:
  models:
    - id: "rss-feeds"
      version: ">=1.0.0"
    - id: "web-annotations"
      version: ">=1.0.0"
    - id: "basic-pkm"
      version: ">=1.0.0"
      optional: true
  platform: ">=0.8.0"

# ─── Permissions ───
permissions:
  commands:
    - "object.create"
    - "object.patch"
    - "edge.create"
    - "body.set"
  sparql:
    read: true
  network:
    - "*"
  backgroundTasks: true
  settings: true

# ─── Backend ───
backend:
  entrypoint: "backend.app:RSSReaderApp"
  requirements: "requirements.txt"

# ─── Scheduled Tasks ───
tasks:
  - id: "poll-feeds"
    description: "Check subscribed feeds for new articles"
    interval: "5m"
    configurable: true
    retryPolicy:
      maxRetries: 3
      backoffMultiplier: 2
      maxBackoff: "5m"

  - id: "sync-hypothesis"
    description: "Sync annotations from Hypothesis"
    interval: "15m"
    configurable: true
    retryPolicy:
      maxRetries: 3

# ─── Frontend ───
frontend:
  staticDir: "frontend/static"
  css:
    - "css/reader.css"
  js:
    - "js/reader.js"

# ─── UI Integration ───
ui:
  pages:
    - id: "reader"
      path: "/"
      label: "RSS Reader"
      icon: "rss"
      nav: "apps"
      fragment: "/_fragments/main"

  contributions:
    rightPane:
      - id: "related-articles"
        label: "Related Articles"
        icon: "file-text"
        fragment: "/_fragments/pane/related-articles"
        context: "object"
        targetTypes: ["*"]
        priority: 60

    views:
      - id: "unread-articles"
        label: "Unread Articles"
        icon: "inbox"
        fragment: "/_fragments/views/unread"
      - id: "starred"
        label: "Starred Articles"
        icon: "star"
        fragment: "/_fragments/views/starred"
      - id: "highlights"
        label: "Highlights"
        icon: "highlighter"
        fragment: "/_fragments/views/highlights"

    commandPalette:
      - id: "subscribe-feed"
        label: "Subscribe to Feed..."
        keywords: ["rss", "feed", "subscribe", "add"]
        actionType: "dialog"
        fragment: "/_fragments/dialogs/subscribe"
      - id: "mark-all-read"
        label: "Mark All as Read"
        keywords: ["read", "rss", "clear"]
        actionType: "post"
        endpoint: "/api/mark-all-read"
      - id: "open-reader"
        label: "Open RSS Reader"
        keywords: ["rss", "reader", "feeds"]
        actionType: "navigate"
        path: "/"

  objectRenderers:
    - type: "rss:Article"
      modes:
        read: "/_fragments/renderers/article-read"
    - type: "oa:Annotation"
      modes:
        read: "/_fragments/renderers/annotation-read"

# ─── Settings ───
settings:
  - key: "hypothesisApiToken"
    label: "Hypothesis API Token"
    description: "Bearer token from https://hypothes.is/account/developer"
    inputType: "password"
    default: ""
  - key: "defaultPollInterval"
    label: "Default Poll Interval"
    description: "How often to check feeds for updates"
    inputType: "select"
    options: ["5m", "15m", "30m", "1h", "2h", "6h"]
    default: "15m"
  - key: "fetchFullContent"
    label: "Fetch Full Article Content"
    description: "Use reader mode to extract full text when feeds provide summaries only"
    inputType: "toggle"
    default: true
  - key: "maxArticleAge"
    label: "Max Article Age"
    description: "Skip articles older than this when first subscribing"
    inputType: "select"
    options: ["7d", "30d", "90d", "365d", "unlimited"]
    default: "30d"
```

---

## 14. Pydantic Schema

```python
"""
App manifest schema — validates manifest.yaml for SemPKM applications.

Follows the same conventions as the Mental Model ManifestSchema:
- camelCase field names (matching YAML keys)
- Strict validation with regex patterns and length constraints
- Custom validators for cross-field consistency
"""

from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator


# ── Nested models ──

class AppAuthor(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    url: str | None = None


class AppModelDependency(BaseModel):
    id: str = Field(pattern=r"^[a-z][a-z0-9-]*$", min_length=2, max_length=64)
    version: str  # semver range, validated below
    optional: bool = False

    @field_validator("version")
    @classmethod
    def validate_version_range(cls, v: str) -> str:
        from packaging.specifiers import SpecifierSet, InvalidSpecifier
        try:
            SpecifierSet(v)
        except InvalidSpecifier:
            raise ValueError(f"Invalid semver range: {v}")
        return v


class AppDependencies(BaseModel):
    models: list[AppModelDependency] = []
    platform: str = ">=0.1.0"

    @field_validator("platform")
    @classmethod
    def validate_platform_range(cls, v: str) -> str:
        from packaging.specifiers import SpecifierSet, InvalidSpecifier
        try:
            SpecifierSet(v)
        except InvalidSpecifier:
            raise ValueError(f"Invalid platform version range: {v}")
        return v


class AppPermissionsSparql(BaseModel):
    read: bool = False


class AppPermissions(BaseModel):
    commands: list[str] = []
    sparql: AppPermissionsSparql = AppPermissionsSparql()
    network: list[str] = []
    backgroundTasks: bool = False
    settings: bool = False


class AppBackend(BaseModel):
    entrypoint: str = Field(
        min_length=1,
        description="Python module:class path, e.g. 'backend.app:RSSReaderApp'"
    )
    requirements: str = "requirements.txt"


class AppTaskRetryPolicy(BaseModel):
    maxRetries: int = Field(default=3, ge=0, le=10)
    backoffMultiplier: int = Field(default=2, ge=1, le=10)
    maxBackoff: str = "5m"


class AppTask(BaseModel):
    id: str = Field(pattern=r"^[a-z][a-z0-9-]*$", min_length=2, max_length=64)
    description: str = Field(min_length=1, max_length=500)
    interval: str  # validated below
    configurable: bool = False
    retryPolicy: AppTaskRetryPolicy = AppTaskRetryPolicy()

    @field_validator("interval")
    @classmethod
    def validate_interval(cls, v: str) -> str:
        """Accept shorthand (30s, 5m, 1h, 6h, 1d) or ISO 8601 duration."""
        shorthand = re.match(r"^(\d+)(s|m|h|d)$", v)
        if shorthand:
            amount, unit = int(shorthand.group(1)), shorthand.group(2)
            seconds = amount * {"s": 1, "m": 60, "h": 3600, "d": 86400}[unit]
            if seconds < 30:
                raise ValueError("Minimum interval is 30 seconds")
            if seconds > 86400:
                raise ValueError("Maximum interval is 24 hours")
            return v
        iso = re.match(r"^PT(\d+[HMS])+$", v)
        if iso:
            return v
        raise ValueError(f"Invalid interval: {v}. Use shorthand (5m) or ISO 8601 (PT5M)")


class AppFrontend(BaseModel):
    staticDir: str = "frontend/static"
    css: list[str] = []
    js: list[str] = []


class AppPage(BaseModel):
    id: str = Field(pattern=r"^[a-z][a-z0-9-]*$", min_length=2, max_length=64)
    path: str = Field(min_length=1)
    label: str = Field(min_length=1, max_length=100)
    icon: str = Field(min_length=1, max_length=64)
    nav: str | None = "apps"
    fragment: str = Field(min_length=1)


class AppRightPaneContribution(BaseModel):
    id: str = Field(pattern=r"^[a-z][a-z0-9-]*$")
    label: str = Field(min_length=1, max_length=100)
    icon: str = Field(min_length=1, max_length=64)
    fragment: str = Field(min_length=1)
    context: str = "object"  # "object" | "view" | "always"
    targetTypes: list[str] = ["*"]
    priority: int = Field(default=50, ge=0, le=100)


class AppViewContribution(BaseModel):
    id: str = Field(pattern=r"^[a-z][a-z0-9-]*$")
    label: str = Field(min_length=1, max_length=100)
    icon: str = Field(min_length=1, max_length=64)
    fragment: str = Field(min_length=1)


class AppCommandPaletteEntry(BaseModel):
    id: str = Field(pattern=r"^[a-z][a-z0-9-]*$")
    label: str = Field(min_length=1, max_length=100)
    keywords: list[str] = []
    actionType: str  # "dialog" | "post" | "navigate"
    fragment: str | None = None
    endpoint: str | None = None
    path: str | None = None

    @model_validator(mode="after")
    def validate_action_target(self) -> "AppCommandPaletteEntry":
        if self.actionType == "dialog" and not self.fragment:
            raise ValueError("dialog action requires fragment")
        if self.actionType == "post" and not self.endpoint:
            raise ValueError("post action requires endpoint")
        if self.actionType == "navigate" and not self.path:
            raise ValueError("navigate action requires path")
        return self


class AppObjectRendererModes(BaseModel):
    read: str | None = None
    edit: str | None = None

    @model_validator(mode="after")
    def at_least_one_mode(self) -> "AppObjectRendererModes":
        if not self.read and not self.edit:
            raise ValueError("At least one mode (read or edit) must be specified")
        return self


class AppObjectRenderer(BaseModel):
    type: str = Field(min_length=1, description="RDF type IRI or prefixed name")
    modes: AppObjectRendererModes


class AppContributions(BaseModel):
    rightPane: list[AppRightPaneContribution] = []
    views: list[AppViewContribution] = []
    commandPalette: list[AppCommandPaletteEntry] = []


class AppUI(BaseModel):
    pages: list[AppPage] = []
    contributions: AppContributions = AppContributions()
    objectRenderers: list[AppObjectRenderer] = []


class AppSettingDef(BaseModel):
    key: str = Field(pattern=r"^[a-zA-Z][a-zA-Z0-9]*$", min_length=1, max_length=64)
    label: str = Field(min_length=1, max_length=200)
    description: str = ""
    inputType: str  # "text" | "password" | "toggle" | "select" | "number"
    options: list[str] | None = None
    default: Any = ""

    @model_validator(mode="after")
    def validate_options(self) -> "AppSettingDef":
        if self.inputType == "select" and not self.options:
            raise ValueError("select inputType requires options list")
        return self


# ── Root schema ──

class AppManifestSchema(BaseModel):
    """Root manifest schema for SemPKM applications."""

    # Identity
    appId: str = Field(
        pattern=r"^[a-z][a-z0-9-]*$",
        min_length=2,
        max_length=64,
    )
    version: str = Field(pattern=r"^\d+\.\d+\.\d+$")
    name: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=2000)
    author: AppAuthor | None = None
    license: str = Field(default="", max_length=64)

    # Dependencies
    dependencies: AppDependencies = AppDependencies()

    # Permissions
    permissions: AppPermissions = AppPermissions()

    # Backend
    backend: AppBackend

    # Tasks
    tasks: list[AppTask] = []

    # Frontend
    frontend: AppFrontend = AppFrontend()

    # UI
    ui: AppUI = AppUI()

    # Settings
    settings: list[AppSettingDef] = []

    # ── Validators ──

    @model_validator(mode="after")
    def validate_task_references(self) -> "AppManifestSchema":
        """Ensure backgroundTasks permission is set if tasks are declared."""
        if self.tasks and not self.permissions.backgroundTasks:
            raise ValueError(
                "App declares tasks but permissions.backgroundTasks is false"
            )
        return self

    @model_validator(mode="after")
    def validate_settings_permission(self) -> "AppManifestSchema":
        """Ensure settings permission is set if settings are declared."""
        if self.settings and not self.permissions.settings:
            raise ValueError(
                "App declares settings but permissions.settings is false"
            )
        return self


def parse_app_manifest(manifest_path: str) -> AppManifestSchema:
    """Load and validate an app manifest from a YAML file."""
    import yaml
    from pathlib import Path

    path = Path(manifest_path)
    if not path.exists():
        raise ValueError(f"Manifest not found: {manifest_path}")

    with open(path) as f:
        data = yaml.safe_load(f)

    if not isinstance(data, dict):
        raise ValueError("Manifest must be a YAML mapping")

    return AppManifestSchema(**data)
```

---

## 15. Disk Layout

### App source directory (in repository or marketplace download)

```
apps/
  rss-reader/
    manifest.yaml                 # App manifest (validated by AppManifestSchema)
    requirements.txt              # Python dependencies (feedparser, trafilatura, etc.)
    backend/
      __init__.py
      app.py                      # RSSReaderApp class (entrypoint)
      services/
        __init__.py
        feed_service.py           # Feed fetching, parsing, discovery
        hypothesis_service.py     # Hypothesis API client + sync logic
      router.py                   # Additional FastAPI routes (beyond task handlers)
    frontend/
      templates/                  # Jinja2 templates (HTML fragments)
        reader.html               # Main reader interface
        article_read.html         # Article read renderer (Level 3)
        annotation_read.html      # Annotation renderer (Level 3)
        feed_list.html            # Feed sidebar fragment
        views/
          unread.html             # Unread articles view
          starred.html            # Starred articles view
          highlights.html         # Highlights view
        pane/
          related_articles.html   # Right pane contribution
        dialogs/
          subscribe.html          # Subscribe dialog (command palette)
      static/
        css/
          reader.css              # App-specific styles
        js/
          reader.js               # App-specific JavaScript
```

### Runtime directories (created by platform at install time)

```
/app/data/apps/
  rss-reader/
    venv/                         # Python virtual environment
      bin/python
      lib/python3.x/site-packages/
        feedparser/
        trafilatura/
        sempkm_app_sdk/           # Injected by platform

/app/data/apps-static/
  rss-reader/                     # Copied from frontend/static/ at install time
    css/reader.css
    js/reader.js
```

### nginx configuration addition

```nginx
# App static assets (one rule for all apps)
location /app-static/ {
    alias /app/data/apps-static/;
    expires 1h;
    add_header Cache-Control "public, immutable";
}
```

---

## 16. Migration & Upgrade

### App upgrades

When an app is upgraded (v0.1.0 → v0.2.0):

1. New manifest is validated
2. Dependencies are checked (new model dependency might need installing first)
3. Venv is updated with new requirements
4. Static assets are replaced
5. App is restarted
6. No data migration — app data is in `current`, typed by shared model schemas
7. App state graph (`urn:sempkm:app:{appId}:state`) may need migration — the app's `on_startup` hook handles this

### Model upgrades (independent of app)

When a shared model is upgraded (rss-feeds v1.0.0 → v1.1.0):

1. Model's ontology/shapes/views are updated via `ModelService.refresh_artifacts()`
2. Data migration is handled by the model's migration system (future milestone)
3. Running apps are notified via a lifecycle hook: `POST /app/{appId}/_lifecycle/model-updated`
4. App can adjust behavior based on new model version

### Version compatibility

The platform checks at install and startup:

```python
def check_dependencies(app: AppManifestSchema) -> list[str]:
    errors = []
    for dep in app.dependencies.models:
        installed = model_service.get_installed_version(dep.id)
        if not installed and not dep.optional:
            errors.append(f"Required model '{dep.id}' is not installed")
        elif installed and not SpecifierSet(dep.version).contains(installed):
            errors.append(
                f"Model '{dep.id}' v{installed} does not satisfy {dep.version}"
            )
    return errors
```

---

## 17. Future Work

Items explicitly out of scope for the initial implementation, to be addressed in later milestones:

### App marketplace
- Centralized registry for publishing and discovering models and apps
- Version management, reviews, compatibility matrix
- One-click install from marketplace

### Subdomain routing
- `rss.sempkm.example.com` → `/app/rss-reader/`
- nginx wildcard config + CORS adjustments
- Nice UX for standalone app access

### App-to-app dependencies
- App A depends on App B's API
- Cross-app event subscriptions
- Shared capabilities (e.g., "notification service" app)

### WebSocket support for apps
- Real-time updates from apps to workspace
- App → platform push notifications
- Hypothesis WebSocket relay

### Model data migrations
- Schema evolution: rename properties, split types, merge fields
- Migration scripts bundled with model versions
- Rollback support

### Multi-user app permissions
- Per-user app install (vs. instance-wide)
- Per-user settings for shared apps
- Role-based app access (some apps for owners only)

### Containerized app isolation
- Docker-in-Docker for untrusted apps
- Resource limits (CPU, memory, network)
- Full OS-level sandboxing

---

## Design Decisions Log

| Decision | Chosen | Alternatives Considered | Rationale |
|----------|--------|------------------------|-----------|
| Models always shared | Yes | Bundled with apps | Composability, independent versioning, data survives app changes |
| App data in `current` | Yes | Separate app graph | Shared models mean data is first-class; IRI prefix for traceability/cleanup |
| Subprocess isolation | Yes | In-process, Docker containers | Balance of safety and simplicity for personal tool |
| Per-app venvs | Yes | Shared deps, pip install to main | Dependency isolation, no conflicts between apps |
| HTTP over unix socket | Yes | JSON-RPC over stdin/stdout | HTTP is standard, debuggable, apps can serve HTML fragments naturally |
| Platform-owned scheduler | Yes | App-owned scheduler | Admin visibility, centralized control, pause/resume from admin |
| All UI is fragments | Yes | Full pages from apps, iframe embedding | Consistent with htmx architecture, platform controls chrome |
| browserVisible per type | Yes | All types visible, separate app object browser | Clean object browser, internal types hidden but still queryable |
| Permissions enforced in SDK | Yes | Advisory only, OS-level enforcement | Practical for personal tool; JWT token scoping adds API-level enforcement |
| Bulk EventStore | Added | Standard-only | Feed ingestion performance; all-or-nothing undo is acceptable trade-off |
