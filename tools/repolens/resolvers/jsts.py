"""JavaScript / TypeScript import resolution.

Where Python names a module and lets the interpreter find the file, JS names
a *path fragment* and lets a bundler finish the job: `./y` may mean `y.ts`,
`y.js` or `y/index.tsx`, and in ESM-flavoured TypeScript `./y.js` routinely
means `y.ts`. There is no import system to ask, so the guessing is done here,
against the file index the discover stage already produced. A guess that hits
nothing is discarded, which is what keeps the false-positive rate low: the
repo itself is the filter.

Two things are deliberately *not* done. No node_modules is read — a bare
specifier is counted as a package and never becomes an edge. And no tsconfig
`paths` aliases are honoured; an alias like `@app/thing` is indistinguishable
from a scoped package here, so it lands in the package count where it is at
least visible.
"""

from __future__ import annotations

import re
from typing import Iterable

from ..pipeline import Context
from . import Language, Resolution, register


EXTENSIONS = (".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx", ".mts", ".cts")

# Tried in this order after the literal path. TS first: TS source writing
# "./y" nearly always means y.ts, and trying .js first would pick up a build
# artefact sitting next to the source.
_TRY = (".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs")

# ESM TypeScript writes the *emitted* extension in the specifier. If "./y.js"
# is not a real file, "./y.ts" usually is.
_REWRITE = {".js": (".ts", ".tsx"), ".jsx": (".tsx",),
            ".mjs": (".mts", ".ts"), ".cjs": (".cts", ".ts")}


# --------------------------------------------------------------------------
# masking comments and template literals
# --------------------------------------------------------------------------

# One left-to-right scan. Quoted strings are recognised so that a `//`, a `/*`
# or a stray backtick *inside* a string cannot open a comment or a template —
# without that, one unbalanced backtick blanks the rest of the file. The
# strings themselves survive: an import specifier is one.
_TOKEN = re.compile(
    r"(//[^\n]*)"                      # 1 line comment      -> blank
    r"|(/\*.*?\*/)"                    # 2 block comment     -> blank
    r"|(`(?:[^`\\]|\\.)*`)"            # 3 template literal  -> blank
    r"|('(?:[^'\\\n]|\\.)*')"          # 4 single-quoted     -> keep
    r'|("(?:[^"\\\n]|\\.)*")',         # 5 double-quoted     -> keep
    re.S,
)


def _blank(m: re.Match) -> str:
    if m.group(1) or m.group(2) or m.group(3):
        return " " * (m.end() - m.start())
    return m.group(0)


def _mask(text: str) -> str:
    """Comments and template literals replaced by blanks of the same width.

    A commented-out import must not draw an edge, and a template literal that
    happens to contain the word `import` (test fixtures do this) must not
    either. Width is preserved so offsets stay meaningful for anything that
    later wants them.
    """
    return _TOKEN.sub(_blank, text)


# --------------------------------------------------------------------------
# finding specifiers
# --------------------------------------------------------------------------

_Q = r"(['\"])([^'\"\n]+)\1"

# The clause between `import`/`export` and `from` may span lines but never
# contains a quote, a semicolon or a paren — which both keeps the match tight
# and stops `export function f(` from running away looking for a `from`. The
# length bound is belt and braces against a pathological file.
_RX_FROM = re.compile(r"\b(?:import|export)\b[^;'\"`()]{0,400}?\bfrom\s*" + _Q)
_RX_SIDE_EFFECT = re.compile(r"\bimport\s*" + _Q)          # import "./y"
_RX_DYNAMIC = re.compile(r"\bimport\s*\(\s*" + _Q)         # await import("./y")
_RX_REQUIRE = re.compile(r"\brequire\s*\(\s*" + _Q)        # const x = require("./y")

_PATTERNS = (_RX_FROM, _RX_SIDE_EFFECT, _RX_DYNAMIC, _RX_REQUIRE)

# The four forms cannot overlap: `from` needs a bare word after the keyword,
# the side-effect form needs a quote, the dynamic form needs a paren.


def _specifiers(masked: str) -> Iterable[str]:
    """Every import specifier in the file, with multiplicity."""
    for rx in _PATTERNS:
        for m in rx.finditer(masked):
            yield m.group(2)


