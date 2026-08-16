"""Serialise the model as RDF, for loading into a triplestore.

The drawing and the graph are two renderings of the same facts. This stage
does not re-measure anything: it runs after `assemble` and turns what is
already there into Turtle in the repolens vocabulary.
"""

from __future__ import annotations

from ..pipeline import Context, stage
from ..rdf import CONTRIBUTORS
from ..rdf.core import PREFIXES
from ..rdf.writer import TurtleWriter


def default_base(ctx: Context) -> str:
    name = (ctx.config.get("model") or {}).get("name") or ctx.root.name
    return f"urn:repolens:{name}:"


@stage("graph", requires=["model"], provides=["graph"])
def graph(ctx: Context) -> None:
    """Write the model as Turtle in the repolens ontology."""
    spec = ctx.config.get("graph") or {}
    base = spec.get("base") or default_base(ctx)
    w = TurtleWriter(PREFIXES, base)

    ran, skipped = [], []
    for cid, contrib in CONTRIBUTORS.items():
        if not contrib.applies(ctx):
            skipped.append(cid)
            continue
        contrib.fn(ctx, w)
        ran.append(cid)

    header = (f"repolens graph of {ctx.root.name}\n"
              f"base {base}\n"
              f"contributors: {', '.join(ran)}"
              + (f"\nskipped (no facts): {', '.join(skipped)}" if skipped else ""))
    out = ctx.root / ctx.config.get("out_dir", ".repolens") / spec.get("file", "repo.ttl")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(w.serialise(header), encoding="utf-8")

    ctx.facts["graph"] = {"triples": w.triple_count, "subjects": w.subject_count,
                          "base": base, "contributors": ran, "skipped": skipped}
    ctx.metric("graph.triples", w.triple_count)
    ctx.metric("graph.subjects", w.subject_count)
    ctx.log(f"{w.triple_count} triples over {w.subject_count} subjects → {out.name}")
    if skipped:
        ctx.log("skipped contributors (nothing to say): " + ", ".join(skipped))
