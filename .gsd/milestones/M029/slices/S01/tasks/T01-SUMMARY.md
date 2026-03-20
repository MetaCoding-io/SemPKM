---
id: T01
parent: S01
milestone: M029
provides:
  - frontend/package.json with all 18 CDN deps version-pinned
  - frontend/build.js esbuild script producing vendor bundle, page-specific bundles, minified app assets, manifest.json, and .gz siblings
  - frontend/.gitignore excluding node_modules/ and dist/
  - frontend/package-lock.json for reproducible installs
key_files:
  - frontend/package.json
  - frontend/build.js
  - frontend/.gitignore
  - frontend/package-lock.json
key_decisions:
  - Used esbuild transform API for concatenated vendor bundle (not build API) for correct dependency ordering
  - highlight.js bundled via esbuild (CJS only, no pre-built UMD in npm package)
  - ninja-keys bundled via esbuild (ESM web component, needs IIFE wrapping)
  - App JS target set to esnext (sparql-console.js uses top-level await)
  - dockview-core, yasgui, and chart.js used pre-built dist files (already UMD/minified)
patterns_established:
  - Vendor concatenation order matches CDN script order in base.html
  - Content hash is first 8 hex chars of SHA-256 of output content
  - manifest.json maps logical names (vendor.js, app.js, theme.css) to hashed filenames
observability_surfaces:
  - frontend/dist/manifest.json — JSON mapping of all logical asset names to content-hashed filenames
  - build.js stdout — file counts, sizes, elapsed time
  - build.js exit code 0/1 for CI/CD success/failure detection
duration: 15m
verification_result: passed
completed_at: 2026-03-20
blocker_discovered: false
---

# T01: Create frontend npm project and esbuild build script

**Created esbuild build pipeline that vendors 18 CDN dependencies into content-hashed bundles with .gz pre-compression and manifest.json**

## What Happened

Created the complete Node.js build infrastructure for vendoring all CDN dependencies locally. The build script (`frontend/build.js`) uses esbuild to:

1. **Vendor JS bundle** — concatenates 15 libraries in strict Cytoscape plugin dependency order, bundles highlight.js (CJS→IIFE) and ninja-keys (ESM→IIFE) via esbuild, then minifies the combined output with `keepNames: true` for htmx compatibility. Produces `vendor-[hash].min.js` (1.5MB, 427KB gzipped).

2. **Vendor CSS bundle** — driver.js CSS minified into `vendor-[hash].min.css`.

3. **Page-specific vendor bundles** — dockview-core JS+CSS (workspace-vendor), @zazuko/yasgui JS+CSS (yasgui), and chart.js UMD (chartjs), each content-hashed separately for lazy loading per D272.

4. **Highlight.js theme CSS** — github and github-dark themes as separate files for dynamic theme switching.

5. **App JS/CSS** — each of 19 JS files and 9 CSS files (excluding dockview-sempkm-bridge.css which goes into workspace-vendor) individually minified with content hashes.

6. **manifest.json** — 37 entries mapping logical names to hashed filenames.

7. **.gz pre-compression** — gzip -9 siblings for all 38 output files (D269).

One deviation from the plan: highlight.js does not ship a UMD file in its npm package (unlike the CDN version), so it required esbuild bundling from `highlight.js/lib/common` with a window.hljs assignment. Also changed app JS target from `es2020` to `esnext` because `sparql-console.js` uses top-level await.

## Verification

- `npm ci` installs cleanly from lockfile (78 packages, 0 vulnerabilities)
- `node build.js` completes in 0.8s with exit code 0
- `ls dist/vendor-*.min.js` returns exactly 1 file
- `manifest.json` exists with 37 entries (≥25 required)
- `.gz` count (38) matches source file count (38)
- All vendor bundles, page-specific bundles, hljs themes, app JS, and app CSS present in manifest

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd frontend && npm ci` | 0 | ✅ pass | 3s |
| 2 | `cd frontend && node build.js` | 0 | ✅ pass | 0.8s |
| 3 | `ls frontend/dist/vendor-*.min.js \| wc -l` (expect 1) | 0 | ✅ pass | <1s |
| 4 | `ls frontend/dist/manifest.json` | 0 | ✅ pass | <1s |
| 5 | `manifest.json grep -c '"'` (expect ≥25, got 37) | 0 | ✅ pass | <1s |
| 6 | `.gz count == source count` (38 == 38) | 0 | ✅ pass | <1s |
| 7 | `node -e "Object.keys(manifest).length"` (expect ≥25, got 37) | 0 | ✅ pass | <1s |

### Slice-level checks (T01 scope):
| # | Check | Result |
|---|-------|--------|
| 1 | `cd frontend && npm ci && node build.js` produces dist/ with manifest.json | ✅ pass |
| 2 | `python -m pytest backend/tests/test_template_helpers.py -v` | ⏳ T02 (not yet created) |
| 3 | `grep -rn unpkg\|jsdelivr\|cdnjs ... | grep -v ...` zero unguarded CDN refs | ⏳ T03 |
| 4-9 | Docker build, curl, workspace tests | ⏳ T04 |

## Diagnostics

- **Inspect build output:** `cat frontend/dist/manifest.json | python3 -m json.tool`
- **Check file sizes:** `ls -lhS frontend/dist/*.js frontend/dist/*.css`
- **Verify gzip:** `ls frontend/dist/*.gz | wc -l` should match `ls frontend/dist/*.js frontend/dist/*.css frontend/dist/*.json | wc -l`
- **Rebuild from clean:** `cd frontend && rm -rf node_modules dist && npm ci && node build.js`
- **Build failure:** Exit code 1 with error on stderr; most common cause would be missing node_modules file path

## Deviations

- **highlight.js:** Plan assumed concatenation from a pre-built UMD file, but the npm package only ships CJS/ESM. Used esbuild to bundle `highlight.js/lib/common` into an IIFE that assigns `window.hljs`. Functionally equivalent.
- **App JS target:** Changed from `es2020` to `esnext` because `sparql-console.js` uses top-level await (dynamic `import()` for CodeMirror). This is safe since all target browsers support it.
- **marked version:** Plan said "15.0.0 or whatever is current" — used 15.0.7 (recent stable). marked-highlight 2.2.3 is compatible (peerDep: `marked >=4 <18`).
- **dompurify version:** Plan said "pin to a specific version" — used 3.3.3 (latest stable at time of build).
- **chart.js version:** Plan said "4.4.0 approximately" — used 4.4.9 (latest 4.4.x patch).

## Known Issues

None.

## Files Created/Modified

- `frontend/package.json` — npm project with 18 CDN deps + esbuild devDependency
- `frontend/package-lock.json` — lockfile for reproducible `npm ci` builds
- `frontend/build.js` — complete esbuild build script (vendor bundles, app minification, content hashing, manifest, gzip)
- `frontend/.gitignore` — ignores node_modules/ and dist/
- `.gsd/milestones/M029/slices/S01/tasks/T01-PLAN.md` — added Observability Impact section (preflight fix)
