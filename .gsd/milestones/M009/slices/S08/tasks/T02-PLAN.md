---
estimated_steps: 5
estimated_files: 4
---

# T02: Add glossary entries, update README TOC, and wire navigation chain

**Slice:** S08 — User Guide Documentation
**Milestone:** M009

## Description

Integrate Chapter 29 into the existing guide structure: add glossary entries, update the README table of contents, and wire the navigation chain between ch. 28, ch. 29, and Appendix A.

## Steps

1. **Add 5 glossary entries** to `docs/guide/appendix-d-glossary.md`. Insert alphabetically — all 5 start with "App" so they go between "ABox" and "Block". Each entry follows the existing format: bold term on its own line, definition paragraph below, with a "See [Chapter 29: App Platform](29-app-platform.md)" cross-reference. The 5 terms:

   - **App Contribution** — A UI element an app contributes to the workspace: right-pane sections, views, command palette entries, or object renderer overrides. Declared in the manifest's `ui.contributions` section. See [Chapter 29: App Platform](29-app-platform.md).
   - **App Manifest** — The `manifest.yaml` file in an app's root directory that declares its identity, dependencies, permissions, tasks, frontend assets, and UI contributions. The platform validates the manifest at install time using a Pydantic schema. See [Chapter 29: App Platform](29-app-platform.md).
   - **App Platform** — The subsystem that manages third-party and first-party Python applications. Apps run as sandboxed subprocesses communicating with the platform via HTTP over unix domain sockets. See [Chapter 29: App Platform](29-app-platform.md).
   - **App Sandbox** — The isolation boundary for each app: a separate Python subprocess with its own virtual environment, communicating with the platform only through a scoped HTTP API. Apps cannot access platform internals directly. See [Chapter 29: App Platform](29-app-platform.md).
   - **App SDK** — The `sempkm-app-sdk` Python package that provides the `App` class, `AppContext`, and scoped clients for building SemPKM applications. Installed automatically into each app's virtual environment. See [Chapter 29: App Platform](29-app-platform.md).

2. **Update `docs/guide/README.md`** — Add `29. [App Platform](29-app-platform.md)` to Part VIII (Discovery and Integration), after the line for ch. 28.

3. **Update `docs/guide/28-dashboards-and-workflows.md` footer** — Change the existing footer line:
   ```
   **Previous:** [Chapter 27: Spatial Canvas](27-spatial-canvas.md) | **Next:** [Appendix A: Environment Variable Reference](appendix-a-environment-variables.md)
   ```
   to:
   ```
   **Previous:** [Chapter 27: Spatial Canvas](27-spatial-canvas.md) | **Next:** [Chapter 29: App Platform](29-app-platform.md)
   ```

4. **Update `docs/guide/29-app-platform.md` footer** — Ensure the footer line at the bottom of ch. 29 reads:
   ```
   **Previous:** [Chapter 28: Dashboards and Workflows](28-dashboards-and-workflows.md) | **Next:** [Appendix A: Environment Variable Reference](appendix-a-environment-variables.md)
   ```
   (T01 may have already set this — verify and fix if needed.)

5. **Verify all links:**
   - `grep "29-app-platform" docs/guide/README.md` — TOC entry present
   - `grep "29-app-platform" docs/guide/28-dashboards-and-workflows.md` — ch. 28 footer updated
   - `grep "Appendix A" docs/guide/29-app-platform.md` — ch. 29 footer points forward
   - `grep "Chapter 28" docs/guide/29-app-platform.md` — ch. 29 footer points backward
   - `grep "App Platform" docs/guide/appendix-d-glossary.md` — glossary entry present
   - `grep "App SDK" docs/guide/appendix-d-glossary.md` — glossary entry present

## Must-Haves

- [ ] 5 glossary entries added in alphabetical position (between ABox and Block)
- [ ] README.md Part VIII has ch. 29 entry after ch. 28
- [ ] Ch. 28 footer `Next:` points to ch. 29 (not Appendix A)
- [ ] Ch. 29 footer has both Previous (ch. 28) and Next (Appendix A)
- [ ] No broken internal links (all referenced files exist)

## Verification

- `grep "App Contribution" docs/guide/appendix-d-glossary.md` — returns match
- `grep "App Manifest" docs/guide/appendix-d-glossary.md` — returns match
- `grep "App Platform" docs/guide/appendix-d-glossary.md` — returns match
- `grep "App Sandbox" docs/guide/appendix-d-glossary.md` — returns match
- `grep "App SDK" docs/guide/appendix-d-glossary.md` — returns match
- `grep "29-app-platform" docs/guide/README.md` — returns match
- `grep "29-app-platform" docs/guide/28-dashboards-and-workflows.md` — returns match
- `grep "Appendix A" docs/guide/29-app-platform.md` — returns match

## Observability Impact

This task modifies static documentation files only — no runtime signals, logs, or metrics are affected. Verification is entirely via `grep` commands checking for expected content in the 4 touched files. If any glossary entry, TOC line, or footer link is missing, the corresponding `grep` returns non-zero — suitable for CI gating. A future agent can re-run the Verification section commands to confirm integrity.

## Inputs

- `docs/guide/29-app-platform.md` — created by T01, needs footer verification/fix
- `docs/guide/appendix-d-glossary.md` — existing glossary (155 lines), entries currently go ABox → Block → ... alphabetically
- `docs/guide/README.md` — existing TOC, Part VIII section has chs. 21-28
- `docs/guide/28-dashboards-and-workflows.md` — existing ch. 28, footer currently points to Appendix A

## Expected Output

- `docs/guide/appendix-d-glossary.md` — modified with 5 new entries (~25 lines added)
- `docs/guide/README.md` — modified with 1 new TOC line
- `docs/guide/28-dashboards-and-workflows.md` — modified footer line
- `docs/guide/29-app-platform.md` — footer verified/corrected if needed
