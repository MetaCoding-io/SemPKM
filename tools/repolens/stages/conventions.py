"""Convention discovery and checking.

Discovery is adapter-based. The gsd adapter needs no LLM at all: gsd keeps
decisions and rules in fixed-column markdown tables, so they parse directly.
An `llm` adapter is left as a declared-but-unimplemented fallback, because the
intent is that anything it infers gets written back into config as a
structured check rather than being re-inferred on every run.
"""

from __future__ import annotations

import re
from collections import Counter

from ..pipeline import Context, stage

# a fenced shell command inside a rule, e.g. `git ls-files .env`
_RUNNABLE = re.compile(r"`([a-z][a-z0-9-]* [^`]{3,120})`")
_RUNNABLE_HEAD = ("git ", "rg ", "grep ", "find ", "docker ", "npx ", "python")


def _parse_md_table(text: str) -> list[dict]:
    """Parse every pipe-table in a markdown document into dicts."""
    rows: list[dict] = []
    headers: list[str] | None = None
    for line in text.splitlines():
        s = line.strip()
        if not s.startswith("|"):
            headers = None
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        if all(set(c) <= set("-: ") and c for c in cells):
            continue                                   # separator row
        if headers is None:
            headers = cells
            continue
        if len(cells) < len(headers):
            cells += [""] * (len(headers) - len(cells))
        rows.append(dict(zip(headers, cells[:len(headers)])))
    return rows


@stage("conventions", provides=["conventions"])
def conventions(ctx: Context) -> None:
    """Read decisions and rules from whatever harness the repo uses."""
    out = {"decisions": [], "rules": [], "sources": []}

    for src in (ctx.config.get("conventions") or {}).get("sources", []):
        adapter = src.get("adapter")
        if adapter in ("gsd", "markdown-table"):
            for kind, key in (("decisions", "decisions"), ("rules", "rules")):
                path = src.get(key)
                if not path:
                    continue
                p = ctx.root / path
                if not p.exists():
                    ctx.warn(f"{adapter}: {path} not found")
                    continue
                rows = _parse_md_table(p.read_text(encoding="utf-8", errors="replace"))
                cols = (src.get("columns") or {}).get(kind, {})
                parsed = [_normalise(r, cols, path) for r in rows]
                parsed = [r for r in parsed if r.get("id")]
                out[kind].extend(parsed)
                out["sources"].append({"adapter": adapter, "kind": kind,
                                       "path": path, "count": len(parsed)})
                ctx.log(f"{adapter}:{kind} — {len(parsed)} rows from {path}")
        elif adapter == "llm":
            ctx.log("llm adapter declared but not implemented; skipped")
        else:
            ctx.warn(f"unknown convention adapter {adapter!r}")

    # Which rules carry their own executable assertion?
    checkable = 0
    for r in out["rules"]:
        cmds = [c for c in _RUNNABLE.findall(r.get("statement", ""))
                if c.startswith(_RUNNABLE_HEAD)]
        r["candidate_commands"] = cmds
        r["kind"] = "checkable" if cmds else "advisory"
        checkable += bool(cmds)

    scopes = Counter(d.get("scope", "") for d in out["decisions"])
    out["decision_scopes"] = dict(scopes.most_common())

    ctx.facts["conventions"] = out
    ctx.metric("conventions.decisions", len(out["decisions"]))
    ctx.metric("conventions.rules", len(out["rules"]))
    ctx.metric("conventions.rules_checkable", checkable)
    ctx.log(f"{len(out['decisions'])} decisions, {len(out['rules'])} rules "
            f"({checkable} carry a runnable command)")


def _normalise(row: dict, cols: dict, source: str) -> dict:
    def pick(*names):
        for n in names:
            if n in row and row[n]:
                return row[n]
        return ""
    return {
        "id": pick(cols.get("id", "#"), "#", "ID"),
        "scope": pick(cols.get("scope", "Scope"), "Scope"),
        "statement": pick(cols.get("statement", "Rule"), "Rule", "Decision", "Choice"),
        "rationale": pick(cols.get("rationale", "Why"), "Why", "Rationale"),
        "when": pick("When", "Added", "Date"),
        "source": source,
    }


