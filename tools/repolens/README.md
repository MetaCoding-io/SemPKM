# repolens

Turns a repository into an inspectable drawing, and keeps that drawing honest.

```bash
python3 -m tools.repolens build      # facts + model + a self-contained page
python3 -m tools.repolens serve      # the page, with its edits writable
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

Four levels, in increasing order of effort:

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

**A new kind of assertion** — a function in the `_KINDS` dict in
`stages/conventions.py`. Three ship: `metric` compares a published number,
`shell` runs a command, `coverage` finds modules that do X without also doing
Y. A fourth is about ten lines.

```python
_KINDS = {"metric": _check_metric, "coverage": _check_coverage,
          "shell": _check_shell, "ratio": _check_ratio}
```

Stages declare `requires`/`provides`, so ordering mistakes fail at startup with
a message rather than halfway through with a `KeyError`.

## Layouts are pluggable

A layout decides where the boxes go. It may also say how tall they are, how a
wire between two of them is routed, and how far the angle dial may be pushed
before its geometry stops making sense. Four ship — `survey`, `stack`, `lowy`,
`rings` — and all four are registered through the same public hook a third
party would use:

```js
repolens.registerLayout({
  id: "circle", label: "Circle",
  maxPitch: 90,                       // 72 for anything stacked by elevation
  route: function (e, api) {          // optional: default turns once on the ground
    return [api.centre(api.byId[e.from]), api.centre(api.byId[e.to])];
  },
  run: function (api) {
    api.nodes.forEach(function (n, i) {
      var a = i / api.nodes.length * Math.PI * 2;
      api.setPos(n, { x: Math.cos(a) * 14, y: Math.sin(a) * 14 });
    });
  }
});
repolens.relayout("circle");
```

The `api` handed to `run` carries `nodes`, `edges`, `byId`, the whole `model`,
`setPos`, `band` (for a band label), `row` (lays a row along the (1,-1)
diagonal, which projects horizontally at every pitch) and `centre`. A layout
button appears the moment a layout is registered, including at runtime.

Overridable per layout: `run` (required), `route`, `height`, `box`, `maxPitch`.
Anything not overridden falls back to `LAYOUT_DEFAULTS`.

## Three levels

Double-click to go down; Escape or the breadcrumb to come back up.

| Level | Nodes are | Edges are | Layout |
|---|---|---|---|
| system | parts of the repo | data flow + imports between parts | survey / layers / volatility / rings |
| part | files of one part | imports between those files | inside |
| file | classes, functions, methods | calls within that file | call graph |

Each level is just a different dataset handed to the same renderer, and each
layout declares which level it can lay out via `scope`. Levels two and three
need the `drilldown` and `symbols` stages in the pipeline; without them the
double-click does nothing rather than breaking.

Language support is a registry: `resolvers/` holds one module per language,
each exposing `prepare` and `resolve` plus a `register()` line. Python resolves
by AST; JS/TS by a scanner that masks comments and template literals first.
Symbols are exact for Python and marked `approx` for JS/TS, where line spans
come from brace counting — the UI says so on the file rather than pretending.

## The numbers in the topbar are lists

A count is a dead end. Declare a page against one and the stat becomes a
button into what it counts — searchable, and openable in the inspector:

```yaml
model:
  stats:
    - { k: "Decisions", v: "${decisions.linked} placed", page: decisions }
  pages:
    decisions:   { label: "Decisions",   from: conventions.decisions }
    commit_sites:{ label: "Commit sites", from: callsites.commit_sites }
    specs:       { label: "E2E specs",   from: tests.list }
```

Three sources ship — `conventions.*`, `callsites.<name>`, `tests.list` — and
all three reduce to the same item shape, so the page has one renderer rather
than three. A fourth is a dozen lines in `build_pages`.

## Links, and correcting them

Every item can link to a **part**, a **file** or a **symbol**. Where those
links come from depends on the source: a commit site knows its file, so its
part is measured; a decision is matched by distinctive words, so its part is a
*guess*, and roughly a fifth of them are wrong.

Guesses need correcting, so the page edits them. Remove a link with its `×`,
add one through a picker that searches every object in the model (2,706 here:
33 parts, 545 files, 2,128 symbols). Edits accumulate in the browser and
**Save** writes them to `.repolens/overlay/links.yml`:

```yaml
decisions:
  "D268":
    add: ["part:U", "sym:backend/app/events/store.py#commit"]
    remove: ["part:N"]
```

That file is authored content like any other overlay: it survives rebuilds,
diffs in review, and can be hand-edited. Authored beats measured in both
directions — an `add` appears even when nothing matched, a `remove` suppresses
a match that was wrong, and the page marks which links a person put there.

Saving needs somewhere to write, which a static file has not got. `serve`
provides it: a stdlib server on 127.0.0.1 that serves `.repolens/` and accepts
exactly one POST, writing exactly one file. Opened as a file — or published as
an artifact, where the CSP blocks the request outright — the page falls back to
putting the same YAML on the clipboard rather than losing the edit.

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

## Running it on a repo that has no overlay

An overlay is optional. With none, `assemble` derives the whole drawing from
measurement: nodes from the chosen node set, the group from the members' parent
directory, the tier from depth in the import graph, and a sentence of facts
instead of prose. The `survey` layout grids them by size rather than expecting
hand-placed coordinates. Verified against a synthetic repo with no overlay at
all — 3 nodes, tiers derived from imports, in 4 ms.

```yaml
# the whole config a new repo needs
module_root: src
nodesets: { modules: { from: dirs("src/*") } }
model:   { name: myrepo, nodeset: modules }
pipelines:
  build: [discover, loc, overlay, nodesets, drilldown, imports, assemble, emit]
```

Nothing in `tools/repolens/` mentions SemPKM. The page title, headline, tagline
and stat tiles all come from config; the template carries no repo name.

## Known edges

- `loc` counts source languages only. Left unbounded it counted 1.5M lines of
  generated `.gsd/reports/*.html` as code.
- YAML 1.1 parses a bare `on:` key as boolean `true`. The flow field is called
  `enabled` for that reason.
- Only Python and JS/TS imports are resolved. Other languages drill into files
  with no edges, and the panel says so rather than implying there are none.
- `verify` is not in the `check` pipeline, so a stale claim never blocks a
  commit. That is deliberate: a wrong drawing is not a broken build.
