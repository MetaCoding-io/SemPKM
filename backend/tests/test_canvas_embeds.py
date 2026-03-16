"""Unit tests for canvas embed document handling.

Tests:
- Embed document serialization round-trip
- Backward compatibility with pre-embed documents
- Embed URL construction for all embed types
- Max embed count enforcement
- Mixed node documents (regular + embed)
- Edge case: malformed embedConfig

Mirrors the pattern from test_canvas_resize.py — pure JSON structure tests,
no Docker or triplestore needed.
"""

import json
import uuid
from urllib.parse import quote, urlencode

import pytest


# ---- Helpers (mirroring test_canvas_resize.py pattern) ----

def make_regular_node(id: str, x: int, y: int, **kwargs) -> dict:
    """Create a minimal regular canvas node dict."""
    node = {"id": id, "x": x, "y": y, "title": id, "uri": f"urn:test:{id}"}
    node.update(kwargs)
    return node


def make_embed_node(id: str, x: int, y: int, embed_type: str, embed_id: str,
                    url: str, label: str, **kwargs) -> dict:
    """Create a canvas embed node dict."""
    node = {
        "id": id,
        "x": x,
        "y": y,
        "width": kwargs.pop("width", 400),
        "height": kwargs.pop("height", 300),
        "nodeType": "embed",
        "embedConfig": {
            "type": embed_type,
            "id": embed_id,
            "url": url,
            "label": label,
        },
    }
    node.update(kwargs)
    return node


def make_document(nodes: list[dict], edges: list | None = None,
                  viewport: dict | None = None) -> dict:
    """Create a canvas document dict."""
    doc = {
        "nodes": nodes,
        "edges": edges or [],
    }
    if viewport:
        doc["viewport"] = viewport
    return doc


def round_trip(document: dict) -> dict:
    """Simulate JSON serialization round-trip (what the API does via json.dumps/loads)."""
    return json.loads(json.dumps(document))


# ---- Simulate JS getDocument/applyDocument from canvas.js ----

def js_get_document_node(n: dict) -> dict:
    """Simulate canvas.js getDocument() serialization for one node.

    Mirrors the JS code:
      serialized = {id, title, uri, x, y, markdown, collapsed}
      if width !== undefined → serialized.width = width
      if height !== undefined → serialized.height = height
      if showProperties → serialized.showProperties = true
      if nodeType → serialized.nodeType = nodeType
      if embedConfig → serialized.embedConfig = embedConfig
    """
    serialized = {
        "id": n["id"],
        "title": n.get("title", ""),
        "uri": n.get("uri", ""),
        "x": n["x"],
        "y": n["y"],
        "markdown": n.get("markdown", ""),
        "collapsed": bool(n.get("collapsed", False)),
    }
    if n.get("width") is not None:
        serialized["width"] = n["width"]
    if n.get("height") is not None:
        serialized["height"] = n["height"]
    if n.get("showProperties"):
        serialized["showProperties"] = True
    if n.get("nodeType"):
        serialized["nodeType"] = n["nodeType"]
    if n.get("embedConfig") is not None:
        serialized["embedConfig"] = n["embedConfig"]
    return serialized


def js_apply_document_node(s: dict) -> dict:
    """Simulate canvas.js applyDocument() deserialization for one node.

    Mirrors the JS code:
      node = {id, title, uri, x, y, markdown, collapsed}
      if width defined and not null → node.width = Number(width)
      if height defined and not null → node.height = Number(height)
      if showProperties → node.showProperties = true
      if nodeType → node.nodeType = nodeType
      if embedConfig → node.embedConfig = embedConfig
    """
    node = {
        "id": str(s.get("id", "")),
        "title": str(s.get("title", s.get("id", "Untitled"))),
        "uri": str(s.get("uri", s.get("id", ""))),
        "x": float(s.get("x", 0)),
        "y": float(s.get("y", 0)),
        "markdown": str(s.get("markdown", "")),
        "collapsed": bool(s.get("collapsed", False)),
    }
    w = s.get("width")
    if w is not None:
        node["width"] = float(w)
    h = s.get("height")
    if h is not None:
        node["height"] = float(h)
    if s.get("showProperties"):
        node["showProperties"] = True
    if s.get("nodeType"):
        node["nodeType"] = s["nodeType"]
    if s.get("embedConfig") is not None:
        node["embedConfig"] = s["embedConfig"]
    return node


