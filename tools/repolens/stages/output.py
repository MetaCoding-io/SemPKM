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

from ..pipeline import Context, _glob_match, stage

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


_WORD = re.compile(r"[a-z0-9_]+")

# words too common in prose to identify a part
_STOPWORDS = {
    "the", "and", "for", "with", "from", "into", "app", "api", "use", "used",
    "new", "not", "all", "one", "two", "per", "via", "its", "this", "that",
    "service", "services", "model", "models", "data", "page", "pages", "test",
    "tests", "code", "file", "files", "type", "types", "name", "names",
}


def node_keywords(node: dict, members: dict) -> set[str]:
    """Distinctive words that mean 'this part' in prose.

    Taken from the member globs — a node whose files live in backend/app/
    federation/ is identified by the word 'federation' — plus the words of its
    own name. Short and common words are dropped, because a decision
    mentioning 'data' is not a decision about the Views module.
    """
    words: set[str] = set()
    for pattern in members.get(node["id"], []):
        for part in pattern.split("/"):
            if "*" in part or "." in part:
                continue
            for w in _WORD.findall(part.lower()):
                if len(w) > 3 and w not in _STOPWORDS:
                    words.add(w)
    for w in _WORD.findall((node.get("name", "") + " " + node.get("short", "")).lower()):
        if len(w) > 3 and w not in _STOPWORDS:
            words.add(w)
    return words


def link_decisions(ctx: Context, nodes: list[dict]) -> dict[str, list[dict]]:
    """Guess which parts each architectural decision is about.

    408 decisions is unreadable in bulk but perfectly readable by location.
    Matching is on distinctive words, and every match records which word hit,
    so a wrong one is visible rather than mysterious. The guess is only a
    starting point: `links.yml` overrides it, and the page can edit that file.
    """
    conv = ctx.facts.get("conventions") or {}
    decisions = conv.get("decisions") or []
    if not decisions or not nodes:
        return {}

    members = ctx.facts.get("declared_members") or {}
    keywords = {n["id"]: node_keywords(n, members) for n in nodes}

    # A word shared by more than one part identifies neither. Every node's globs
    # start "backend/app/", so without this Federation matched any decision
    # saying "backend"; and "frontend" is shared by nginx and the workspace, so
    # 40 front-end decisions landed on the nginx config file.
    freq: dict[str, int] = {}
    for kws in keywords.values():
        for w in kws:
            freq[w] = freq.get(w, 0) + 1
    common = {w for w, c in freq.items() if c > 1}
    keywords = {nid: (kws - common) for nid, kws in keywords.items()}
    if common:
        ctx.log("ignoring non-distinctive words: " + ", ".join(sorted(common)))

    auto: dict[str, list[dict]] = {}
    for d in decisions:
        hay = (d.get("statement", "") + " " + d.get("rationale", "") + " " +
               d.get("scope", "")).lower()
        words = set(_WORD.findall(hay))
        for n in nodes:
            hit = keywords[n["id"]] & words
            if hit:
                auto.setdefault(d["id"], []).append(
                    {"to": n["id"], "kind": "part", "why": sorted(hit)[:3],
                     "src": "matched"})
    return auto


def parse_target(s: str) -> tuple[str, str]:
    """A link target: 'part:C', 'file:backend/app/x.py', 'sym:path#name'.

    An unprefixed string means a part, so a hand-written `add: [C]` works.
    """
    for kind in ("part", "file", "sym"):
        if s.startswith(kind + ":"):
            return kind, s[len(kind) + 1:]
    return "part", s


def apply_link_overlay(ctx: Context, page_id: str,
                       auto: dict[str, list[dict]]) -> dict[str, list[dict]]:
    """Layer the authored links.yml over a guessed or measured mapping.

    Authored wins, in both directions: an `add` appears even when nothing
    matched, and a `remove` suppresses a link that was wrong. Both are marked,
    so the page can show which links a person put there and which it guessed.
    """
    authored = (ctx.facts.get("links") or {}).get(page_id) or {}
    out = {k: [dict(v) for v in vs] for k, vs in auto.items()}
    added = removed = 0
    for item_id, edit in (authored or {}).items():
        cur = out.setdefault(item_id, [])
        for raw in edit.get("remove") or []:
            kind, value = parse_target(str(raw))
            before = len(cur)
            cur[:] = [ln for ln in cur
                      if not (ln["to"] == value and ln.get("kind", "part") == kind)]
            removed += before - len(cur)
        have = {(ln.get("kind", "part"), ln["to"]) for ln in cur}
        for raw in edit.get("add") or []:
            kind, value = parse_target(str(raw))
            if (kind, value) not in have:
                cur.append({"to": value, "kind": kind, "why": [], "src": "authored"})
                have.add((kind, value))
                added += 1
        if not cur:
            out.pop(item_id, None)
    if added or removed:
        ctx.log(f"links.yml on '{page_id}': {added} added, {removed} removed")
    return out


def attach_decisions(ctx: Context, nodes: list[dict], links: dict[str, list[dict]],
                     limit: int = 12) -> None:
    """Write the final decision links back onto the nodes that carry them."""
    by_id = {d["id"]: d for d in (ctx.facts.get("conventions") or {}).get("decisions", [])}
    per_node: dict[str, list[dict]] = {}
    for dec_id, lns in links.items():
        d = by_id.get(dec_id)
        if not d:
            continue
        for ln in lns:
            if ln.get("kind", "part") != "part":
                continue                       # a file link belongs on the file
            per_node.setdefault(ln["to"], []).append({
                "id": dec_id, "when": d.get("when", ""), "scope": d.get("scope", ""),
                "statement": d.get("statement", "")[:400],
                "rationale": d.get("rationale", "")[:400],
                "why": ln.get("why", []), "src": ln.get("src", "matched"),
            })
    for n in nodes:
        hits = sorted(per_node.get(n["id"], []), key=lambda h: h["id"], reverse=True)
        n["decisions"] = hits[:limit]
        n["decision_count"] = len(hits)

    total = len(by_id)
    ctx.metric("decisions.linked", len(links))
    ctx.metric("decisions.unlinked", total - len(links))
    ctx.log(f"{len(links)} of {total} decisions linked to a part")


