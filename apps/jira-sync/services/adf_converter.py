"""Atlassian Document Format (ADF) ↔ Markdown converter.

Pure module with zero dependencies on the App SDK, network, or state.
ADF is Jira Cloud v3's JSON-based rich text format — all issue descriptions
arrive as ADF and must be sent back as ADF.

Covers ~12 common ADF node types. Unknown types emit
``[unsupported: {type}]`` placeholder — never crash.

The Markdown→ADF reverse direction handles only the subset SemPKM produces:
paragraphs, headings, lists, code blocks, links.
"""

from __future__ import annotations

import re

# ---------------------------------------------------------------------------
# ADF → Markdown
# ---------------------------------------------------------------------------


def adf_to_markdown(adf_doc: dict | None) -> str:
    """Convert an ADF document to Markdown.

    Args:
        adf_doc: ADF document dict (``{"version": 1, "type": "doc", "content": [...]}``),
                 or ``None``.

    Returns:
        Markdown string. Empty string for None/empty/invalid input.
    """
    if not adf_doc or not isinstance(adf_doc, dict):
        return ""
    content = adf_doc.get("content")
    if not content or not isinstance(content, list):
        return ""
    blocks = []
    for node in content:
        block = _convert_block(node, indent=0)
        if block is not None:
            blocks.append(block)
    return "\n\n".join(blocks)


def _convert_block(node: dict, indent: int = 0) -> str | None:
    """Convert a single ADF block node to Markdown."""
    if not node or not isinstance(node, dict):
        return None
    node_type = node.get("type", "")

    if node_type == "paragraph":
        return _convert_paragraph(node)
    elif node_type == "heading":
        return _convert_heading(node)
    elif node_type == "bulletList":
        return _convert_bullet_list(node, indent)
    elif node_type == "orderedList":
        return _convert_ordered_list(node, indent)
    elif node_type == "codeBlock":
        return _convert_code_block(node)
    elif node_type == "blockquote":
        return _convert_blockquote(node)
    elif node_type == "table":
        return _convert_table(node)
    elif node_type == "rule":
        return "---"
    elif node_type == "mediaGroup":
        return _convert_media_group(node)
    elif node_type == "mediaSingle":
        return _convert_media_group(node)
    else:
        return f"[unsupported: {node_type}]"


def _convert_paragraph(node: dict) -> str:
    """Convert paragraph node — inline content joined."""
    return _convert_inline_content(node.get("content", []))


def _convert_heading(node: dict) -> str:
    """Convert heading node — ``# text`` with level from attrs."""
    attrs = node.get("attrs", {})
    level = attrs.get("level", 1)
    level = max(1, min(6, level))
    text = _convert_inline_content(node.get("content", []))
    return f"{'#' * level} {text}"


def _convert_bullet_list(node: dict, indent: int = 0) -> str:
    """Convert bulletList — ``- item`` per listItem."""
    items = []
    for item_node in node.get("content", []):
        if not isinstance(item_node, dict):
            continue
        item_text = _convert_list_item(item_node, indent, bullet="- ")
        if item_text is not None:
            items.append(item_text)
    return "\n".join(items)


def _convert_ordered_list(node: dict, indent: int = 0) -> str:
    """Convert orderedList — ``N. item`` per listItem."""
    items = []
    for idx, item_node in enumerate(node.get("content", []), start=1):
        if not isinstance(item_node, dict):
            continue
        item_text = _convert_list_item(item_node, indent, bullet=f"{idx}. ")
        if item_text is not None:
            items.append(item_text)
    return "\n".join(items)


def _convert_list_item(node: dict, indent: int, bullet: str) -> str | None:
    """Convert a listItem node with proper indentation and nested list handling."""
    content = node.get("content", [])
    if not content:
        return None

    prefix = "  " * indent
    parts = []
    first_line = True

    for child in content:
        if not isinstance(child, dict):
            continue
        child_type = child.get("type", "")

        if child_type in ("bulletList", "orderedList"):
            # Nested list — recurse with increased indent
            nested = _convert_block(child, indent + 1)
            if nested:
                parts.append(nested)
        elif child_type == "paragraph":
            text = _convert_paragraph(child)
            if first_line:
                parts.append(f"{prefix}{bullet}{text}")
                first_line = False
            else:
                parts.append(f"{prefix}  {text}")
        else:
            # Other block content inside list item
            block = _convert_block(child, indent)
            if block:
                if first_line:
                    parts.append(f"{prefix}{bullet}{block}")
                    first_line = False
                else:
                    parts.append(f"{prefix}  {block}")

    if not parts:
        return None
    return "\n".join(parts)


