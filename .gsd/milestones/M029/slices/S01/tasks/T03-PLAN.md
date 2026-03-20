---
estimated_steps: 8
estimated_files: 6
---

# T03: Replace CDN references in all templates with conditional local/CDN blocks

**Slice:** S01 — Build Pipeline & Local Vendoring
**Milestone:** M029

## Description

Replace every CDN `<script>` and `<link>` tag in all templates with a conditional block that uses local vendored assets in production (when `asset_manifest_available` is true) and preserves the existing CDN URLs for dev mode (when false). This is the highest-risk change in the slice because a single missed or incorrectly structured reference will break page rendering.

The approach uses Jinja2 conditional blocks: `{% if asset_manifest_available %}...{% else %}...{% endif %}`. Dev mode is the `{% else %}` branch containing the exact existing CDN tags — this means dev mode is literally unchanged from the current working code.

For app JS/CSS files (workspace.js, canvas.js, etc.), use `{{ 'filename.ext' | asset_url }}` unconditionally — the filter returns the original dev path (/js/filename.ext) when no manifest exists, and the hashed production path (/assets/filename-hash.min.ext) when the manifest is loaded. This means app file references don't need conditional blocks.

## Steps

1. **Edit `backend/app/templates/base.html`** — the main template with 15 CDN references.

   Replace the block of CDN script/link tags (lines 19-46 approximately) with:

   ```jinja2
   {# ── Vendor libraries ── #}
   {% if asset_manifest_available %}
   {# Production: locally-vendored, minified, content-hashed bundles #}
   <script src="{{ 'vendor.js' | asset_url }}"></script>
   <link rel="stylesheet" href="{{ 'vendor.css' | asset_url }}">
   <link id="hljs-theme" rel="stylesheet"
         href="{{ 'hljs-github.css' | asset_url }}"
         data-light-href="{{ 'hljs-github.css' | asset_url }}"
         data-dark-href="{{ 'hljs-github-dark.css' | asset_url }}">
   {% else %}
   {# Dev mode: CDN-loaded libraries (volume-mounted raw files) #}
   <script src="https://unpkg.com/htmx.org@2.0.4"></script>
   <script src="https://unpkg.com/split.js@1.6.5/dist/split.min.js"></script>
   <script type="module" src="https://unpkg.com/ninja-keys@1.2.2?module"></script>
   <script src="https://unpkg.com/cytoscape@3.33.1/dist/cytoscape.min.js"></script>
   <script src="https://unpkg.com/layout-base@2.0.1/layout-base.js"></script>
   <script src="https://unpkg.com/cose-base@2.2.0/cose-base.js"></script>
   <script src="https://unpkg.com/cytoscape-fcose@2.2.0/cytoscape-fcose.js"></script>
   <script src="https://unpkg.com/dagre@0.8.5/dist/dagre.min.js"></script>
   <script src="https://unpkg.com/cytoscape-dagre@2.5.0/cytoscape-dagre.js"></script>
   <script src="https://cdn.jsdelivr.net/npm/marked/lib/marked.umd.js"></script>
   <script src="https://cdn.jsdelivr.net/npm/marked-highlight/lib/index.umd.js"></script>
   <link id="hljs-theme" rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.11.1/styles/github.min.css">
   <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.11.1/highlight.min.js"></script>
   <script src="https://cdn.jsdelivr.net/npm/dompurify/dist/purify.min.js"></script>
   <script src="https://unpkg.com/lucide@0.575.0/dist/umd/lucide.min.js"></script>
   <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/driver.js@1.4.0/dist/driver.css">
   <script src="https://cdn.jsdelivr.net/npm/driver.js@1.4.0/dist/driver.js.iife.js"></script>
   {% endif %}
   ```

   For app JS/CSS files (non-CDN), replace hardcoded paths with asset_url filter. These are unconditional (work in both modes):
   ```jinja2
   <link rel="stylesheet" href="{{ 'theme.css' | asset_url }}">
   <link rel="stylesheet" href="{{ 'style.css' | asset_url }}">
   <link rel="stylesheet" href="{{ 'workspace.css' | asset_url }}">
   <link rel="stylesheet" href="{{ 'forms.css' | asset_url }}">
   <link rel="stylesheet" href="{{ 'views.css' | asset_url }}">
   <link rel="stylesheet" href="{{ 'settings.css' | asset_url }}">
   <link rel="stylesheet" href="{{ 'vfs-browser.css' | asset_url }}">
   ...
   <script src="{{ 'posthog.js' | asset_url }}"></script>
   <script src="{{ 'auth.js' | asset_url }}"></script>
   <script src="{{ 'tutorials.js' | asset_url }}"></script>
   ...
   <script src="{{ 'cleanup.js' | asset_url }}"></script>
   <script src="{{ 'markdown-render.js' | asset_url }}"></script>
   <script type="module" src="{{ 'editor.js' | asset_url }}"></script>
   <script src="{{ 'sidebar.js' | asset_url }}"></script>
   <script src="{{ 'theme.js' | asset_url }}"></script>
   <script src="{{ 'settings.js' | asset_url }}"></script>
   <script src="{{ 'workspace-layout.js' | asset_url }}"></script>
   <script src="{{ 'named-layouts.js' | asset_url }}"></script>
   <script src="{{ 'workspace.js' | asset_url }}"></script>
   <script src="{{ 'graph.js' | asset_url }}"></script>
   <script src="{{ 'canvas.js' | asset_url }}"></script>
   <script src="{{ 'column-prefs.js' | asset_url }}"></script>
   ```
   
   IMPORTANT: the `<script type="module" ...>` on editor.js must stay as `type="module"` — do not change the script type.

