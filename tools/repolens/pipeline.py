"""Stage registry and runner.

A pipeline is an ordered list of stages. Each stage reads and writes a shared
Context. Stages declare what they `provides` and what they `requires`. The
order comes from the `pipeline:` list in config; the runner validates it and
refuses to run a stage whose inputs no earlier stage produced. It does not
reorder for you — silently rearranging a bad order would hide the mistake.

Adding a stage is the extension point: write a function, decorate it with
@stage(...), import its module from stages/__init__.py, and name it in the
`pipeline:` list in .repolens.yml. Nothing else needs to change.
"""

from __future__ import annotations

import fnmatch
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterable


# --------------------------------------------------------------------------
# Context — the value every stage receives
# --------------------------------------------------------------------------

@dataclass
class Context:
    root: Path
    config: dict
    facts: dict = field(default_factory=dict)
    model: dict = field(default_factory=dict)
    timings: dict = field(default_factory=dict)
    logs: list = field(default_factory=list)
    verbose: bool = False

    # -- logging ----------------------------------------------------------
    def log(self, msg: str) -> None:
        self.logs.append(msg)
        if self.verbose:
            print("    " + msg)

    def warn(self, msg: str) -> None:
        self.logs.append("WARNING: " + msg)
        print("    ! " + msg)

    # -- shared helpers ---------------------------------------------------
    def metric(self, name: str, value) -> None:
        """Publish a named metric. Checks refer to these by name."""
        self.facts.setdefault("metrics", {})[name] = value

    def get_metric(self, name: str, default=None):
        return self.facts.get("metrics", {}).get(name, default)

    def rel(self, p: Path) -> str:
        return str(p.relative_to(self.root)).replace("\\", "/")

    def files(self) -> list[dict]:
        return self.facts.get("files", [])

    def match(self, patterns: Iterable[str]) -> list[dict]:
        """Files whose repo-relative path matches any glob."""
        pats = list(patterns)
        out = []
        for f in self.files():
            path = f["path"]
            for p in pats:
                if _glob_match(path, p):
                    out.append(f)
                    break
        return out

    def sh(self, cmd: str, timeout: int = 60) -> tuple[int, str]:
        """Run a shell command at the repo root. Used by shell-kind checks."""
        try:
            r = subprocess.run(
                cmd, shell=True, cwd=self.root, capture_output=True,
                text=True, timeout=timeout,
            )
            return r.returncode, (r.stdout or "").strip()
        except subprocess.TimeoutExpired:
            return 124, ""


def _glob_match(path: str, pattern: str) -> bool:
    """fnmatch, but with ** spanning directory separators.

    fnmatch treats * as matching /, which makes 'backend/app/*' match
    everything underneath. Anchor each segment instead.
    """
    if "**" in pattern:
        head, _, tail = pattern.partition("**")
        if not path.startswith(head.rstrip("/")):
            return False
        tail = tail.lstrip("/")
        if not tail:
            return True
        return fnmatch.fnmatch(path, "*" + tail) or fnmatch.fnmatch(path.rsplit("/", 1)[-1], tail)
    # no ** — * must not cross a separator
    if pattern.count("/") != path.count("/"):
        return False
    return fnmatch.fnmatch(path, pattern)


# --------------------------------------------------------------------------
# Registry
# --------------------------------------------------------------------------

@dataclass
class Stage:
    id: str
    fn: Callable[[Context], None]
    requires: list[str]
    provides: list[str]
    doc: str = ""


REGISTRY: dict[str, Stage] = {}


def stage(id: str, *, requires: Iterable[str] = (), provides: Iterable[str] = ()):
    def deco(fn):
        REGISTRY[id] = Stage(
            id=id, fn=fn,
            requires=list(requires), provides=list(provides),
            doc=(fn.__doc__ or "").strip().split("\n")[0],
        )
        return fn
    return deco


# --------------------------------------------------------------------------
# Runner
# --------------------------------------------------------------------------

class PipelineError(RuntimeError):
    pass


def resolve_order(requested: list[str]) -> list[str]:
    """Validate that the configured order satisfies every `requires`.

    Deliberately does not reorder: the config's order is the source of truth,
    and silently rearranging it would hide a mistake rather than report it.
    """
    unknown = [s for s in requested if s not in REGISTRY]
    if unknown:
        raise PipelineError(
            f"unknown stage(s): {', '.join(unknown)}. "
            f"Known: {', '.join(sorted(REGISTRY))}"
        )
    produced: set[str] = set()
    for sid in requested:
        st = REGISTRY[sid]
        missing = [r for r in st.requires if r not in produced]
        if missing:
            raise PipelineError(
                f"stage '{sid}' requires {missing} which no earlier stage provides. "
                f"Reorder the `pipeline:` list in your config."
            )
        produced.update(st.provides)
    return requested


def run(ctx: Context, requested: list[str],
        only: list[str] | None = None, skip: list[str] | None = None) -> Context:
    order = resolve_order(requested)
    if only:
        order = [s for s in order if s in only]
    if skip:
        order = [s for s in order if s not in skip]

    for sid in order:
        st = REGISTRY[sid]
        t0 = time.perf_counter()
        print(f"  → {sid:<14} {st.doc}")
        st.fn(ctx)
        ctx.timings[sid] = round((time.perf_counter() - t0) * 1000)
    return ctx
