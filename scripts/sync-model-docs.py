#!/usr/bin/env python3
"""Mirror bundled Mental Model READMEs into the user guide.

Each ``models/{id}/README.md`` is the single source of truth for that model's
documentation (rendered in-app on the model's Documentation tab). The public
user guide (GitHub Pages serves ``docs/`` only) and the in-app Docs hub cannot
reach ``models/``, so this script writes a generated copy to
``docs/guide/model-{id}.md`` with a banner and a back-link.

Usage:
    python3 scripts/sync-model-docs.py          # regenerate the mirrors
    python3 scripts/sync-model-docs.py --check  # exit 1 if any mirror is stale

The pre-commit hook runs ``--check`` whenever a model README or a mirror is
staged, and ``backend/tests/test_model_docs.py`` asserts the same invariant.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
MODELS_DIR = REPO_ROOT / "models"
GUIDE_DIR = REPO_ROOT / "docs" / "guide"
MIRROR_PREFIX = "model-"
CATALOG_CHAPTER = "11-mental-model-catalog.md"


def model_dirs() -> list[Path]:
    """Bundled model directories that ship a README.md, sorted by id."""
    return sorted(
        p for p in MODELS_DIR.iterdir()
        if p.is_dir() and (p / "manifest.yaml").is_file() and (p / "README.md").is_file()
    )


def _model_name(readme: str, model_id: str) -> str:
    m = re.search(r"^#\s+(.+?)\s*$", readme, re.M)
    return m.group(1).strip() if m else model_id


def render_mirror(model_id: str, readme: str) -> str:
    """Build the guide page content for one model README."""
    name = _model_name(readme, model_id)
    banner = (
        f"<!-- GENERATED FILE. Do not edit. Source: models/{model_id}/README.md. "
        f"Regenerate with: python3 scripts/sync-model-docs.py -->\n"
        f"> **Bundled model documentation.** This page mirrors the `README.md` shipped inside the "
        f"`{model_id}` Mental Model archive. The same text is available in the app under "
        f"**Admin > Models > {name} > Documentation** and at `/api/models/{model_id}/docs`. "
        f"To change it, edit `models/{model_id}/README.md` and run `scripts/sync-model-docs.py`.\n\n"
    )
    footer = (
        "\n\n---\n\n"
        f"**Back:** [Chapter 11: Mental Model Catalog]({CATALOG_CHAPTER})\n"
    )
    return banner + readme.rstrip("\n") + footer


def expected_mirrors() -> dict[Path, str]:
    """Map of mirror path -> expected content for every bundled model."""
    out: dict[Path, str] = {}
    for d in model_dirs():
        readme = (d / "README.md").read_text(encoding="utf-8")
        out[GUIDE_DIR / f"{MIRROR_PREFIX}{d.name}.md"] = render_mirror(d.name, readme)
    return out


def stale_mirrors() -> list[Path]:
    """Mirrors that are missing, outdated, or orphaned (no matching model)."""
    expected = expected_mirrors()
    stale = [p for p, content in expected.items()
             if not p.is_file() or p.read_text(encoding="utf-8") != content]
    for p in GUIDE_DIR.glob(f"{MIRROR_PREFIX}*.md"):
        if p not in expected:
            stale.append(p)
    return sorted(stale)


def sync() -> int:
    expected = expected_mirrors()
    written = 0
    for path, content in expected.items():
        if not path.is_file() or path.read_text(encoding="utf-8") != content:
            path.write_text(content, encoding="utf-8")
            written += 1
    removed = 0
    for p in GUIDE_DIR.glob(f"{MIRROR_PREFIX}*.md"):
        if p not in expected:
            p.unlink()
            removed += 1
    print(f"Synced {len(expected)} model docs into docs/guide/ "
          f"({written} written, {removed} orphan(s) removed)")
    return 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--check", action="store_true",
                        help="report stale mirrors and exit non-zero instead of writing")
    args = parser.parse_args(argv)
    if args.check:
        stale = stale_mirrors()
        if stale:
            print("Model documentation mirrors are out of date:", file=sys.stderr)
            for p in stale:
                print(f"  {p.relative_to(REPO_ROOT)}", file=sys.stderr)
            print("Run: python3 scripts/sync-model-docs.py", file=sys.stderr)
            return 1
        print("Model documentation mirrors are up to date.")
        return 0
    return sync()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
