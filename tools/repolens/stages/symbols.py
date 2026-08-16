"""Symbol-level drill-down inside a file.

Third level of the drill: repo → part → file → **symbols**. Where `drilldown`
answers "what files are in this box, and which of them import each other", this
one answers "what is *in* a file, and which of those things call each other".

Output is keyed by repo-relative file path:

    {"backend/app/events/store.py": {
        "symbols":  [{id, name, kind, line, end_line, lines, parent, doc}, ...],
        "edges":    [{"from": id, "to": id, "kind": "call"}, ...],
        "imported": ["URIRef", "Literal", ...],
     }}

Two extractors, and the difference between them is declared rather than hidden:

  * **Python** is parsed with `ast`. Line spans, nesting and call edges are
    real. A file this interpreter cannot parse (the repo targets a newer Python
    than repolens may run on — PEP 701 f-strings need 3.12+) is counted, logged
    and skipped. One bad file never kills the stage.

  * **JS/TS** is scanned with regexes over brace-depth-tracked text. Strings,
    comments and regex literals are blanked first so the depth counter and the
    declaration patterns cannot be fooled by their contents. Every symbol it
    produces carries `"approx": true`, and so does the file entry, so the page
    can say so out loud instead of implying a parse that never happened.

Scope is bounded on purpose. Extracting symbols for every file in the tree
would cost more than the rest of the build and bloat the model with modules
nobody drills into. The default is the members of the drawing's nodeset;
`symbols.scope` overrides it, `symbols.max_files` caps it.
"""

from __future__ import annotations

import ast
import re
from bisect import bisect_right

from ..pipeline import Context, stage
from .code import _read          # shared text cache — read each file once


PY_EXT = (".py",)
JS_EXT = (".js", ".mjs", ".jsx", ".ts", ".tsx")

DEFAULT_MAX_FILES = 400
DEFAULT_MAX_BYTES = 250_000       # above this it is generated or minified
DEFAULT_DOC_CHARS = 120


# --------------------------------------------------------------------------
# shared helpers
# --------------------------------------------------------------------------

def _first_doc_line(doc: str | None, limit: int) -> str:
    """First meaningful line of a docstring, collapsed and truncated."""
    if not doc:
        return ""
    for raw in doc.strip().splitlines():
        line = " ".join(raw.split())
        if line:
            return line if len(line) <= limit else line[: limit - 1].rstrip() + "…"
    return ""


# --------------------------------------------------------------------------
# python — real parse
# --------------------------------------------------------------------------

_FUNC = (ast.FunctionDef, ast.AsyncFunctionDef)

# Names that look like calls but say nothing about this file's structure.
_CALL_NOISE = {"len", "str", "int", "list", "dict", "set", "print", "super"}


def _py_symbols(tree: ast.Module, doc_chars: int) -> list[dict]:
    """Module functions, classes, and the methods (and nested classes) inside.

    Descends into class bodies only. A closure defined inside a function is not
    a symbol of its own — its calls are attributed to the function that owns it,
    which is the level anyone drilling in actually asked about.
    """
    out: list[dict] = []

    def visit(body, parent_id: str | None) -> None:
        for node in body:
            if isinstance(node, _FUNC):
                name = node.name
                sid = f"{parent_id}.{name}" if parent_id else name
                out.append({
                    "id": sid,
                    "name": name,
                    "kind": "method" if parent_id else "function",
                    "line": node.lineno,
                    "end_line": node.end_lineno or node.lineno,
                    "lines": (node.end_lineno or node.lineno) - node.lineno + 1,
                    "parent": parent_id,
                    "doc": _first_doc_line(ast.get_docstring(node), doc_chars),
                })
            elif isinstance(node, ast.ClassDef):
                name = node.name
                sid = f"{parent_id}.{name}" if parent_id else name
                out.append({
                    "id": sid,
                    "name": name,
                    "kind": "class",
                    "line": node.lineno,
                    "end_line": node.end_lineno or node.lineno,
                    "lines": (node.end_lineno or node.lineno) - node.lineno + 1,
                    "parent": parent_id,
                    "doc": _first_doc_line(ast.get_docstring(node), doc_chars),
                })
                visit(node.body, sid)

    visit(tree.body, None)
    out.sort(key=lambda s: (s["line"], s["id"]))
    return out


