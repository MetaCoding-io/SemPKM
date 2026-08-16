"""Stages that build the file inventory and roll it up into node sets."""

from __future__ import annotations

import fnmatch
from pathlib import Path

from ..pipeline import Context, stage, _glob_match

LANG_BY_EXT = {
    ".py": "python", ".js": "javascript", ".mjs": "javascript", ".ts": "typescript",
    ".tsx": "typescript", ".jsx": "javascript", ".html": "html", ".css": "css",
    ".yml": "yaml", ".yaml": "yaml", ".json": "json", ".md": "markdown",
    ".sql": "sql", ".sh": "shell", ".toml": "toml", ".conf": "config",
    ".ttl": "rdf", ".rs": "rust", ".go": "go", ".rb": "ruby", ".java": "java",
}


@stage("discover", provides=["files"])
def discover(ctx: Context) -> None:
    """Walk the tree, honouring excludes, and classify every file."""
    excludes = ctx.config.get("exclude", [])
    root = ctx.root
    files: list[dict] = []

    def excluded(rel: str) -> bool:
        return any(_glob_match(rel, p) or fnmatch.fnmatch(rel, p) for p in excludes)

    for p in sorted(root.rglob("*")):
        if p.is_dir() or p.is_symlink():
            continue
        rel = str(p.relative_to(root)).replace("\\", "/")
        if excluded(rel):
            continue
        ext = p.suffix.lower()
        files.append({
            "path": rel,
            "ext": ext,
            "lang": LANG_BY_EXT.get(ext, "other"),
            "bytes": p.stat().st_size,
        })

    ctx.facts["files"] = files
    ctx.metric("files.total", len(files))
    ctx.log(f"{len(files)} files after excludes")


@stage("loc", requires=["files"], provides=["loc"])
def loc(ctx: Context) -> None:
    """Count lines per file; roll totals up by language.

    Only source languages are counted. A repo like this one carries megabytes
    of generated JSON and appended markdown, and letting those into the total
    makes 'lines of code' meaningless.
    """
    spec = ctx.config.get("loc") or {}
    langs = set(spec.get("langs") or LANG_BY_EXT.values())
    max_bytes = spec.get("max_bytes", 4_000_000)

    by_lang: dict[str, int] = {}
    total = 0
    for f in ctx.facts["files"]:
        if f["lang"] not in langs or f["bytes"] > max_bytes:
            f["lines"] = 0
            continue
        p = ctx.root / f["path"]
        try:
            with p.open("rb") as fh:
                n = sum(1 for _ in fh)
        except OSError:
            n = 0
        f["lines"] = n
        total += n
        by_lang[f["lang"]] = by_lang.get(f["lang"], 0) + n

    ctx.facts["loc_by_lang"] = dict(sorted(by_lang.items(), key=lambda kv: -kv[1]))
    ctx.metric("loc.total", total)
    for lang, n in by_lang.items():
        ctx.metric(f"loc.{lang}", n)
    ctx.log(f"{total:,} lines across {len(by_lang)} languages")


@stage("nodesets", requires=["files", "loc", "overlay"], provides=["nodesets"])
def nodesets(ctx: Context) -> None:
    """Group files into nodes and roll up their metrics.

    Two selector kinds are supported today:
      from: dirs("<glob>")   one node per matching directory  (generic default)
      from: declared         nodes and their member globs come from a file
    """
    out: dict[str, list[dict]] = {}

    for ns_id, spec in (ctx.config.get("nodesets") or {}).items():
        src = spec.get("from", "")
        if src.startswith("dirs("):
            nodes = _from_dirs(ctx, src, spec)
        elif src == "declared":
            nodes = _from_declared(ctx, spec)
        else:
            ctx.warn(f"nodeset '{ns_id}': unsupported selector {src!r}, skipped")
            continue
        out[ns_id] = nodes
        ctx.metric(f"nodeset.{ns_id}.count", len(nodes))
        ctx.metric(f"nodeset.{ns_id}.loc", sum(n["metrics"]["loc"] for n in nodes))
        ctx.log(f"{ns_id}: {len(nodes)} nodes")

    ctx.facts["nodesets"] = out


def _rollup(ctx: Context, members: list[dict]) -> dict:
    return {
        "loc": sum(m.get("lines", 0) for m in members),
        "files": len(members),
        "bytes": sum(m.get("bytes", 0) for m in members),
    }


def _from_dirs(ctx: Context, src: str, spec: dict) -> list[dict]:
    glob = src[src.index("(") + 1: src.rindex(")")].strip().strip("\"'")
    base = glob.rstrip("/*")
    exclude = set(spec.get("exclude", []))
    seen: dict[str, list[dict]] = {}

    for f in ctx.facts["files"]:
        path = f["path"]
        if not path.startswith(base.rstrip("/") + "/"):
            continue
        rest = path[len(base.rstrip("/")) + 1:]
        name = rest.split("/")[0]
        if "/" not in rest:          # a loose file, not inside a subdirectory
            name = "(root)"
        if name in exclude:
            continue
        seen.setdefault(name, []).append(f)

    nodes = []
    for name, members in sorted(seen.items()):
        nodes.append({
            "id": name, "label": name,
            "members": [m["path"] for m in members],
            "metrics": _rollup(ctx, members),
        })
    return nodes


def _from_declared(ctx: Context, spec: dict) -> list[dict]:
    members_map = ctx.facts.get("declared_members") or {}
    if not members_map:
        ctx.warn("nodeset 'declared': no member map loaded (is the overlay stage earlier?)")
        return []

    nodes = []
    for node_id, patterns in members_map.items():
        members = ctx.match(patterns)
        if not members:
            ctx.warn(f"declared node '{node_id}' matched no files: {patterns}")
        nodes.append({
            "id": node_id, "label": node_id,
            "members": [m["path"] for m in members],
            "metrics": _rollup(ctx, members),
            "patterns": patterns,
        })
    return nodes