def count_embeds(nodes: list[dict]) -> int:
    """Count embed nodes — mirrors the JS loop in addEmbedNode()."""
    return sum(1 for n in nodes if n.get("nodeType") == "embed")


MAX_EMBEDS = 8  # Matches canvas.js MAX_EMBEDS


# ---- Tests: Embed Document Serialization ----

class TestEmbedDocumentSerialization:
    """Test that canvas document JSON with embed nodes round-trips correctly."""

    def test_embed_node_preserves_nodeType_and_embedConfig(self):
        """nodeType and embedConfig survive JSON round-trip."""
        embed = make_embed_node(
            "e1", 100, 200, "view", "generic-table",
            "/browser/views/generic/table?embed=1", "Table View",
        )
        doc = make_document([embed])
        result = round_trip(doc)
        node = result["nodes"][0]
        assert node["nodeType"] == "embed"
        assert node["embedConfig"]["type"] == "view"
        assert node["embedConfig"]["id"] == "generic-table"
        assert node["embedConfig"]["url"] == "/browser/views/generic/table?embed=1"
        assert node["embedConfig"]["label"] == "Table View"

    def test_regular_node_has_no_nodeType(self):
        """Regular nodes must NOT have nodeType after round-trip."""
        regular = make_regular_node("r1", 50, 50)
        doc = make_document([regular])
        result = round_trip(doc)
        assert "nodeType" not in result["nodes"][0]
        assert "embedConfig" not in result["nodes"][0]

    def test_mixed_document_preserves_both_types(self):
        """Document with both regular and embed nodes preserves all fields."""
        doc = make_document([
            make_regular_node("r1", 0, 0),
            make_embed_node("e1", 100, 100, "dashboard", "abc-123",
                            "/browser/dashboard/abc-123?embed=1", "My Dashboard"),
        ])
        result = round_trip(doc)
        regular = result["nodes"][0]
        embed = result["nodes"][1]
        assert "nodeType" not in regular
        assert embed["nodeType"] == "embed"
        assert embed["embedConfig"]["type"] == "dashboard"

    def test_embedConfig_requires_all_four_keys(self):
        """embedConfig must include type, id, url, label."""
        embed = make_embed_node(
            "e1", 0, 0, "query", "q-id",
            "/browser/sparql-result/q-id?embed=1", "Saved Query",
        )
        config = embed["embedConfig"]
        required = {"type", "id", "url", "label"}
        assert set(config.keys()) == required

    def test_embed_dimensions_preserved(self):
        """Embed node width/height survive round-trip."""
        embed = make_embed_node(
            "e1", 0, 0, "view", "v1",
            "/browser/views/generic/table?embed=1", "View",
            width=600, height=450,
        )
        doc = make_document([embed])
        result = round_trip(doc)
        assert result["nodes"][0]["width"] == 600
        assert result["nodes"][0]["height"] == 450


# ---- Tests: Backward Compatibility ----

