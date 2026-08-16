"""Stages that read source text: call sites, routes, smells, imports.

Every query here is declared in config rather than hardcoded, so pulling a new
signal out of a repo is a config edit, not a code change.
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict

from ..pipeline import Context, stage

_CACHE: dict[str, str] = {}


def _read(ctx: Context, path: str) -> str:
    if path not in _CACHE:
        try:
            _CACHE[path] = (ctx.root / path).read_text(encoding="utf-8", errors="replace")
        except OSError:
            _CACHE[path] = ""
    return _CACHE[path]


_SPEC_TITLE = re.compile(
    r"""(?:describe|suite|test\.describe)\s*\(\s*['"`]([^'"`]{2,120})['"`]""")


def _spec_title(ctx: Context, path: str) -> str:
    """The name a test file gives itself, falling back to its filename.

    Reading the first describe() is worth the file open: 'Command bar keyboard
    navigation' is findable by search, 'nav-2.spec.ts' is not.
    """
    m = _SPEC_TITLE.search(_read(ctx, path))
    if m:
        return m.group(1).strip()
    stem = path.rsplit("/", 1)[-1]
    for suffix in (".spec.ts", ".spec.js", ".test.ts", ".test.js"):
        if stem.endswith(suffix):
            stem = stem[: -len(suffix)]
            break
    return stem.replace("-", " ").replace("_", " ")


def _module_of(ctx: Context, path: str) -> str:
    """Attribute a file to a module by the first segment under module_root."""
    base = ctx.config.get("module_root", "").rstrip("/")
    if base and path.startswith(base + "/"):
        rest = path[len(base) + 1:]
        return rest.split("/")[0] if "/" in rest else "(root)"
    return path.split("/")[0]


@stage("callsites", requires=["files"], provides=["callsites"])
def callsites(ctx: Context) -> None:
    """Run the configured call-site queries and attribute hits to modules."""
    queries = ctx.config.get("callsites") or {}
    results: dict[str, dict] = {}

    for name, spec in queries.items():
        rx = re.compile(spec["pattern"])
        scope = spec.get("scope", ["**/*"])
        if isinstance(scope, str):
            scope = [scope]
        skip = set(spec.get("exclude", []))
        hits = []
        for f in ctx.match(scope):
            if f["path"] in skip:
                continue
            for i, line in enumerate(_read(ctx, f["path"]).splitlines(), 1):
                if rx.search(line):
                    hits.append({"path": f["path"], "line": i,
                                 "module": _module_of(ctx, f["path"]),
                                 "text": line.strip()[:160]})
        by_module = Counter(h["module"] for h in hits)
        results[name] = {
            "total": len(hits),
            "by_module": dict(by_module.most_common()),
            "hits": hits,
        }
        ctx.metric(f"callsites.{name}.total", len(hits))
        ctx.metric(f"callsites.{name}.modules", len(by_module))
        ctx.log(f"{name}: {len(hits)} hits across {len(by_module)} modules")

    ctx.facts["callsites"] = results


@stage("routes", requires=["files"], provides=["routes"])
def routes(ctx: Context) -> None:
    """Count HTTP route declarations and router registrations."""
    spec = ctx.config.get("routes") or {}
    if not spec:
        return
    rx = re.compile(spec.get("pattern", r"@router\.(get|post|put|patch|delete)"))
    scope = spec.get("scope", ["**/*.py"])
    by_module: Counter = Counter()
    total = 0
    for f in ctx.match(scope):
        n = len(rx.findall(_read(ctx, f["path"])))
        if n:
            by_module[_module_of(ctx, f["path"])] += n
            total += n

    registrations = 0
    if spec.get("registration_pattern") and spec.get("registration_file"):
        rrx = re.compile(spec["registration_pattern"])
        registrations = len(rrx.findall(_read(ctx, spec["registration_file"])))

    ctx.facts["routes"] = {"total": total, "by_module": dict(by_module.most_common()),
                           "registrations": registrations}
    ctx.metric("routes.total", total)
    ctx.metric("routes.registrations", registrations)
    ctx.log(f"{total} endpoints, {registrations} router registrations")


@stage("signals", requires=["files", "loc"], provides=["signals"])
def signals(ctx: Context) -> None:
    """Cheap health signals: declared regex counts plus the largest files."""
    out: dict = {}
    for name, spec in (ctx.config.get("signals") or {}).items():
        rx = re.compile(spec["pattern"])
        scope = spec.get("scope", ["**/*"])
        if isinstance(scope, str):
            scope = [scope]
        n = sum(len(rx.findall(_read(ctx, f["path"]))) for f in ctx.match(scope))
        out[name] = n
        ctx.metric(f"signals.{name}", n)
        ctx.log(f"{name}: {n}")

    top_n = (ctx.config.get("largest_files") or {}).get("count", 12)
    scope = (ctx.config.get("largest_files") or {}).get("scope", ["**/*.py"])
    biggest = sorted(ctx.match(scope), key=lambda f: -f.get("lines", 0))[:top_n]
    out["largest_files"] = [{"path": f["path"], "lines": f["lines"]} for f in biggest]
    if biggest:
        ctx.metric("largest_file.lines", biggest[0]["lines"])
        ctx.metric("largest_file.path", biggest[0]["path"])

    ctx.facts["signals"] = out


@stage("imports", requires=["files"], provides=["edges.imports"])
def imports(ctx: Context) -> None:
    """Build a module-to-module import graph.

    Not consumed by the current UI — it is here to show that a new edge
    provider adds data to facts.json without the renderer changing.
    """
    spec = ctx.config.get("imports") or {}
    if not spec:
        return
    rx = re.compile(spec["pattern"])
    scope = spec.get("scope", ["**/*.py"])
    pairs: Counter = Counter()

    for f in ctx.match(scope):
        src = _module_of(ctx, f["path"])
        for m in rx.finditer(_read(ctx, f["path"])):
            dst = m.group(1).split(".")[0]
            if dst and dst != src:
                pairs[(src, dst)] += 1

    edges = [{"from": a, "to": b, "weight": w} for (a, b), w in pairs.most_common()]
    ctx.facts.setdefault("edges", {})["imports"] = edges
    ctx.metric("edges.imports.count", len(edges))
    ctx.log(f"{len(edges)} module import pairs")


@stage("tests", requires=["files"], provides=["tests"])
def tests(ctx: Context) -> None:
    """Count test specs and their directories."""
    spec = ctx.config.get("tests") or {}
    if not spec:
        return
    scope = spec.get("scope", [])
    if isinstance(scope, str):
        scope = [scope]
    specs = ctx.match(scope)
    dirs = sorted({f["path"].rsplit("/", 1)[0] for f in specs})
    ctx.facts["tests"] = {
        "specs": len(specs),
        "dirs": len(dirs),
        "lines": sum(f.get("lines", 0) for f in specs),
        "list": [{"path": f["path"], "dir": f["path"].rsplit("/", 1)[0],
                  "lines": f.get("lines", 0), "title": _spec_title(ctx, f["path"])}
                 for f in sorted(specs, key=lambda f: f["path"])],
    }
    ctx.metric("tests.specs", len(specs))
    ctx.metric("tests.dirs", len(dirs))
    ctx.log(f"{len(specs)} specs across {len(dirs)} directories")
