"""The code-analysis half of the graph: structure, connections, measurement,
judgement. Nothing here knows what gsd is."""

from __future__ import annotations

from . import contributor

RL = "urn:sempkm:model:repolens:"
GIST = "https://w3id.org/semanticarts/ns/ontology/gist/"

PREFIXES = {
    "rl": RL,
    "rlg": "urn:sempkm:model:repolens-gsd:",
    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
    "xsd": "http://www.w3.org/2001/XMLSchema#",
    "dcterms": "http://purl.org/dc/terms/",
    "skos": "http://www.w3.org/2004/02/skos/core#",
    "schema": "https://schema.org/",
    "prov": "http://www.w3.org/ns/prov#",
    "gist": GIST,
}

# Aspects — what a measurement counts. Repo-local individuals rather than
# vocabulary terms, because a repo may measure something no other repo does.
ASPECTS = {
    "lines": "Lines of code",
    "files": "Files",
    "symbols": "Symbols",
    "outDegree": "Outgoing connections",
    "occurrences": "Occurrences of a declared query",
}


def revision_of(ctx) -> str:
    """The id everything time-varying is scoped by."""
    return (ctx.facts.get("revision") or {}).get("id") or "working"


def _label_of(node: dict) -> str:
    return node.get("name") or node.get("short") or node["id"]


def part_iri(w, node_id: str) -> str:
    return w.iri("part", node_id)


def file_iri(w, path: str) -> str:
    return w.iri("file", path)


def symbol_iri(w, path: str, name: str) -> str:
    return w.iri("symbol", path, name)


@contributor("repository")
def repository(ctx, w) -> None:
    """The repository, the scan that produced this graph, and the vocabularies
    the drawing groups things by."""
    model = ctx.model
    repo = w.iri("repo")
    w.add(repo, "a", "rl:Repository")
    w.add_text(repo, "dcterms:title", model["repo"].get("name", ctx.root.name))
    w.add_text(repo, "dcterms:description", model["repo"].get("headline", ""))

    rev = ctx.facts.get("revision") or {}
    w.add_text(repo, "rl:revision", rev.get("sha"))

    # Entities keep one IRI for all time — part/U is part/U at every commit,
    # which is what makes two snapshots comparable. Everything that varies is
    # scoped by revision instead, or loading two of them together would have
    # each measurement contradicting the other.
    scan = w.iri("scan", revision_of(ctx))
    w.add(scan, "a", "rl:Scan")
    w.add_text(scan, "rdfs:label", "scan of " + revision_of(ctx))
    w.add_text(scan, "dcterms:identifier", revision_of(ctx))
    if rev.get("date"):
        w.add(scan, "prov:startedAtTime", w.datetime(rev["date"]))
    w.add_text(scan, "dcterms:description", rev.get("subject"))
    generated = (model.get("meta") or {}).get("generated")
    if generated:
        w.add(scan, "prov:endedAtTime", w.datetime(generated))
    w.add(scan, "prov:used", repo)

    for aspect, label in ASPECTS.items():
        a = w.iri("aspect", aspect)
        w.add(a, "a", "gist:Aspect")
        w.add_text(a, "rdfs:label", label)

    for kind, cls in (("groups", "rl:Group"), ("tiers", "rl:Tier"),
                      ("layers", "rl:Layer"), ("flows", "rl:Flow")):
        for i, entry in enumerate(model.get(kind) or []):
            # tiers arrive as bare strings; the rest as {id, label}
            eid = entry.get("id") if isinstance(entry, dict) else f"t{i}"
            label = entry.get("label") if isinstance(entry, dict) else entry
            node = w.iri(kind[:-1], eid)
            w.add(node, "a", cls)
            w.add_text(node, "rdfs:label", label)