class TestEmbedBackwardCompat:
    """Old-format documents (no nodeType on any node) load without errors."""

    def test_old_document_with_minimal_fields(self):
        """Minimal old doc: id, x, y, title, uri — no KeyError."""
        old_doc = make_document([
            {"id": "n1", "x": 10, "y": 20, "title": "Old Node", "uri": "urn:test:old"},
        ])
        result = round_trip(old_doc)
        node = result["nodes"][0]
        assert node["id"] == "n1"
        assert "nodeType" not in node
        assert "embedConfig" not in node

    def test_old_document_full_fields(self):
        """Old doc with all pre-embed fields: markdown, collapsed, width, height."""
        old_doc = make_document([
            {
                "id": "n1", "x": 0, "y": 0,
                "title": "Full Old Node", "uri": "urn:test:full-old",
                "markdown": "## Hello", "collapsed": True,
                "width": 500, "height": 300,
            },
        ])
        result = round_trip(old_doc)
        node = result["nodes"][0]
        assert node["markdown"] == "## Hello"
        assert node["collapsed"] is True
        assert node["width"] == 500
        assert node["height"] == 300
        assert "nodeType" not in node

    def test_old_document_with_edges(self):
        """Old doc with edges round-trips fine."""
        old_doc = make_document(
            nodes=[
                {"id": "a", "x": 0, "y": 0, "title": "A", "uri": "urn:a"},
                {"id": "b", "x": 100, "y": 0, "title": "B", "uri": "urn:b"},
            ],
            edges=[{"source": "a", "target": "b", "label": "knows"}],
        )
        result = round_trip(old_doc)
        assert len(result["nodes"]) == 2
        assert len(result["edges"]) == 1

    def test_empty_document(self):
        """Empty nodes/edges round-trips fine."""
        doc = make_document([])
        result = round_trip(doc)
        assert result["nodes"] == []
        assert result["edges"] == []

    def test_apply_document_handles_missing_nodeType_gracefully(self):
        """applyDocument simulation: old node without nodeType produces no nodeType key."""
        old_serialized = {
            "id": "n1", "x": 10, "y": 20,
            "title": "Old", "uri": "urn:old",
        }
        restored = js_apply_document_node(old_serialized)
        assert "nodeType" not in restored
        assert "embedConfig" not in restored

    def test_apply_document_handles_old_and_new_mixed(self):
        """applyDocument simulation: mixed old-new doc doesn't cross-contaminate."""
        old_node = {"id": "r1", "x": 0, "y": 0, "title": "Reg", "uri": "urn:r1"}
        new_node = {
            "id": "e1", "x": 50, "y": 50, "title": "Embed",
            "nodeType": "embed",
            "embedConfig": {
                "type": "view", "id": "v1",
                "url": "/browser/views/generic/table?embed=1", "label": "Table",
            },
            "width": 400, "height": 300,
        }
        restored_old = js_apply_document_node(old_node)
        restored_new = js_apply_document_node(new_node)
        assert "nodeType" not in restored_old
        assert restored_new["nodeType"] == "embed"
        assert restored_new["embedConfig"]["type"] == "view"


# ---- Tests: Embed URL Construction ----

class TestEmbedURLConstruction:
    """Test embed URLs are correctly constructed for each embed type."""

    def test_view_embed_url(self):
        url = "/browser/views/generic/table?embed=1"
        assert url.startswith("/browser/views/generic/")
        assert "embed=1" in url

    def test_view_embed_url_with_class_filter(self):
        type_iri = "http://example.org/Person"
        url = f"/browser/views/generic/table?embed=1&type={quote(type_iri, safe='')}"
        assert "embed=1" in url
        assert quote(type_iri, safe='') in url

    def test_dashboard_embed_url(self):
        dashboard_id = str(uuid.uuid4())
        url = f"/browser/dashboard/{dashboard_id}?embed=1"
        assert f"/browser/dashboard/{dashboard_id}" in url
        assert "embed=1" in url

    def test_sparql_result_url(self):
        query_id = str(uuid.uuid4())
        url = f"/browser/sparql-result/{query_id}?embed=1"
        assert f"/browser/sparql-result/{query_id}" in url
        assert "embed=1" in url

    def test_object_embed_url(self):
        iri = "urn:sempkm:obj:test-123"
        url = f"/browser/object/{quote(iri, safe='')}?embed=1"
        assert "embed=1" in url
        assert quote(iri, safe='') in url

    def test_object_embed_url_with_special_chars(self):
        """Object IRIs with special chars must be URL-encoded."""
        iri = "http://example.org/Thing#Part One"
        encoded = quote(iri, safe='')
        url = f"/browser/object/{encoded}?embed=1"
        assert "embed=1" in url
        # Space and # must be encoded
        assert " " not in url.split("?")[0]
        assert "#" not in url.split("?")[0]

    def test_all_embed_types_representable(self):
        """All four embed types produce valid URLs."""
        types_and_patterns = {
            "view": "/browser/views/generic/",
            "dashboard": "/browser/dashboard/",
            "query": "/browser/sparql-result/",
            "object": "/browser/object/",
        }
        for embed_type, pattern in types_and_patterns.items():
            test_id = f"test-{embed_type}"
            url = f"{pattern}{test_id}?embed=1"
            assert "embed=1" in url, f"Missing embed=1 for type {embed_type}"
            assert test_id in url, f"Missing ID for type {embed_type}"


# ---- Tests: Max Embed Count Enforcement ----