def _convert_code_block(node: dict) -> str:
    """Convert codeBlock — triple backtick with optional language."""
    attrs = node.get("attrs", {})
    language = attrs.get("language", "")
    content = node.get("content", [])
    # Code block content is plain text nodes
    text_parts = []
    for child in content:
        if isinstance(child, dict) and child.get("type") == "text":
            text_parts.append(child.get("text", ""))
    code_text = "".join(text_parts)
    return f"```{language}\n{code_text}\n```"


def _convert_blockquote(node: dict) -> str:
    """Convert blockquote — prefix each line with ``> ``."""
    content = node.get("content", [])
    inner_blocks = []
    for child in content:
        block = _convert_block(child, indent=0)
        if block is not None:
            inner_blocks.append(block)
    inner = "\n\n".join(inner_blocks)
    # Prefix every line with >
    lines = inner.split("\n")
    return "\n".join(f"> {line}" for line in lines)


def _convert_table(node: dict) -> str:
    """Convert table — pipe-delimited Markdown table."""
    rows = []
    for row_node in node.get("content", []):
        if not isinstance(row_node, dict) or row_node.get("type") != "tableRow":
            continue
        cells = []
        for cell_node in row_node.get("content", []):
            if not isinstance(cell_node, dict):
                continue
            cell_type = cell_node.get("type", "")
            if cell_type in ("tableCell", "tableHeader"):
                cell_content = cell_node.get("content", [])
                # Convert inner content of cell
                cell_texts = []
                for inner in cell_content:
                    if isinstance(inner, dict):
                        block = _convert_block(inner, indent=0)
                        if block:
                            cell_texts.append(block)
                cells.append(" ".join(cell_texts) if cell_texts else "")
        rows.append(cells)

    if not rows:
        return ""

    # Build markdown table
    lines = []
    # First row
    first_row = rows[0]
    lines.append("| " + " | ".join(first_row) + " |")
    # Separator
    lines.append("| " + " | ".join("---" for _ in first_row) + " |")
    # Remaining rows
    for row in rows[1:]:
        # Pad row to match header length
        while len(row) < len(first_row):
            row.append("")
        lines.append("| " + " | ".join(row) + " |")

    return "\n".join(lines)


def _convert_media_group(node: dict) -> str:
    """Convert mediaGroup/mediaSingle — placeholder with media ID."""
    content = node.get("content", [])
    media_ids = []
    for child in content:
        if isinstance(child, dict) and child.get("type") == "media":
            attrs = child.get("attrs", {})
            media_id = attrs.get("id", "unknown")
            media_ids.append(media_id)
    if media_ids:
        return " ".join(f"[media: {mid}]" for mid in media_ids)
    return "[media]"


# ---------------------------------------------------------------------------
# Inline content conversion
# ---------------------------------------------------------------------------


def _convert_inline_content(content: list | None) -> str:
    """Convert a list of inline nodes to Markdown text."""
    if not content:
        return ""
    parts = []
    for node in content:
        if not isinstance(node, dict):
            continue
        inline = _convert_inline(node)
        if inline:
            parts.append(inline)
    return "".join(parts)


def _convert_inline(node: dict) -> str:
    """Convert a single inline node to Markdown."""
    node_type = node.get("type", "")

    if node_type == "text":
        return _convert_text(node)
    elif node_type == "mention":
        return _convert_mention(node)
    elif node_type == "inlineCard":
        return _convert_inline_card(node)
    elif node_type == "hardBreak":
        return "\n"
    elif node_type == "emoji":
        attrs = node.get("attrs", {})
        return attrs.get("text", attrs.get("shortName", ""))
    else:
        return f"[unsupported: {node_type}]"


