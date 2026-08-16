"""The gsd half: decisions, rules, and what they govern.

Separate from core on purpose. A repository with no `.gsd` directory produces
no triples from here — the contributor declares `conventions.decisions` as a
requirement and is skipped rather than emitting an empty vocabulary.
"""

from __future__ import annotations

from . import contributor
from .core import part_iri


def _decision_iri(w, code: str) -> str:
    return w.iri("decision", code)


@contributor("gsd-decisions", requires=["conventions.decisions"])
def decisions(ctx, w) -> None:
    """Decisions, their scopes and the milestones they were taken during."""
    conv = ctx.facts.get("conventions") or {}
    scopes, milestones = set(), set()

    for d in conv.get("decisions") or []:
        s = _decision_iri(w, d["id"])
        w.add(s, "a", "rlg:Decision")
        w.add_text(s, "dcterms:identifier", d["id"])
        w.add_text(s, "dcterms:title", d.get("statement"))
        w.add_text(s, "rlg:rationale", d.get("rationale"))
        w.add_text(s, "rlg:sourceDocument", d.get("source"))
        if d.get("scope"):
            scope = w.iri("scope", d["scope"])
            w.add(s, "rlg:scope", scope)
            scopes.add((scope, d["scope"]))
        if d.get("when"):
            ms = w.iri("milestone", d["when"])
            w.add(s, "rlg:decidedDuring", ms)
            milestones.add((ms, d["when"]))

    for iri, label in sorted(scopes):
        w.add(iri, "a", "rlg:Scope")
        w.add_text(iri, "rdfs:label", label)
    for iri, label in sorted(milestones):
        w.add(iri, "a", "rlg:Milestone")
        w.add_text(iri, "rdfs:label", label)


@contributor("gsd-rules", requires=["conventions.rules"])
def rules(ctx, w) -> None:
    """Rules, and whether each one is actually enforceable."""
    for r in (ctx.facts.get("conventions") or {}).get("rules") or []:
        s = w.iri("rule", r["id"])
        w.add(s, "a", "rlg:Rule")
        w.add_text(s, "dcterms:identifier", r["id"])
        w.add_text(s, "dcterms:title", r.get("statement"))
        w.add_text(s, "rlg:rationale", r.get("rationale"))
        commands = r.get("candidate_commands") or []
        w.add(s, "rlg:checkable", w.boolean(bool(commands)))
        for cmd in commands:
            w.add_text(s, "rlg:command", cmd)


@contributor("gsd-links", requires=["decision_links"])
def links(ctx, w) -> None:
    """What each decision governs, and how that was arrived at.

    Read from the published link map rather than from each node's decision
    list: that list is capped for the inspector, and emitting from it silently
    dropped every link past the twelfth on a part.

    Every link is written twice — once as a plain triple so a query needs no
    join, and once as a resource carrying the word that caused a guess. A link
    a person made carries no word and says so.
    """
    guessed = authored = 0
    known = {n["id"] for n in ctx.model.get("nodes") or []}
    for dec_id, lns in sorted((ctx.facts.get("decision_links") or {}).items()):
        s = _decision_iri(w, dec_id)
        for ln in lns:
            kind = ln.get("kind", "part")
            if kind == "part":
                if ln["to"] not in known:
                    continue
                target = part_iri(w, ln["to"])
                target_slug = ln["to"]
            elif kind == "file":
                target = w.iri("file", ln["to"])
                target_slug = ln["to"]
            elif kind == "sym":
                path, _, name = ln["to"].partition("#")
                target = w.iri("symbol", path, name)
                target_slug = ln["to"].replace("#", "/")
            else:
                continue

            w.add(s, "rlg:governs", target)
            link = w.iri("declink", dec_id, target_slug)
            w.add(link, "a", "rlg:DecisionLink")
            w.add(link, "rl:source", s)
            w.add(link, "rl:target", target)
            matched = ln.get("src", "matched") == "matched"
            w.add(link, "rl:provenance", "rl:measured" if matched else "rl:authored")
            for word in ln.get("why") or []:
                w.add_text(link, "rlg:matchedWord", word)
            guessed += 1 if matched else 0
            authored += 0 if matched else 1
    ctx.metric("graph.decision_links.guessed", guessed)
    ctx.metric("graph.decision_links.authored", authored)