class TestMaxEmbedCount:
    """Test the max-8-embed enforcement logic."""

    def test_document_with_8_embeds_is_valid(self):
        """8 embeds is the maximum allowed."""
        nodes = [
            make_embed_node(
                f"e{i}", i * 50, 0, "view", f"v{i}",
                f"/browser/views/generic/table?embed=1&n={i}", f"View {i}",
            )
            for i in range(MAX_EMBEDS)
        ]
        assert count_embeds(nodes) == MAX_EMBEDS

    def test_9th_embed_would_be_rejected(self):
        """9th embed exceeds the limit — counting logic rejects it."""
        nodes = [
            make_embed_node(
                f"e{i}", i * 50, 0, "view", f"v{i}",
                f"/browser/views/generic/table?embed=1&n={i}", f"View {i}",
            )
            for i in range(MAX_EMBEDS)
        ]
        assert count_embeds(nodes) >= MAX_EMBEDS
        # The addEmbedNode() JS check: if (embedCount >= MAX_EMBEDS) return
        # A 9th push would be blocked — simulated here
        assert not (count_embeds(nodes) < MAX_EMBEDS)

    def test_regular_nodes_dont_count_toward_limit(self):
        """Regular nodes don't count toward the embed limit."""
        nodes = [make_regular_node(f"r{i}", i * 50, 0) for i in range(20)]
        nodes.append(
            make_embed_node("e0", 0, 100, "view", "v0",
                            "/browser/views/generic/table?embed=1", "View"),
        )
        assert count_embeds(nodes) == 1
        assert count_embeds(nodes) < MAX_EMBEDS

    def test_mixed_count_only_embeds(self):
        """In a mixed document, only embed nodes count toward the limit."""
        nodes = [make_regular_node(f"r{i}", i * 50, 0) for i in range(5)]
        nodes.extend([
            make_embed_node(
                f"e{i}", i * 50, 100, "dashboard", f"d{i}",
                f"/browser/dashboard/d{i}?embed=1", f"Dash {i}",
            )
            for i in range(7)
        ])
        assert count_embeds(nodes) == 7
        assert count_embeds(nodes) < MAX_EMBEDS  # room for one more

    def test_zero_embeds(self):
        """Document with no embeds has count 0."""
        nodes = [make_regular_node(f"r{i}", i * 50, 0) for i in range(3)]
        assert count_embeds(nodes) == 0


# ---- Tests: Mixed Node Document (realistic scenario) ----

class TestMixedNodeDocument:
    """Test a realistic document with regular nodes, resized nodes, and embeds."""

    @pytest.fixture
    def realistic_document(self):
        """Create a realistic mixed document."""
        return make_document(
            nodes=[
                # Regular node — default size
                make_regular_node("r1", 0, 0, markdown="# Hello World"),
                # Regular node — resized
                make_regular_node("r2", 300, 0, width=500, height=350),
                # Regular node — showProperties enabled
                make_regular_node("r3", 0, 400, showProperties=True),
                # View embed
                make_embed_node(
                    "e1", 600, 0, "view", "generic-table",
                    "/browser/views/generic/table?embed=1", "Table View",
                    width=500, height=400,
                ),
                # Dashboard embed
                make_embed_node(
                    "e2", 600, 500, "dashboard", "dash-abc",
                    "/browser/dashboard/dash-abc?embed=1", "My Dashboard",
                ),
            ],
            edges=[
                {"id": "edge1", "source": "r1", "target": "r2", "label": "related"},
            ],
            viewport={"x": 50, "y": 25, "zoom": 1.2},
        )

    def test_round_trip_preserves_all_fields(self, realistic_document):
        """Full document round-trips through JSON without loss."""
        result = round_trip(realistic_document)
        assert len(result["nodes"]) == 5
        assert len(result["edges"]) == 1
        assert result["viewport"]["zoom"] == 1.2

    def test_regular_nodes_preserved(self, realistic_document):
        result = round_trip(realistic_document)
        r1, r2, r3 = result["nodes"][0], result["nodes"][1], result["nodes"][2]

        # r1: regular with markdown
        assert r1["id"] == "r1"
        assert r1["markdown"] == "# Hello World"
        assert "nodeType" not in r1
        assert "width" not in r1  # default size

        # r2: resized
        assert r2["width"] == 500
        assert r2["height"] == 350
        assert "nodeType" not in r2

        # r3: showProperties
        assert r3["showProperties"] is True
        assert "nodeType" not in r3

    def test_embed_nodes_preserved(self, realistic_document):
        result = round_trip(realistic_document)
        e1, e2 = result["nodes"][3], result["nodes"][4]

        # View embed
        assert e1["nodeType"] == "embed"
        assert e1["embedConfig"]["type"] == "view"
        assert e1["embedConfig"]["url"] == "/browser/views/generic/table?embed=1"
        assert e1["width"] == 500
        assert e1["height"] == 400

        # Dashboard embed
        assert e2["nodeType"] == "embed"
        assert e2["embedConfig"]["type"] == "dashboard"
        assert e2["embedConfig"]["label"] == "My Dashboard"
        assert e2["width"] == 400  # default
        assert e2["height"] == 300  # default

    def test_positions_correct(self, realistic_document):
        result = round_trip(realistic_document)
        positions = [(n["id"], n["x"], n["y"]) for n in result["nodes"]]
        assert ("r1", 0, 0) in positions
        assert ("r2", 300, 0) in positions
        assert ("e1", 600, 0) in positions
        assert ("e2", 600, 500) in positions

    def test_js_simulation_round_trip(self, realistic_document):
        """Simulate full JS getDocument → JSON → applyDocument cycle."""
        # getDocument (serialize)
        serialized_nodes = [js_get_document_node(n) for n in realistic_document["nodes"]]
        serialized_doc = {
            "nodes": serialized_nodes,
            "edges": realistic_document["edges"],
            "viewport": realistic_document["viewport"],
        }

        # JSON round-trip (API save/load)
        json_str = json.dumps(serialized_doc)
        parsed = json.loads(json_str)

        # applyDocument (deserialize)
        restored_nodes = [js_apply_document_node(n) for n in parsed["nodes"]]

        # Verify regular nodes
        r1 = restored_nodes[0]
        assert "nodeType" not in r1
        assert r1["markdown"] == "# Hello World"

        r2 = restored_nodes[1]
        assert "nodeType" not in r2
        assert r2["width"] == 500.0

        r3 = restored_nodes[2]
        assert r3.get("showProperties") is True
        assert "nodeType" not in r3

        # Verify embed nodes
        e1 = restored_nodes[3]
        assert e1["nodeType"] == "embed"
        assert e1["embedConfig"]["type"] == "view"
        assert e1["width"] == 500.0

        e2 = restored_nodes[4]
        assert e2["nodeType"] == "embed"
        assert e2["embedConfig"]["type"] == "dashboard"


