"""File-level drill-down inside a node.

The survey nodeset answers "how big is this box". This stage answers "what is
inside it": the individual files, how they import each other, and how often the
box reaches out to a different box.

Everything here is derived from facts that earlier stages already produced —
`files` for line counts, `nodesets` for membership. Nothing is re-globbed.

Only Python is parsed today. JS/CSS/HTML/TS members still appear in `files`
(so the drawing can list them) but contribute no edges.
"""

from __future__ import annotations

import ast
import os
import re
from collections import defaultdict

from ..pipeline import Context, stage
from .code import _read          # shared text cache — read each file once


# --------------------------------------------------------------------------
# id shortening
# --------------------------------------------------------------------------

def _common_prefix(paths: list[str]) -> str:
    """Longest shared *directory* prefix of a node's members, with trailing /.

    Stripping it keeps ids short ("store.py") while staying unique inside the
    node, because the full paths were unique to begin with.
    """
    if not paths:
        return ""
    if len(paths) == 1:
        head = paths[0].rsplit("/", 1)
        return head[0] + "/" if len(head) == 2 else ""
    segs = [p.split("/")[:-1] for p in paths]
    shared: list[str] = []
    for parts in zip(*segs):
        if len(set(parts)) != 1:
            break
        shared.append(parts[0])
    return "/".join(shared) + "/" if shared else ""


# --------------------------------------------------------------------------
# python import resolution
# --------------------------------------------------------------------------

def _import_roots(ctx: Context) -> list[str]:
    """Directories that behave like sys.path entries for this repo.

    `module_root: backend/app` means `app` is an importable package, so the
    path entry is its parent. Config may override with `drilldown.roots`.
    """
    spec = ctx.config.get("drilldown") or {}
    roots = spec.get("roots")
    if roots:
        return [r.rstrip("/") for r in roots]
    mr = (ctx.config.get("module_root") or "").strip("/")
    parent = os.path.dirname(mr)
    return [parent] if parent else [""]


def _candidates(root: str, dotted: str) -> list[str]:
    """Repo-relative paths a dotted module could live at."""
    rel = dotted.replace(".", "/")
    stem = f"{root}/{rel}" if root else rel
    return [stem + ".py", stem + "/__init__.py"]


class _Resolver:
    """Maps an import target onto a repo-relative .py path, or None."""

    def __init__(self, ctx: Context, py_paths: set[str]):
        self.roots = _import_roots(ctx)
        self.py = py_paths

    def absolute(self, dotted: str) -> str | None:
        for root in self.roots:
            for cand in _candidates(root, dotted):
                if cand in self.py:
                    return cand
        return None

    def relative(self, src_path: str, level: int, dotted: str | None) -> str | None:
        """`from . import x` / `from ..pkg.mod import y`, resolved from src."""
        pkg = src_path.rsplit("/", 1)[0]            # directory holding the file
        parts = pkg.split("/") if pkg else []
        up = level - 1                              # level 1 == this package
        if up > len(parts):
            return None
        base = parts[: len(parts) - up] if up else parts
        rel = "/".join(base + (dotted.split(".") if dotted else []))
        for cand in (rel + ".py", rel + "/__init__.py"):
            if cand in self.py:
                return cand
        return None

    def submodule(self, container: str, name: str) -> str | None:
        """`from pkg import mod` where mod is a module, not an attribute."""
        if not container.endswith("/__init__.py"):
            return None
        pkg_dir = container[: -len("/__init__.py")]
        for cand in (f"{pkg_dir}/{name}.py", f"{pkg_dir}/{name}/__init__.py"):
            if cand in self.py:
                return cand
        return None


def _targets(tree: ast.AST, src_path: str, res: _Resolver) -> list[str]:
    """Every repo file the given module imports from, with multiplicity."""
    out: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                hit = res.absolute(alias.name)
                if hit:
                    out.append(hit)
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                hit = res.relative(src_path, node.level, node.module)
            else:
                hit = res.absolute(node.module) if node.module else None
            if not hit:
                continue
            # `from pkg import mod` names a module; `from mod import Thing`
            # names an attribute. Prefer the module when one exists.
            named = [res.submodule(hit, a.name) for a in node.names]
            named = [n for n in named if n]
            out.extend(named or [hit])
    return out


_RX_FROM = re.compile(r"^[ \t]*from[ \t]+(\.*)([\w.]*)[ \t]+import[ \t]+(.+)$", re.M)
_RX_IMPORT = re.compile(r"^[ \t]*import[ \t]+([\w.]+)", re.M)


