# Quick Task 24: Create PPV Mental Model

## Goal
Translate August Bradley's Pillars, Pipelines & Vaults (PPV) productivity system from research TTL into a full SemPKM model package.

## Source Material
- `.planning/research/ppv-ontology.ttl` — 1206-line RDFS/OWL/SHACL ontology

## Design Decisions

### Scope: Full PPV (all 10 types)
- **Hierarchy chain:** Pillar, ValueGoal, GoalOutcome, Project, ActionItem
- **Review cycle:** WeeklyReview, MonthlyReview, QuarterlyReview, YearlyReview
- **Grouping:** PillarGroup

### Vocabulary: Hybrid
- **Standard vocabs** for common properties: `dcterms:title`, `dcterms:description`, `schema:startDate`, `schema:endDate`, `dcterms:created`
- **PPV namespace** (`urn:sempkm:model:ppv:`) for domain-specific: status, priority, pillarGroup, doDate, energy, context, focusObjective, cycle, progress, done, etc.

### Views: Full Dashboard Set (5+ views)
1. **Life Dashboard** — Pillar overview with hierarchy rollup stats
2. **Goals Overview** — ValueGoals + GoalOutcomes with progress
3. **Projects Board** — Projects with status/priority/dates
4. **Action Items** — Filterable by status/priority/context/energy
5. **Review Calendar** — Reviews by cycle type
6. **Hierarchy Graph** — Full chain visualization

### Seed Data: Rich Example Set
- 3 pillars (e.g., Health & Fitness, Career, Relationships)
- 2-3 value goals per pillar
- Goal outcomes, projects, action items cascading down
- Sample review entities (1 weekly, 1 monthly)

## Reference Model
- `models/basic-pkm/` — packaging format, manifest schema, JSON-LD conventions
