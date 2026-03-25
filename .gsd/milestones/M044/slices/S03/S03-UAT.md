# S03: Window Namespace Consolidation — UAT

**Milestone:** M044
**Written:** 2026-03-25T19:54:29.753Z

# S03: Window Namespace Consolidation — UAT

**Milestone:** M044
**Written:** 2026-03-25

## UAT Type

- UAT mode: artifact-driven
- Why this mode is sufficient: This is a pure namespace refactoring — zero runtime behavior changes. Verification is structural (grep for remaining bare globals) rather than behavioral. Runtime proof deferred to S07 E2E regression suite.

## Preconditions

- All 25 JS files in `frontend/static/js/` are present and pass `node --check`
- All 52+ modified templates exist under `backend/app/templates/`
- E2E test files compile without errors in S03-modified files

## Smoke Test

Run `rg 'window\.\w+ =' frontend/static/js/ | grep -v 'window\.SemPKM' | grep -v '//' | grep -v 'window\.(location|posthog|htmx|lucide|DockviewCore|Chart|Yasgui|driver|open\(|confirm\(|matchMedia|localStorage)'` — must return zero lines. This confirms no custom globals leak outside the SemPKM namespace.

## Test Cases

### 1. Namespace Bootstrap Present

1. Open `frontend/static/js/api-fetch.js`
2. Verify line `window.SemPKM = window.SemPKM || {};` exists near the top of the IIFE
3. **Expected:** Bootstrap initializes the namespace object before any exports

### 2. All JS Exports Use SemPKM Namespace

1. Run: `rg 'window\.[a-zA-Z_]\w* =' frontend/static/js/ | grep -v 'window\.SemPKM' | grep -v '//' | grep -v 'window\.(location|posthog|htmx|lucide|DockviewCore|Chart|Yasgui|driver|open\(|confirm\(|matchMedia|localStorage)'`
2. **Expected:** Zero lines returned. All custom exports use `window.SemPKM.X =` pattern.

### 3. All Template onclick Handlers Use SemPKM Namespace

1. Run: `rg 'onclick=.*window\.' backend/app/templates/ | grep -v 'window\.(location|confirm|prompt|open|matchMedia|lucide|htmx|posthog|close|print|getComputedStyle|innerWidth|scrollTo|addEventListener|removeEventListener|setTimeout|clearTimeout|setInterval|clearInterval|requestAnimationFrame|getSelection|DOMParser|MutationObserver|IntersectionObserver|ResizeObserver|URL|fetch|history|navigator|performance|CustomEvent|dispatchEvent|Event|localStorage|sessionStorage)'`
2. **Expected:** Only lines containing `window.SemPKM` or `window.SemPKMCanvas` (explicitly out-of-scope pre-namespaced globals).

### 4. Template typeof Guards Migrated

1. Run: `rg 'typeof window\.[a-z]\w+ ==' backend/app/templates/ | grep -v 'window\.(renderMarkdownBody|renderMarkdownFromUrl|initRecurrenceEditor|initExdateEditor|initEditor|markDirty|SemPKM)'`
2. **Expected:** Zero lines. All typeof guards use `typeof SemPKM.X` pattern.

### 5. E2E Tests Use SemPKM Namespace

1. Run: `rg 'window\.[a-z]\w+' e2e/ -g '*.ts' | grep -v 'window\.(SemPKM|location|dispatchEvent|document|addEventListener|removeEventListener|setTimeout|clearTimeout|navigator|localStorage|innerWidth|innerHeight|scrollY|getComputedStyle|history|performance|matchMedia|open|close|confirm)' | wc -l`
2. **Expected:** 0 lines. All E2E `page.evaluate()` calls use `(window as any).SemPKM.X`.

### 6. Zero Backward-Compat Shims Remain

1. Run: `rg '^\s*window\.[a-zA-Z_]\w+\s*=\s*(window\.)?SemPKM\.' frontend/static/js/ | grep -v '//'`
2. **Expected:** Zero lines. All shim lines (`window.X = window.SemPKM.X`) removed.

### 7. JS Syntax Validity

1. Run: `for f in frontend/static/js/*.js; do node --check "$f" 2>&1 || echo "FAIL: $f"; done | grep FAIL`
2. **Expected:** Zero FAIL lines. All JS files parse without syntax errors.

### 8. Pre-Namespaced Globals Untouched

1. Run: `rg 'window\.SemPKMSettings|window\.SemPKMLayouts|window\.SemPKMCanvas' frontend/static/js/ | head -5`
2. **Expected:** Lines exist — these concatenated-name globals were intentionally left as-is per plan scope.

## Edge Cases

### Template with page-local functions (admin pages)

1. Open `backend/app/templates/admin/app.html`
2. Verify `switchTab()` and `executeCommand()` are page-local (defined in inline script), NOT migrated to SemPKM
3. **Expected:** Admin/debug pages that use their own local functions (from app.js or inline) are unaffected by the migration

### Drag payload cross-file communication

1. Verify `window.SemPKM.__canvasDragPayload` is used in both canvas.js (write) and workspace-layout.js (read)
2. Verify `window.SemPKM.__calendarDragPayload` is used in both kanban.js (write) and calendar.js (read)
3. **Expected:** Both files reference the same SemPKM-namespaced property — no broken cross-file communication

## Failure Signals

- Any `window.X =` assignment in JS files not matching `window.SemPKM` (excluding browser builtins and third-party libs)
- Any `onclick="bareFunction()"` in templates where `bareFunction` is defined in a workspace JS IIFE
- Any E2E test using `(window as any).X` where X is a custom function (should be `(window as any).SemPKM.X`)
- TypeScript compilation errors in S03-modified E2E files
- `node --check` failure on any JS file

## Requirements Proved By This UAT

- None — this is an internal code quality improvement, not a user-facing requirement

## Not Proven By This UAT

- Runtime behavior correctness — deferred to S07 E2E regression suite
- Third-party library collision testing — the namespace prevents collisions but no collision scenario was tested
- Performance impact of the extra namespace lookup — expected negligible

## Notes for Tester

- The grep commands use extensive exclusion lists for browser builtins (window.location, window.confirm, etc.) and third-party libs (window.htmx, window.lucide, etc.). If a new third-party lib is added later, its `window.X` reference will show up as a false positive.
- `window.SemPKMSettings`, `window.SemPKMLayouts`, `window.SemPKMCanvas` are intentionally NOT under `window.SemPKM` — they use concatenated naming and were explicitly out of scope.
- Pre-existing TypeScript errors in ~15 E2E test files are unrelated to this slice.
