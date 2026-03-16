"""Unit tests for canvas document serialization with width/height fields.

Tests JSON round-trip fidelity for node dimensions (resize persistence).
No Docker or triplestore needed — pure JSON structure tests.
"""

import json

import pytest


# ---- Helpers ----

def make_node(id: str, x: int, y: int, **kwargs) -> dict:
    """Create a minimal canvas node dict."""
    node = {"id": id, "x": x, "y": y, "title": id, "uri": f"urn:test:{id}"}
    node.update(kwargs)
    return node


def make_document(nodes: list[dict], edges: list | None = None) -> dict:
    """Create a canvas document dict."""
    return {
        "nodes": nodes,
        "edges": edges or [],
    }


def round_trip(document: dict) -> dict:
    """Simulate JSON serialization round-trip (what the API does)."""
    return json.loads(json.dumps(document))


# ---- Tests: width/height round-trip ----

class TestCanvasNodeDimensions:
    """Tests for canvas node width/height serialization."""

    def test_width_height_preserved_on_round_trip(self):
        """A node with explicit width/height round-trips through JSON."""
        doc = make_document([
            make_node("a", 0, 0, width=500, height=300),
        ])
        result = round_trip(doc)
        node = result["nodes"][0]
        assert node["width"] == 500
        assert node["height"] == 300

    def test_multiple_nodes_with_dimensions(self):
        """Multiple nodes with different dimensions all preserve correctly."""
        doc = make_document([
            make_node("a", 0, 0, width=500, height=300),
            make_node("b", 300, 0, width=260, height=160),
            make_node("c", 600, 0, width=800, height=600),
        ])
        result = round_trip(doc)
        assert result["nodes"][0]["width"] == 500
        assert result["nodes"][0]["height"] == 300
        assert result["nodes"][1]["width"] == 260
        assert result["nodes"][1]["height"] == 160
        assert result["nodes"][2]["width"] == 800
        assert result["nodes"][2]["height"] == 600

    def test_float_dimensions_preserved(self):
        """Grid-snapped values are always ints, but floats shouldn't break."""
        doc = make_document([
            make_node("a", 0, 0, width=500.5, height=300.75),
        ])
        result = round_trip(doc)
        assert result["nodes"][0]["width"] == 500.5
        assert result["nodes"][0]["height"] == 300.75


# ---- Tests: backward compatibility ----

class TestBackwardCompatibility:
    """Tests for documents without width/height fields (pre-resize sessions)."""

    def test_document_without_dimensions_parses(self):
        """Old documents without width/height on nodes parse without error."""
        doc = make_document([
            make_node("a", 0, 0),
            make_node("b", 300, 0),
        ])
        result = round_trip(doc)
        assert len(result["nodes"]) == 2
        assert "width" not in result["nodes"][0]
        assert "height" not in result["nodes"][0]

    def test_empty_nodes_list(self):
        """Empty nodes list round-trips fine."""
        doc = make_document([])
        result = round_trip(doc)
        assert result["nodes"] == []

    def test_mixed_nodes_with_and_without_dimensions(self):
        """A document with a mix of resized and default nodes serializes correctly."""
        doc = make_document([
            make_node("resized", 0, 0, width=500, height=300),
            make_node("default", 300, 0),  # No width/height — CSS default
            make_node("partial-w", 600, 0, width=400),  # Only width
            make_node("partial-h", 0, 300, height=200),  # Only height
        ])
        result = round_trip(doc)

        # Resized: both dimensions present
        assert result["nodes"][0]["width"] == 500
        assert result["nodes"][0]["height"] == 300

        # Default: neither dimension present
        assert "width" not in result["nodes"][1]
        assert "height" not in result["nodes"][1]

        # Partial width: only width present
        assert result["nodes"][2]["width"] == 400
        assert "height" not in result["nodes"][2]

        # Partial height: only height present
        assert "width" not in result["nodes"][3]
        assert result["nodes"][3]["height"] == 200