def path_owner(members: dict, path: str) -> str | None:
    """The node whose declared globs claim a file. First match wins."""
    for node_id, patterns in members.items():
        for pattern in patterns or []:
            if _glob_match(path, pattern):
                return node_id
    return None


def build_pages(ctx: Context, nodes: list[dict],
                prelinked: dict[str, dict]) -> dict:
    """Datasets behind the topbar numbers.

    A number in the topbar is a dead end; the thing it counts is not. Each
    declared page turns one measured count into a list you can search, open and
    link. The item shape is the same for all of them so the page needs one
    renderer, not three, and every page takes the same authored overrides.
    """
    spec = (ctx.config.get("model") or {}).get("pages") or {}
    if not spec:
        return {}
    members = ctx.facts.get("declared_members") or {}
    known = {n["id"] for n in nodes}
    drill = ctx.facts.get("drilldown", {})
    mod2node = {target_module(drill, nid): nid for nid in drill}

    def owned_by(path: str, module: str | None = None) -> list[dict]:
        owner = (mod2node.get(module) if module else None) or path_owner(members, path)
        return ([{"to": owner, "kind": "part", "why": [], "src": "measured"}]
                if owner in known else [])

    pages = {}
    for page_id, ps in spec.items():
        src = ps.get("from", "")
        items: list[dict] = []
        base: dict[str, list[dict]] = {}

        if src.startswith("conventions."):
            kind = src.split(".", 1)[1]
            for d in (ctx.facts.get("conventions") or {}).get(kind, []):
                items.append({
                    "id": d["id"], "title": d.get("statement", d["id"]),
                    "body": d.get("rationale", ""),
                    "meta": [["Scope", d.get("scope", "")], ["When", d.get("when", "")],
                             ["Source", d.get("source", "")]],
                })

        elif src.startswith("callsites."):
            name = src.split(".", 1)[1]
            for h in ((ctx.facts.get("callsites") or {}).get(name) or {}).get("hits", []):
                item_id = f"{h['path']}:{h['line']}"
                items.append({
                    "id": item_id,
                    "title": h["path"].rsplit("/", 1)[-1] + ":" + str(h["line"]),
                    "body": h.get("text", ""),
                    "meta": [["Path", h["path"]], ["Module", h.get("module", "")]],
                })
                base[item_id] = owned_by(h["path"], h.get("module"))

        elif src.startswith("tests."):
            for t in (ctx.facts.get("tests") or {}).get("list", []):
                items.append({
                    "id": t["path"], "title": t.get("title") or t["path"],
                    "body": t["path"],
                    "meta": [["Directory", t["dir"]], ["Lines", str(t.get("lines", 0))]],
                })
                base[t["path"]] = owned_by(t["path"])
        else:
            ctx.warn(f"page '{page_id}': unknown source '{src}'")
            continue

        # Decisions were linked and overridden earlier so the nodes could carry
        # them; everything else takes the overlay here.
        final = prelinked.get(page_id)
        if final is None:
            final = apply_link_overlay(ctx, page_id, base)
        for it in items:
            it["links"] = [ln for ln in final.get(it["id"], [])
                           if ln.get("kind", "part") != "part" or ln["to"] in known]

        pages[page_id] = {
            "id": page_id, "label": ps.get("label", page_id),
            "note": _fmt(ctx, ps.get("note", "")),
            "source": src, "items": items,
        }
        ctx.log(f"page '{page_id}': {len(items)} items from {src}")
    return pages


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


def _load_yaml_or_json(ctx: Context, d: Path, name: str) -> dict:
    """Read <name>.json, else <name>.yml. Either form, whichever is present."""
    data = _load_json(d / f"{name}.json", {})
    if data:
        return data
    f = d / f"{name}.yml"
    if not f.exists():
        return {}
    try:
        import yaml
        return yaml.safe_load(f.read_text(encoding="utf-8")) or {}
    except Exception as e:                                      # pragma: no cover
        ctx.warn(f"{f.name} unreadable: {e}")
        return {}


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

    members = _load_yaml_or_json(ctx, d, "members")
    ctx.facts["declared_members"] = members or {}

    # Written by the page, not by hand — see `repolens serve`. Kept separate
    # from members.yml so a machine-written file never sits in an authored one.
    ctx.facts["links"] = _load_yaml_or_json(ctx, d, "links") or {}

    edits = sum(len(v) for v in ctx.facts["links"].values())
    ctx.log(f"{len(nodes)} authored nodes, {len(ctx.facts['declared_members'])} member globs"
            + (f", {edits} link edits" if edits else ""))


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

    dec_links = apply_link_overlay(ctx, "decisions", link_decisions(ctx, nodes))
    attach_decisions(ctx, nodes, dec_links)

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
            "stats": [{"k": s["k"], "v": _fmt(ctx, str(s["v"])), "flag": s.get("flag"),
                       "page": s.get("page")}
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
        # what the topbar numbers count, one searchable list each
        "pages": build_pages(ctx, nodes, {"decisions": dec_links}),
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
