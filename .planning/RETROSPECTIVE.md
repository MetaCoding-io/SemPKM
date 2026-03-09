# Project Retrospective

*A living document updated after each milestone. Lessons feed forward into future planning.*

---

## Milestone: v2.1 — Architecture Decision Gate

**Shipped:** 2026-03-01
**Phases:** 3 (20-22) | **Plans:** 9 | **Duration:** ~1 day (2026-02-28 → 2026-03-01)
**Commits:** ~30

### What Was Built

- **4 committed architectural decisions** formalized in RESEARCH.md files: RDF4J LuceneSail (FTS), @zazuko/yasgui CDN embed (SPARQL console), wsgidav + a2wsgi (VFS/WebDAV), dockview-core (UI shell)
- **DECISIONS.md** — consolidated v2.2 architecture reference with Phases 23-27 sequencing, cross-cutting concerns (auth scoping, SPARQL patterns, CSS tokens), and tech debt schedule
- **Alembic migration runner** replacing SQLAlchemy `create_all` at startup (asyncio.to_thread bridge for env.py's asyncio.run)
- **SMTP email delivery** for magic links with console fallback, app_base_url config, and bool return for graceful failure
- **Session cleanup job** at startup — expired sessions purged, non-zero count logged
- **ViewSpecService TTL cache** (300s, 64 entries) wired to model install/uninstall invalidation, reducing SPARQL overhead

### What Worked

- **Wave-based parallel execution** for Phase 20: 4 annotation plans ran in parallel, saving significant wall time. Wave model matches natural dependency structure (annotate → verify/commit).
- **Highly specified plans**: Phase 20 and 22 plans contained exact text to insert, specific file paths, and precise acceptance criteria. Executors needed minimal judgment — zero deviations.
- **Phase 21 self-created**: Phase 21 (Research Synthesis) had no plan directory at execute time. Orchestrator created the plan from ROADMAP spec and executed it without user interruption. Demonstrates robustness of the specification-driven approach.
- **3/3 phases passed verification on first attempt** with perfect scores (4/4, 6/6, 4/4). No gap closure needed.
- **Pure documentation milestone**: v2.1 had zero risk of regression — no application code changed in Phases 20-21. Phase 22 was isolated tech debt with contained blast radius.

### What Was Inefficient

- **Missing plan directory at execute time**: Phase 21 had no plan directory when `/gsd:execute-phase 21` was called. The milestone phase specification in ROADMAP said "Plans: TBD" — this should have been resolved during milestone planning, not at execution time. Orchestrator recovered gracefully but it added friction.
- **CLI `milestone complete` doesn't accomplish much**: The tool archived files but left most of the work (ROADMAP.md reorganization, PROJECT.md evolution, RETROSPECTIVE.md) to the AI. The distinction between what the CLI handles vs what the AI handles is blurry and could be better documented.
- **v2.1 milestone naming**: The ROADMAP heading said "v2.1" but STATE.md said `milestone: v1.0` (stale from v1.0 era). This caused confusion in the `gsd-tools init` output showing `milestone_version: v1.0`.

### Patterns Established

- **Decision-as-planning artifact**: Annotating RESEARCH.md files with `## Decision` + `## v2.2 Handoff` sections transforms research references into binding commitments. The handoff section's "prerequisites + first steps" pattern is repeatable.
- **Synthesis document before implementation**: DECISIONS.md is a cross-cutting synthesis that surfaces concerns invisible in per-decision RESEARCH.md files (auth scoping differences, CSS token budget). Worth creating before any multi-decision implementation milestone.
- **Phase 21 self-creation precedent**: When a plan is simple and fully specified in ROADMAP.md, the orchestrator can create the plan directory and execute without routing through `/gsd:plan-phase`. Reduces ceremony for well-understood single-artifact phases.

### Key Lessons

1. **Document the "Plans: TBD" gap earlier.** When a phase has `Plans: TBD` in ROADMAP.md at milestone creation time, flag it as a planning prerequisite before starting execution. Either plan it during milestone creation or note it explicitly in STATE.md.
2. **Verification passes predictably when plans are highly specified.** Phases with exact text, exact file paths, and binary acceptance criteria (does `## Decision` exist? does the text contain "LuceneSail"?) pass on first attempt. Under-specified plans (vague objectives, non-checkable criteria) are higher risk.
3. **Architecture decision milestones are low-risk.** Pure planning/documentation milestones with no application code changes have zero regression risk. They're good candidates for high autonomy (`--auto` flag).
4. **Cross-cutting synthesis is valuable.** The DECISIONS.md artifact (Phase 21) surfaced concerns that weren't visible in the individual RESEARCH.md files — specifically, that yasgui and wsgidav use different auth patterns, and that CSS token expansion is a prerequisite for the dockview migration. These cross-cutting concerns would have caused integration friction in v2.2 without this synthesis step.

### Cost Observations

- Model: Sonnet (inherited executor, balanced profile)
- Phases: 3 (documentation only — no code execution, no tests to run)
- All 3 phases passed verification on first attempt
- Notable: Documentation milestone runs faster than code phases — no build times, no test runs, no Docker stack needed

---

## Milestone: v2.2 — Data Discovery

**Shipped:** 2026-03-01
**Phases:** 6 (23-28) | **Plans:** 14 | **Duration:** ~1 intensive day
**Commits:** ~120+

### What Was Built

- **SPARQL Console** — Yasgui v4.5.0 CDN embed with lazy init via tab click handler, custom YASR URI formatter rendering SemPKM IRIs as teal pill links, dark mode CSS overrides, localStorage persistence
- **FTS Keyword Search** — RDF4J LuceneSail wrapping NativeStore (config:lucene.indexDir, graph-scoped via SPARQL GRAPH clause), SearchService with SPARQL magic predicates (search:matches), GET /api/search endpoint, Ctrl+K palette integration with inline SVG type icons
- **CSS Token Expansion** — 108 tokens in two-tier primitive (`--_*`) / semantic (`--color-*`, etc.) architecture; dockview-sempkm-bridge.css pattern file for v2.3 Phase A
- **VFS Read-Only** — wsgidav + a2wsgi WSGI bridge, SyncTriplestoreClient (sync httpx wrapper), SemPKMDAVProvider hierarchy (Root→Model→Type→Resource), Markdown+SHACL-frontmatter ResourceFile with TTL directory cache and threading.Lock
- **VFS Write + Auth** — SHA-256 API token model with hard-delete revocation, SemPKMWsgiAuthenticator, begin_write/end_write write path → event store, SHA-256 ETag concurrency, Settings UI with fetch()-based token display (one-time plaintext)
- **UI Polish + Integration** — chevron icon token fixes, full 4-panel HTML5 drag-reorder with insert-before/after and localStorage persistence, tab-type-aware contextual accent bar, Playwright E2E stubs for SPARQL/FTS/VFS
- **Post-ship quick tasks** — event log tabular CSS Grid, user name UUID fix, Diff/Undo button color states, SPARQL Console to Admin nav, Event Console page (/events), diff table arrow, relations collapsible rollup per predicate

### What Worked

- **Intensive single-day execution** across 6 phases: all planned + post-ship polish completed in one session. Demonstrates how high-quality v2.1 architecture decisions + DECISIONS.md handoff translate directly into fast execution with minimal rework.
- **gsd:quick for post-ship polish**: Running 7 ad-hoc quick tasks after Phase 28 (event log polish, Event Console, relations rollup) was the right pattern for small, user-visible improvements that don't fit formal phases.
- **Parallel phase planning**: Phases 23-27 were all planned before execution started, allowing waves to proceed without planning interruptions.
- **wsgidav container-first debugging**: When LuceneSail config properties differed from docs, the fix was to create a test repo via the workbench and inspect the generated config.ttl. Source-of-truth verification pattern.
- **Phase 25 CSS tokens as infrastructure**: Shipping the CSS token expansion before VFS/FTS UI surfaces ensured consistent styling across all new components. The dockview bridge CSS file is immediately useful for v2.3.

### What Was Inefficient

- **VFS write path required multiple corrections**: begin_write/end_write hook names weren't in the wsgidav docs consulted; discovered by error inspection. write_data() doesn't exist. Several file-level corrections needed across Phase 27 plans.
- **28-03 gap closure plan**: POLSH-01 chevrons and POLSH-03 accent bar had UAT failures requiring a third unplanned plan. The flex-container SVG shrink issue (CLAUDE.md) was a known pitfall but still manifested. Better pre-flight UAT checklist for icon-heavy phases would catch this earlier.
- **Phase 28 plan reordering**: E2E test files were created before the features they test were fully validated, requiring test.skip() degradation. Ideal order: validate features first, then write tests.

### Patterns Established

- **SyncTriplestoreClient pattern**: For WSGI-threaded contexts that can't use async/await (wsgidav), create a synchronous httpx.Client wrapper mirroring the async TriplestoreClient API. Reusable for any future WSGI-mounted Python service.
- **API token one-time display**: Use fetch() (not htmx) to intercept the token response and swap it into the DOM before the server truncates the plaintext. Pattern is reusable for any one-time secret display.
- **Custom DOM events for panel cross-communication**: `sempkm:tab-activated` / `sempkm:tabs-empty` custom events dispatched from workspace.js decouple the contextual panel indicator from the tab management code. Cleaner than direct function calls across JS files.
- **gsd:quick post-ship batch**: After major feature phases complete, run a batch of quick improvement tasks on main branch before archiving. Documented in STATE.md Quick Tasks table.

### Key Lessons

1. **Verify third-party config format by creating a test instance.** When LuceneSail (or any config-driven middleware) differs from docs, create a test instance via its own tooling and inspect the generated config. Beats reading docs that may be stale.
2. **Lucide SVG in flex containers requires `flex-shrink: 0`.** Documented in CLAUDE.md. Every new icon button in a flex layout needs this check in the acceptance criteria.
3. **wsgidav API requires reading source code, not just docs.** The wsgidav Python package's hook API (begin_write/end_write vs write_data) is only reliably known from the source. Add source inspection to VFS-category plan prerequisites.
4. **Post-ship quick tasks are a genuine workflow accelerator.** The 7 post-ship tasks added significant user-visible polish without any planning overhead. Prefer gsd:quick for improvements that are obviously correct and low-risk.
5. **Architecture decision documents (DECISIONS.md) have a measurable payoff.** Every v2.2 phase that had a v2.1 DECISIONS.md handoff (LuceneSail, Yasgui, wsgidav, dockview bridge) executed faster with fewer deviations than phases without handoffs.

### Cost Observations

- Model: Sonnet 4.5/4.6 (quality profile)
- All 6 phases completed with 1 gap closure (28-03)
- Post-ship: 7 quick tasks, all single-session
- Notable: DECISIONS.md from v2.1 eliminated research overhead for all 4 committed architecture decisions — each executed with confidence from day 1

---

## Milestone: v2.5 — Polish, Import & Identity

**Shipped:** 2026-03-09
**Phases:** 8 (44-51) | **Plans:** 22 | **Duration:** 3 days (2026-03-07 → 2026-03-09)
**Commits:** 184 | **Files:** 257 | **Lines:** +28,502 / -1,649

### What Was Built

- **Obsidian Import Wizard** — Full 6-step in-app wizard (upload → scan → type mapping → property mapping → preview → batch import) with SSE progress, wiki-link/tag edge resolution, two-pass import (objects then edges)
- **WebID Profiles** — Per-user Ed25519 key pairs (Fernet-encrypted), RDF profile documents (FOAF + W3C Security Vocabulary), content negotiation (Turtle/JSON-LD/HTML), `rel="me"` links for Mastodon/fediverse verification
- **IndieAuth Provider** — Full OAuth2 authorization code flow with mandatory PKCE, consent screen, token introspection, refresh token rotation, authorized apps management UI, metadata discovery endpoint
- **Spatial Canvas UX** — Per-node expand/delete/chevron controls with provenance-scoped collapse, HTML5 drag-drop from nav tree with custom MIME types, named session management (save-as, auto-restore, session index)
- **UI Polish** — CodeMirror CSS variable theming, dockview tab type icons, dynamic sidebar accent colors, capture-phase keyboard shortcuts, VFS markdown preview toggle
- **User Guide** — 27 chapters across 9 parts covering all features from v2.0-v2.5, 11 new glossary terms, screenshot capture spec

### What Worked

- **Three parallel workstreams**: UI cleanup, Obsidian import, and Identity ran independently. Phase 44 (UI), 45-47 (Obsidian), and 48-49 (Identity) had zero dependency conflicts. Documentation (Phase 50) correctly sequenced after all feature phases.
- **SSE race condition handling**: The pattern of saving import_result.json server-side and serving it via GET when the SSE broadcast has already closed solved a real timing bug in Phase 47. Reusable for any SSE-based progress workflow.
- **htmx page navigation for tool pages**: Decision to use htmx full-page navigation (not dockview tabs) for Import Vault was correct — tool pages need full-page state, not tab-scoped state.
- **Phase 51 added mid-milestone**: Spatial Canvas UX was added during execution as an informal phase. It shipped cleanly with 3 plans, demonstrating roadmap flexibility.
- **Alt-key shortcuts**: Switching from Ctrl to Alt prefix for app shortcuts resolved browser shortcut conflicts (Ctrl+J downloads, Ctrl+K address bar).

### What Was Inefficient

- **Chrome drag-drop DataTransfer restrictions**: Chrome restricts reading `dataTransfer.getData()` during dragover events (only in drop). Required a side-channel payload check pattern that took multiple iterations to discover.
- **Import wizard CSS not loading initially**: The import page CSS was in a separate file but not loaded by the base template. Required a debugging session to identify the missing stylesheet include.
- **Phase 46 plan count mismatch**: Roadmap said 3/3 plans but progress table said 2/3. Minor bookkeeping inconsistency from mid-execution plan structure changes.

### Patterns Established

- **SSE + saved result fallback**: For any long-running async operation, save the result to disk and serve it via GET endpoint as a fallback when SSE broadcast closes before client connects.
- **Custom MIME types in DnD**: Using `text/iri` and `text/label` custom MIME types in HTML5 dataTransfer provides clean data channels without parsing hacks.
- **Inline SVG constants for dynamic DOM**: When creating DOM nodes dynamically (canvas nodes), use inline SVG string constants instead of Lucide `data-lucide` attributes to avoid re-scan overhead.
- **Separate KDF salts per encryption domain**: WebID keys and LLM keys use separate Fernet key derivation domains for key compromise isolation.
- **Standalone HTML templates for public pages**: WebID profile and IndieAuth consent screen don't extend base.html — they're self-contained for external consumption.

### Key Lessons

1. **Browser DnD APIs have significant cross-browser differences.** Chrome's DataTransfer restrictions during dragover require workarounds that Firefox doesn't need. Always test DnD in both browsers.
2. **Wizard-style multi-step flows in htmx work best with htmx partials per step.** Each step is a separate template partial, auto-saved via hx-trigger="change", with step bar as a shared partial.
3. **Content negotiation is straightforward with FastAPI's Request.headers["accept"].** The Accept header parsing + ?format= query param fallback pattern is simple and spec-compliant.
4. **Ed25519 key management is simple with Python's cryptography library.** Key generation, serialization (PEM), and Fernet-encrypted storage is under 100 lines of code.
5. **Documentation phases are faster when features are already shipped.** Phase 50 (4 plans) completed in one session because all features were final — no moving target.

### Cost Observations

- Model: Quality profile (Opus for planning/verification, executor agents)
- 8 phases completed in 3 days, 22 plans
- Phase 51 added organically mid-milestone
- Notable: Obsidian import (3 phases, 8 plans) was the largest feature workstream; identity (2 phases, 5 plans) was surprisingly compact given its OAuth2 complexity

---

## Cross-Milestone Trends

### Process Evolution

| Milestone | Phases | Plans | Key Change |
|-----------|--------|-------|------------|
| v1.0 | 9 | 26 | GSD system established; all planning and execution patterns defined |
| v2.0 | 10 | 27 | Wave-based parallelization, Split.js pitfall avoidance, CSS token system |
| v2.1 | 3 | 9 | Architecture decision formalization pattern; synthesis-before-implementation |
| v2.2 | 6 | 14 | DECISIONS.md handoff payoff; gsd:quick post-ship batch; sync client wrapper for WSGI contexts |
| v2.5 | 8 | 22 | 3 parallel workstreams; SSE+fallback pattern; standalone HTML for public pages; DnD cross-browser lessons |

### Cumulative Quality

| Milestone | Verifications | Pass Rate | Gap Closures |
|-----------|--------------|-----------|--------------|
| v2.1 | 3/3 | 100% | 0 |
| v2.2 | 6/6 | 100% | 1 (28-03 gap closure for chevrons + accent bar) |
| v2.5 | 8/8 | 100% | 0 |

### Top Lessons (Verified Across Milestones)

1. **Highly specified plans pass verification on first attempt.** Binary acceptance criteria (file exists? text present? git commit found?) are better than subjective criteria (looks good? is complete?).
2. **Wave-based parallelization works best when Wave N tasks are truly independent.** Phase 20 Wave 1 ran 4 agents in parallel with no shared files — zero conflicts.
3. **Synthesis steps pay for themselves.** DECISIONS.md took ~3 minutes to produce and surfaced cross-cutting concerns that would have caused v2.2 integration friction.
4. **Architecture decisions with explicit handoffs eliminate research overhead.** Every v2.2 feature that had a v2.1 handoff (LuceneSail, Yasgui, wsgidav, dockview bridge) executed faster and with fewer deviations.
5. **Post-ship quick tasks are a genuine workflow accelerator.** Ad-hoc gsd:quick tasks after phase completion add significant user-visible polish with no planning overhead.