# ---- Tests: edge preservation alongside dimensions ----

class TestEdgesWithDimensions:
    """Edges serialize alongside nodes with dimensions."""

    def test_edges_preserved_with_resized_nodes(self):
        """Document with edges and resized nodes round-trips correctly."""
        doc = make_document(
            nodes=[
                make_node("a", 0, 0, width=500, height=300),
                make_node("b", 600, 0),
            ],
            edges=[
                {"id": "e1", "source": "a", "target": "b", "label": "references"},
            ],
        )
        result = round_trip(doc)
        assert len(result["edges"]) == 1
        assert result["edges"][0]["source"] == "a"
        assert result["edges"][0]["target"] == "b"
        assert result["nodes"][0]["width"] == 500

    def test_viewport_preserved(self):
        """Viewport state round-trips alongside node dimensions."""
        doc = {
            "nodes": [make_node("a", 0, 0, width=400, height=200)],
            "edges": [],
            "viewport": {"x": 100, "y": 50, "zoom": 1.5},
        }
        result = round_trip(doc)
        assert result["viewport"]["x"] == 100
        assert result["viewport"]["zoom"] == 1.5
        assert result["nodes"][0]["width"] == 400


# ---- Tests: simulate getDocument/applyDocument JS logic ----

class TestGetDocumentApplyDocumentSimulation:
    """Simulate the JS getDocument/applyDocument conditional serialization.

    getDocument() only includes width/height when defined (not undefined/null).
    applyDocument() restores Number(n.width) only when defined and not null.
    """

    @staticmethod
    def js_get_document_node(node: dict) -> dict:
        """Simulate canvas.js getDocument() serialization for one node."""
        serialized = {
            "id": node["id"],
            "x": node["x"],
            "y": node["y"],
            "title": node.get("title", ""),
            "uri": node.get("uri", ""),
        }
        if node.get("width") is not None:
            serialized["width"] = node["width"]
        if node.get("height") is not None:
            serialized["height"] = node["height"]
        return serialized

    @staticmethod
    def js_apply_document_node(serialized: dict) -> dict:
        """Simulate canvas.js applyDocument() deserialization for one node."""
        node = {
            "id": serialized["id"],
            "x": serialized["x"],
            "y": serialized["y"],
            "title": serialized.get("title", ""),
            "uri": serialized.get("uri", ""),
        }
        w = serialized.get("width")
        if w is not None:
            node["width"] = float(w)
        h = serialized.get("height")
        if h is not None:
            node["height"] = float(h)
        return node

    def test_resized_node_round_trips(self):
        """Resized node → getDocument → JSON → applyDocument preserves dims."""
        original = {"id": "a", "x": 0, "y": 0, "width": 500, "height": 300, "title": "A", "uri": "urn:a"}
        serialized = self.js_get_document_node(original)
        json_str = json.dumps(serialized)
        parsed = json.loads(json_str)
        restored = self.js_apply_document_node(parsed)
        assert restored["width"] == 500.0
        assert restored["height"] == 300.0

    def test_default_node_has_no_dimensions(self):
        """Unresized node → getDocument omits width/height → applyDocument has none."""
        original = {"id": "b", "x": 100, "y": 100, "title": "B", "uri": "urn:b"}
        serialized = self.js_get_document_node(original)
        assert "width" not in serialized
        assert "height" not in serialized
        json_str = json.dumps(serialized)
        parsed = json.loads(json_str)
        restored = self.js_apply_document_node(parsed)
        assert "width" not in restored
        assert "height" not in restored

    def test_null_dimensions_treated_as_absent(self):
        """Explicit null in width/height → applyDocument treats as absent."""
        serialized = {"id": "c", "x": 0, "y": 0, "title": "C", "uri": "urn:c", "width": None, "height": None}
        json_str = json.dumps(serialized)
        parsed = json.loads(json_str)
        restored = self.js_apply_document_node(parsed)
        assert "width" not in restored
        assert "height" not in restored