2. **Edit `backend/app/templates/base_embed.html`** — embed template with 4 CDN scripts.

   Same pattern: conditional vendor block for the 4 CDN libs (htmx, marked, dompurify, lucide), app files use asset_url unconditionally.

   ```jinja2
   {% if asset_manifest_available %}
   <script src="{{ 'vendor.js' | asset_url }}"></script>
   {% else %}
   <script src="https://unpkg.com/htmx.org@2.0.4"></script>
   <script src="https://cdn.jsdelivr.net/npm/marked/lib/marked.umd.js"></script>
   <script src="https://cdn.jsdelivr.net/npm/dompurify/dist/purify.min.js"></script>
   <script src="https://unpkg.com/lucide@0.575.0/dist/umd/lucide.min.js"></script>
   {% endif %}
   ```

   Note: embed pages will load the full vendor.js in production (which includes more libs than needed). This is acceptable — the vendor bundle is cached and embed pages need fast first-load above all. Alternatively, a `vendor-embed.js` subset could be created but is scope creep for S01.

   App CSS files use asset_url:
   ```jinja2
   <link rel="stylesheet" href="{{ 'theme.css' | asset_url }}">
   <link rel="stylesheet" href="{{ 'style.css' | asset_url }}">
   <link rel="stylesheet" href="{{ 'workspace.css' | asset_url }}">
   <link rel="stylesheet" href="{{ 'views.css' | asset_url }}">
   ```

3. **Edit `backend/app/templates/browser/workspace.html`** — dockview CSS + JS.

   The workspace.html `{% block head %}` has dockview CDN references. Replace with conditional:
   ```jinja2
   {% block head %}
   {% if asset_manifest_available %}
   <link rel="stylesheet" href="{{ 'workspace-vendor.css' | asset_url }}">
   <script src="{{ 'workspace-vendor.js' | asset_url }}"></script>
   {% else %}
   <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/dockview-core@4.11.0/dist/styles/dockview.css">
   <link rel="stylesheet" href="/css/dockview-sempkm-bridge.css">
   <script src="https://cdn.jsdelivr.net/npm/dockview-core@4.11.0/dist/dockview-core.min.js"></script>
   {% endif %}
   ...
   {% endblock %}
   ```

   Note: In production, dockview-sempkm-bridge.css is merged into workspace-vendor.css by the build script. In dev mode, it's loaded separately via CDN + static file.

4. **Edit `backend/app/templates/admin/sparql.html`** — Yasgui CDN refs.

   In the `{% block head %}` section:
   ```jinja2
   {% block head %}
   {% if asset_manifest_available %}
   <link rel="stylesheet" href="{{ 'yasgui.css' | asset_url }}">
   <script src="{{ 'yasgui.js' | asset_url }}"></script>
   {% else %}
   <link rel="stylesheet" href="https://unpkg.com/@zazuko/yasgui@4.5.0/build/yasgui.min.css">
   <script src="https://unpkg.com/@zazuko/yasgui@4.5.0/build/yasgui.min.js"></script>
   {% endif %}
   ```

