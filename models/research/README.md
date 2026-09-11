# Research Workflow

**Model ID:** `research` · **Namespace:** `urn:sempkm:model:research:` · **Prefix:** `res:`

The Research Workflow model supports academic and research knowledge management. It tracks
**Papers**, extracts **Claims**, links **Evidence**, constructs **Arguments**, and manages
**Research Questions** — all with confidence tracking and evidence quality assessment.
SHACL-AF rules surface unsupported and contested claims automatically.

## Types

### Paper

An academic paper or publication.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| Title | string | ✓ | Full title of the paper |
| Authors | string | | Author names (comma-separated) |
| Year | gYear | | Publication year |
| Venue | string | | Journal, conference, or publication venue |
| DOI | URI | | Digital Object Identifier |
| Paper Type | enum | | `journal-article`, `conference-paper`, `preprint`, `book-chapter`, `thesis`, `report`, `other` |
| Date Added | date | | When the paper entered your library |
| Abstract | string | | Abstract or summary |
| Cites | → Paper | | Papers this paper references |
| Cited By | → Paper | | Papers that cite this paper (inverse) |
| Has Claims | → Claim | | Claims extracted from this paper |

### Claim

A specific assertion or proposition extracted from a paper, with a confidence level.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| Statement | string | ✓ | The assertion text |
| Confidence | enum | | `established`, `supported`, `contested`, `speculative`, `refuted` |
| Rationale | string | | Justification for the confidence assessment |
| Date Added | date | | When the claim was recorded |
| Extracted From | → Paper | | The paper this claim came from |
| Corroborates | → Claim | | Claims that say the same thing from different sources |
| Contradicts | → Claim | | Claims that oppose this one |
| Depends On | → Claim | | Claims this one logically depends on |
| Supported By | → Evidence | | Evidence that supports this claim |
| Refuted By | → Evidence | | Evidence that refutes this claim |
| Addressed By | → Argument | | Arguments that incorporate this claim |

### Evidence

Empirical data, experimental results, or observations that support or refute claims.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| Description | string | ✓ | What this evidence shows |
| Evidence Type | enum | | `empirical-data`, `statistical-finding`, `case-study`, `expert-opinion`, `logical-argument`, `observation`, `quote` |
| Source | string | | Citation or reference (e.g., "Table 3, p. 42") |
| Methodology | string | | Research methodology used |
| Strength | enum | | `strong`, `moderate`, `weak`, `anecdotal`, `preliminary` |
| Date Added | date | | When the evidence was recorded |
| Supports | → Claim | | Claims this evidence supports |
| Refutes | → Claim | | Claims this evidence refutes |
| From Paper | → Paper | | The paper this evidence originates from |

### ResearchQuestion

An open question driving your investigation.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| Question | string | ✓ | The research question text |
| Status | enum | | `open`, `partially-answered`, `answered`, `abandoned` |
| Context | string | | Background or motivation |
| Significance | string | | Why this question matters |
| Date Added | date | | When the question was posed |
| Has Arguments | → Argument | | Arguments that address this question |

### Argument

A structured reasoning unit that synthesizes claims and evidence to address a research question.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| Thesis | string | ✓ | The central thesis |
| Argument Type | enum | | `literature-review`, `position-paper`, `analysis`, `synthesis`, `rebuttal` |
| Summary | string | | Brief summary of the reasoning |
| Date Added | date | | When the argument was drafted |
| Addresses | → ResearchQuestion | | The research question being answered |
| Uses Claims | → Claim | | Claims used as premises |
| Uses Evidence | → Evidence | | Evidence incorporated in the argument |

## Evidence tracking

Each Claim can accumulate multiple Evidence objects. Evidence has both a **type** (what kind of
data it is) and a **strength** (how compelling it is). Evidence links to claims via `supports`
(confirming) or `refutes` (challenging). When a claim has both supporting and refuting evidence,
the rules flag it as contested.

## Relationships

```
Paper ──cites──▸ Paper (inverse: citedBy)
Paper ──hasClaim──▸ Claim (inverse: extractedFrom)
Claim ──corroborates──▸ Claim
Claim ──contradicts──▸ Claim
Claim ──dependsOn──▸ Claim
Evidence ──supports──▸ Claim (inverse: supportedBy)
Evidence ──refutes──▸ Claim (inverse: refutedBy)
Evidence ──fromPaper──▸ Paper
Argument ──addresses──▸ ResearchQuestion (inverse: hasArgument)
Argument ──usesClaim──▸ Claim (inverse: addressedBy)
Argument ──usesEvidence──▸ Evidence
```

## Views and saved queries

Table views for every type, plus the **Evidence Map** graph on Claims. Saved queries:

| Query | Description |
|-------|-------------|
| Unsupported Claims | Claims with no linked evidence |
| Contested Claims | Claims with both supporting and refuting evidence |
| Research Gaps | Open research questions with no arguments |
| Orphan Evidence | Evidence not linked to any claim |
| High Confidence Claims | Claims marked as `established` or `supported` |
| Citation Network | Graph of paper-to-paper citation links |
| All Papers with Claim Counts | Paper table with count of extracted claims |
| Evidence Map | Graph of claims and their evidence connections |

## Validation rules

| Rule | Severity | Message |
|------|----------|---------|
| Unsupported claim | Warning | "Claim marked as {confidence} but has no supporting evidence." |
| Contested claim | Info | "This claim has conflicting evidence — review the argument." |
| Orphan evidence | Warning | "This evidence isn't linked to any claim." |
| Unanswered question | Info | "This research question has no arguments yet." |
| Claim without rationale | Info | "Claim has no rationale. Consider explaining why you believe this." |

## Installation

Go to **Admin > Models**, pick **Research Workflow** from the bundled catalog (or enter the path
`/app/models/research`) and click **Install**. The five types appear in the Explorer sidebar;
seed data includes an unsupported claim so the warning rule has something to flag.

## Recommended dashboards

Use a **sidebar-main** layout:

- **Sidebar:** embed the "Unsupported Claims" saved query — claims that need evidence are your highest-priority research gap.
- **Main:** embed the Evidence Map graph view to see how evidence connects to claims.

For a deeper overview, create a **grid-2x2** dashboard: Unsupported Claims (top-left), Contested
Claims (top-right), Research Gaps (bottom-left), and High Confidence Claims (bottom-right).
