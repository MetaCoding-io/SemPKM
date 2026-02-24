---
status: diagnosed
trigger: "Investigate why Ctrl+K command palette (ninja-keys) may intermittently fail to open in Firefox."
created: 2026-02-23T00:00:00Z
updated: 2026-02-23T00:10:00Z
---

## Current Focus

hypothesis: CONFIRMED — two distinct but related mechanisms allow Firefox to intercept Ctrl+K before ninja-keys sees it
test: Read workspace.js, base.html, workspace.html, and ninja-keys@1.2.2 source
expecting: No preventDefault() for Ctrl+K in the app's own keydown handler
next_action: DONE — report findings, no fix requested

## Symptoms

expected: Ctrl+K opens the ninja-keys command palette in all browsers
actual: Intermittently fails to open in Firefox — user noted "Ctrl+K does something in FF now" but it worked later
errors: No JS error reported — browser silently intercepts the shortcut
reproduction: Open Firefox, focus an editable field or the page, press Ctrl+K
started: Noticed during UAT testing

## Eliminated

- hypothesis: "workspace.js has a custom Ctrl+K keydown handler that might conflict"
  evidence: The initKeyboardShortcuts() keydown handler (lines 482-530) handles Ctrl+S, Ctrl+W, Ctrl+\, Ctrl+[, Ctrl+], Ctrl+E. There is NO handler for Ctrl+K in that function. The keydown handler does not call event.preventDefault() for Ctrl+K at all.
  timestamp: 2026-02-23T00:08:00Z

- hypothesis: "The app has a second keydown listener somewhere (sidebar.js, app.js) that catches Ctrl+K"
  evidence: sidebar.js has no keydown listener. app.js and other static JS files contain no Ctrl+K handling. There is only one document keydown listener in the codebase.
  timestamp: 2026-02-23T00:09:00Z

## Evidence

- timestamp: 2026-02-23T00:05:00Z
  checked: workspace.js initKeyboardShortcuts() lines 482-530
  found: The keydown handler does NOT include any case for Ctrl+K. No preventDefault() is called for Ctrl+K anywhere in the application's own JavaScript.
  implication: The application entirely delegates Ctrl+K opening to ninja-keys' internal hotkeys-js listener.

- timestamp: 2026-02-23T00:06:00Z
  checked: base.html line 25 — ninja-keys script tag
  found: `<script type="module" src="https://unpkg.com/ninja-keys?module"></script>` — unpinned CDN, resolves to ninja-keys@1.2.2/dist/ninja-keys.js
  implication: Version is whatever unpkg currently serves for "latest". The ?module URL serves an ESM file with bare specifier imports (import hotkeys from 'hotkeys-js'), which requires the browser to resolve these specifiers. There is NO import map in the HTML.

- timestamp: 2026-02-23T00:07:00Z
  checked: ninja-keys@1.2.2 dist source — _registerInternalHotkeys()
  found: ninja-keys registers `hotkeys('cmd+k,ctrl+k', handler)` via the hotkeys-js library. The handler calls event.preventDefault() INSIDE the hotkeys-js callback. The key question is whether hotkeys-js fires at all when Firefox has already consumed the event.
  implication: ninja-keys correctly calls preventDefault, but only AFTER hotkeys-js has received the event. If Firefox consumes the event at the browser chrome level (before the page's JS runs), neither hotkeys-js nor the app can prevent it.

- timestamp: 2026-02-23T00:08:00Z
  checked: hotkeys-js default filter behavior (well-known library behavior)
  found: hotkeys-js by default does NOT fire callbacks when focus is inside an INPUT, TEXTAREA, or SELECT element. This is its built-in filter. ninja-keys does NOT override this filter.
  implication: If the user has focus in a text input (e.g., a form field in the object editor), Ctrl+K won't trigger the hotkeys-js handler at all — the library silently ignores it. Firefox then sees an unhandled Ctrl+K and focuses its search bar. This explains the "intermittent" nature: it fails specifically when focus is in a form field, but works when focus is on the page body or a non-input element.

- timestamp: 2026-02-23T00:09:00Z
  checked: workspace.html — ninja-keys element and overall form field density
  found: The workspace contains SHACL-generated forms with multiple INPUT, TEXTAREA, and SELECT fields. The editor area loads form content via htmx. The right pane has relations/lint sections.
  implication: Users working in the editor will often have focus inside a form input when they press Ctrl+K, which is precisely when hotkeys-js silences the event and Firefox intercepts it.

## Resolution

root_cause: |
  Two contributing mechanisms produce the Firefox Ctrl+K interception:

  PRIMARY CAUSE — hotkeys-js input field filter:
  ninja-keys uses the hotkeys-js library to register its Ctrl+K listener. hotkeys-js has a
  built-in default filter that explicitly ignores keydown events when the focused element is
  an INPUT, TEXTAREA, or SELECT. ninja-keys does not override this filter. When the user
  has focus inside any form field in the workspace (very common during normal use), hotkeys-js
  silently drops the Ctrl+K event. Firefox then sees an unhandled Ctrl+K and uses its built-in
  binding to focus the address/search bar. This is the primary mechanism for the "intermittent"
  failure — it is not random, it is focus-state-dependent.

  SECONDARY CAUSE — no app-level preventDefault for Ctrl+K:
  The application's own document keydown handler (workspace.js initKeyboardShortcuts, lines 482-530)
  handles Ctrl+S, Ctrl+W, Ctrl+\, Ctrl+[, Ctrl+], and Ctrl+E — but has NO case for Ctrl+K.
  This means there is no fallback to call event.preventDefault() for Ctrl+K from the app layer.
  Entirely delegating to ninja-keys/hotkeys-js is safe in Chrome (Chrome does not use Ctrl+K as a
  browser shortcut), but unsafe in Firefox where Ctrl+K is a reserved browser binding (focus search bar).

  TERTIARY CAUSE — unpinned CDN version:
  The ninja-keys import uses `https://unpkg.com/ninja-keys?module` (no version pin). If unpkg
  updates the "latest" tag, behavior could change without a code change. Currently resolves to
  v1.2.2. This is a reliability risk separate from the Firefox issue but compounds it.

fix: NOT APPLIED (goal: find_root_cause_only)

verification: N/A

files_changed: []