def _convert_text(node: dict) -> str:
    """Convert text node with marks (bold, italic, code, etc.)."""
    text = node.get("text", "")
    if not text:
        return ""

    marks = node.get("marks", [])
    if not marks:
        return text

    # Apply marks — order matters for nesting
    # Process link mark first to get the URL
    link_href = None
    for mark in marks:
        if mark.get("type") == "link":
            attrs = mark.get("attrs", {})
            link_href = attrs.get("href", "")

    # Apply formatting marks
    for mark in marks:
        mark_type = mark.get("type", "")
        if mark_type == "strong":
            text = f"**{text}**"
        elif mark_type == "em":
            text = f"*{text}*"
        elif mark_type == "code":
            text = f"`{text}`"
        elif mark_type == "strike":
            text = f"~~{text}~~"
        elif mark_type == "link":
            # Handled after other marks
            pass
        elif mark_type == "textColor":
            # Pass through text as-is (color not representable in Markdown)
            pass
        elif mark_type == "subsup":
            # Pass through text as-is
            pass
        elif mark_type == "underline":
            # No standard Markdown for underline, pass through
            pass

    # Apply link mark last to wrap everything
    if link_href is not None:
        text = f"[{text}]({link_href})"

    return text


def _convert_mention(node: dict) -> str:
    """Convert mention node — ``@{text}``."""
    attrs = node.get("attrs", {})
    text = attrs.get("text", "")
    if not text:
        # Fallback to id
        text = attrs.get("id", "unknown")
    return f"@{text}"


def _convert_inline_card(node: dict) -> str:
    """Convert inlineCard — ``[url](url)`` or ``[link](url)``."""
    attrs = node.get("attrs", {})
    url = attrs.get("url", "")
    if url:
        return f"[{url}]({url})"
    data = attrs.get("data", {})
    url = data.get("url", "")
    if url:
        return f"[{url}]({url})"
    return "[link]"


# ---------------------------------------------------------------------------
# Markdown → ADF
# ---------------------------------------------------------------------------


def markdown_to_adf(md_text: str | None) -> dict:
    """Convert Markdown text to an ADF document.

    Handles the subset SemPKM produces: paragraphs, headings, bullet lists,
    ordered lists, code blocks (with language), and inline links.

    Args:
        md_text: Markdown text string, or ``None``.

    Returns:
        ADF document dict: ``{"version": 1, "type": "doc", "content": [...]}``.
        Returns empty doc for None/empty input.
    """
    empty_doc = {"version": 1, "type": "doc", "content": []}

    if not md_text or not isinstance(md_text, str):
        return empty_doc

    lines = md_text.split("\n")
    content: list[dict] = []
    i = 0

    while i < len(lines):
        line = lines[i]

        # Code block (triple backtick)
        if line.startswith("```"):
            language = line[3:].strip()
            code_lines = []
            i += 1
            while i < len(lines) and not lines[i].startswith("```"):
                code_lines.append(lines[i])
                i += 1
            i += 1  # skip closing ```
            code_node: dict = {
                "type": "codeBlock",
                "content": [{"type": "text", "text": "\n".join(code_lines)}],
            }
            if language:
                code_node["attrs"] = {"language": language}
            content.append(code_node)
            continue

        # Heading
        heading_match = re.match(r"^(#{1,6})\s+(.+)$", line)
        if heading_match:
            level = len(heading_match.group(1))
            text = heading_match.group(2)
            content.append({
                "type": "heading",
                "attrs": {"level": level},
                "content": _parse_inline_md(text),
            })
            i += 1
            continue

        # Horizontal rule
        if re.match(r"^(-{3,}|_{3,}|\*{3,})$", line.strip()):
            content.append({"type": "rule"})
            i += 1
            continue

        # Bullet list
        if re.match(r"^[-*+]\s+", line):
            list_items = []
            while i < len(lines) and re.match(r"^[-*+]\s+", lines[i]):
                item_text = re.sub(r"^[-*+]\s+", "", lines[i])
                list_items.append({
                    "type": "listItem",
                    "content": [{
                        "type": "paragraph",
                        "content": _parse_inline_md(item_text),
                    }],
                })
                i += 1
            content.append({
                "type": "bulletList",
                "content": list_items,
            })
            continue

        # Ordered list
        if re.match(r"^\d+\.\s+", line):
            list_items = []
            while i < len(lines) and re.match(r"^\d+\.\s+", lines[i]):
                item_text = re.sub(r"^\d+\.\s+", "", lines[i])
                list_items.append({
                    "type": "listItem",
                    "content": [{
                        "type": "paragraph",
                        "content": _parse_inline_md(item_text),
                    }],
                })
                i += 1
            content.append({
                "type": "orderedList",
                "content": list_items,
            })
            continue

        # Blockquote
        if line.startswith("> "):
            quote_lines = []
            while i < len(lines) and lines[i].startswith("> "):
                quote_lines.append(lines[i][2:])
                i += 1
            # Parse the inner content as paragraphs
            inner_text = "\n".join(quote_lines)
            inner_paragraphs = _split_paragraphs(inner_text)
            quote_content = []
            for para in inner_paragraphs:
                quote_content.append({
                    "type": "paragraph",
                    "content": _parse_inline_md(para),
                })
            content.append({
                "type": "blockquote",
                "content": quote_content,
            })
            continue

        # Blank line — skip
        if not line.strip():
            i += 1
            continue

        # Paragraph — collect non-blank, non-special lines
        para_lines = []
        while i < len(lines):
            current = lines[i]
            if not current.strip():
                break
            if current.startswith("```"):
                break
            if re.match(r"^#{1,6}\s+", current):
                break
            if re.match(r"^[-*+]\s+", current):
                break
            if re.match(r"^\d+\.\s+", current):
                break
            if current.startswith("> "):
                break
            if re.match(r"^(-{3,}|_{3,}|\*{3,})$", current.strip()):
                break
            para_lines.append(current)
            i += 1
        if para_lines:
            content.append({
                "type": "paragraph",
                "content": _parse_inline_md(" ".join(para_lines)),
            })
        continue

    if not content:
        return empty_doc

    return {"version": 1, "type": "doc", "content": content}