# --------------------------------------------------------------------------
# turning a specifier into a repo path
# --------------------------------------------------------------------------

def _clean(spec: str) -> str:
    """Drop a bundler query or fragment: './y?raw', './y#frag'."""
    for sep in ("?", "#"):
        cut = spec.find(sep)
        if cut != -1:
            spec = spec[:cut]
    return spec


def _join(base_dir: str, spec: str) -> str | None:
    """Normalise a relative specifier against the importing file's directory."""
    parts = base_dir.split("/") if base_dir else []
    for seg in spec.split("/"):
        if seg in ("", "."):
            continue
        if seg == "..":
            if not parts:
                return None                 # climbed out of the repo
            parts.pop()
        else:
            parts.append(seg)
    return "/".join(parts) if parts else None


def _ext_of(path: str) -> str:
    dot = path.rfind(".")
    return path[dot:] if dot > path.rfind("/") else ""


def _candidates(stem: str) -> list[str]:
    """Every file a specifier could mean, best guess first."""
    out = [stem]
    out += [stem + e for e in _TRY]
    out += [f"{stem}/index{e}" for e in _TRY]
    for emitted, sources in _REWRITE.items():
        if stem.endswith(emitted):
            base = stem[: -len(emitted)]
            out += [base + s for s in sources]
            break
    return out


def _package(spec: str) -> str:
    """The installable name behind a bare specifier: '@scope/pkg/sub' -> '@scope/pkg'."""
    parts = spec.split("/")
    if spec.startswith("@") and len(parts) >= 2:
        return "/".join(parts[:2])
    return parts[0]


class _State:
    """The file index plus a memo of specifiers already resolved.

    e2e alone imports '../../fixtures/auth' from 118 files; without the memo
    the same candidate list is rebuilt for every one of them.
    """

    def __init__(self, paths: set[str]):
        self.paths = paths
        self.memo: dict[tuple[str, str], str | None] = {}
        self._by_suffix: dict[str, str | None] | None = None

    def resolve_relative(self, base_dir: str, spec: str) -> str | None:
        key = (base_dir, spec)
        if key not in self.memo:
            stem = _join(base_dir, spec)
            hit = None
            if stem:
                for cand in _candidates(stem):
                    if cand in self.paths:
                        hit = cand
                        break
            self.memo[key] = hit
        return self.memo[key]

    def resolve_rooted(self, spec: str) -> str | None:
        """A server-absolute specifier: import('/js/copilot.js').

        There is no filesystem root to resolve against — that mapping lives in
        a web server config — so the only honest move is to look for exactly
        one file in the repo whose path ends with the specifier. Ambiguity is
        treated as failure rather than guessed at.
        """
        key = ("/", spec)
        if key in self.memo:
            return self.memo[key]
        hit = None
        for cand in _candidates(spec.lstrip("/")):
            tail = "/" + cand
            found = [p for p in self.paths if p.endswith(tail)]
            if len(found) == 1:
                hit = found[0]
                break
            if found:
                break                       # ambiguous — do not guess
        self.memo[key] = hit
        return hit


def prepare(ctx: Context, paths: set[str]) -> _State:
    return _State(paths)


def resolve(state: _State, path: str, text: str) -> Resolution:
    if "import" not in text and "require" not in text:
        return Resolution()                 # cheap out before masking
    base_dir = path.rsplit("/", 1)[0] if "/" in path else ""
    targets: list[str] = []
    packages: list[str] = []
    for raw in _specifiers(_mask(text)):
        spec = _clean(raw)
        if not spec:
            continue
        if spec.startswith("."):
            hit = state.resolve_relative(base_dir, spec)
            if hit and hit != path:
                targets.append(hit)
        elif spec.startswith("/"):
            hit = state.resolve_rooted(spec)
            if hit and hit != path:
                targets.append(hit)
        elif "://" in spec or spec.startswith("data:"):
            continue                        # a URL import, not a repo file
        else:
            packages.append(_package(spec))
    return Resolution(targets=tuple(targets), packages=tuple(packages))


register(Language(id="jsts", extensions=EXTENSIONS,
                  prepare=prepare, resolve=resolve))
