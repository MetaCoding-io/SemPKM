# Roadmap: SemPKM

## Milestones

- ✅ **v1.0 MVP** — Phases 1-9 (shipped 2026-02-23) — [Full details](milestones/v1.0-ROADMAP.md)
- ✅ **v2.0 Tighten Web UI** — Phases 10-19 (shipped 2026-03-01) — [Full details](milestones/v2.0-ROADMAP.md)
- 📋 **v2.1 Architecture Decision Gate** — Phases 20-22 (planned)

## Phases

<details>
<summary>✅ v1.0 MVP (Phases 1-9) — SHIPPED 2026-02-23</summary>

- [x] Phase 1: Core Data Foundation (4/4 plans) — completed 2026-02-21
- [x] Phase 2: Semantic Services (2/2 plans) — completed 2026-02-21
- [x] Phase 3: Mental Model System (3/3 plans) — completed 2026-02-22
- [x] Phase 4: Admin Shell and Object Creation (6/6 plans) — completed 2026-02-22
- [x] Phase 5: Data Browsing and Visualization (3/3 plans) — completed 2026-02-22
- [x] Phase 6: User and Team Management (4/4 plans) — completed 2026-02-22
- [x] Phase 7: Route Protection and Provenance (2/2 plans) — completed 2026-02-23
- [x] Phase 8: Integration Bug Fixes (1/1 plan) — completed 2026-02-23
- [x] Phase 9: Provenance and Redirect Micro-Fixes (1/1 plan) — completed 2026-02-23

**26 plans, ~354 tasks, 43/43 requirements satisfied**

</details>

<details>
<summary>✅ v2.0 Tighten Web UI (Phases 10-19) — SHIPPED 2026-03-01</summary>

- [x] Phase 10: Bug Fixes and Cleanup Architecture (3/3 plans) — completed 2026-02-23
- [x] Phase 11: Read-Only Object View (2/2 plans) — completed 2026-02-23
- [x] Phase 12: Sidebar and Navigation (2/2 plans) — completed 2026-02-23
- [x] Phase 13: Dark Mode and Visual Polish (4/4 plans) — completed 2026-02-24
- [x] Phase 14: Split Panes and Bottom Panel (3/3 plans) — completed 2026-02-24
- [x] Phase 15: Settings System and Node Type Icons (3/3 plans) — completed 2026-02-24
- [x] Phase 16: Event Log Explorer (3/3 plans) — completed 2026-02-24
- [x] Phase 17: LLM Connection Configuration (2/2 plans) — completed 2026-02-24
- [x] Phase 18: Tutorials and Documentation (2/2 plans) — completed 2026-02-25
- [x] Phase 19: Bug Fixes and E2E Test Hardening (3/3 plans) — completed 2026-02-27

**27 plans, 53 tasks, 46/46 requirements satisfied**

</details>

### 📋 v2.1 Architecture Decision Gate (Phases 20-22)

- [ ] **Phase 20: Architecture Decision Commit** - Annotate and commit all 4 research tracks as finalized architectural decisions
- [ ] **Phase 21: Research Synthesis** - Produce DECISIONS.md consolidating all decisions with v2.2 implementation guidance
- [x] **Phase 22: Tech Debt Sprint** - Implement 4 medium-priority tech debt items (Alembic, SMTP, session cleanup, ViewSpec cache) (completed 2026-03-01)

## Phase Details

### Phase 20: Architecture Decision Commit
**Goal**: All 4 completed research tracks are formalized as committed architectural decisions — each RESEARCH.md annotated with the chosen approach, rationale, and v2.2 implementation handoff
**Depends on**: Nothing (research already complete in .planning/research/phase-2{0-3}-*)
**Requirements**: DEC-01, DEC-02, DEC-03, DEC-04
**Success Criteria** (what must be TRUE):
  1. Each of the 4 RESEARCH.md files has a "Decision" section at the top stating the chosen approach in one clear sentence
  2. Each RESEARCH.md records the rationale for the chosen approach and explicitly rules out the alternatives considered
  3. Each RESEARCH.md contains a "v2.2 Handoff" section listing concrete implementation prerequisites and first steps
  4. A reviewer reading any single RESEARCH.md can determine the committed approach without reading the others
**Plans**: 5 plans
Plans:
- [ ] 20-01-PLAN.md — Annotate FTS/Vector RESEARCH.md with Decision + v2.2 Handoff (DEC-01)
- [ ] 20-02-PLAN.md — Annotate SPARQL UI RESEARCH.md with Decision + v2.2 Handoff (DEC-02)
- [ ] 20-03-PLAN.md — Annotate VFS RESEARCH.md with Decision + v2.2 Handoff (DEC-03)
- [ ] 20-04-PLAN.md — Annotate UI Shell RESEARCH.md with Decision + v2.2 Handoff (DEC-04)
- [ ] 20-05-PLAN.md — Verify, commit all 4 decisions, update planning metadata