def _enclosing(symbols: list[dict], starts: list[int], line: int) -> dict | None:
    """Innermost recorded symbol whose span contains `line`.

    Attribution is by line rather than by re-walking each symbol's subtree.
    Spans nest, so the last symbol that starts at or before the line and still
    contains it is the innermost one — and this costs one bisect instead of a
    second traversal per symbol, which was most of the stage's runtime.
    """
    i = bisect_right(starts, line) - 1
    while i >= 0:
        s = symbols[i]
        if s["end_line"] >= line:
            return s
        i -= 1
    return None


def _py_edges(symbols: list[dict], calls: list[ast.Call]) -> list[dict]:
    """Calls from one symbol in this file to another symbol in this file.

    Bare names resolve against module-level definitions. Attribute calls
    (`self.foo()`, `client.commit()`) resolve to a method only when the name
    picks out exactly one — with a same-class match preferred for `self`/`cls`.
    Anything ambiguous is dropped rather than guessed: a wrong edge on a drawing
    is worse than a missing one, because nobody can tell it is wrong by looking.
    """
    top: dict[str, str] = {s["name"]: s["id"] for s in symbols if s["parent"] is None}
    by_id = {s["id"]: s for s in symbols}
    by_method: dict[str, list[str]] = {}
    for s in symbols:
        if s["kind"] == "method":
            by_method.setdefault(s["name"], []).append(s["id"])

    starts = [s["line"] for s in symbols]
    seen: set[tuple[str, str]] = set()
    edges: list[dict] = []

    for call in calls:
        func = call.func
        if isinstance(func, ast.Name):
            name, on_self = func.id, False
            if name in _CALL_NOISE or name not in top:
                continue
        elif isinstance(func, ast.Attribute):
            name = func.attr
            on_self = (isinstance(func.value, ast.Name)
                       and func.value.id in ("self", "cls"))
            if name not in by_method:
                continue
        else:
            continue

        sym = _enclosing(symbols, starts, call.lineno)
        if sym is None:                       # module-level code owns no symbol
            continue

        if isinstance(func, ast.Name):
            target = top.get(name)
        else:
            cands = by_method.get(name, [])
            owner = sym["parent"] if sym["kind"] == "method" else (
                sym["id"] if sym["kind"] == "class" else None)
            same = f"{owner}.{name}" if owner else None
            if on_self and same in by_id:
                target = same
            elif len(cands) == 1 and (on_self or name not in top):
                # unique method name, and not shadowed by a module-level
                # function of the same name — safe to attribute
                target = cands[0]
            else:
                target = None

        if not target or target == sym["id"]:
            continue
        key = (sym["id"], target)
        if key in seen:
            continue
        seen.add(key)
        edges.append({"from": sym["id"], "to": target, "kind": "call"})

    return edges


def _extract_python(text: str, path: str, doc_chars: int) -> dict:
    tree = ast.parse(text, filename=path)          # SyntaxError handled by caller
    symbols = _py_symbols(tree, doc_chars)

    # One traversal for both imports and call sites. Two separate ast.walk
    # passes over every module was the second-largest cost in this stage.
    imported: set[str] = set()
    calls: list[ast.Call] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            calls.append(node)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in node.names:
                if alias.name != "*":
                    imported.add(alias.asname or alias.name.split(".")[0])

    return {
        "symbols": symbols,
        "edges": _py_edges(symbols, calls) if symbols else [],
        "imported": sorted(imported),
    }


# --------------------------------------------------------------------------
# js/ts — declared approximation
# --------------------------------------------------------------------------

_JS_SCAN = re.compile(r"//|/\*|[\"'`/]")
_NOT_NL = re.compile(r"[^\n]")
_REGEX_PREV = set("(,=:[!&|?{};+-*%^~<>") | {""}


def _blanked(segment: str) -> str:
    """The segment with every non-newline character replaced by a space."""
    return _NOT_NL.sub(" ", segment)