def _split_paragraphs(text: str) -> list[str]:
    """Split text into paragraphs on blank lines."""
    paragraphs = []
    current = []
    for line in text.split("\n"):
        if not line.strip():
            if current:
                paragraphs.append(" ".join(current))
                current = []
        else:
            current.append(line)
    if current:
        paragraphs.append(" ".join(current))
    return paragraphs


def _parse_inline_md(text: str) -> list[dict]:
    """Parse inline Markdown (links, bold, italic, code) into ADF inline nodes.

    Returns a list of ADF inline node dicts (text with marks).
    """
    if not text:
        return [{"type": "text", "text": ""}]

    nodes: list[dict] = []
    # Pattern to match inline elements: links, bold, italic, code, strikethrough
    # Process from left to right using a regex that captures known patterns
    pattern = re.compile(
        r"(?P<link>\[(?P<link_text>[^\]]*)\]\((?P<link_url>[^)]*)\))"
        r"|(?P<code>`(?P<code_text>[^`]+)`)"
        r"|(?P<bold>\*\*(?P<bold_text>[^*]+)\*\*)"
        r"|(?P<italic>\*(?P<italic_text>[^*]+)\*)"
        r"|(?P<strike>~~(?P<strike_text>[^~]+)~~)"
    )

    pos = 0
    for match in pattern.finditer(text):
        # Add any plain text before this match
        if match.start() > pos:
            plain = text[pos:match.start()]
            if plain:
                nodes.append({"type": "text", "text": plain})

        if match.group("link"):
            link_text = match.group("link_text")
            link_url = match.group("link_url")
            nodes.append({
                "type": "text",
                "text": link_text,
                "marks": [{"type": "link", "attrs": {"href": link_url}}],
            })
        elif match.group("code"):
            code_text = match.group("code_text")
            nodes.append({
                "type": "text",
                "text": code_text,
                "marks": [{"type": "code"}],
            })
        elif match.group("bold"):
            bold_text = match.group("bold_text")
            nodes.append({
                "type": "text",
                "text": bold_text,
                "marks": [{"type": "strong"}],
            })
        elif match.group("italic"):
            italic_text = match.group("italic_text")
            nodes.append({
                "type": "text",
                "text": italic_text,
                "marks": [{"type": "em"}],
            })
        elif match.group("strike"):
            strike_text = match.group("strike_text")
            nodes.append({
                "type": "text",
                "text": strike_text,
                "marks": [{"type": "strike"}],
            })

        pos = match.end()

    # Add remaining text
    if pos < len(text):
        remaining = text[pos:]
        if remaining:
            nodes.append({"type": "text", "text": remaining})

    if not nodes:
        nodes.append({"type": "text", "text": text})

    return nodes
