"""Unit tests for Jira Sync ADF ↔ Markdown converter.

Loads ``adf_converter.py`` from the apps directory using importlib to avoid
requiring the app to be installed as a package. All functions are pure —
no mocks needed.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Load adf_converter module from apps directory
# ---------------------------------------------------------------------------

_MODULE_PATH = (
    Path(__file__).resolve().parent.parent.parent
    / "apps"
    / "jira-sync"
    / "services"
    / "adf_converter.py"
)


def _load_module():
    spec = importlib.util.spec_from_file_location("jira_adf_converter", _MODULE_PATH)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["jira_adf_converter"] = mod
    spec.loader.exec_module(mod)
    return mod


adf = _load_module()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_adf_doc(*content_nodes: dict) -> dict:
    """Wrap nodes in a valid ADF document structure."""
    return {"version": 1, "type": "doc", "content": list(content_nodes)}


def _text(t: str, marks: list[dict] | None = None) -> dict:
    """Build an ADF text inline node."""
    node: dict = {"type": "text", "text": t}
    if marks:
        node["marks"] = marks
    return node


def _para(*inlines: dict) -> dict:
    """Build an ADF paragraph block node."""
    return {"type": "paragraph", "content": list(inlines)}


def _heading(level: int, *inlines: dict) -> dict:
    """Build an ADF heading block node."""
    return {"type": "heading", "attrs": {"level": level}, "content": list(inlines)}


def _list_item(*blocks: dict) -> dict:
    """Build an ADF listItem node."""
    return {"type": "listItem", "content": list(blocks)}


# ===================================================================
# adf_to_markdown — null/empty input
# ===================================================================


class TestAdfToMarkdownEmpty:
    def test_none_input(self):
        assert adf.adf_to_markdown(None) == ""

    def test_empty_dict(self):
        assert adf.adf_to_markdown({}) == ""

    def test_empty_content_array(self):
        doc = _make_adf_doc()
        # content is an empty list
        doc["content"] = []
        assert adf.adf_to_markdown(doc) == ""

    def test_missing_content_key(self):
        assert adf.adf_to_markdown({"version": 1, "type": "doc"}) == ""

    def test_non_dict_input(self):
        assert adf.adf_to_markdown("not a dict") == ""

    def test_content_not_list(self):
        assert adf.adf_to_markdown({"version": 1, "type": "doc", "content": "bad"}) == ""


# ===================================================================
# adf_to_markdown — paragraph
# ===================================================================


class TestAdfToMarkdownParagraph:
    def test_simple_text(self):
        doc = _make_adf_doc(_para(_text("Hello world")))
        assert adf.adf_to_markdown(doc) == "Hello world"

    def test_text_with_inline_marks(self):
        doc = _make_adf_doc(_para(
            _text("Hello "),
            _text("bold", marks=[{"type": "strong"}]),
            _text(" world"),
        ))
        assert adf.adf_to_markdown(doc) == "Hello **bold** world"

    def test_multiple_paragraphs(self):
        doc = _make_adf_doc(
            _para(_text("First paragraph")),
            _para(_text("Second paragraph")),
        )
        result = adf.adf_to_markdown(doc)
        assert "First paragraph" in result
        assert "Second paragraph" in result
        assert "\n\n" in result

    def test_empty_paragraph(self):
        doc = _make_adf_doc({"type": "paragraph", "content": []})
        assert adf.adf_to_markdown(doc) == ""

    def test_paragraph_no_content_key(self):
        doc = _make_adf_doc({"type": "paragraph"})
        assert adf.adf_to_markdown(doc) == ""


# ===================================================================
# adf_to_markdown — heading
# ===================================================================


class TestAdfToMarkdownHeading:
    def test_h1(self):
        doc = _make_adf_doc(_heading(1, _text("Title")))
        assert adf.adf_to_markdown(doc) == "# Title"

    def test_h2(self):
        doc = _make_adf_doc(_heading(2, _text("Subtitle")))
        assert adf.adf_to_markdown(doc) == "## Subtitle"

    def test_h3(self):
        doc = _make_adf_doc(_heading(3, _text("Section")))
        assert adf.adf_to_markdown(doc) == "### Section"

    def test_h6(self):
        doc = _make_adf_doc(_heading(6, _text("Deep")))
        assert adf.adf_to_markdown(doc) == "###### Deep"

    def test_heading_with_bold(self):
        doc = _make_adf_doc(_heading(2, _text("Important", marks=[{"type": "strong"}])))
        assert adf.adf_to_markdown(doc) == "## **Important**"

    def test_heading_missing_level(self):
        """Heading with no level attr defaults to 1."""
        doc = _make_adf_doc({"type": "heading", "content": [_text("No level")]})
        assert adf.adf_to_markdown(doc) == "# No level"

    def test_heading_level_clamped(self):
        """Level > 6 gets clamped to 6."""
        doc = _make_adf_doc(_heading(10, _text("Big")))
        assert adf.adf_to_markdown(doc).startswith("######")


# ===================================================================
# adf_to_markdown — bulletList
# ===================================================================


class TestAdfToMarkdownBulletList:
    def test_flat_list(self):
        doc = _make_adf_doc({
            "type": "bulletList",
            "content": [
                _list_item(_para(_text("Item one"))),
                _list_item(_para(_text("Item two"))),
            ],
        })
        result = adf.adf_to_markdown(doc)
        assert "- Item one" in result
        assert "- Item two" in result

    def test_nested_bullet_list(self):
        doc = _make_adf_doc({
            "type": "bulletList",
            "content": [
                _list_item(
                    _para(_text("Parent")),
                    {
                        "type": "bulletList",
                        "content": [
                            _list_item(_para(_text("Child"))),
                        ],
                    },
                ),
            ],
        })
        result = adf.adf_to_markdown(doc)
        assert "- Parent" in result
        assert "  - Child" in result

    def test_list_with_inline_formatting(self):
        doc = _make_adf_doc({
            "type": "bulletList",
            "content": [
                _list_item(_para(
                    _text("Click "),
                    _text("here", marks=[{"type": "strong"}]),
                )),
            ],
        })
        result = adf.adf_to_markdown(doc)
        assert "- Click **here**" in result

    def test_empty_list(self):
        doc = _make_adf_doc({"type": "bulletList", "content": []})
        result = adf.adf_to_markdown(doc)
        assert result == ""


# ===================================================================
# adf_to_markdown — orderedList
# ===================================================================


class TestAdfToMarkdownOrderedList:
    def test_simple_ordered(self):
        doc = _make_adf_doc({
            "type": "orderedList",
            "content": [
                _list_item(_para(_text("First"))),
                _list_item(_para(_text("Second"))),
                _list_item(_para(_text("Third"))),
            ],
        })
        result = adf.adf_to_markdown(doc)
        assert "1. First" in result
        assert "2. Second" in result
        assert "3. Third" in result

    def test_multi_item_ordered(self):
        doc = _make_adf_doc({
            "type": "orderedList",
            "content": [
                _list_item(_para(_text("Step A"))),
                _list_item(_para(_text("Step B"))),
            ],
        })
        result = adf.adf_to_markdown(doc)
        lines = result.strip().split("\n")
        assert len(lines) == 2


# ===================================================================
# adf_to_markdown — codeBlock
# ===================================================================


class TestAdfToMarkdownCodeBlock:
    def test_with_language(self):
        doc = _make_adf_doc({
            "type": "codeBlock",
            "attrs": {"language": "python"},
            "content": [_text("print('hello')")],
        })
        result = adf.adf_to_markdown(doc)
        assert "```python" in result
        assert "print('hello')" in result
        assert result.endswith("```")

    def test_without_language(self):
        doc = _make_adf_doc({
            "type": "codeBlock",
            "content": [_text("some code")],
        })
        result = adf.adf_to_markdown(doc)
        assert result.startswith("```\n")
        assert "some code" in result

    def test_empty_code_block(self):
        doc = _make_adf_doc({
            "type": "codeBlock",
            "attrs": {"language": "js"},
            "content": [],
        })
        result = adf.adf_to_markdown(doc)
        assert "```js" in result

    def test_multiline_code(self):
        doc = _make_adf_doc({
            "type": "codeBlock",
            "attrs": {"language": "python"},
            "content": [_text("line1\nline2\nline3")],
        })
        result = adf.adf_to_markdown(doc)
        assert "line1\nline2\nline3" in result


# ===================================================================
# adf_to_markdown — blockquote
# ===================================================================


class TestAdfToMarkdownBlockquote:
    def test_simple_quote(self):
        doc = _make_adf_doc({
            "type": "blockquote",
            "content": [_para(_text("Quoted text"))],
        })
        result = adf.adf_to_markdown(doc)
        assert "> Quoted text" in result

    def test_multi_paragraph_quote(self):
        doc = _make_adf_doc({
            "type": "blockquote",
            "content": [
                _para(_text("First line")),
                _para(_text("Second line")),
            ],
        })
        result = adf.adf_to_markdown(doc)
        assert "> First line" in result
        assert "> Second line" in result


# ===================================================================
# adf_to_markdown — table
# ===================================================================


class TestAdfToMarkdownTable:
    def test_header_and_data_rows(self):
        doc = _make_adf_doc({
            "type": "table",
            "content": [
                {
                    "type": "tableRow",
                    "content": [
                        {"type": "tableHeader", "content": [_para(_text("Name"))]},
                        {"type": "tableHeader", "content": [_para(_text("Value"))]},
                    ],
                },
                {
                    "type": "tableRow",
                    "content": [
                        {"type": "tableCell", "content": [_para(_text("foo"))]},
                        {"type": "tableCell", "content": [_para(_text("bar"))]},
                    ],
                },
            ],
        })
        result = adf.adf_to_markdown(doc)
        assert "| Name | Value |" in result
        assert "| --- | --- |" in result
        assert "| foo | bar |" in result

    def test_cells_with_inline_content(self):
        doc = _make_adf_doc({
            "type": "table",
            "content": [
                {
                    "type": "tableRow",
                    "content": [
                        {"type": "tableHeader", "content": [_para(_text("Col"))]},
                    ],
                },
                {
                    "type": "tableRow",
                    "content": [
                        {"type": "tableCell", "content": [
                            _para(_text("bold", marks=[{"type": "strong"}])),
                        ]},
                    ],
                },
            ],
        })
        result = adf.adf_to_markdown(doc)
        assert "**bold**" in result

    def test_empty_table(self):
        doc = _make_adf_doc({"type": "table", "content": []})
        result = adf.adf_to_markdown(doc)
        assert result == ""


# ===================================================================
# adf_to_markdown — text marks
# ===================================================================


class TestAdfToMarkdownTextMarks:
    def test_strong(self):
        doc = _make_adf_doc(_para(_text("bold", marks=[{"type": "strong"}])))
        assert "**bold**" in adf.adf_to_markdown(doc)

    def test_em(self):
        doc = _make_adf_doc(_para(_text("italic", marks=[{"type": "em"}])))
        assert "*italic*" in adf.adf_to_markdown(doc)

    def test_code(self):
        doc = _make_adf_doc(_para(_text("code", marks=[{"type": "code"}])))
        assert "`code`" in adf.adf_to_markdown(doc)

    def test_strike(self):
        doc = _make_adf_doc(_para(_text("struck", marks=[{"type": "strike"}])))
        assert "~~struck~~" in adf.adf_to_markdown(doc)

    def test_link(self):
        doc = _make_adf_doc(_para(_text("click", marks=[
            {"type": "link", "attrs": {"href": "https://example.com"}},
        ])))
        result = adf.adf_to_markdown(doc)
        assert "[click](https://example.com)" in result

    def test_combined_bold_and_italic(self):
        doc = _make_adf_doc(_para(_text("both", marks=[
            {"type": "strong"},
            {"type": "em"},
        ])))
        result = adf.adf_to_markdown(doc)
        # Should have both ** and * wrapping
        assert "**" in result
        assert "*" in result
        assert "both" in result

    def test_bold_link(self):
        doc = _make_adf_doc(_para(_text("link", marks=[
            {"type": "strong"},
            {"type": "link", "attrs": {"href": "https://example.com"}},
        ])))
        result = adf.adf_to_markdown(doc)
        assert "**link**" in result
        assert "https://example.com" in result

    def test_text_color_pass_through(self):
        doc = _make_adf_doc(_para(_text("colored", marks=[
            {"type": "textColor", "attrs": {"color": "#ff0000"}},
        ])))
        result = adf.adf_to_markdown(doc)
        assert "colored" in result

    def test_empty_text_skipped(self):
        doc = _make_adf_doc(_para(_text("")))
        assert adf.adf_to_markdown(doc) == ""


# ===================================================================
# adf_to_markdown — mention
# ===================================================================


class TestAdfToMarkdownMention:
    def test_mention_with_text(self):
        doc = _make_adf_doc(_para({
            "type": "mention",
            "attrs": {"id": "user123", "text": "Alice"},
        }))
        assert "@Alice" in adf.adf_to_markdown(doc)

    def test_mention_id_fallback(self):
        doc = _make_adf_doc(_para({
            "type": "mention",
            "attrs": {"id": "user456"},
        }))
        assert "@user456" in adf.adf_to_markdown(doc)

    def test_mention_no_attrs(self):
        doc = _make_adf_doc(_para({
            "type": "mention",
            "attrs": {},
        }))
        result = adf.adf_to_markdown(doc)
        assert "@unknown" in result


# ===================================================================
# adf_to_markdown — inlineCard
# ===================================================================


class TestAdfToMarkdownInlineCard:
    def test_inline_card_with_url(self):
        doc = _make_adf_doc(_para({
            "type": "inlineCard",
            "attrs": {"url": "https://jira.example.com/browse/PROJ-1"},
        }))
        result = adf.adf_to_markdown(doc)
        assert "[https://jira.example.com/browse/PROJ-1]" in result
        assert "(https://jira.example.com/browse/PROJ-1)" in result

    def test_inline_card_with_data_url(self):
        doc = _make_adf_doc(_para({
            "type": "inlineCard",
            "attrs": {"data": {"url": "https://example.com"}},
        }))
        result = adf.adf_to_markdown(doc)
        assert "https://example.com" in result

    def test_inline_card_no_url(self):
        doc = _make_adf_doc(_para({
            "type": "inlineCard",
            "attrs": {},
        }))
        result = adf.adf_to_markdown(doc)
        assert "[link]" in result


# ===================================================================
# adf_to_markdown — mediaGroup
# ===================================================================


class TestAdfToMarkdownMediaGroup:
    def test_media_with_id(self):
        doc = _make_adf_doc({
            "type": "mediaGroup",
            "content": [{
                "type": "media",
                "attrs": {"id": "abc-123", "type": "file"},
            }],
        })
        result = adf.adf_to_markdown(doc)
        assert "[media: abc-123]" in result

    def test_media_multiple(self):
        doc = _make_adf_doc({
            "type": "mediaGroup",
            "content": [
                {"type": "media", "attrs": {"id": "id1"}},
                {"type": "media", "attrs": {"id": "id2"}},
            ],
        })
        result = adf.adf_to_markdown(doc)
        assert "[media: id1]" in result
        assert "[media: id2]" in result

    def test_media_no_content(self):
        doc = _make_adf_doc({
            "type": "mediaGroup",
            "content": [],
        })
        result = adf.adf_to_markdown(doc)
        assert "[media]" in result


# ===================================================================
# adf_to_markdown — rule
# ===================================================================


class TestAdfToMarkdownRule:
    def test_horizontal_rule(self):
        doc = _make_adf_doc({"type": "rule"})
        assert adf.adf_to_markdown(doc) == "---"

    def test_rule_between_paragraphs(self):
        doc = _make_adf_doc(
            _para(_text("Above")),
            {"type": "rule"},
            _para(_text("Below")),
        )
        result = adf.adf_to_markdown(doc)
        assert "Above" in result
        assert "---" in result
        assert "Below" in result


# ===================================================================
# adf_to_markdown — unknown type
# ===================================================================


class TestAdfToMarkdownUnknown:
    def test_unknown_block_type(self):
        doc = _make_adf_doc({"type": "customPanel", "content": []})
        result = adf.adf_to_markdown(doc)
        assert "[unsupported: customPanel]" in result

    def test_unknown_inline_type(self):
        doc = _make_adf_doc(_para({"type": "status", "attrs": {"text": "In Progress"}}))
        result = adf.adf_to_markdown(doc)
        assert "[unsupported: status]" in result

    def test_unknown_does_not_crash(self):
        """Document with unknown types should not raise any exception."""
        doc = _make_adf_doc(
            {"type": "weirdBlock"},
            _para(_text("normal"), {"type": "weirdInline"}),
            {"type": "anotherWeird", "content": [{"type": "deep"}]},
        )
        result = adf.adf_to_markdown(doc)
        assert "[unsupported: weirdBlock]" in result
        assert "[unsupported: weirdInline]" in result


# ===================================================================
# adf_to_markdown — hardBreak and emoji
# ===================================================================


class TestAdfToMarkdownMisc:
    def test_hard_break(self):
        doc = _make_adf_doc(_para(
            _text("Line one"),
            {"type": "hardBreak"},
            _text("Line two"),
        ))
        result = adf.adf_to_markdown(doc)
        assert "Line one\nLine two" in result

    def test_emoji(self):
        doc = _make_adf_doc(_para(
            _text("Hello "),
            {"type": "emoji", "attrs": {"shortName": ":smile:", "text": "😄"}},
        ))
        result = adf.adf_to_markdown(doc)
        assert "😄" in result


# ===================================================================
# adf_to_markdown — complex / combined documents
# ===================================================================


class TestAdfToMarkdownComplex:
    def test_heading_paragraph_list(self):
        doc = _make_adf_doc(
            _heading(1, _text("Title")),
            _para(_text("Some intro text.")),
            {
                "type": "bulletList",
                "content": [
                    _list_item(_para(_text("Item A"))),
                    _list_item(_para(_text("Item B"))),
                ],
            },
        )
        result = adf.adf_to_markdown(doc)
        assert "# Title" in result
        assert "Some intro text." in result
        assert "- Item A" in result
        assert "- Item B" in result

    def test_full_document(self):
        """A realistic Jira description with multiple node types."""
        doc = _make_adf_doc(
            _heading(2, _text("Bug Report")),
            _para(
                _text("The "),
                _text("login", marks=[{"type": "code"}]),
                _text(" endpoint returns "),
                _text("500", marks=[{"type": "strong"}]),
                _text("."),
            ),
            {
                "type": "codeBlock",
                "attrs": {"language": "bash"},
                "content": [_text("curl -X POST /api/login")],
            },
            {
                "type": "orderedList",
                "content": [
                    _list_item(_para(_text("Open the app"))),
                    _list_item(_para(_text("Click login"))),
                    _list_item(_para(_text("See error"))),
                ],
            },
        )
        result = adf.adf_to_markdown(doc)
        assert "## Bug Report" in result
        assert "`login`" in result
        assert "**500**" in result
        assert "```bash" in result
        assert "1. Open the app" in result


# ===================================================================
# markdown_to_adf — null/empty input
# ===================================================================


class TestMarkdownToAdfEmpty:
    def test_none_input(self):
        result = adf.markdown_to_adf(None)
        assert result["version"] == 1
        assert result["type"] == "doc"
        assert result["content"] == []

    def test_empty_string(self):
        result = adf.markdown_to_adf("")
        assert result["content"] == []

    def test_whitespace_only(self):
        result = adf.markdown_to_adf("   \n\n  ")
        assert result["content"] == []

    def test_non_string_input(self):
        result = adf.markdown_to_adf(123)
        assert result["version"] == 1
        assert result["content"] == []


# ===================================================================
# markdown_to_adf — paragraphs
# ===================================================================


class TestMarkdownToAdfParagraph:
    def test_simple_paragraph(self):
        result = adf.markdown_to_adf("Hello world")
        assert len(result["content"]) == 1
        node = result["content"][0]
        assert node["type"] == "paragraph"
        assert node["content"][0]["text"] == "Hello world"

    def test_two_paragraphs(self):
        result = adf.markdown_to_adf("First paragraph\n\nSecond paragraph")
        assert len(result["content"]) == 2
        assert result["content"][0]["type"] == "paragraph"
        assert result["content"][1]["type"] == "paragraph"


# ===================================================================
# markdown_to_adf — headings
# ===================================================================


class TestMarkdownToAdfHeading:
    def test_h1(self):
        result = adf.markdown_to_adf("# Title")
        node = result["content"][0]
        assert node["type"] == "heading"
        assert node["attrs"]["level"] == 1
        assert node["content"][0]["text"] == "Title"

    def test_h2(self):
        result = adf.markdown_to_adf("## Subtitle")
        node = result["content"][0]
        assert node["attrs"]["level"] == 2

    def test_h3(self):
        result = adf.markdown_to_adf("### Section")
        node = result["content"][0]
        assert node["attrs"]["level"] == 3


# ===================================================================
# markdown_to_adf — bullet lists
# ===================================================================


class TestMarkdownToAdfBulletList:
    def test_bullet_list(self):
        result = adf.markdown_to_adf("- Item one\n- Item two")
        node = result["content"][0]
        assert node["type"] == "bulletList"
        assert len(node["content"]) == 2
        assert node["content"][0]["type"] == "listItem"

    def test_bullet_with_star(self):
        result = adf.markdown_to_adf("* Star item")
        node = result["content"][0]
        assert node["type"] == "bulletList"

    def test_bullet_with_plus(self):
        result = adf.markdown_to_adf("+ Plus item")
        node = result["content"][0]
        assert node["type"] == "bulletList"


# ===================================================================
# markdown_to_adf — ordered lists
# ===================================================================


class TestMarkdownToAdfOrderedList:
    def test_ordered_list(self):
        result = adf.markdown_to_adf("1. First\n2. Second\n3. Third")
        node = result["content"][0]
        assert node["type"] == "orderedList"
        assert len(node["content"]) == 3

    def test_ordered_list_text(self):
        result = adf.markdown_to_adf("1. Step one")
        items = result["content"][0]["content"]
        para = items[0]["content"][0]
        assert para["type"] == "paragraph"
        # Extract text from the inline nodes
        texts = [n["text"] for n in para["content"] if n.get("text")]
        assert "Step one" in " ".join(texts)


# ===================================================================
# markdown_to_adf — code blocks
# ===================================================================


class TestMarkdownToAdfCodeBlock:
    def test_code_block_with_language(self):
        md = "```python\nprint('hello')\n```"
        result = adf.markdown_to_adf(md)
        node = result["content"][0]
        assert node["type"] == "codeBlock"
        assert node["attrs"]["language"] == "python"
        assert node["content"][0]["text"] == "print('hello')"

    def test_code_block_without_language(self):
        md = "```\nsome code\n```"
        result = adf.markdown_to_adf(md)
        node = result["content"][0]
        assert node["type"] == "codeBlock"
        assert "attrs" not in node or not node.get("attrs", {}).get("language")

    def test_multiline_code_block(self):
        md = "```js\nconst x = 1;\nconst y = 2;\n```"
        result = adf.markdown_to_adf(md)
        node = result["content"][0]
        assert "const x = 1;\nconst y = 2;" in node["content"][0]["text"]


# ===================================================================
# markdown_to_adf — links
# ===================================================================


class TestMarkdownToAdfLinks:
    def test_inline_link(self):
        result = adf.markdown_to_adf("Click [here](https://example.com) now")
        para = result["content"][0]
        # Find the link node
        link_nodes = [n for n in para["content"] if n.get("marks")]
        assert len(link_nodes) >= 1
        link_mark = link_nodes[0]["marks"][0]
        assert link_mark["type"] == "link"
        assert link_mark["attrs"]["href"] == "https://example.com"

    def test_link_text_preserved(self):
        result = adf.markdown_to_adf("[Example](https://example.com)")
        para = result["content"][0]
        link_nodes = [n for n in para["content"] if n.get("marks")]
        assert link_nodes[0]["text"] == "Example"


# ===================================================================
# markdown_to_adf — blockquotes
# ===================================================================


class TestMarkdownToAdfBlockquote:
    def test_simple_blockquote(self):
        result = adf.markdown_to_adf("> Quoted text")
        node = result["content"][0]
        assert node["type"] == "blockquote"

    def test_multi_line_blockquote(self):
        result = adf.markdown_to_adf("> Line one\n> Line two")
        node = result["content"][0]
        assert node["type"] == "blockquote"


# ===================================================================
# markdown_to_adf — horizontal rule
# ===================================================================


class TestMarkdownToAdfRule:
    def test_horizontal_rule(self):
        result = adf.markdown_to_adf("---")
        node = result["content"][0]
        assert node["type"] == "rule"

    def test_horizontal_rule_underscores(self):
        result = adf.markdown_to_adf("___")
        node = result["content"][0]
        assert node["type"] == "rule"


# ===================================================================
# markdown_to_adf — mixed content
# ===================================================================


class TestMarkdownToAdfMixed:
    def test_mixed_content_document(self):
        md = """# Title

