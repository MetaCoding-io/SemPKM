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
