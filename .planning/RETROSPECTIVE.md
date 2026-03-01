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

## Cross-Milestone Trends

### Process Evolution

| Milestone | Phases | Plans | Key Change |
|-----------|--------|-------|------------|
| v1.0 | 9 | 26 | GSD system established; all planning and execution patterns defined |
| v2.0 | 10 | 27 | Wave-based parallelization, Split.js pitfall avoidance, CSS token system |
| v2.1 | 3 | 9 | Architecture decision formalization pattern; synthesis-before-implementation |

### Cumulative Quality

| Milestone | Verifications | Pass Rate | Gap Closures |
|-----------|--------------|-----------|--------------|
| v2.1 | 3/3 | 100% | 0 |

### Top Lessons (Verified Across Milestones)

1. **Highly specified plans pass verification on first attempt.** Binary acceptance criteria (file exists? text present? git commit found?) are better than subjective criteria (looks good? is complete?).
2. **Wave-based parallelization works best when Wave N tasks are truly independent.** Phase 20 Wave 1 ran 4 agents in parallel with no shared files — zero conflicts.
3. **Synthesis steps pay for themselves.** DECISIONS.md took ~3 minutes to produce and surfaced cross-cutting concerns that would have caused v2.2 integration friction.