def _blank_js(text: str) -> str:
    """Replace string, comment and regex-literal contents with spaces.

    Line structure and length are preserved, so line numbers still line up.
    Blanking first is what makes a brace counter and a set of `^\\s*function`
    patterns trustworthy: a `{` inside a template literal or a `/\\d{2}/`
    regex no longer moves the depth, and a declaration quoted inside a string
    no longer registers as a declaration.

    The scan jumps between interesting characters with a compiled pattern and
    copies the ordinary stretches wholesale. A character-at-a-time version of
    this was the single most expensive thing in the stage; most of a JS file is
    not a quote.
    """
    n = len(text)
    parts: list[str] = []
    i = 0
    prev = ""                    # last significant char, for regex-vs-divide

    while i < n:
        m = _JS_SCAN.search(text, i)
        if not m:
            parts.append(text[i:])
            break
        start = m.start()
        if start > i:
            plain = text[i:start]
            parts.append(plain)
            stripped = plain.rstrip()
            if stripped:
                prev = stripped[-1]
        tok = m.group(0)

        if tok == "//":
            j = text.find("\n", start)
            j = n if j < 0 else j
        elif tok == "/*":
            j = text.find("*/", start + 2)
            j = n if j < 0 else j + 2
        elif tok in "\"'`":
            j = start + 1
            while j < n:
                ch = text[j]
                if ch == "\\":
                    j += 2
                    continue
                if ch == tok:
                    j += 1
                    break
                if ch == "\n" and tok != "`":
                    break        # unterminated quote; do not eat the file
                j += 1
            prev = "x"
        else:                    # a bare '/' — regex literal, or division
            if prev not in _REGEX_PREV:
                parts.append("/")
                prev = "/"
                i = start + 1
                continue
            j, in_class, closed = start + 1, False, False
            while j < n and text[j] != "\n":
                ch = text[j]
                if ch == "\\":
                    j += 2
                    continue
                if ch == "[":
                    in_class = True
                elif ch == "]":
                    in_class = False
                elif ch == "/" and not in_class:
                    j += 1
                    closed = True
                    break
                j += 1
            if not closed:       # not a regex after all
                parts.append("/")
                prev = "/"
                i = start + 1
                continue
            prev = "x"

        parts.append(_blanked(text[start:j]))
        i = j
    return "".join(parts)


_JS_FUNC = re.compile(
    r"^\s*(?:export\s+(?:default\s+)?)?(?:async\s+)?function\s*\*?\s*"
    r"([A-Za-z_$][\w$]*)\s*\(")
_JS_ARROW = re.compile(
    r"^\s*(?:export\s+)?(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*"
    r"(?:async\s+)?(?:\([^;]*\)|[A-Za-z_$][\w$]*)\s*=>")
_JS_FUNCEXPR = re.compile(
    r"^\s*(?:export\s+)?(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*"
    r"(?:async\s+)?function\b")
_JS_CLASS = re.compile(
    r"^\s*(?:export\s+(?:default\s+)?)?class\s+([A-Za-z_$][\w$]*)")
_JS_METHOD = re.compile(
    r"^\s*(?:static\s+)?(?:async\s+)?(?:get\s+|set\s+)?\*?\s*"
    r"([A-Za-z_$#][\w$]*)\s*\([^;{]*\)\s*\{")
_JS_IMPORT_FROM = re.compile(r"^\s*import\s+(.+?)\s+from\s", re.M)
_JS_REQUIRE = re.compile(
    r"(?:const|let|var)\s+(\{[^}]*\}|[A-Za-z_$][\w$]*)\s*=\s*require\s*\(")

_JS_KEYWORDS = {
    "if", "for", "while", "switch", "catch", "do", "else", "return", "function",
    "class", "try", "finally", "with", "case", "typeof", "await", "new", "delete",
}


def _depths(lines: list[str]) -> tuple[list[int], list[int]]:
    """Brace depth before and after each line of already-blanked text."""
    before, after = [], []
    d = 0
    for line in lines:
        before.append(d)
        d += line.count("{") - line.count("}")
        after.append(d)
    return before, after


def _close_at(after: list[int], start: int, base: int) -> int:
    """1-based line where a block opened on `start` returns to depth `base`."""
    for j in range(start, len(after)):
        if after[j] <= base:
            return j + 1
    return len(after)