@contributor("parts")
def parts(ctx, w) -> None:
    """One node per part, its prose, its placement, and its measurements."""
    repo = w.iri("repo")
    members = ctx.facts.get("declared_members") or {}
    for n in ctx.model["nodes"]:
        s = part_iri(w, n["id"])
        w.add(s, "a", "rl:Part")
        w.add_text(s, "dcterms:title", _label_of(n))
        w.add_text(s, "rl:shortName", n.get("short"))
        w.add_text(s, "rl:key", n.get("key"))
        w.add(s, "rl:partOf", repo)
        w.add(repo, "rl:hasPart", s)
        w.add_text(s, "dcterms:description", n.get("does"))
        w.add_text(s, "skos:note", n.get("built"))
        for glob in members.get(n["id"], []) or []:
            w.add_text(s, "rl:memberGlob", glob)
        if n.get("grp"):
            w.add(s, "rl:inGroup", w.iri("group", n["grp"]))
        if n.get("layer"):
            w.add(s, "rl:inLayer", w.iri("layer", str(n["layer"])))
        if n.get("tier") is not None:
            w.add(s, "rl:inTier", w.iri("tier", f"t{n['tier']}"))
        key = "part-" + n["id"]
        _measure(ctx, w, s, key, "lines", n.get("loc"))
        _measure(ctx, w, s, key, "files", n.get("files"))


def measure_iri(w, rev: str, key: str, aspect: str) -> str:
    return w.iri("measure", rev, key, aspect)


def _measure(ctx, w, subject: str, key: str, aspect: str, value,
             provenance: str = "rl:measured") -> None:
    """One measurement. `key` names the subject stably — deriving it from the
    subject IRI by string surgery was how the claim link broke the first time."""
    if value is None:
        return
    rev = revision_of(ctx)
    m = measure_iri(w, rev, key, aspect)
    w.add(m, "a", "rl:Measurement")
    w.add(m, "rl:measures", subject)
    w.add(m, "rl:aspect", w.iri("aspect", aspect))
    w.add(m, "rl:value", w.decimal(value))
    w.add(m, "rl:provenance", provenance)
    w.add(m, "rl:fromScan", w.iri("scan", rev))


@contributor("files", requires=["drilldown"])
def files(ctx, w) -> None:
    """Files, attributed to the part whose globs claim them."""
    for node_id, d in sorted((ctx.facts.get("drilldown") or {}).items()):
        part = part_iri(w, node_id)
        for f in d.get("files", []):
            s = file_iri(w, f["path"])
            w.add(s, "a", "rl:File")
            w.add_text(s, "rl:path", f["path"])
            w.add_text(s, "dcterms:title", f.get("name"))
            w.add_text(s, "rl:language", f.get("lang"))
            w.add(s, "rl:fileOf", part)
            w.add(part, "rl:hasFile", s)
            _measure(ctx, w, s, "file-" + f["path"], "lines", f.get("lines"))
        for e in d.get("edges", []):
            src, dst = e.get("from"), e.get("to")
            if src and dst:
                by_id = {f["id"]: f["path"] for f in d.get("files", [])}
                if src in by_id and dst in by_id:
                    w.add(file_iri(w, by_id[src]), "rl:imports", file_iri(w, by_id[dst]))


@contributor("symbols", requires=["symbols"])
def symbols(ctx, w) -> None:
    """Symbols and the calls between them, marked approximate where the span
    was counted rather than parsed."""
    for path, rec in sorted((ctx.facts.get("symbols") or {}).items()):
        f = file_iri(w, path)
        approx = bool(rec.get("approx"))
        for sym in rec.get("symbols", []):
            s = symbol_iri(w, path, sym["id"])
            w.add(s, "a", "rl:Symbol")
            w.add_text(s, "dcterms:title", sym.get("name"))
            w.add_text(s, "rl:symbolKind", sym.get("kind"))
            w.add(s, "rl:definedIn", f)
            w.add(f, "rl:definesSymbol", s)
            if sym.get("line"):
                w.add(s, "rl:startLine", w.integer(sym["line"]))
            if sym.get("end_line"):
                w.add(s, "rl:endLine", w.integer(sym["end_line"]))
            if sym.get("parent"):
                w.add(s, "rl:enclosedBy", symbol_iri(w, path, sym["parent"]))
            w.add_text(s, "dcterms:description", sym.get("doc"))
            if approx:
                w.add(s, "rl:approximate", w.boolean(True))
        for e in rec.get("edges", []):
            if e.get("from") and e.get("to"):
                w.add(symbol_iri(w, path, e["from"]), "rl:calls",
                      symbol_iri(w, path, e["to"]))


