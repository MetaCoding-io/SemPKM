"""Python import resolution.

Lifted verbatim out of the drilldown stage when the resolvers became
pluggable; the behaviour is unchanged, only its address is new.

A Python import names a module, not a file, so resolution is: turn the dotted
name into a path under each sys.path-ish root, and keep the first candidate
that is a real file in the repo. Anything that resolves to nothing is a
third-party or stdlib import.
"""

from __future__ import annotations

import ast
import os
import re

from ..pipeline import Context
from . import Language, Resolution, register


# --------------------------------------------------------------------------
# module index
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


# --------------------------------------------------------------------------
# extraction
# --------------------------------------------------------------------------

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
# the language
# --------------------------------------------------------------------------

class _State:
    def __init__(self, ctx: Context, paths: set[str]):
        self.res = _Resolver(ctx, {p for p in paths if p.endswith(".py")})
        self.unparsed: list[str] = []


def prepare(ctx: Context, paths: set[str]) -> _State:
    return _State(ctx, paths)


def resolve(state: _State, path: str, text: str) -> Resolution:
    try:
        found = _targets(ast.parse(text, filename=path), path, state.res)
    except (SyntaxError, ValueError):
        state.unparsed.append(path)
        found = _targets_regex(text, path, state.res)
    # Packages are not counted for Python: a dotted name that resolves to
    # nothing is stdlib, third-party or a typo, and this stage cannot tell
    # them apart without a dependency manifest.
    return Resolution(targets=tuple(found))


def notes(state: _State) -> list[str]:
    if not state.unparsed:
        return []
    return [f"{len(state.unparsed)} file(s) needed the regex fallback "
            f"(newer syntax than this interpreter): {', '.join(state.unparsed[:3])}"]


register(Language(id="python", extensions=(".py",),
                  prepare=prepare, resolve=resolve, notes=notes))