Some intro text.

- Bullet one
- Bullet two

```python
code here
```

1. Step one
2. Step two"""
        result = adf.markdown_to_adf(md)
        types = [n["type"] for n in result["content"]]
        assert "heading" in types
        assert "paragraph" in types
        assert "bulletList" in types
        assert "codeBlock" in types
        assert "orderedList" in types

    def test_valid_adf_structure(self):
        """All outputs have version, type, and content."""
        result = adf.markdown_to_adf("Hello")
        assert result["version"] == 1
        assert result["type"] == "doc"
        assert isinstance(result["content"], list)


# ===================================================================
# markdown_to_adf — inline formatting
# ===================================================================


class TestMarkdownToAdfInlineFormatting:
    def test_bold_text(self):
        result = adf.markdown_to_adf("This is **bold** text")
        para = result["content"][0]
        bold_nodes = [n for n in para["content"]
                      if n.get("marks") and any(m["type"] == "strong" for m in n["marks"])]
        assert len(bold_nodes) >= 1
        assert bold_nodes[0]["text"] == "bold"

    def test_italic_text(self):
        result = adf.markdown_to_adf("This is *italic* text")
        para = result["content"][0]
        italic_nodes = [n for n in para["content"]
                        if n.get("marks") and any(m["type"] == "em" for m in n["marks"])]
        assert len(italic_nodes) >= 1

    def test_inline_code(self):
        result = adf.markdown_to_adf("Use `code` here")
        para = result["content"][0]
        code_nodes = [n for n in para["content"]
                      if n.get("marks") and any(m["type"] == "code" for m in n["marks"])]
        assert len(code_nodes) >= 1

    def test_strikethrough(self):
        result = adf.markdown_to_adf("This is ~~deleted~~ text")
        para = result["content"][0]
        strike_nodes = [n for n in para["content"]
                        if n.get("marks") and any(m["type"] == "strike" for m in n["marks"])]
        assert len(strike_nodes) >= 1


# ===================================================================
# Round-trip tests
# ===================================================================


class TestRoundTrip:
    def test_paragraph_roundtrip(self):
        """Paragraph survives ADF → MD → ADF."""
        adf_doc = _make_adf_doc(_para(_text("Hello world")))
        md = adf.adf_to_markdown(adf_doc)
        back = adf.markdown_to_adf(md)
        assert back["content"][0]["type"] == "paragraph"
        assert "Hello" in back["content"][0]["content"][0]["text"]

    def test_heading_roundtrip(self):
        """Heading survives ADF → MD → ADF."""
        adf_doc = _make_adf_doc(_heading(2, _text("My Title")))
        md = adf.adf_to_markdown(adf_doc)
        back = adf.markdown_to_adf(md)
        assert back["content"][0]["type"] == "heading"
        assert back["content"][0]["attrs"]["level"] == 2

    def test_bullet_list_roundtrip(self):
        """Bullet list survives ADF → MD → ADF."""
        adf_doc = _make_adf_doc({
            "type": "bulletList",
            "content": [
                _list_item(_para(_text("A"))),
                _list_item(_para(_text("B"))),
            ],
        })
        md = adf.adf_to_markdown(adf_doc)
        back = adf.markdown_to_adf(md)
        assert back["content"][0]["type"] == "bulletList"
        assert len(back["content"][0]["content"]) == 2

    def test_code_block_roundtrip(self):
        """Code block survives ADF → MD → ADF."""
        adf_doc = _make_adf_doc({
            "type": "codeBlock",
            "attrs": {"language": "python"},
            "content": [_text("x = 1")],
        })
        md = adf.adf_to_markdown(adf_doc)
        back = adf.markdown_to_adf(md)
        assert back["content"][0]["type"] == "codeBlock"
        assert back["content"][0]["attrs"]["language"] == "python"

    def test_complex_roundtrip(self):
        """Multi-block document structure preserved through roundtrip."""
        adf_doc = _make_adf_doc(
            _heading(1, _text("Title")),
            _para(_text("Intro text")),
            {
                "type": "bulletList",
                "content": [_list_item(_para(_text("Item")))],
            },
        )
        md = adf.adf_to_markdown(adf_doc)
        back = adf.markdown_to_adf(md)
        types = [n["type"] for n in back["content"]]
        assert "heading" in types
        assert "paragraph" in types
        assert "bulletList" in types

    def test_rule_roundtrip(self):
        """Horizontal rule roundtrips."""
        adf_doc = _make_adf_doc({"type": "rule"})
        md = adf.adf_to_markdown(adf_doc)
        back = adf.markdown_to_adf(md)
        assert back["content"][0]["type"] == "rule"
