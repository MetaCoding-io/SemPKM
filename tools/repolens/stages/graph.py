"""Serialise the model as RDF, for loading into a triplestore.

The drawing and the graph are two renderings of the same facts. This stage
does not re-measure anything: it runs after `assemble` and turns what is
already there into Turtle in the repolens vocabulary.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from ..pipeline import Context, stage
from ..rdf import CONTRIBUTORS
from ..rdf.core import PREFIXES
from ..rdf.revision import git_revision
from ..rdf.writer import TurtleWriter


def default_base(ctx: Context) -> str:
    name = (ctx.config.get("model") or {}).get("name") or ctx.root.name
    return f"urn:repolens:{name}:"


def write_snapshot(ctx: Context, turtle: str, rev: dict, stats: dict,
                   snap_dir: Path) -> Path | None:
    """Keep one graph per revision, so the series can be replayed later.

    Stored as plain Turtle rather than compressed: two consecutive snapshots
    are ~99% the same text, which git deltifies to almost nothing, while gzip
    output changes wholesale for any input change and would cost the full size
    every time. Plain also stays greppable and diffable.
    """
    if rev.get("dirty"):
        ctx.log("tree is dirty — no snapshot taken (it would not describe the commit)")
        return None
    snap_dir.mkdir(parents=True, exist_ok=True)
    path = snap_dir / f"{rev['id']}.ttl"
    path.write_text(turtle, encoding="utf-8")

    index_path = snap_dir / "index.json"
    try:
        index = json.loads(index_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        index = {"snapshots": []}
    entry = {"id": rev["id"], "sha": rev.get("sha", ""), "date": rev.get("date", ""),
             "branch": rev.get("branch", ""), "subject": rev.get("subject", ""),
             "file": path.name,
             "scanned": datetime.now(timezone.utc).isoformat(timespec="seconds"),
             **stats}
    index["snapshots"] = [s for s in index["snapshots"] if s.get("id") != rev["id"]]
    index["snapshots"].append(entry)
    index["snapshots"].sort(key=lambda s: (s.get("date") or "", s.get("id")))
    index_path.write_text(json.dumps(index, indent=2, sort_keys=True) + "\n",
                          encoding="utf-8")
    return path


@stage("graph", requires=["model"], provides=["graph"])
def graph(ctx: Context) -> None:
    """Write the model as Turtle in the repolens ontology."""
    spec = ctx.config.get("graph") or {}
    base = spec.get("base") or default_base(ctx)
    rev = git_revision(ctx.root)
    ctx.facts["revision"] = rev
    w = TurtleWriter(PREFIXES, base)

    ran, skipped = [], []
    for cid, contrib in CONTRIBUTORS.items():
        if not contrib.applies(ctx):
            skipped.append(cid)
            continue
        contrib.fn(ctx, w)
        ran.append(cid)

    header = (f"repolens graph of {ctx.root.name}\n"
              f"revision {rev['id']}"
              + (f" — {rev['subject']}" if rev.get("subject") else "") + "\n"
              f"base {base}\n"
              f"contributors: {', '.join(ran)}"
              + (f"\nskipped (no facts): {', '.join(skipped)}" if skipped else ""))
    turtle = w.serialise(header)
    out_dir = ctx.root / ctx.config.get("out_dir", ".repolens")
    out = out_dir / spec.get("file", "repo.ttl")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(turtle, encoding="utf-8")

    stats = {"triples": w.triple_count, "subjects": w.subject_count}
    snapped = None
    if spec.get("snapshots", True) and rev.get("vcs"):
        snapped = write_snapshot(
            ctx, turtle, rev, stats,
            ctx.root / spec.get("snapshot_dir", ".repolens/snapshots"))

    ctx.facts["graph"] = {**stats, "base": base, "revision": rev,
                          "contributors": ran, "skipped": skipped,
                          "snapshot": snapped.name if snapped else None}
    ctx.metric("graph.triples", w.triple_count)
    ctx.metric("graph.subjects", w.subject_count)
    ctx.log(f"{w.triple_count} triples over {w.subject_count} subjects → {out.name}"
            f"  ({rev['id']})")
    if snapped:
        ctx.log(f"snapshot kept: {snapped.relative_to(ctx.root)}")
    if skipped:
        ctx.log("skipped contributors (nothing to say): " + ", ".join(skipped))