### Phase 21: Research Synthesis
**Goal**: A single DECISIONS.md exists that consolidates all 4 architectural decisions, surfaces cross-cutting concerns, and provides a v2.2 phase structure with implementation order
**Depends on**: Phase 20
**Requirements**: SYN-01
**Success Criteria** (what must be TRUE):
  1. DECISIONS.md exists at .planning/DECISIONS.md and opens with a summary table of all 4 decisions (technology chosen, status, target milestone)
  2. DECISIONS.md has a cross-cutting concerns section covering shared infrastructure (auth scoping, SPARQL query patterns, CSS token usage)
  3. DECISIONS.md proposes a concrete v2.2 phase structure — named phases with requirements and sequencing rationale
  4. DECISIONS.md includes a tech debt schedule mapping TECH items to target milestones (those not in v2.1 get a home)
**Plans**: TBD

### Phase 22: Tech Debt Sprint
**Goal**: Four medium-priority tech debt items are resolved — the application uses Alembic for schema migrations, sends real emails for magic links, purges expired sessions, and caches view spec lookups
**Depends on**: Nothing (independent of Phases 20-21; can run in parallel)
**Requirements**: TECH-01, TECH-02, TECH-03, TECH-04
**Success Criteria** (what must be TRUE):
  1. Application startup runs Alembic migrations instead of create_all; adding a new column to the auth schema requires only a migration file, not a manual DB drop
  2. Magic link emails arrive in a real inbox when SMTP settings are configured; the console fallback still works when SMTP is not configured
  3. Expired sessions are not present in the auth database after startup; the cleanup runs without manual intervention
  4. A view spec lookup that was recently resolved does not trigger a SPARQL query to the triplestore (TTL cache hit is observable in logs or metrics)
**Plans**: 3 plans
Plans:
- [ ] 22-01-PLAN.md — Alembic migration runner at startup + session cleanup (TECH-01, TECH-03)
- [ ] 22-02-PLAN.md — SMTP email delivery for magic links (TECH-02)
- [ ] 22-03-PLAN.md — ViewSpecService TTL cache + invalidation wiring (TECH-04)

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Core Data Foundation | v1.0 | 4/4 | Complete | 2026-02-21 |
| 2. Semantic Services | v1.0 | 2/2 | Complete | 2026-02-21 |
| 3. Mental Model System | v1.0 | 3/3 | Complete | 2026-02-22 |
| 4. Admin Shell and Object Creation | v1.0 | 6/6 | Complete | 2026-02-22 |
| 5. Data Browsing and Visualization | v1.0 | 3/3 | Complete | 2026-02-22 |
| 6. User and Team Management | v1.0 | 4/4 | Complete | 2026-02-22 |
| 7. Route Protection and Provenance | v1.0 | 2/2 | Complete | 2026-02-23 |
| 8. Integration Bug Fixes | v1.0 | 1/1 | Complete | 2026-02-23 |
| 9. Provenance and Redirect Micro-Fixes | v1.0 | 1/1 | Complete | 2026-02-23 |
| 10. Bug Fixes and Cleanup Architecture | v2.0 | 3/3 | Complete | 2026-02-23 |
| 11. Read-Only Object View | v2.0 | 2/2 | Complete | 2026-02-23 |
| 12. Sidebar and Navigation | v2.0 | 2/2 | Complete | 2026-02-23 |
| 13. Dark Mode and Visual Polish | v2.0 | 4/4 | Complete | 2026-02-24 |
| 14. Split Panes and Bottom Panel | v2.0 | 3/3 | Complete | 2026-02-24 |
| 15. Settings System and Node Type Icons | v2.0 | 3/3 | Complete | 2026-02-24 |
| 16. Event Log Explorer | v2.0 | 3/3 | Complete | 2026-02-24 |
| 17. LLM Connection Configuration | v2.0 | 2/2 | Complete | 2026-02-24 |
| 18. Tutorials and Documentation | v2.0 | 2/2 | Complete | 2026-02-25 |
| 19. Bug Fixes and E2E Test Hardening | v2.0 | 3/3 | Complete | 2026-02-27 |
| 20. Architecture Decision Commit | 2/5 | In Progress|  | - |
| 21. Research Synthesis | v2.1 | 0/1 | Not started | - |
| 22. Tech Debt Sprint | 3/3 | Complete   | 2026-03-01 | - |

---
*Roadmap created: 2026-02-21*
*v1.0 archived: 2026-02-23*
*v2.0 archived: 2026-03-01*
*v2.1 roadmap added: 2026-03-01*
