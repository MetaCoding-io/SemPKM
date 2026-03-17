---
estimated_steps: 6
estimated_files: 1
---

# T02: Add inference and validation rules for Tasks

**Slice:** S01 — basic-pkm v2 — Task & Milestone Types
**Milestone:** M011

## Description

Add SHACL-AF inference rules and SHACL SPARQLConstraint validation rules to the basic-pkm rules file. This task addresses the highest-risk item in the slice: the overdue-task SPARQLConstraint that requires date arithmetic in SPARQL.

Key decisions driving this implementation:
- **D153**: Validation rules use sh:sparql SPARQLConstraint on separate NodeShapes (not mixed with inference SPARQLRule shapes). sh:severity goes on the parent NodeShape.
- **D154**: Seed data pre-populates both sides, so inference produces 0 new triples for seed. But the rules must still work for user-created data where only one side exists.

## Steps

1. **Read the existing rules file** at `models/basic-pkm/rules/basic-pkm.ttl` to understand the pattern. It already has:
   - `bpkm:ProjectRelatedNoteRule` (sh:SPARQLRule on sh:NodeShape targeting bpkm:Note)
   - `bpkm:PrefixDeclarations` (sh:declare block)

2. **Add prefix declarations** to the existing `bpkm:PrefixDeclarations` block — add `xsd:` and `dcterms:` namespace declarations (needed for date comparison in SPARQL):
   ```turtle
   sh:declare [
       sh:prefix "xsd" ;
       sh:namespace "http://www.w3.org/2001/XMLSchema#"^^xsd:anyURI ;
   ] ,
   [
       sh:prefix "dcterms" ;
       sh:namespace "http://purl.org/dc/terms/"^^xsd:anyURI ;
   ] .
   ```

3. **Add TaskProjectDenormRule** — inference rule that derives `bpkm:taskProject` on a Task from its Milestone's project:
   ```turtle
   bpkm:TaskProjectDenormRule
       a sh:NodeShape ;
       sh:targetClass bpkm:Task ;
       sh:rule [
           a sh:SPARQLRule ;
           sh:order 1 ;
           rdfs:label "Derive task project from milestone" ;
           sh:prefixes bpkm:PrefixDeclarations ;
           sh:construct """
               CONSTRUCT { $this bpkm:taskProject ?project . }
               WHERE {
                   $this bpkm:milestone ?ms .
                   ?ms bpkm:milestoneProject ?project .
                   FILTER NOT EXISTS { $this bpkm:taskProject ?existingProject }
               }
           """ ;
       ] .
   ```

4. **Add owl:inverseOf inference rules** — since the platform handles owl:inverseOf via the entailment engine (entailment_defaults.owl_inverseOf: true in manifest), we do NOT need to duplicate inverse inference in rules. The existing engine handles `taskProject↔hasProjectTasks`, `milestone↔hasTasks`, `milestoneProject↔hasMilestones`, `assignedTo↔hasAssignedTask` automatically. Confirm this by checking that `entailment_defaults.owl_inverseOf: true` is in the manifest (it already is).

5. **Add OverdueTaskValidation** — SPARQLConstraint on a SEPARATE NodeShape (D153) with sh:severity sh:Warning. This shape ONLY does validation, no inference:
   ```turtle
   bpkm:OverdueTaskValidationShape
       a sh:NodeShape ;
       sh:targetClass bpkm:Task ;
       sh:severity sh:Warning ;
       sh:sparql [
           a sh:SPARQLConstraint ;
           sh:message "Task is overdue: due date has passed but task is not done or cancelled." ;
           sh:prefixes bpkm:PrefixDeclarations ;
           sh:select """
               SELECT $this ?dueDate ?status
               WHERE {
                   $this bpkm:dueDate ?dueDate .
                   $this bpkm:taskStatus ?status .
                   FILTER (?status IN ("todo", "in-progress", "blocked"))
                   FILTER (?dueDate < xsd:date(NOW()))
               }
           """ ;
       ] .
   ```
   Note: `xsd:date(NOW())` converts the current dateTime to a date for comparison with xsd:date values. If pyshacl doesn't support this cast, fall back to string comparison or `BIND(xsd:date(NOW()) AS ?today)`.

6. **Verify** the rules file parses:
   ```bash
   cd /home/james/Code/SemPKM
   python -c "from rdflib import Graph; g=Graph(); g.parse('models/basic-pkm/rules/basic-pkm.ttl', format='turtle'); print(f'Rules: {len(g)} triples')"
   ```

## Must-Haves

- [ ] TaskProjectDenormRule: SPARQL inference rule deriving taskProject from milestone's project
- [ ] OverdueTaskValidationShape: separate NodeShape (D153) with sh:severity sh:Warning
- [ ] SPARQLConstraint uses date comparison (dueDate < today) for tasks with status todo/in-progress/blocked
- [ ] sh:severity sh:Warning on the NodeShape (NOT on the SPARQLConstraint node) per D153
- [ ] PrefixDeclarations extended with xsd: and dcterms: namespaces
- [ ] Rules file parses as valid Turtle
- [ ] Existing ProjectRelatedNoteRule preserved unchanged

## Verification

- `python -c "from rdflib import Graph; g=Graph(); g.parse('models/basic-pkm/rules/basic-pkm.ttl', format='turtle'); print(f'{len(g)} triples')"` — succeeds without error
- Count NodeShapes: should be 3 (original ProjectRelatedNoteRule + TaskProjectDenormRule + OverdueTaskValidationShape)
- Verify sh:severity placement: `python -c "from rdflib import Graph, URIRef; g=Graph(); g.parse('models/basic-pkm/rules/basic-pkm.ttl', format='turtle'); sev=list(g.triples((None, URIRef('http://www.w3.org/ns/shacl#severity'), None))); print(f'severity triples: {len(sev)}'); assert len(sev)==1"` — exactly one severity triple, on the validation shape

## Inputs

- `models/basic-pkm/rules/basic-pkm.ttl` — existing v1.3 rules with ProjectRelatedNoteRule and PrefixDeclarations
- T01 output: ontology has `bpkm:Task`, `bpkm:Milestone`, `bpkm:taskProject`, `bpkm:milestone`, `bpkm:milestoneProject`, `bpkm:taskStatus`, `bpkm:dueDate` property IRIs

## Observability Impact

- **Rules triple count** increases from ~14 to ~35 — verifiable via `python -c "from rdflib import Graph; g=Graph(); g.parse('models/basic-pkm/rules/basic-pkm.ttl', format='turtle'); print(len(g))"`
- **NodeShape count in rules** goes from 1 to 3 — each inspectable by role: ProjectRelatedNoteRule (inference), TaskProjectDenormRule (inference), OverdueTaskValidationShape (validation)
- **pyshacl validation** now produces sh:Warning for overdue tasks — detectable in validation results graph via `SH.resultSeverity == SH.Warning` and source shape `bpkm:OverdueTaskValidationShape`
- **Failure shapes**: rdflib Turtle parse errors surface via Python tracebacks; pyshacl constraint failures show focus node, source shape, and message in results text

## Expected Output

- `models/basic-pkm/rules/basic-pkm.ttl` — expanded with TaskProjectDenormRule inference shape and OverdueTaskValidationShape validation shape, extended PrefixDeclarations
