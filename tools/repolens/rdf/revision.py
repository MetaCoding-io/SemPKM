"""Which commit a graph describes.

A snapshot that cannot say what it is a snapshot of is not much use, and two
snapshots that cannot be told apart are worse than one — load them together
and every measurement contradicts itself. So the revision is captured here and
threaded into the IRIs of everything that varies over time.
"""

from __future__ import annotations

import subprocess
from pathlib import Path


def _git(root: Path, *args: str) -> str | None:
    try:
        out = subprocess.run(["git", *args], cwd=str(root), capture_output=True,
                             text=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return None
    return out.stdout.strip() if out.returncode == 0 else None


def git_revision(root: Path) -> dict:
    """The commit, its date and subject, and whether the tree is dirty.

    A dirty tree gets an id ending `-wip`, because a snapshot taken over
    uncommitted work does not describe the commit it claims to.
    """
    sha = _git(root, "rev-parse", "--short=12", "HEAD")
    if not sha:
        return {"id": "working", "sha": "", "date": "", "subject": "",
                "dirty": True, "vcs": False}
    dirty = bool(_git(root, "status", "--porcelain"))
    return {
        "id": sha + ("-wip" if dirty else ""),
        "sha": sha,
        "date": _git(root, "log", "-1", "--format=%cI") or "",
        "subject": (_git(root, "log", "-1", "--format=%s") or "")[:120],
        "branch": _git(root, "rev-parse", "--abbrev-ref", "HEAD") or "",
        "dirty": dirty,
        "vcs": True,
    }