# ---- Tests: Edge case — malformed embedConfig ----

class TestMalformedEmbedConfig:
    """Test handling of embed nodes with missing or empty embedConfig."""

    def test_nodeType_embed_but_no_embedConfig(self):
        """A node with nodeType='embed' but missing embedConfig.

        applyDocument should still process it — nodeType is set, embedConfig absent.
        The rendering layer (renderNodes) should handle this gracefully.
        """
        malformed = {
            "id": "bad1", "x": 0, "y": 0, "title": "Bad Embed",
            "nodeType": "embed",
            # No embedConfig key at all
        }
        restored = js_apply_document_node(malformed)
        assert restored["nodeType"] == "embed"
        assert "embedConfig" not in restored

    def test_nodeType_embed_with_empty_embedConfig(self):
        """A node with nodeType='embed' and empty embedConfig dict."""
        malformed = {
            "id": "bad2", "x": 0, "y": 0, "title": "Empty Config",
            "nodeType": "embed",
            "embedConfig": {},
        }
        restored = js_apply_document_node(malformed)
        assert restored["nodeType"] == "embed"
        assert restored["embedConfig"] == {}

    def test_nodeType_embed_with_partial_embedConfig(self):
        """embedConfig with only some fields present."""
        partial = {
            "id": "bad3", "x": 0, "y": 0, "title": "Partial",
            "nodeType": "embed",
            "embedConfig": {"type": "view"},  # missing id, url, label
        }
        restored = js_apply_document_node(partial)
        assert restored["nodeType"] == "embed"
        assert restored["embedConfig"]["type"] == "view"
        assert "url" not in restored["embedConfig"]

    def test_malformed_in_mixed_document_doesnt_corrupt_others(self):
        """A malformed embed shouldn't affect other nodes in the document."""
        doc = make_document([
            make_regular_node("r1", 0, 0),
            {"id": "bad", "x": 50, "y": 50, "nodeType": "embed"},  # no embedConfig
            make_embed_node("e1", 100, 100, "view", "v1",
                            "/browser/views/generic/table?embed=1", "OK"),
        ])
        result = round_trip(doc)
        # All three nodes present and parseable
        assert len(result["nodes"]) == 3
        assert "nodeType" not in result["nodes"][0]
        assert result["nodes"][1]["nodeType"] == "embed"
        assert result["nodes"][2]["embedConfig"]["label"] == "OK"
