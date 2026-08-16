"""Turtle emission, as a registry of contributors.

The same split the rest of the tool uses: core code analysis knows nothing
about gsd, and gsd knows nothing about how files are counted. Each contributor
declares what it needs from the facts and is skipped when that is absent, so a
repository with no `.gsd` directory simply produces a graph without decisions
rather than an error.

Adding a contributor is a module in this package, a `@contributor` decorator
and an import below.
"""

from __future__ import annotations

from typing import Callable

CONTRIBUTORS: dict[str, "Contributor"] = {}


class Contributor:
    def __init__(self, cid: str, fn: Callable, requires: list[str], doc: str) -> None:
        self.id = cid
        self.fn = fn
        self.requires = requires
        self.doc = doc

    def applies(self, ctx) -> bool:
        return all(_present(ctx, key) for key in self.requires)


def _present(ctx, key: str) -> bool:
    """A dotted path into facts, e.g. 'conventions.decisions'."""
    node = ctx.facts
    for part in key.split("."):
        if not isinstance(node, dict) or part not in node:
            return False
        node = node[part]
    return bool(node)


def contributor(cid: str, requires: list[str] | None = None):
    def wrap(fn):
        CONTRIBUTORS[cid] = Contributor(cid, fn, requires or [], (fn.__doc__ or "").strip())
        return fn
    return wrap


from . import core   # noqa: E402,F401  (registers)
from . import gsd    # noqa: E402,F401
