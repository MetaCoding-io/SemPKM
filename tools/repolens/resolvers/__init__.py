"""Per-language import resolvers, keyed by language.

`drilldown` needs one question answered for every member file: *which other
files in this repo does this one import?* The answer is language-specific — a
Python file names a dotted module that lives under a sys.path root, a JS file
names a path fragment and lets the bundler guess the extension — but the shape
of the answer is not, so the shape is what this package fixes.

A language is two functions and one `register(...)` line:

    prepare(ctx, paths) -> state          # once per build; build your indexes
    resolve(state, path, text) -> Resolution

`Resolution.targets` are repo-relative paths. The caller, not the resolver,
decides whether each one is a sibling edge or a hop to another part — a
resolver never learns about drawing nodes. `Resolution.packages` are
specifiers that deliberately resolve to nothing in this repo (third-party
imports): counted so a part's package appetite is visible, never drawn.

`notes` is optional and exists so a resolver can report on itself (how many
files needed a fallback path, say) without the caller special-casing it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Iterable

from ..pipeline import Context


# --------------------------------------------------------------------------
# the contract
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class Resolution:
    """What one source file imports.

    `targets` carries multiplicity — two imports of the same file appear
    twice, which is what gives an edge its weight.
    """
    targets: tuple[str, ...] = ()
    packages: tuple[str, ...] = ()


EMPTY = Resolution()


@dataclass(frozen=True)
class Language:
    id: str
    extensions: tuple[str, ...]
    prepare: Callable[[Context, set[str]], Any]
    resolve: Callable[[Any, str, str], Resolution]
    notes: Callable[[Any], list[str]] | None = None


REGISTRY: dict[str, Language] = {}


def register(lang: Language) -> Language:
    """Add a language. Later registrations of the same id replace earlier ones."""
    clash = [e for e in lang.extensions
             for other in REGISTRY.values()
             if other.id != lang.id and e in other.extensions]
    if clash:
        raise ValueError(f"language '{lang.id}' claims extensions already taken: {clash}")
    REGISTRY[lang.id] = lang
    return lang


# --------------------------------------------------------------------------
# one build's worth of prepared resolvers
# --------------------------------------------------------------------------

@dataclass
class Bound:
    """Every registered language, prepared against one snapshot of the repo.

    Built once per run. `handles()` is separate from `resolve()` so a caller
    can avoid reading a file no resolver will look at — most of a repo's
    members are images, config and markup.
    """
    ctx: Context
    paths: set[str]
    _by_ext: dict[str, tuple[Language, Any]] = field(default_factory=dict, init=False)
    _states: list[tuple[Language, Any]] = field(default_factory=list, init=False)

    def __post_init__(self) -> None:
        for lang in REGISTRY.values():
            state = lang.prepare(self.ctx, self.paths)
            self._states.append((lang, state))
            for ext in lang.extensions:
                self._by_ext[ext] = (lang, state)

    @staticmethod
    def _ext(path: str) -> str:
        dot = path.rfind(".")
        slash = path.rfind("/")
        return path[dot:].lower() if dot > slash else ""

    def handles(self, path: str) -> bool:
        return self._ext(path) in self._by_ext

    def resolve(self, path: str, text: str) -> Resolution:
        hit = self._by_ext.get(self._ext(path))
        if not hit:
            return EMPTY
        lang, state = hit
        return lang.resolve(state, path, text)

    def notes(self) -> Iterable[str]:
        for lang, state in self._states:
            if lang.notes:
                yield from lang.notes(state)


# Importing the modules is what registers them.
from . import python as _python      # noqa: E402,F401
from . import jsts as _jsts          # noqa: E402,F401
