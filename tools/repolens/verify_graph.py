"""Check that the emitted graph, the ontology and the views agree.

Three things can drift apart independently: the exporter emits a predicate the
ontology never declared, the ontology renames a term the exporter still writes,
or a view queries for something neither produces. Each is invisible until
someone opens the model in SemPKM and finds an empty table.

This runs all three against each other and fails on any of them.

    python3 -m tools.repolens.verify_graph            # after `repolens graph`

Needs rdflib, which the repolens CLI deliberately does not: this is a
development check, not part of producing a graph.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

MODELS = ["repolens", "repolens-gsd"]


def load(root: Path, ttl: Path):
    import rdflib
    g = rdflib.Graph()
    g.parse(str(ttl), format="turtle")
    data_only = len(g)
    for m in MODELS:
        for kind in ("ontology", "shapes"):
            p = root / "models" / m / kind / f"{m}.jsonld"
            if p.exists():
                g.parse(data=p.read_text(encoding="utf-8"), format="json-ld")
    return g, data_only


def undeclared_predicates(g) -> list[str]:
    """Predicates the data uses that the vocabulary never declares."""
    import rdflib
    from rdflib.namespace import RDF, OWL
    declared = set()
    for t in (OWL.ObjectProperty, OWL.DatatypeProperty, OWL.AnnotationProperty):
        declared |= set(g.subjects(RDF.type, t))
    ours = "urn:sempkm:model:repolens"
    used = {p for p in set(g.predicates()) if str(p).startswith(ours)}
    return sorted(str(p) for p in used - declared)


def main(argv=None) -> int:
    root = Path(argv[0]) if argv else Path(".")
    ttl = root / ".repolens" / "repo.ttl"
    if not ttl.exists():
        print(f"no graph at {ttl} — run `repolens graph` first.", file=sys.stderr)
        return 2
    try:
        g, data_only = load(root, ttl)
    except ImportError:
        print("rdflib is needed for this check: pip install rdflib", file=sys.stderr)
        return 2

    print(f"{data_only:,} data triples, {len(g):,} with the vocabulary loaded\n")

    problems = 0

    stray = undeclared_predicates(g)
    if stray:
        problems += len(stray)
        print("predicates used but never declared:")
        for p in stray:
            print("   ", p)
        print()

    for m in MODELS:
        spec = root / "models" / m / "views" / f"{m}.jsonld"
        if not spec.exists():
            continue
        for node in json.loads(spec.read_text(encoding="utf-8"))["@graph"]:
            q = node.get("sempkm:sparqlQuery")
            if not q:
                continue
            label = node.get("rdfs:label", node["@id"])
            try:
                rows = len(list(g.query(q)))
            except Exception as e:
                problems += 1
                print(f"  {label:<34} QUERY FAILED — {str(e)[:90]}")
                continue
            print(f"  {label:<34} {rows:>6} rows" + ("   <-- EMPTY" if not rows else ""))
            if not rows:
                problems += 1

    print()
    print("everything agrees" if not problems else f"{problems} problem(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