def _targets_regex(text: str, src_path: str, res: _Resolver) -> list[str]:
    """Fallback for text this interpreter cannot parse.

    The repo targets a newer Python than the one repolens may be running on
    (PEP 701 f-strings parse only on 3.12+), and dropping those files would
    silently delete real edges. Resolution against the file index does the
    filtering, so prose that merely looks like an import resolves to nothing
    and is discarded.
    """
    out: list[str] = []
    for dots, mod, names in _RX_FROM.findall(text):
        if dots:
            hit = res.relative(src_path, len(dots), mod or None)
        else:
            hit = res.absolute(mod) if mod else None
        if not hit:
            continue
        parts = [n.strip().split(" as ")[0].strip()
                 for n in names.strip(" ()\\").split(",")]
        named = [res.submodule(hit, n) for n in parts if n.isidentifier()]
        named = [n for n in named if n]
        out.extend(named or [hit])
    for mod in _RX_IMPORT.findall(text):
        hit = res.absolute(mod)
        if hit:
            out.append(hit)
    return out


# --------------------------------------------------------------------------
# the stage
# --------------------------------------------------------------------------

@stage("drilldown", requires=["files", "nodesets"], provides=["drilldown"])
def drilldown(ctx: Context) -> None:
    """Files inside each survey node and the imports between them."""
    ns_id = (ctx.config.get("model") or {}).get("nodeset", "survey")
    nodes = ctx.facts.get("nodesets", {}).get(ns_id) or []
    if not nodes:
        ctx.log(f"nodeset '{ns_id}' is empty — nothing to drill into")
        ctx.facts["drilldown"] = {}
        return

    by_path = {f["path"]: f for f in ctx.facts.get("files", [])}
    py_paths = {p for p in by_path if p.endswith(".py")}
    res = _Resolver(ctx, py_paths)

    # path -> owning node, built once and shared by every node's external pass.
    # First declaration wins if two nodes' globs overlap.
    owner: dict[str, str] = {}
    for n in nodes:
        for p in n["members"]:
            owner.setdefault(p, n["id"])

    out: dict[str, dict] = {}
    tot_files = tot_edges = 0
    unparsed: list[str] = []

    for n in nodes:
        members = list(n["members"])
        prefix = _common_prefix(members)
        fid = {p: (p[len(prefix):] if prefix and p.startswith(prefix) else p)
               for p in members}
        member_set = set(members)

        files = []
        for p in members:
            f = by_path.get(p, {})
            files.append({
                "id": fid[p],
                "path": p,
                "name": p.rsplit("/", 1)[-1],
                "lines": f.get("lines", 0),
                "lang": f.get("lang", "other"),
            })

        pairs: dict[tuple[str, str], int] = defaultdict(int)
        external: dict[str, int] = defaultdict(int)

        for p in members:
            # TODO: JS/TS is the next language here — resolving `import x from
            # './y'` plus the bundler-ish extension guessing needs its own
            # resolver. Until then U/J/ET get files with no edges.
            if not p.endswith(".py"):
                continue
            text = _read(ctx, p)
            try:
                found = _targets(ast.parse(text, filename=p), p, res)
            except (SyntaxError, ValueError):
                unparsed.append(p)
                found = _targets_regex(text, p, res)
            for dst in found:
                if dst == p:
                    continue
                if dst in member_set:
                    pairs[(fid[p], fid[dst])] += 1
                else:
                    other = owner.get(dst)
                    if other and other != n["id"]:
                        external[other] += 1

        edges = [{"from": a, "to": b, "kind": "import", "weight": w}
                 for (a, b), w in sorted(pairs.items(), key=lambda kv: (-kv[1], kv[0]))]

        out[n["id"]] = {
            "files": files,
            "edges": edges,
            "external": [{"to_node": k, "count": v}
                         for k, v in sorted(external.items(), key=lambda kv: -kv[1])],
        }
        tot_files += len(files)
        tot_edges += len(edges)

    ctx.facts["drilldown"] = out
    ctx.metric("drilldown.nodes", len(out))
    ctx.metric("drilldown.files", tot_files)
    ctx.metric("drilldown.edges", tot_edges)
    if unparsed:
        ctx.log(f"{len(unparsed)} file(s) needed the regex fallback "
                f"(newer syntax than this interpreter): {', '.join(unparsed[:3])}")
    ctx.log(f"{len(out)} nodes, {tot_files} files, {tot_edges} intra-node import edges")
