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
            "tagline": cfg.get("tagline", ""),
            "stats": [{"k": s["k"], "v": _fmt(ctx, str(s["v"])), "flag": s.get("flag")}
                      for s in cfg.get("stats", [])],
        },
        "groups": cfg.get("groups", []),
        "flows": [{"id": f["id"], "label": f["label"], "enabled": bool(f.get("enabled"))}
                  for f in cfg.get("flows", [])],
        "tiers": cfg.get("tiers", []),
        "layers": cfg.get("layers", []),
        "nodes": nodes,
        "edges": ov["edges"],
        "findings": findings,
        "system": {k: _fmt(ctx, v) for k, v in (ov["system"] or {}).items()},
        "meta": {
            "tool": "repolens",
            "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "root": ctx.root.name,
            "metrics": ctx.facts.get("metrics", {}),
        },
    }
    ctx.log(f"{len(nodes)} nodes, {len(ov['edges'])} edges, {len(findings)} findings")


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
        if payload not in page:
            ctx.warn("template has no /*__MODEL__*/null placeholder — page not built")
        else:
            (out / "index.html").write_text(page, encoding="utf-8")
            ctx.log(f"index.html — {len(page):,} bytes")
    else:
        ctx.warn(f"no template at {tmpl_path}; wrote model.json only")

    ctx.log(f"wrote {ctx.rel(out / 'facts.json')} and {ctx.rel(out / 'model.json')}")