5. **Edit `backend/app/templates/admin/model_detail.html`** — Chart.js CDN refs.

   There are TWO Chart.js script tags in model_detail.html (lines ~382 and ~477, per the research). Both need conditional wrapping:
   ```jinja2
   {% if asset_manifest_available %}
   <script src="{{ 'chartjs.js' | asset_url }}"></script>
   {% else %}
   <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4/dist/chart.umd.min.js"></script>
   {% endif %}
   ```

6. **Edit `frontend/static/js/theme.js`** — highlight.js theme switcher.

   Current code (line ~38-42):
   ```javascript
   var hljsLink = document.getElementById('hljs-theme');
   if (hljsLink) {
     var base = 'https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.11.1/styles/';
     hljsLink.href = base + (resolved === 'dark' ? 'github-dark.min.css' : 'github.min.css');
   }
   ```

   Replace with a dual-mode approach:
   ```javascript
   var hljsLink = document.getElementById('hljs-theme');
   if (hljsLink) {
     // Production: data attributes contain local asset URLs
     var lightHref = hljsLink.getAttribute('data-light-href');
     var darkHref = hljsLink.getAttribute('data-dark-href');
     if (lightHref && darkHref) {
       hljsLink.href = resolved === 'dark' ? darkHref : lightHref;
     } else {
       // Dev mode: construct CDN URL
       var base = 'https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.11.1/styles/';
       hljsLink.href = base + (resolved === 'dark' ? 'github-dark.min.css' : 'github.min.css');
     }
   }
   ```

7. **Cross-check all templates** for any CDN references not caught:
   ```bash
   grep -rn 'unpkg\|jsdelivr\|cdnjs' backend/app/templates/ | grep -v 'if not asset_manifest\|else\|endif\|{#\|{%-'
   ```
   This must return zero lines. Any hits are unguarded CDN references that need wrapping.

8. Verify that templates render correctly in dev mode (no manifest) by checking that all original paths are preserved in the `{% else %}` blocks.

## Must-Haves

- [ ] All 15 CDN references in base.html are inside `{% if asset_manifest_available %}` guards
- [ ] All 4 CDN references in base_embed.html are guarded
- [ ] Dockview CDN refs in workspace.html are guarded
- [ ] Yasgui CDN refs in admin/sparql.html are guarded
- [ ] Chart.js CDN refs in admin/model_detail.html are guarded (both occurrences)
- [ ] All app JS/CSS files use `{{ name | asset_url }}` filter
- [ ] theme.js handles both local (data-attribute) and CDN hljs theme paths
- [ ] `editor.js` script tag retains `type="module"` attribute
- [ ] Zero unguarded CDN references remain (grep verification)

## Verification

- `grep -rn 'unpkg\|jsdelivr\|cdnjs' backend/app/templates/ | grep -v '{% else %}\|{# Dev\|{% if not\|{% endif %}'` returns zero lines of unguarded CDN references (adjust the grep exclusion pattern to match actual template syntax used)
- `grep -c 'asset_url' backend/app/templates/base.html` returns ≥20 (all app assets + vendor bundles)
- `grep 'type="module"' backend/app/templates/base.html` still shows editor.js with type="module"
- `grep 'data-light-href\|data-dark-href' backend/app/templates/base.html` shows hljs theme data attributes in production block
- `grep -c 'asset_manifest_available' backend/app/templates/base.html` returns ≥2 (at least one if/else pair)

## Inputs

- T02 output: `asset_url` filter and `asset_manifest_available` global registered in Jinja2 environment
- T01 output: manifest.json key naming convention (e.g., "vendor.js", "workspace.js", "hljs-github.css")
- Current CDN URLs in `backend/app/templates/base.html` lines 19-46
- Current CDN URLs in `backend/app/templates/base_embed.html` lines 20-23
- Current dockview CDN URLs in `backend/app/templates/browser/workspace.html` lines 9-12
- Current Yasgui CDN URLs in `backend/app/templates/admin/sparql.html` lines 6-7
- Current Chart.js CDN URLs in `backend/app/templates/admin/model_detail.html` lines ~382, ~477

## Expected Output

- `backend/app/templates/base.html` — all CDN refs guarded, all app assets use asset_url
- `backend/app/templates/base_embed.html` — all CDN refs guarded, all app assets use asset_url
- `backend/app/templates/browser/workspace.html` — dockview refs guarded
- `backend/app/templates/admin/sparql.html` — Yasgui refs guarded
- `backend/app/templates/admin/model_detail.html` — Chart.js refs guarded (both occurrences)
- `frontend/static/js/theme.js` — dual-mode hljs theme handling
