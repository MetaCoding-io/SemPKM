"""Overlay loading, model assembly, verification and emission.

The overlay holds everything a scanner cannot derive: prose, packet payloads,
the Löwy layer, and the hand-placed survey coordinates. Measured values always
win over authored ones — an author's number is treated as a claim, and the
verify stage reports where a claim and the tree disagree.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

from ..pipeline import Context, stage

_METRIC_REF = re.compile(r"\$\{([a-zA-Z0-9_.]+)\}")


def byid_name(nodes: list[dict], node_id: str) -> str:
    for n in nodes:
        if n["id"] == node_id:
            return n["name"]
    return node_id


def target_module(drill: dict, node_id: str) -> str:
    """A representative module path for the target, for the payload text."""
    files = (drill.get(node_id) or {}).get("files") or []
    if not files:
        return node_id.lower()
    parts = files[0].get("path", "").split("/")
    return parts[2] if len(parts) > 2 else node_id.lower()


def derive_nodes(ctx: Context, ns_id: str, measured: dict) -> tuple[list[dict], list[dict]]:
    """Build a drawing from measurement alone, for a repo with no overlay.

    Nothing here is authored: the group is the member files' common parent, the
    tier is depth in the import graph, and the prose is a sentence of facts.
    Returns (nodes, groups).
    """
    imports = (ctx.facts.get("edges") or {}).get("imports") or []
    out_edges: dict[str, set] = {}
    for e in imports:
        out_edges.setdefault(e["from"], set()).add(e["to"])

    # tier = how far a node sits from anything that nothing imports
    roots = [nid for nid in measured if nid not in
             {t for tos in out_edges.values() for t in tos}]
    depth = {r: 0 for r in roots}
    frontier = list(roots)
    while frontier:
        cur = frontier.pop(0)
        for nxt in out_edges.get(cur, ()):
            if nxt in measured and nxt not in depth:
                depth[nxt] = depth[cur] + 1
                frontier.append(nxt)
    max_depth = max(depth.values()) if depth else 0

    nodes, groups = [], {}
    for nid, rec in sorted(measured.items(), key=lambda kv: -kv[1]["metrics"]["loc"]):
        members = rec.get("members") or []
        parent = members[0].rsplit("/", 1)[0] if members else ""
        grp = parent.split("/")[0] if parent else "(root)"
        groups[grp] = True
        loc = rec["metrics"]["loc"]
        nodes.append({
            "id": nid, "key": nid[:2].upper(), "short": nid.upper()[:10], "name": nid,
            "grp": grp, "layer": None, "tier": depth.get(nid, max_depth),
            "x": 0, "y": 0, "w": 2.1, "d": 2.1,
            "loc": loc, "files": rec["metrics"]["files"],
            "sub": parent or nid,
            "does": f"{loc:,} lines across {rec['metrics']['files']} file"
                    f"{'' if rec['metrics']['files'] == 1 else 's'}. "
                    "Nothing has been written about this part yet — everything "
                    "shown here was measured.",
            "built": f"Members: {parent or nid}. "
                     f"Import depth {depth.get(nid, max_depth)} of {max_depth}.",
            "cond": [["measured", "Derived with no overlay: no prose, no "
                                  "hand-placed position, no claims to check."]],
        })
    return nodes, [{"id": g, "label": g} for g in sorted(groups)]


def compact_symbols(ctx: Context) -> dict:
    """Project the symbol facts down to what the page actually reads.

    The whole model is inlined into the page, so anything carried here is
    downloaded by every viewer. `imported` is context the UI never shows, and
    docs are truncated. Set `symbols.in_model: false` to leave them out
    entirely on a repo where the weight is not worth it.
    """
    spec = ctx.config.get("symbols") or {}
    if not spec.get("in_model", True):
        return {}
    cap = int(spec.get("model_doc_chars", 90))
    out = {}
    for path, rec in (ctx.facts.get("symbols") or {}).items():
        syms = []
        for s in rec.get("symbols", []):
            t = {k: v for k, v in s.items() if k != "doc"}
            if s.get("doc"):
                t["doc"] = s["doc"][:cap]
            syms.append(t)
        out[path] = {"symbols": syms, "edges": rec.get("edges", []),
                     "approx": rec.get("approx", False)}
    return out


def _derived_tiers(nodes: list[dict]) -> list[str]:
    """Tier labels for a derived model: import depth, named plainly."""
    depths = sorted({n.get("tier") or 0 for n in nodes})
    return [("Imported by nothing" if d == 0 else f"Import depth {d}") for d in depths]


def _load_json(p: Path, default):
    if not p.exists():
        return default
    return json.loads(p.read_text(encoding="utf-8"))


def _fmt(ctx: Context, text: str) -> str:
    """Substitute ${metric.name} against published metrics."""
    def sub(m):
        v = ctx.get_metric(m.group(1))
        if v is None:
            return m.group(0)
        return f"{v:,}" if isinstance(v, int) else str(v)
    return _METRIC_REF.sub(sub, text)


@stage("overlay", provides=["overlay"])
def overlay(ctx: Context) -> None:
    """Load authored content and the declared node member map."""
    d = ctx.root / ctx.config.get("overlay_dir", ".repolens/overlay")
    nodes = _load_json(d / "nodes.json", [])
    ctx.facts["overlay"] = {
        "nodes": nodes,
        "edges": _load_json(d / "edges.json", []),
        "findings": _load_json(d / "findings.json", []),
        "system": _load_json(d / "system.json", {}),
    }

    members = _load_json(d / "members.json", {})
    if not members:
        try:
            import yaml
            f = d / "members.yml"
            members = yaml.safe_load(f.read_text(encoding="utf-8")) if f.exists() else {}
        except Exception as e:                                  # pragma: no cover
            ctx.warn(f"member map unreadable: {e}")
            members = {}
    ctx.facts["declared_members"] = members or {}

    ctx.log(f"{len(nodes)} authored nodes, {len(ctx.facts['declared_members'])} member globs")


@stage("assemble", requires=["nodesets", "overlay"], provides=["model"])
def assemble(ctx: Context) -> None:
    """Merge measured metrics with authored content into the render model."""
    cfg = ctx.config.get("model") or {}
    ov = ctx.facts["overlay"]
    ns_id = cfg.get("nodeset", "survey")
    measured = {n["id"]: n for n in ctx.facts.get("nodesets", {}).get(ns_id, [])}

    derived_groups = []
    if not ov["nodes"]:
        # No overlay — a repository nobody has written about yet. Derive the
        # whole drawing from what was measured, so pointing the tool at an
        # unfamiliar repo produces something rather than nothing.
        nodes, derived_groups = derive_nodes(ctx, ns_id, measured)
        ctx.metric("model.derived", 1)
        ctx.log(f"no overlay — derived {len(nodes)} nodes from nodeset '{ns_id}'")
    else:
        nodes = []
        for a in ov["nodes"]:
            m = measured.get(a["id"], {}).get("metrics", {})
            s = a.get("survey") or {}
            nodes.append({
                "id": a["id"], "key": a.get("key", a["id"]),
                "short": a.get("short", a["id"]), "name": a.get("name", a["id"]),
                "grp": a.get("group"), "layer": a.get("layer"), "tier": a.get("tier"),
                "x": s.get("x", 0), "y": s.get("y", 0), "w": s.get("w", 2), "d": s.get("d", 2),
                # measured wins; the authored number survives only as a fallback
                "loc": m.get("loc", a.get("claimed", {}).get("loc", 0)),
                "files": m.get("files", a.get("claimed", {}).get("files", 0)),
                "sub": _fmt(ctx, a.get("sub", "")),
                "does": _fmt(ctx, a.get("does", "")),
                "built": _fmt(ctx, a.get("built", "")),
                "cond": [[c[0], _fmt(ctx, c[1])] for c in a.get("cond", [])],
            })

    # Import edges between parts, derived from the drill-down's external counts.
    # These deliberately land on the same node pairs as the authored data-flow
    # edges, which is what makes edge bundling in the UI mean anything.
    edges = list(ov["edges"])
    drill = ctx.facts.get("drilldown", {})
    known = {n["id"] for n in nodes}
    import_edges = 0
    for node_id, d in sorted(drill.items()):
        for ext in d.get("external", []):
            target = ext.get("to_node")
            if target not in known or target == node_id:
                continue
            n_from, n_to = byid_name(nodes, node_id), byid_name(nodes, target)
            edges.append({
                "from": node_id, "to": target, "flow": "import",
                "label": f"{ext['count']} imports",
                "pk": "Python imports",
                "body": (f"# {n_from} → {n_to}\n"
                         f"# {ext['count']} import statement"
                         f"{'' if ext['count'] == 1 else 's'} resolved by AST\n\n"
                         f"from app.{target_module(drill, target)} import ...\n\n"
                         "# counted from the drilldown stage: every import that\n"
                         "# resolves to a file belonging to the other part."),
                "note": ("Static import structure, not runtime data flow. Where this "
                         "sits on the same route as a data-flow edge, the two share "
                         "one line in the drawing and the line thickens."),
            })
            import_edges += 1
    ctx.metric("edges.import_between_parts", import_edges)
    if import_edges:
        ctx.log(f"{import_edges} import edges between parts")

    # A finding computed from a live check supersedes the authored copy of the
    # same finding — same words, but the numbers in it are current. Match on
    # the title, because authored entries predate check ids and have none.
    def norm(t: str) -> str:
        return "".join(ch for ch in (t or "").lower() if ch.isalnum())

    computed = []
    for r in ctx.facts.get("checks", []):
        if r["passed"] or not r.get("body"):
            continue
        computed.append({
            "sev": r["severity"], "node": r.get("node"), "title": r["title"],
            "body": r["body"], "ev": r.get("evidence", ""), "id": r["id"],
            "computed": True,
        })

    superseded = {norm(c["title"]) for c in computed}
    findings = [dict(f) for f in ov["findings"] if norm(f.get("title")) not in superseded]
    dropped = len(ov["findings"]) - len(findings)
    findings += computed
    if dropped:
        ctx.log(f"{dropped} authored finding(s) superseded by live checks")

    ctx.model = {
        "repo": {
            "name": cfg.get("name", ctx.root.name),
            "title": cfg.get("title", cfg.get("name", ctx.root.name)),
            "headline": cfg.get("headline", cfg.get("name", ctx.root.name)),
            "tagline": cfg.get("tagline", ""),
            "stats": [{"k": s["k"], "v": _fmt(ctx, str(s["v"])), "flag": s.get("flag")}
                      for s in cfg.get("stats", [])],
        },
        "groups": cfg.get("groups") or derived_groups,
        "flows": [{"id": f["id"], "label": f["label"], "enabled": bool(f.get("enabled"))}
                  for f in cfg.get("flows", [])],
        "tiers": cfg.get("tiers") or _derived_tiers(nodes),
        "layers": cfg.get("layers", []),
        "nodes": nodes,
        "edges": edges,
        # optional: empty when the drilldown stage is not in this pipeline
        "drill": ctx.facts.get("drilldown", {}),
        # the third level; empty when the symbols stage is not in this pipeline
        "symbols": compact_symbols(ctx),
        "findings": findings,
        "system": {k: _fmt(ctx, v) for k, v in (ov["system"] or {}).items()},
        "meta": {
            "tool": "repolens",
            "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "root": ctx.root.name,
            "metrics": ctx.facts.get("metrics", {}),
        },
    }
    ctx.log(f"{len(nodes)} nodes, {len(edges)} edges "
            f"({len(ov['edges'])} authored + {import_edges} measured), "
            f"{len(findings)} findings")


@stage("verify", requires=["model"], provides=["verify"])
def verify(ctx: Context) -> None:
    """Compare authored claims against what the tree actually measures."""
    ov = {n["id"]: n for n in ctx.facts["overlay"]["nodes"]}
    drift = []
    for n in ctx.model["nodes"]:
        claim = ov.get(n["id"], {}).get("claimed") or {}
        for field in ("loc", "files"):
            if field not in claim:
                continue
            got, want = n[field], claim[field]
            if got != want:
                pct = abs(got - want) / max(1, want) * 100
                drift.append({"node": n["id"], "field": field,
                              "claimed": want, "measured": got,
                              "delta": got - want, "pct": round(pct, 1)})
    drift.sort(key=lambda d: -d["pct"])
    ctx.facts["verify"] = {"drift": drift, "checked": len(ctx.model["nodes"])}
    ctx.metric("verify.drift", len(drift))
    if drift:
        worst = ", ".join(f"{d['node']}.{d['field']} {d['claimed']}→{d['measured']}"
                          for d in drift[:6])
        ctx.log(f"{len(drift)} claims disagree with the tree: {worst}")
    else:
        ctx.log("every authored number matches the tree")


@stage("emit", requires=["model"], provides=["emit"])
def emit(ctx: Context) -> None:
    """Write facts.json, model.json and the self-contained page."""
    out = ctx.root / ctx.config.get("out_dir", ".repolens")
    out.mkdir(parents=True, exist_ok=True)

    facts = dict(ctx.facts)
    if not ctx.config.get("facts_include_files", True):
        facts.pop("files", None)
    facts.pop("overlay", None)
    facts.pop("declared_members", None)

    (out / "facts.json").write_text(json.dumps(facts, indent=2, sort_keys=True), encoding="utf-8")
    (out / "model.json").write_text(json.dumps(ctx.model, indent=2), encoding="utf-8")

    tmpl_path = Path(__file__).resolve().parent.parent / "template" / "page.html"
    if tmpl_path.exists():
        tmpl = tmpl_path.read_text(encoding="utf-8")
        payload = json.dumps(ctx.model, separators=(",", ":"))
        # the artifact CSP forbids fetch, so the model is inlined at build time
        page = tmpl.replace("/*__MODEL__*/null", payload)
        # <title> is read before any script runs, so it is substituted here
        page = page.replace("__TITLE__", ctx.model["repo"].get("title") or ctx.root.name)
        if payload not in page:
            ctx.warn("template has no /*__MODEL__*/null placeholder — page not built")
        else:
            (out / "index.html").write_text(page, encoding="utf-8")
            ctx.log(f"index.html — {len(page):,} bytes")
    else:
        ctx.warn(f"no template at {tmpl_path}; wrote model.json only")

    ctx.log(f"wrote {ctx.rel(out / 'facts.json')} and {ctx.rel(out / 'model.json')}")
