# Project Knowledge

Append-only register of project-specific rules, patterns, and lessons learned.
Agents read this before every unit. Add entries when you discover something worth remembering.

## Rules

| # | Scope | Rule | Why | Added |
|---|-------|------|-----|-------|

## Patterns

| # | Pattern | Where | Notes |
|---|---------|-------|-------|
| 1 | SPARQL date comparison in rdflib: use `STRDT(SUBSTR(STR(NOW()), 1, 10), xsd:date)` instead of `xsd:date(NOW())` | `models/basic-pkm/rules/basic-pkm.ttl` | rdflib does not support `xsd:date()` cast — produces empty results. The STRDT+SUBSTR approach constructs a proper typed xsd:date literal that compares correctly with xsd:date values in FILTER. |

## Lessons Learned

| # | What Happened | Root Cause | Fix | Scope |
|---|--------------|------------|-----|-------|
| K001 | SHACL-AF stale-contact rule with `?today - "P90D"^^xsd:dayTimeDuration` doesn't work in rdflib's SPARQL engine | rdflib does not implement xsd:dayTimeDuration subtraction from xsd:date | Use `NOT EXISTS` for zero-interaction check in SHACL rules; use SavedQuery with direct date comparison for time-windowed checks | models/crm/rules, any SHACL-AF SPARQL using date arithmetic |
| K002 | Seed data `dcterms:created` with `xsd:dateTime` caused spurious `sh:Violation` when SHACL shape constrains that property to `xsd:date` | SHACL `sh:datatype xsd:date` is strict — `xsd:dateTime` values fail the check even though both represent temporal data | Match the seed data's `@type` to whatever the SHACL shape's `sh:datatype` declares for that property. Check shapes before authoring seed data. | Any model's seed data where shapes constrain date fields |

## E2E Test: SPARQL API Does Not Support UPDATE/DELETE

**Discovery date:** 2026-03-17  
**Context:** T02 E2E Playwright test for mental model expansion  

The `/api/sparql` endpoint (both GET and POST) only executes read queries (SELECT, ASK, CONSTRUCT, DESCRIBE). It does NOT support SPARQL UPDATE operations (INSERT, DELETE). Sending a DELETE query returns `400 Malformed SPARQL query`.

The triplestore client (`app.triplestore.client.TriplestoreClient`) has an `update()` method that works, but it's not exposed through any HTTP API endpoint.

**Impact:** E2E tests cannot clean up triplestore data (seed instances, created objects) via the API. Model uninstall is blocked when seed data exists because `check_user_data_exists()` queries `urn:sempkm:current` graph and finds instances.

**Workaround:** Make cleanup best-effort with skip-if-already-installed logic for idempotent reruns. For a proper fix, add a SPARQL UPDATE endpoint or a force-uninstall admin API.

## E2E Test: Docker Test Stack Volume Mounts From Worktree

**Discovery date:** 2026-03-17  
**Context:** T02 E2E Playwright test for mental model expansion  

The Docker test stack (docker-compose.test.yml) started from `.gsd/worktrees/M007/` mounts volumes from that worktree path, not from the main tree at `/home/james/Code/SemPKM/`. For example, `./models:/app/models:ro` resolves to `.gsd/worktrees/M007/models/`.

If model directories only exist in the main tree (e.g., after a T01 task copies them there), they must also be copied to the worktree's `models/` directory for the Docker container to see them.

**Check:** `docker inspect <container> --format '{{json .Mounts}}'` shows the resolved source paths.

---

### SHACL Property Shapes: Blank Nodes vs Typed Nodes

**Context:** `ShapesService.get_labels_for_predicates()` and `get_helptext_for_predicates()` iterate property shape nodes to resolve predicate metadata.

**Gotcha:** The installed model shapes (e.g., basic-pkm) use **inline blank nodes** attached via `sh:property` on NodeShapes. These blank nodes do NOT carry explicit `rdf:type sh:PropertyShape` triples. Only iterating `graph.subjects(RDF.type, SH.PropertyShape)` finds zero shapes on real data.

**Fix:** Always iterate both sources:
```python
prop_nodes = set(graph.subjects(RDF.type, SH.PropertyShape))  # typed
for obj in graph.objects(predicate=SH.property):               # inline
    prop_nodes.add(obj)
```

**Diagnostic:** If `get_labels_for_predicates()` returns empty dict on known predicates like `dcterms:title`, check the graph for PropertyShape types vs sh:property blank node count.
