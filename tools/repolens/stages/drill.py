"""File-level drill-down inside a node.

The survey nodeset answers "how big is this box". This stage answers "what is
inside it": the individual files, how they import each other, and how often the
box reaches out to a different box.

Everything here is derived from facts that earlier stages already produced —
`files` for line counts, `nodesets` for membership. Nothing is re-globbed.

Language knowledge lives in `..resolvers`, one module per language, so this
stage is language-agnostic: it reads a member, asks whichever resolver claims
the extension what that file imports, and sorts the answers into sibling
edges, hops to another node, and third-party packages. Members whose extension
no resolver claims (CSS, HTML, nginx.conf) still appear in `files` so the
drawing can list them; they simply contribute no edges.
"""

from __future__ import annotations

from collections import defaultdict

from ..pipeline import Context, stage
from ..resolvers import Bound
from .code import _read          # shared text cache — read each file once


# --------------------------------------------------------------------------
# id shortening
# --------------------------------------------------------------------------

def _common_prefix(paths: list[str]) -> str:
    """Longest shared *directory* prefix of a node's members, with trailing /.

    Stripping it keeps ids short ("store.py") while staying unique inside the
    node, because the full paths were unique to begin with.
    """
    if not paths:
        return ""
    if len(paths) == 1:
        head = paths[0].rsplit("/", 1)
        return head[0] + "/" if len(head) == 2 else ""
    segs = [p.split("/")[:-1] for p in paths]
    shared: list[str] = []
    for parts in zip(*segs):
        if len(set(parts)) != 1:
            break
        shared.append(parts[0])
    return "/".join(shared) + "/" if shared else ""


# --------------------------------------------------------------------------
# the stage
# --------------------------------------------------------------------------

@stage("drilldown", requires=["files", "nodesets"], provides=["drilldown"])
def drilldown(ctx: Context) -> None:
    """Files inside each survey node and the imports between them."""
    ns_id = (ctx.config.get("model") or {}).get("nodeset", "survey")
    nodes = ctx.facts.get("nodesets", {}).get(ns_id) or []
    if not nodes:
        ctx.log(f"nodeset '{ns_id}' is empty — nothing to drill into")
        ctx.facts["drilldown"] = {}
        return

    by_path = {f["path"]: f for f in ctx.facts.get("files", [])}
    langs = Bound(ctx, set(by_path))

    # path -> owning node, built once and shared by every node's external pass.
    # First declaration wins if two nodes' globs overlap.
    owner: dict[str, str] = {}
    for n in nodes:
        for p in n["members"]:
            owner.setdefault(p, n["id"])

    out: dict[str, dict] = {}
    tot_files = tot_edges = tot_pkg_refs = 0
    all_packages: dict[str, int] = defaultdict(int)

    for n in nodes:
        members = list(n["members"])
        prefix = _common_prefix(members)
        fid = {p: (p[len(prefix):] if prefix and p.startswith(prefix) else p)
               for p in members}
        member_set = set(members)

        files = []
        for p in members:
            f = by_path.get(p, {})
            files.append({
                "id": fid[p],
                "path": p,
                "name": p.rsplit("/", 1)[-1],
                "lines": f.get("lines", 0),
                "lang": f.get("lang", "other"),
            })

        pairs: dict[tuple[str, str], int] = defaultdict(int)
        external: dict[str, int] = defaultdict(int)
        packages: dict[str, int] = defaultdict(int)

        for p in members:
            if not langs.handles(p):
                continue
            found = langs.resolve(p, _read(ctx, p))
            for dst in found.targets:
                if dst == p:
                    continue
                if dst in member_set:
                    pairs[(fid[p], fid[dst])] += 1
                else:
                    other = owner.get(dst)
                    if other and other != n["id"]:
                        external[other] += 1
            for name in found.packages:
                packages[name] += 1
                all_packages[name] += 1
                tot_pkg_refs += 1

        edges = [{"from": a, "to": b, "kind": "import", "weight": w}
                 for (a, b), w in sorted(pairs.items(), key=lambda kv: (-kv[1], kv[0]))]

        out[n["id"]] = {
            "files": files,
            "edges": edges,
            "external": [{"to_node": k, "count": v}
                         for k, v in sorted(external.items(), key=lambda kv: -kv[1])],
            # Third-party specifiers that resolve to no file here. Not drawable
            # — there is nothing to draw an edge to — but a part that pulls in
            # twelve packages is a different kind of part from one that pulls
            # in none, and that is worth measuring.
            "packages": [{"name": k, "count": v}
                         for k, v in sorted(packages.items(), key=lambda kv: (-kv[1], kv[0]))],
        }
        tot_files += len(files)
        tot_edges += len(edges)

    ctx.facts["drilldown"] = out
    ctx.metric("drilldown.nodes", len(out))
    ctx.metric("drilldown.files", tot_files)
    ctx.metric("drilldown.edges", tot_edges)
    ctx.metric("drilldown.package_refs", tot_pkg_refs)
    ctx.metric("drilldown.packages", len(all_packages))
    for msg in langs.notes():
        ctx.log(msg)
    if all_packages:
        top = sorted(all_packages.items(), key=lambda kv: (-kv[1], kv[0]))[:4]
        ctx.log(f"{tot_pkg_refs} bare specifiers to {len(all_packages)} packages "
                f"({', '.join(f'{k} ×{v}' for k, v in top)})")
    ctx.log(f"{len(out)} nodes, {tot_files} files, {tot_edges} intra-node import edges")