def _extract_js(text: str, doc_chars: int) -> dict:
    clean = _blank_js(text)
    lines = clean.split("\n")
    raw_lines = text.split("\n")
    before, after = _depths(lines)

    symbols: list[dict] = []
    claimed: set[int] = set()          # line indexes already inside a class body

    def add(name: str, kind: str, i: int, end: int, parent: str | None) -> None:
        symbols.append({
            "id": f"{parent}.{name}" if parent else name,
            "name": name,
            "kind": kind,
            "line": i + 1,
            "end_line": end,
            "lines": max(1, end - i),
            "parent": parent,
            "doc": _jsdoc(raw_lines, i, doc_chars),
            "approx": True,
        })

    # classes first, so their bodies can claim their methods
    for i, line in enumerate(lines):
        m = _JS_CLASS.match(line)
        if not m:
            continue
        end = _close_at(after, i, before[i])
        add(m.group(1), "class", i, end, None)
        cls = m.group(1)
        body_depth = before[i] + 1
        for k in range(i + 1, min(end, len(lines))):
            claimed.add(k)
            if before[k] != body_depth:
                continue
            mm = _JS_METHOD.match(lines[k])
            if not mm or mm.group(1) in _JS_KEYWORDS:
                continue
            add(mm.group(1), "method", k, _close_at(after, k, before[k]), cls)

    for i, line in enumerate(lines):
        if i in claimed:
            continue
        m = _JS_FUNC.match(line) or _JS_FUNCEXPR.match(line) or _JS_ARROW.match(line)
        if not m or m.group(1) in _JS_KEYWORDS:
            continue
        end = i + 1 if after[i] <= before[i] else _close_at(after, i, before[i])
        add(m.group(1), "function", i, end, None)

    symbols.sort(key=lambda s: (s["line"], s["id"]))
    return {
        "symbols": symbols,
        "edges": _js_edges(lines, symbols),
        "imported": _js_imported(clean, text),
        "approx": True,
    }


def _jsdoc(raw_lines: list[str], i: int, limit: int) -> str:
    """The `//` or `/** */` line immediately above a declaration, if any."""
    k = i - 1
    while k >= 0 and not raw_lines[k].strip():
        k -= 1
    if k < 0:
        return ""
    prev = raw_lines[k].strip()
    if prev.startswith("//"):
        return _first_doc_line(prev.lstrip("/ "), limit)
    if prev.startswith("*") or prev.startswith("/*"):
        body = prev.lstrip("/* ").rstrip("*/ ")
        return _first_doc_line(body, limit)
    return ""


def _js_edges(lines: list[str], symbols: list[dict]) -> list[dict]:
    """Same-file calls, by name, inside each symbol's line span.

    Only names declared at the top of this file are considered targets, and
    only bare `name(` call sites count — `obj.name()` is left alone because
    nothing here knows what `obj` is.
    """
    top = {s["name"]: s["id"] for s in symbols if s["parent"] is None}
    if not top:
        return []
    rx = re.compile(r"(?<![\w$.])(" + "|".join(re.escape(n) for n in top) + r")\s*\(")
    decl = re.compile(r"\b(?:function|class|const|let|var)\b")

    seen: set[tuple[str, str]] = set()
    edges: list[dict] = []
    for sym in symbols:
        for k in range(sym["line"] - 1, min(sym["end_line"], len(lines))):
            line = lines[k]
            if k == sym["line"] - 1 and decl.search(line):
                continue                          # the declaration itself
            for name in rx.findall(line):
                target = top[name]
                if target == sym["id"]:
                    continue
                key = (sym["id"], target)
                if key in seen:
                    continue
                seen.add(key)
                edges.append({"from": sym["id"], "to": target, "kind": "call"})
    return edges


def _js_imported(clean: str, text: str) -> list[str]:
    names: set[str] = set()
    for clause in _JS_IMPORT_FROM.findall(clean):
        for part in clause.replace("{", " ").replace("}", " ").split(","):
            token = part.strip().split(" as ")[-1].strip()
            if token and token != "*" and re.fullmatch(r"[A-Za-z_$][\w$]*", token):
                names.add(token)
    for clause in _JS_REQUIRE.findall(clean):
        for part in clause.strip("{}").split(","):
            token = part.strip().split(":")[-1].strip()
            if token and re.fullmatch(r"[A-Za-z_$][\w$]*", token):
                names.add(token)
    return sorted(names)


