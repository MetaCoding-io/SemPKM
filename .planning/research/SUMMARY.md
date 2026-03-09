# Research Summary: SemPKM v2.6 Power User & Collaboration

**Domain:** Semantic PKM platform -- SPARQL power tools, RDF federation/sync, custom VFS, UI improvements
**Researched:** 2026-03-09
**Overall confidence:** MEDIUM (SPARQL/VFS/UI work HIGH; federation protocol integration MEDIUM)

## Executive Summary

SemPKM v2.6 targets eight feature areas across five capability domains: SPARQL Interface enhancements, Collaboration & Federation, User Custom VFS (MountSpec), UI polish, and bug fixes. The existing three-layer architecture (htmx frontend / FastAPI backend / RDF4J triplestore) accommodates all new features without structural changes and without any new dependencies.

The SPARQL Interface enhancements are the highest-value, lowest-risk work. Permission enforcement is a simple guard layer on the existing `sparql/router.py` -- the `all_graphs` bypass must be gated behind `require_role("owner")` immediately (currently any authenticated user can access event data). Autocomplete requires a cached schema endpoint that Yasgui's custom completer queries once on init, avoiding per-keystroke SPARQL queries that would flood RDF4J. Server-side history and saved queries use SQL tables (high-churn CRUD data, not knowledge), requiring Alembic migrations. The killer differentiator is "named queries as views" -- promoting a saved SPARQL query to a ViewSpec alongside model-defined views.

Federation is the highest-complexity, highest-risk domain. RDF Patch serialization maps cleanly onto the existing EventStore's `Operation` dataclass (which already has `materialize_inserts` and `materialize_deletes` lists). The critical constraint: all federation writes MUST go through `EventStore.commit()` to preserve the audit trail, trigger SHACL validation, and fire webhooks. Sync requires infinite-loop prevention via `syncSource` tagging on federation-originated events. LDN provides standards-based notification exchange with rate limiting and peer authentication to prevent inbox spam.

User Custom VFS (MountSpec) extends the current fixed `/{model}/{type}/{object}.md` hierarchy with five user-defined directory strategies (ByType, ByDate, ByProperty, Flat, ByTag). The main architectural risk is multi-path aliasing: the same object appearing at multiple paths across strategies creates write conflicts. Solution: exactly one strategy per mount is writable (canonical path); others are read-only aliases.

No new Python or JavaScript dependencies are required. Three new SQL tables via Alembic. Four new triplestore named graph patterns. All UI improvements are htmx + vanilla JS + CSS.

## Key Findings

**Stack:** Zero new dependencies. All features build on existing rdflib, httpx, cryptography, SQLAlchemy, wsgidav, Yasgui CDN. Three SQL tables (sparql_query_history, saved_sparql_queries, federation_peers). Four new named graph patterns (user views, user mounts, sync conflicts, LDN inbox).

**Architecture:** New `federation/` package (4 modules: patch, sync, ldn, auth). Extended `sparql/` module (autocomplete, history, saved queries). Extended `vfs/` module (mounts, strategies, SHACL frontmatter writes). All other changes are modifications to existing modules.

**Critical pitfalls:**
1. `all_graphs=true` bypass available to all users -- gate behind owner role immediately (one-line fix)
2. Federation sync MUST go through EventStore -- bypassing creates ghost triples with no audit trail
3. MountSpec multi-path aliasing -- designate one canonical writable path per mount; others read-only
4. WebID federation trusts self-asserted documents -- require explicit trusted instance allowlist
5. SPARQL saved queries execute with runner's permissions -- never store execution params in saved queries

## Implications for Roadmap

Based on research, suggested phase structure:

1. **Bug Fixes & Security** - SPARQL permissions, event log fixes, lint dashboard fixes
   - Addresses: Security gap (all_graphs bypass), known regressions
   - Avoids: Shipping new features on broken foundations

2. **SPARQL Power User** - Autocomplete, server-side history, saved queries, IRI pills enhancement
   - Addresses: Core SPARQL Interface table stakes
   - Avoids: Pitfall 6 (autocomplete flooding) via cached schema endpoint

3. **SPARQL Advanced** - Named queries as views, shared queries
   - Addresses: Key differentiators, foundation for collaboration
   - Avoids: Pitfall 5 (permission escalation via shared queries), Pitfall 10 (view cache inconsistency)

