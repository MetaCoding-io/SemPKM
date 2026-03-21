"""Pure OPML parser — converts OPML XML bytes to a list of feed dicts.

No SDK or framework dependency.  Fully testable as a standalone module.
"""

from __future__ import annotations

import logging
import xml.etree.ElementTree as ET

logger = logging.getLogger(__name__)


def parse_opml(xml_content: bytes) -> list[dict]:
    """Parse OPML *xml_content* (bytes) and return a list of feed dicts.

    Each dict has keys:
        url      – feed URL (xmlUrl attribute)
        title    – human-readable title (text > title > xmlUrl fallback)
        html_url – site URL (htmlUrl) or None
        category – slash-delimited category path or None

    Returns an empty list on any parse error (malformed XML, missing
    ``<body>`` element, etc.).
    """
    try:
        root = ET.fromstring(xml_content)
    except ET.ParseError as exc:
        logger.warning("OPML parse error (ParseError): %s", exc)
        return []
    except Exception as exc:  # noqa: BLE001
        logger.warning("OPML parse error (%s): %s", type(exc).__name__, exc)
        return []

    body = root.find("body")
    if body is None:
        logger.warning("OPML has no <body> element")
        return []

    feeds: list[dict] = []
    _walk_outlines(body, category_parts=[], feeds=feeds)
    return feeds


def _walk_outlines(
    parent: ET.Element,
    *,
    category_parts: list[str],
    feeds: list[dict],
) -> None:
    """Recursively walk ``<outline>`` children of *parent*.

    Outlines **with** an ``xmlUrl`` attribute are feed entries.
    Outlines **without** ``xmlUrl`` are category folders — their ``text``
    attribute becomes a segment of the ``/``-delimited category path.
    """
    for outline in parent.findall("outline"):
        xml_url = outline.get("xmlUrl")

        if xml_url:
            # ── Feed entry ──
            title = (
                outline.get("text")
                or outline.get("title")
                or xml_url
            )
            html_url = outline.get("htmlUrl") or None
            category = "/".join(category_parts) if category_parts else None

            feeds.append(
                {
                    "url": xml_url,
                    "title": title,
                    "html_url": html_url,
                    "category": category,
                }
            )
        else:
            # ── Category folder — recurse ──
            folder_name = outline.get("text") or outline.get("title") or ""
            _walk_outlines(
                outline,
                category_parts=[*category_parts, folder_name],
                feeds=feeds,
            )
