---
estimated_steps: 9
estimated_files: 3
---

# T01: Create frontend npm project and esbuild build script

**Slice:** S01 — Build Pipeline & Local Vendoring
**Milestone:** M029

## Description

Create the Node.js build infrastructure that vendors all 18 CDN dependencies, bundles them into logical groups, minifies all app JS/CSS, content-hashes everything, and produces a manifest.json mapping logical names to hashed filenames. This is pure build tooling with no backend coupling — testable via `npm ci && node build.js`.

Key decisions to implement:
- **D267:** esbuild for all JS/CSS bundling, minification, and content-hashing
- **D268:** npm + esbuild vendor bundle strategy
- **D272:** Yasgui and Chart.js stay as separate lazy-loaded bundles, not in vendor bundle
- **D269:** Generate .gz pre-compressed siblings for all output files

## Steps

1. Create `frontend/package.json` with all 18 CDN deps as version-pinned npm dependencies. Versions must match the CDN versions currently in base.html:
   - htmx.org@2.0.4
   - split.js@1.6.5
   - ninja-keys@1.2.2
   - cytoscape@3.33.1
   - layout-base@2.0.1 
   - cose-base@2.2.0
   - cytoscape-fcose@2.2.0
   - dagre@0.8.5
   - cytoscape-dagre@2.5.0
   - marked@latest (CDN uses unversioned latest — pick a specific recent version like 15.0.0 or whatever is current)
   - marked-highlight@latest (match marked version compatibility)
   - highlight.js@11.11.1
   - dompurify@latest (CDN uses unversioned — pin to a specific version)
   - lucide@0.575.0
   - driver.js@1.4.0
   - dockview-core@4.11.0
   - @zazuko/yasgui@4.5.0
   - chart.js@4.4.0 (approximately — the CDN URL says `@4.4`)
   - esbuild as devDependency

2. Create `frontend/.gitignore` with:
   ```
   node_modules/
   dist/
   package-lock.json
   ```
   Note: package-lock.json is generated and typically gitignored in non-app projects; for reproducibility in Docker, `npm ci` uses it. Actually, for reproducible Docker builds, package-lock.json SHOULD be committed. Omit it from .gitignore. Only `node_modules/` and `dist/`.

3. Create `frontend/build.js` — the esbuild build script. This must produce:

   **Vendor bundle (global, every page):**
   - `vendor-[hash].min.js` — concatenates in this exact order for Cytoscape plugin registration:
     1. htmx.org (IIFE, registers `htmx` global)
     2. split.js (IIFE, registers `Split` global)
     3. cytoscape (IIFE, registers `cytoscape` global)
     4. layout-base (must load after cytoscape)
     5. cose-base (must load after layout-base)
     6. cytoscape-fcose (must load after cose-base)
     7. dagre (IIFE, registers `dagre` global)
     8. cytoscape-dagre (must load after dagre + cytoscape)
     9. marked UMD (registers `marked` global)
     10. marked-highlight UMD
     11. highlight.js (registers `hljs` global)
     12. DOMPurify (registers `DOMPurify` global)
     13. lucide UMD (registers `lucide` global)
     14. driver.js IIFE
     15. ninja-keys (web component — self-registers via side effects)
   - Use esbuild `bundle: true` with an entrypoint that imports all in order, OR concatenate the resolved node_modules files. The concatenation approach is simpler since these are all UMD/IIFE — just read each file and write them in order. Use `--keep-names` for htmx compatibility.
   - `vendor-[hash].min.css` — driver.js CSS

   **Page-specific vendor bundles (lazy-loaded):**
   - `workspace-vendor-[hash].min.js` — dockview-core JS
   - `workspace-vendor-[hash].min.css` — dockview-core CSS + dockview-sempkm-bridge.css
   - `yasgui-[hash].min.js` — @zazuko/yasgui JS
   - `yasgui-[hash].min.css` — @zazuko/yasgui CSS
   - `chartjs-[hash].min.js` — chart.js UMD

   **Highlight.js themes (separate files, dynamically loaded by theme.js):**
   - `hljs-github-[hash].css` — highlight.js github theme
   - `hljs-github-dark-[hash].css` — highlight.js github-dark theme

   **App JS (each file minified individually):**
   - For each file in `static/js/*.js`: minify and produce `[name]-[hash].min.js`

   **App CSS (each file minified individually):**
   - For each file in `static/css/*.css` (except dockview-sempkm-bridge.css which goes into workspace-vendor): minify and produce `[name]-[hash].min.css`

   **manifest.json** — maps logical names to hashed filenames:
   ```json
   {
     "vendor.js": "vendor-a1b2c3d4.min.js",
     "vendor.css": "vendor-e5f6g7h8.min.css",
     "workspace-vendor.js": "workspace-vendor-i9j0k1l2.min.js",
     "workspace-vendor.css": "workspace-vendor-m3n4o5p6.min.css",
     "yasgui.js": "yasgui-q7r8s9t0.min.js",
     "yasgui.css": "yasgui-u1v2w3x4.min.css",
     "chartjs.js": "chartjs-y5z6a7b8.min.js",
     "hljs-github.css": "hljs-github-c9d0e1f2.css",
     "hljs-github-dark.css": "hljs-github-dark-g3h4i5j6.css",
     "workspace.js": "workspace-k7l8m9n0.min.js",
     "workspace.css": "workspace-o1p2q3r4.min.css",
     ...
   }
   ```