# --------------------------------------------------------------------------
# Checks
# --------------------------------------------------------------------------

_OPS = {
    "==": lambda a, b: a == b,
    "!=": lambda a, b: a != b,
    "<":  lambda a, b: a < b,
    "<=": lambda a, b: a <= b,
    ">":  lambda a, b: a > b,
    ">=": lambda a, b: a >= b,
}


@stage("checks", requires=["callsites"], provides=["checks"])
def checks(ctx: Context) -> None:
    """Evaluate declarative checks into findings.

    Three kinds ship: `metric` compares a published metric, `coverage` finds
    modules that do one thing without doing another, and `shell` runs a
    command. A new kind is a new function in this dict.
    """
    results = []
    for spec in ctx.config.get("checks") or []:
        kind = spec.get("kind", "metric")
        fn = _KINDS.get(kind)
        if not fn:
            ctx.warn(f"check '{spec.get('id')}': unknown kind {kind!r}")
            continue
        res = fn(ctx, spec)
        res.update({
            "id": spec.get("id"),
            "kind": kind,
            "severity": spec.get("severity", "note"),
            "title": spec.get("title", spec.get("id")),
            "node": spec.get("node"),
        })
        results.append(res)
        mark = "ok " if res["passed"] else "FAIL"
        ctx.log(f"[{mark}] {res['id']}: {res.get('evidence', '')[:90]}")

    ctx.facts["checks"] = results
    failed = [r for r in results if not r["passed"]]
    ctx.metric("checks.total", len(results))
    ctx.metric("checks.failed", len(failed))
    ctx.log(f"{len(failed)}/{len(results)} checks failing")


def _check_metric(ctx: Context, spec: dict) -> dict:
    actual = ctx.get_metric(spec["metric"])
    op = _OPS.get(spec.get("op", "=="))
    expected = spec.get("value")
    passed = bool(op(actual, expected)) if actual is not None and op else False
    return {
        "passed": passed,
        "actual": actual,
        "expected": f"{spec.get('op','==')} {expected}",
        "evidence": spec.get("evidence", "").format(actual=actual, expected=expected),
        "body": spec.get("body", "").format(actual=actual, expected=expected),
    }


def _check_coverage(ctx: Context, spec: dict) -> dict:
    """Modules that do X without also doing Y.

    This is the shape of most real architectural findings: a write path that
    forgets to notify, a route that forgets to authorise.
    """
    cs = ctx.facts.get("callsites", {})
    of = cs.get(spec["of"], {}).get("by_module", {})
    cov = cs.get(spec["covered_by"], {}).get("by_module", {})
    allowed = set(spec.get("allow", []))
    missing = sorted(m for m in of if m not in cov and m not in allowed)
    total_sites = sum(of.values())
    covered_sites = sum(v for m, v in of.items() if m in cov or m in allowed)

    fmt = {
        "missing": ", ".join(missing) or "none",
        "missing_count": len(missing),
        "module_count": len(of),
        "total": total_sites,
        "covered": covered_sites,
        "uncovered": total_sites - covered_sites,
    }
    return {
        "passed": not missing,
        "actual": fmt["missing_count"],
        "expected": "0 uncovered modules",
        "missing": missing,
        "evidence": spec.get("evidence", "").format(**fmt),
        "body": spec.get("body", "").format(**fmt),
    }


def _check_shell(ctx: Context, spec: dict) -> dict:
    code, out = ctx.sh(spec["run"])
    expect = spec.get("expect_empty", False)
    passed = (out == "") if expect else (code == 0)
    return {
        "passed": passed,
        "actual": out[:200] or f"exit {code}",
        "expected": "empty output" if expect else "exit 0",
        "evidence": spec.get("evidence", spec["run"]),
        "body": spec.get("body", ""),
    }


_KINDS = {"metric": _check_metric, "coverage": _check_coverage, "shell": _check_shell}