4. **Object Browser & VFS Browser UI** - Refresh/plus icons, multi-select, edge inspector, view filtering, breadcrumbs, preview pane
   - Addresses: Daily workflow friction, VFS browser completeness
   - Avoids: Pitfall 11 (multi-select race conditions) via single EventStore.commit()

5. **VFS MountSpec** - Vocabulary, service, strategies, SHACL frontmatter writes, management UI
   - Addresses: User custom VFS, markdown editor integration
   - Avoids: Pitfall 3 (multi-path aliasing) via canonical-path-is-writable rule

6. **Spatial Canvas UX** - Improvements TBD during phase planning
   - Addresses: Canvas usability
   - Avoids: Isolated module, low cross-cutting risk

7. **Federation** - RDF Patch serializer, federation auth, sync engine, LDN inbox/sender, collaboration UI
   - Addresses: Multi-instance collaboration
   - Avoids: Pitfall 2 (event store bypass) via mandatory EventStore.commit(), Pitfall 4 (WebID trust) via allowlist

**Phase ordering rationale:**
- Security and bug fixes first (group 1) establishes correctness before new features
- SPARQL enhancements (groups 2-3) before federation because shared queries are a prerequisite for meaningful collaboration, and these features have the best value-to-risk ratio
- UI improvements (group 4) can proceed in parallel with MountSpec backend work
- VFS MountSpec (group 5) before federation because it is user-facing with lower risk
- Federation last (group 7) because it has the highest complexity, the lowest urgency for personal-first deployments, and depends on WebID infrastructure already shipped in v2.5

**Research flags for phases:**
- Phase 7 (Federation): Needs deeper research on HTTP Signatures (RFC 9421) implementation in Python and sync conflict resolution UX
- Phase 5 (MountSpec): Needs careful design of path template grammar, sanitization rules, and SHACL-to-frontmatter reverse mapping completeness
- Phase 3 (Named Queries as Views): Needs design for ViewSpec cache separation (user views vs model views)
- Phases 1-2, 4, 6: Standard patterns, unlikely to need additional research

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Zero new deps; existing tools cover all needs; verified via codebase analysis |
| SPARQL Features | HIGH | Direct extension of existing sparql/ module; well-understood patterns |
| Object Browser UI | HIGH | Template/CSS/JS changes with clear scope and existing patterns |
| VFS MountSpec | MEDIUM | wsgidav collection subclass pattern is proven; directory strategy design and SHACL reverse mapping need validation |
| Federation | MEDIUM | No prior federation art in codebase; HTTP Signatures and sync loop prevention need implementation validation |
| Event Log/Lint Fixes | HIGH | Template-level fixes with identifiable bugs |

## Gaps to Address

- HTTP Signatures (RFC 9421) implementation details for Python -- validate Ed25519 signing/verification flow with httpx
- Yasgui custom autocompleter API specifics for @zazuko/yasgui v4.5.0 -- verify CDN version's completer registration method
- RDF Patch format edge cases -- blank nodes, language-tagged literals, named graph patches in rdflib serializer vs manual generation
- Sync conflict resolution UX -- how to present and resolve last-writer-wins conflicts in the collaboration UI
- SHACL frontmatter reverse mapping -- which SHACL constraints meaningfully map to YAML frontmatter keys; multi-valued properties, IRI references, typed literals
- MountSpec path template sanitization -- grammar for template variables, path traversal prevention, filename collision handling

## Sources

- `.planning/PROJECT.md` -- v2.6 milestone definition and constraints
- `.planning/research/STACK.md` -- technology stack analysis (zero new deps confirmed)
- `.planning/research/FEATURES.md` -- feature landscape with 11 table stakes, 12 differentiators, 7 anti-features
- `.planning/research/PITFALLS.md` -- 15 domain pitfalls with prevention strategies
- `.planning/research/ARCHITECTURE.md` -- integration architecture with component boundaries and data flows
- [RDF Patch specification](https://afs.github.io/rdf-patch/)
- [W3C Linked Data Notifications](https://www.w3.org/TR/ldn/)
- [Yasgui documentation (Triply)](https://docs.triply.cc/yasgui/)
- [W3C Linked Data Patch Format](https://www.w3.org/TR/ldpatch/)

---
*Research completed: 2026-03-09*
*Ready for roadmap: yes*