4. For the vendor bundle concatenation approach:
   - Read each vendor file from node_modules, in correct order
   - Concatenate into a single buffer
   - Use esbuild's `transform` API with `minify: true, keepNames: true` on the concatenated result
   - Compute content hash (first 8 chars of hex SHA-256 or use esbuild's built-in hashing)
   - Write to `dist/vendor-[hash].min.js`

5. For app JS/CSS files, use esbuild's `build` API with:
   - `entryPoints: [file]` for each file individually
   - `outdir: 'dist'`
   - `minify: true`
   - `entryNames: '[name]-[hash]'` (esbuild auto-hashes)
   - `format: 'iife'` for JS
   - Parse esbuild's metafile output to extract the input→output filename mappings for manifest.json

6. For ninja-keys: it's distributed as an ES module that self-registers a web component. Use esbuild bundle with `format: 'iife'` to wrap the ESM import. Same for dockview-core if it's ESM-only.

7. Generate .gz pre-compressed siblings: after all files are written, iterate dist/ and run `gzip -k -9` on each .js, .css, and .json file (creates .gz alongside original).

8. Write the complete manifest.json with all mappings.

9. Add `dist/` and `node_modules/` to `frontend/.gitignore`.

## Must-Haves

- [ ] package.json has all 18 CDN dependencies with version pins matching current CDN versions
- [ ] `node build.js` runs in <30s and produces dist/ with manifest.json
- [ ] vendor.min.js concatenates deps in correct Cytoscape plugin dependency order
- [ ] manifest.json has entries for every vendor bundle, page-specific bundle, hljs theme, app JS file, and app CSS file
- [ ] All output files have content-hash in filename
- [ ] .gz pre-compressed siblings exist for all output files
- [ ] ninja-keys builds successfully as IIFE (web component self-registers)
- [ ] dockview-core builds successfully (may need ESM→IIFE wrapping)

## Verification

- `cd frontend && npm ci` installs without errors
- `cd frontend && node build.js` completes with exit code 0
- `ls frontend/dist/vendor-*.min.js` returns exactly one file
- `ls frontend/dist/manifest.json` exists
- `cat frontend/dist/manifest.json | python3 -m json.tool | grep -c '"'` returns ≥25 entries
- `ls frontend/dist/*.gz | wc -l` matches number of .js + .css + .json files
- `node -e "const m = require('./frontend/dist/manifest.json'); console.log(Object.keys(m).length)"` returns ≥25

## Observability Impact

- **Signals changed:** `frontend/dist/manifest.json` is the primary inspection surface — a JSON file mapping logical asset names to content-hashed filenames. Its presence/absence determines whether the backend serves local or CDN assets.
- **How to inspect:** `cat frontend/dist/manifest.json | python3 -m json.tool` shows all asset mappings. `ls -la frontend/dist/` shows all built files with sizes. `ls frontend/dist/*.gz` confirms pre-compression.
- **Failure visibility:** `node build.js` exits non-zero with stderr on any build failure. Missing vendor files or npm packages produce clear error messages referencing the missing module path. An incomplete manifest.json (fewer than expected entries) indicates a build step was skipped.
- **Build timing:** `node build.js` logs elapsed time and file counts to stdout, enabling CI performance regression detection.

## Inputs

- `frontend/static/js/*.js` — 19 app JS files to minify
- `frontend/static/css/*.css` — 10 app CSS files to minify
- CDN version pins from `backend/app/templates/base.html` lines 19-46
- Decisions D267, D268, D272

## Expected Output

- `frontend/package.json` — npm project with all 18 deps + esbuild
- `frontend/package-lock.json` — lockfile for reproducible builds
- `frontend/build.js` — complete esbuild build script
- `frontend/.gitignore` — ignores node_modules/ and dist/
- `frontend/dist/` — complete build output with all bundles, minified files, manifest.json, and .gz files
