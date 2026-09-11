"""Structural checks for the user guide under docs/guide/.

The guide has three hand-maintained chapter lists (the public viewer's sidebar
in docs/guide/index.html, the docs/guide/README.md table of contents, and
GUIDE_SECTIONS in app.shell.router) plus per-chapter Previous/Next footers.
These tests keep chapter numbering, ordering, and cross-links consistent so
the guide cannot drift back out of order.
"""

import json
import re
from pathlib import Path

import pytest

from app.shell.router import GUIDE_SECTIONS, LEGACY_GUIDE_FILES

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
GUIDE_DIR = REPO_ROOT / "docs" / "guide"

CHAPTER_RE = re.compile(r"^(\d{2})-[a-z0-9-]+\.md$")
H1_RE = re.compile(r"^# Chapter (\d+): (.+?)\s*$")
FOOTER_RE = re.compile(
    r"^\*\*Previous:\*\* \[[^\]]+\]\(([^)]+)\) \| \*\*Next:\*\* \[[^\]]+\]\(([^)]+)\)\s*$"
)
LINK_RE = re.compile(r"\]\(((?:\d{2}-[a-z0-9-]+|appendix-[a-f]-[a-z0-9-]+|model-[a-z-]+|README)\.md)(?:#[^)]*)?\)")


def _chapters() -> list[Path]:
    files = sorted(p for p in GUIDE_DIR.glob("*.md") if CHAPTER_RE.match(p.name))
    assert files, "no numbered chapters found"
    return files


def _number(path: Path) -> int:
    return int(CHAPTER_RE.match(path.name).group(1))


def _guide_section_files() -> list[str]:
    for section in GUIDE_SECTIONS:
        if section["title"] == "User Guide":
            return [i["filename"] for i in section["items"] if not i.get("appendix")]
    raise AssertionError("GUIDE_SECTIONS has no 'User Guide' section")


def _sidebar_files() -> list[str]:
    html = (GUIDE_DIR / "index.html").read_text(encoding="utf-8")
    return re.findall(r'data-file="([A-Za-z0-9._-]+\.md)"', html)


def _readme_files() -> list[str]:
    text = (GUIDE_DIR / "README.md").read_text(encoding="utf-8")
    return re.findall(r"^\d+\. \[[^\]]+\]\((\d{2}-[a-z0-9-]+\.md)\)", text, re.M)


class TestChapterNumbering:
    def test_numbers_are_contiguous_from_one(self):
        nums = [_number(p) for p in _chapters()]
        assert nums == list(range(1, len(nums) + 1)), nums

    @pytest.mark.parametrize("path", _chapters(), ids=lambda p: p.name)
    def test_h1_matches_filename_number(self, path: Path):
        first = path.read_text(encoding="utf-8").splitlines()[0]
        m = H1_RE.match(first)
        assert m, f"{path.name}: first line must be '# Chapter N: Title', got {first!r}"
        assert int(m.group(1)) == _number(path), f"{path.name}: H1 says Chapter {m.group(1)}"


class TestChapterLists:
    def test_guide_sections_lists_every_chapter_in_order(self):
        expected = [p.name for p in _chapters()]
        assert _guide_section_files() == expected

    def test_guide_sections_titles_carry_chapter_numbers(self):
        for section in GUIDE_SECTIONS:
            if section["title"] != "User Guide":
                continue
            for item in section["items"]:
                if item.get("appendix"):
                    continue
                num = int(CHAPTER_RE.match(item["filename"]).group(1))
                assert item["title"].startswith(f"{num}. "), item

    def test_public_sidebar_lists_every_chapter_in_order(self):
        numbered = [f for f in _sidebar_files() if CHAPTER_RE.match(f)]
        assert numbered == [p.name for p in _chapters()]

    def test_public_sidebar_labels_carry_chapter_numbers(self):
        html = (GUIDE_DIR / "index.html").read_text(encoding="utf-8")
        for fn, label in re.findall(r'data-file="(\d{2}-[a-z0-9-]+\.md)">([^<]+)<', html):
            num = int(CHAPTER_RE.match(fn).group(1))
            assert label.startswith(f"{num}. "), (fn, label)

    def test_readme_toc_lists_every_chapter_in_order(self):
        assert _readme_files() == [p.name for p in _chapters()]

    def test_readme_toc_numbers_match_filenames(self):
        text = (GUIDE_DIR / "README.md").read_text(encoding="utf-8")
        for num, fn in re.findall(r"^(\d+)\. \[[^\]]+\]\((\d{2}-[a-z0-9-]+\.md)\)", text, re.M):
            assert int(num) == int(CHAPTER_RE.match(fn).group(1)), (num, fn)

    def test_every_listed_file_exists(self):
        listed = set(_sidebar_files()) | set(_readme_files()) | {
            i["filename"] for s in GUIDE_SECTIONS if s["type"] == "chapters" for i in s["items"]
        }
        missing = sorted(f for f in listed if not (GUIDE_DIR / f).is_file())
        assert not missing, missing


class TestFootersAndLinks:
    def test_previous_next_footers_form_a_linear_chain(self):
        chapters = _chapters()
        for i, path in enumerate(chapters):
            last = path.read_text(encoding="utf-8").rstrip("\n").splitlines()[-1]
            m = FOOTER_RE.match(last)
            assert m, f"{path.name}: last line must be a Previous/Next footer, got {last!r}"
            prev, nxt = m.groups()
            exp_prev = "README.md" if i == 0 else chapters[i - 1].name
            exp_next = (
                "appendix-a-environment-variables.md"
                if i == len(chapters) - 1
                else chapters[i + 1].name
            )
            assert prev == exp_prev, f"{path.name}: Previous -> {prev}, expected {exp_prev}"
            assert nxt == exp_next, f"{path.name}: Next -> {nxt}, expected {exp_next}"

    def test_all_internal_markdown_links_resolve(self):
        dangling = []
        for path in GUIDE_DIR.glob("*.md"):
            for target in LINK_RE.findall(path.read_text(encoding="utf-8")):
                if not (GUIDE_DIR / target).is_file():
                    dangling.append(f"{path.name} -> {target}")
        assert not dangling, dangling

    def test_chapter_link_text_numbers_match_targets(self):
        """'[Chapter N: ...](NN-slug.md)' must use the target's current number."""
        bad = []
        pat = re.compile(r"\[Chapter (\d+)[^\]]*\]\((\d{2})-[a-z0-9-]+\.md")
        for path in list(GUIDE_DIR.glob("*.md")) + [REPO_ROOT / "docs" / "index.html"]:
            text = path.read_text(encoding="utf-8")
            for said, actual in pat.findall(text):
                if int(said) != int(actual):
                    bad.append(f"{path.name}: says Chapter {said}, links {actual}")
        assert not bad, bad


class TestLegacyChapterMap:
    def test_map_targets_exist_and_sources_do_not(self):
        data = json.loads((GUIDE_DIR / "legacy-chapter-map.json").read_text(encoding="utf-8"))
        assert data == LEGACY_GUIDE_FILES
        for old_stem, new_file in data.items():
            assert (GUIDE_DIR / new_file).is_file(), new_file
            assert not (GUIDE_DIR / f"{old_stem}.md").is_file(), old_stem

    def test_public_viewer_embeds_the_same_map(self):
        html = (GUIDE_DIR / "index.html").read_text(encoding="utf-8")
        m = re.search(r"var LEGACY_CHAPTERS = (\{.*?\});", html, re.S)
        assert m, "LEGACY_CHAPTERS missing from docs/guide/index.html"
        assert json.loads(m.group(1)) == LEGACY_GUIDE_FILES
