# repolens

Turns a repository into an inspectable drawing, and keeps that drawing honest.

```bash
python3 -m tools.repolens build      # facts + model + a self-contained page
python3 -m tools.repolens check      # conventions; exit 1 on regression
python3 -m tools.repolens baseline   # accept today's findings as known
python3 -m tools.repolens stages     # what runs, and in what order
```

Output lands in `.repolens/`: `facts.json` (what was measured), `model.json`
(what gets drawn), `index.html` (the page, model inlined).

## The three phases

```
repo ──[extract]──▶ facts.json ──[assemble]──▶ model.json ──[template]──▶ page
      deterministic              + overlay                   unchanged
```

**Extract** is deterministic and needs no model. Everything it produces comes
from a declared query in `.repolens.yml` — a glob, a regex, a scope.

**Assemble** merges those facts with the *overlay*: the things a scanner cannot
derive — prose, packet payloads, the Löwy layer, hand-placed coordinates.
Measured values always win. An authored number is treated as a **claim**, and
the `verify` stage reports where a claim and the tree disagree. Porting the
original hand-authored drawing this way caught two wrong file counts in it.

**Template** is the renderer, lifted from the authored page with every data
literal replaced by a model read. It is not repo-specific.

## Adding to the pipeline

Three levels, in increasing order of effort:

**A new measurement** — edit `.repolens.yml`:

```yaml
callsites:
  raw_sql:
    pattern: 'execute\(\s*["'']SELECT'
    scope: ["backend/**/*.py"]
```

**A new assertion** — also just config. `coverage` is the useful one: modules
that do X without also doing Y, which is the shape of most real architectural
findings.

```yaml
checks:
  - id: sql-through-repo
    kind: coverage
    of: raw_sql
    covered_by: repository_layer
    severity: high
```

**A new kind of thing** — a stage. Write a module in `stages/`, decorate it,
import it from `stages/__init__.py`, name it in a `pipelines:` list:

```python
@stage("cochange", requires=["files"], provides=["edges.cochange"])
def cochange(ctx: Context) -> None:
    """Files that change together, from git history."""
    ...
    ctx.facts.setdefault("edges", {})["cochange"] = edges
    ctx.metric("edges.cochange.count", len(edges))
```

Stages declare `requires`/`provides`, so ordering mistakes fail at startup with
a message rather than halfway through with a `KeyError`.

## Baselines

`check` blocks on **regressions**, not on history. A checker introduced to a
mature codebase that fails on pre-existing findings gets switched off within a
day; this one records `baseline.json` and fails only when a check that used to
pass starts failing, or a count goes up. `--strict` ignores the baseline.

The pre-commit hook and the CI workflow both shell out to the same `check`
command, so there is one definition of the rules. The hook runs only when
`backend/`, `frontend/` or `e2e/` files are staged, and completes in ~550ms.

## Conventions

Convention sources are adapters, not prompts. gsd keeps decisions and rules in
fixed-column markdown tables, so the `gsd` adapter parses 408 decisions and 9
rules directly — no model involved. It also notices which rules carry a
runnable command in their text (6 of 9 do, e.g. R08's `git ls-files .env`) and
marks the rest advisory rather than pretending they are testable.

An `llm` adapter is declared but deliberately unimplemented. The intent is that
anything inferred gets written back into config as a structured check, so it is
inferred once rather than on every run.

## Known edges

- `loc` counts source languages only. Left unbounded it counted 1.5M lines of
  generated `.gsd/reports/*.html` as code.
- YAML 1.1 parses a bare `on:` key as boolean `true`. The flow field is called
  `enabled` for that reason.
- Layout is deliberately out of scope here. `tier` and `layer` are just an int
  and an enum per node; only the `survey` view needs coordinates, and a node
  without them still renders in the computed layouts.