@contributor("connections")
def connections(ctx, w) -> None:
    """Edges as resources, so each keeps its flow layer and example payload."""
    for i, e in enumerate(ctx.model.get("edges") or []):
        s = w.iri("conn", f"{i:04d}")
        w.add(s, "a", "rl:Connection")
        w.add(s, "rl:source", part_iri(w, e["from"]))
        w.add(s, "rl:target", part_iri(w, e["to"]))
        w.add_text(s, "dcterms:title", e.get("pk") or e.get("label"))
        if e.get("flow"):
            w.add(s, "rl:flow", w.iri("flow", e["flow"]))
        w.add_text(s, "rl:payloadExample", e.get("body"))
        w.add_text(s, "skos:note", e.get("note"))
        w.add(s, "rl:provenance",
              "rl:measured" if e.get("flow") == "import" else "rl:authored")
        # the direct form as well, so a plain graph query needs no join
        if e.get("flow") == "import":
            w.add(part_iri(w, e["from"]), "rl:imports", part_iri(w, e["to"]))


@contributor("occurrences", requires=["callsites"])
def occurrences(ctx, w) -> None:
    """Every hit of every declared query, with its path and line."""
    for name, rec in sorted((ctx.facts.get("callsites") or {}).items()):
        q = w.iri("query", name)
        w.add(q, "a", "gist:Category")
        w.add_text(q, "rdfs:label", name.replace("_", " "))
        for i, hit in enumerate(rec.get("hits", [])):
            s = w.iri("occurrence", name, str(i))
            w.add(s, "a", "rl:Occurrence")
            w.add(s, "rl:matches", q)
            w.add(s, "rl:occursIn", file_iri(w, hit["path"]))
            w.add(s, "rl:lineNumber", w.integer(hit["line"]))
            w.add_text(s, "rl:snippet", (hit.get("text") or "").strip())
            w.add(s, "rl:provenance", "rl:measured")
        _measure(ctx, w, q, "query-" + name, "occurrences", rec.get("total"))


@contributor("findings", requires=["checks"])
def findings(ctx, w) -> None:
    """Checks and the findings they produce, keeping which is which."""
    for r in ctx.facts.get("checks") or []:
        c = w.iri("check", r["id"])
        w.add(c, "a", "rl:Check")
        w.add_text(c, "dcterms:title", r.get("title") or r["id"])
        w.add_text(c, "rl:checkKind", r.get("kind"))
        w.add(c, "rl:passed", w.boolean(r.get("passed")))
        if r.get("expected") is not None:
            w.add_text(c, "rl:expected", r["expected"])
        if r.get("actual") is not None:
            w.add_text(c, "rl:actual", r["actual"])
        if r.get("severity"):
            w.add(c, "rl:severity", f"rl:{r['severity']}")

    for i, f in enumerate(ctx.model.get("findings") or []):
        s = w.iri("finding", f.get("id") or f"f{i:02d}")
        w.add(s, "a", "rl:Finding")
        w.add_text(s, "dcterms:title", f.get("title"))
        w.add_text(s, "dcterms:description", f.get("body"))
        w.add_text(s, "rl:evidence", f.get("ev"))
        if f.get("sev"):
            w.add(s, "rl:severity", f"rl:{f['sev']}")
        if f.get("node"):
            w.add(s, "rl:about", part_iri(w, f["node"]))
        computed = bool(f.get("computed"))
        w.add(s, "rl:provenance", "rl:computed" if computed else "rl:authored")
        if computed and f.get("id"):
            w.add(s, "rl:producedBy", w.iri("check", f["id"]))


@contributor("claims", requires=["overlay"])
def claims(ctx, w) -> None:
    """Every authored number, and the measurement it should agree with.

    All of them, not only the ones that currently disagree. A claim that
    happens to match is still a claim, and emitting only the drifting ones
    would make the graph say the author never asserted anything.
    """
    aspect_of = {"loc": "lines", "files": "files"}
    for node in (ctx.facts.get("overlay") or {}).get("nodes") or []:
        for field, value in (node.get("claimed") or {}).items():
            aspect = aspect_of.get(field, field)
            c = w.iri("claim", revision_of(ctx), node["id"], aspect)
            w.add(c, "a", "rl:Claim")
            w.add(c, "rl:measures", part_iri(w, node["id"]))
            w.add(c, "rl:aspect", w.iri("aspect", aspect))
            w.add(c, "rl:value", w.decimal(value))
            w.add(c, "rl:provenance", "rl:authored")
            w.add(c, "rl:verifies",
                  measure_iri(w, revision_of(ctx), "part-" + node["id"], aspect))
