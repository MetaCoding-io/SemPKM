"""ONE-TIME PORT SCRIPT — kept for the record, not part of the build.

The template it produced (tools/repolens/template/page.html) is now the source
of truth for the renderer and is edited directly. Re-running this against the
original hand-authored artifact would discard everything added since.

Turn the authored artifact into a data-driven template.

The renderer and the data were written together; this lifts the data out and
leaves a page that eats a model. Every substitution asserts, so a change to the
source page that breaks an anchor fails here rather than silently shipping a
half-templated file.

    python3 -m tools.repolens.make_template <source.html> <out.html>
"""

from __future__ import annotations

import re
import sys
from pathlib import Path


def cut_block(src: str, opener: str, closer: str = "\n];") -> tuple[str, str]:
    """Return (block_text, src_without_block)."""
    i = src.index(opener)
    j = src.index(closer, i) + len(closer)
    return src[i:j], src[:i] + "\x00PLACEHOLDER\x00" + src[j:]


def replace_block(src: str, opener: str, replacement: str, closer: str = "\n];") -> str:
    if opener not in src:
        raise SystemExit(f"anchor not found: {opener!r}")
    i = src.index(opener)
    j = src.index(closer, i) + len(closer)
    return src[:i] + replacement + src[j:]


def sub_once(src: str, old: str, new: str, what: str) -> str:
    if src.count(old) != 1:
        raise SystemExit(f"expected exactly one {what}; found {src.count(old)}")
    return src.replace(old, new)


def build(src: str) -> str:
    # ---- 1. data blocks become model reads --------------------------------
    src = replace_block(src, "var NODES = [", """var MODEL = /*__MODEL__*/null;

/* Every array below is data now. The renderer past this point is unchanged
   from the hand-authored page — it just reads a model instead of literals. */
var NODES = MODEL.nodes;""")

    src = replace_block(src, "var FLOWS = {", """var FLOWS = {};
MODEL.flows.forEach(function (f) { FLOWS[f.id] = { label: f.label, on: !!f.enabled }; });""",
                        closer="\n};")

    src = replace_block(src, "var EDGES = [", "var EDGES = MODEL.edges;")
    src = replace_block(src, "var FINDINGS = [", "var FINDINGS = MODEL.findings;")
    src = replace_block(src, "var SYSTEM = {", "var SYSTEM = MODEL.system;", closer="\n};")
    src = replace_block(src, "var GROUPS = [", "var GROUPS = MODEL.groups;")

    # ---- 2. layout band labels come from the model ------------------------
    src = sub_once(src, """      var TIERS = [
        "Surfaces", "Edge & identity", "Routers", "Write & orchestration",
        "Domain services", "Access", "Resources"
      ];""", "      var TIERS = MODEL.tiers;", "TIERS literal")

    src = sub_once(src, """      var ORDER = ["client", "manager", "engine", "access", "resource"];
      var LABELS = { client:"Clients", manager:"Managers", engine:"Engines",
                     access:"Resource access", resource:"Resources" };""",
                   """      var STACKED = MODEL.layers.filter(function (l) { return !l.side; });
      var ORDER = STACKED.map(function (l) { return l.id; });
      var LABELS = {};
      MODEL.layers.forEach(function (l) { LABELS[l.id] = l.label; });
      var SIDE = MODEL.layers.filter(function (l) { return l.side; })[0];""",
                   "layer literal")

    src = sub_once(src,
                   """      var utils = NODES.filter(function (n) { return n.layer === "utility"; });
      layRow(utils, -TIER_GAP, 0, "Utilities · any band may call");""",
                   """      if (SIDE) {
        var utils = NODES.filter(function (n) { return n.layer === SIDE.id; });
        layRow(utils, -TIER_GAP, 0, SIDE.label);
      }""", "utilities row")

    # ---- 3. the top bar renders from the model ----------------------------
    bar_start = src.index('<div class="repo-cell">')
    bar_end = src.index('<div id="topbar-actions">')
    src = src[:bar_start] + '<div class="repo-cell" id="repo-cell"></div>\n    ' + src[bar_end:]

    src = sub_once(src, "buildRail();", """paintTopbar();
buildRail();""", "boot hook")

    src = sub_once(src, "/* ============================================================\n   9. LEFT RAIL",
                   """function paintTopbar() {
  var cell = document.getElementById("repo-cell");
  cell.innerHTML = "";
  var b = document.createElement("b"); b.textContent = MODEL.repo.name;
  var s = document.createElement("span"); s.textContent = "\u00a0" + (MODEL.repo.tagline || "");
  cell.appendChild(b); cell.appendChild(s);

  var bar = document.getElementById("topbar");
  var anchor = document.getElementById("topbar-actions");
  (MODEL.repo.stats || []).forEach(function (st) {
    var d = document.createElement("div");
    d.className = "stat";
    var k = document.createElement("span"); k.className = "stat-k"; k.textContent = st.k;
    var v = document.createElement("span");
    v.className = "stat-v" + (st.flag === "bad" ? " bad" : "");
    v.textContent = st.v;
    d.appendChild(k); d.appendChild(v);
    bar.insertBefore(d, anchor);
  });
}

/* ============================================================
   9. LEFT RAIL""", "topbar painter insertion point")

    if "/*__MODEL__*/null" not in src:
        raise SystemExit("model placeholder missing from output")
    return src


def main(argv):
    if len(argv) != 3:
        raise SystemExit(__doc__)
    src = Path(argv[1]).read_text(encoding="utf-8")
    out = Path(argv[2])
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(build(src), encoding="utf-8")
    print(f"template written: {out} ({out.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main(sys.argv)