# --------------------------------------------------------------------------
# scope
# --------------------------------------------------------------------------

def _candidates(ctx: Context, spec: dict) -> list[dict]:
    """Which files to open, and in what order they survive the cap.

    Declared scope wins. Otherwise the drawing's own nodeset decides: the files
    someone can actually drill into are exactly the files worth extracting.
    """
    scope = spec.get("scope")
    by_path = {f["path"]: f for f in ctx.facts.get("files", [])}

    if scope:
        if isinstance(scope, str):
            scope = [scope]
        picked = ctx.match(scope)
        ctx.log(f"scope: {len(picked)} file(s) from {len(scope)} pattern(s)")
    else:
        ns_id = (ctx.config.get("model") or {}).get("nodeset", "survey")
        nodes = ctx.facts.get("nodesets", {}).get(ns_id) or []
        paths: list[str] = []
        seen: set[str] = set()
        for n in nodes:
            for p in n["members"]:
                if p not in seen:
                    seen.add(p)
                    paths.append(p)
        picked = [by_path[p] for p in paths if p in by_path]
        ctx.log(f"scope: nodeset '{ns_id}', {len(picked)} member file(s)")

    exts = tuple(PY_EXT) + tuple(JS_EXT)
    return [f for f in picked if f["path"].endswith(exts)]


# --------------------------------------------------------------------------
# the stage
# --------------------------------------------------------------------------

@stage("symbols", requires=["files", "nodesets"], provides=["symbols"])
def symbols(ctx: Context) -> None:
    """Functions, classes and methods per file, and the calls between them."""
    spec = ctx.config.get("symbols") or {}
    max_files = int(spec.get("max_files", DEFAULT_MAX_FILES))
    max_bytes = int(spec.get("max_bytes", DEFAULT_MAX_BYTES))
    doc_chars = int(spec.get("doc_chars", DEFAULT_DOC_CHARS))

    files = _candidates(ctx, spec)

    oversized = [f for f in files if f.get("bytes", 0) > max_bytes]
    files = [f for f in files if f.get("bytes", 0) <= max_bytes]
    if oversized:
        ctx.log(f"{len(oversized)} file(s) over {max_bytes:,}B skipped: "
                + ", ".join(f["path"] for f in oversized[:3]))

    if len(files) > max_files:
        # Keep the biggest: they hold the most symbols per file opened, and
        # they are what anyone drilling in is looking for.
        files = sorted(files, key=lambda f: (-f.get("lines", 0), f["path"]))[:max_files]
        ctx.log(f"capped at max_files={max_files} (largest first)")

    out: dict[str, dict] = {}
    total = edge_total = 0
    failed: list[str] = []

    for f in sorted(files, key=lambda f: f["path"]):
        path = f["path"]
        text = _read(ctx, path)
        if not text.strip():
            continue
        try:
            if path.endswith(PY_EXT):
                entry = _extract_python(text, path, doc_chars)
            else:
                entry = _extract_js(text, doc_chars)
        except SyntaxError:
            # The repo may target a newer Python than repolens runs on (PEP 701
            # f-strings need 3.12+). One unparseable file loses that file's
            # symbols, never the stage.
            failed.append(path)
            continue
        except (ValueError, RecursionError) as e:      # pragma: no cover
            failed.append(path)
            ctx.log(f"{path}: {type(e).__name__} — skipped")
            continue
        if not entry["symbols"]:
            continue
        out[path] = entry
        total += len(entry["symbols"])
        edge_total += len(entry["edges"])

    ctx.facts["symbols"] = out
    ctx.metric("symbols.files", len(out))
    ctx.metric("symbols.total", total)
    ctx.metric("symbols.edges", edge_total)
    ctx.metric("symbols.unparsed", len(failed))

    if failed:
        ctx.log(f"{len(failed)} file(s) did not parse and were skipped: "
                + ", ".join(failed[:5]))
    ctx.log(f"{total} symbols across {len(out)} files, {edge_total} call edges")
