"""Unit tests for quadrant renderer backend: axis detection,
SPARQL query building, Eisenhower labelling, and server-side
grouping into quadrant buckets.

Tests cover _detect_quadrant_axes(), _build_quadrant_select(),
_quadrant_label(), and execute_quadrant_query() on ViewSpecService.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.services.shapes import NodeShapeForm, PropertyShape, ShapesService
from app.views.service import ViewSpecService


# ── Helpers ────────────────────────────────────────────────────


def _make_property(
    path: str,
    name: str,
    order: float = 0.0,
    in_values: list[str] | None = None,
) -> PropertyShape:
    return PropertyShape(
        path=path,
        name=name,
        order=order,
        in_values=in_values or [],
    )


def _make_form(
    target_class: str,
    properties: list[PropertyShape],
    label: str = "Test Shape",
) -> NodeShapeForm:
    return NodeShapeForm(
        shape_iri=f"urn:test:{label.lower().replace(' ', '-')}",
        target_class=target_class,
        label=label,
        properties=properties,
    )


def _build_service(
    form_return: NodeShapeForm | None = None,
    form_side_effect: Exception | None = None,
    shapes_service_none: bool = False,
    query_bindings: list[dict] | None = None,
) -> ViewSpecService:
    """Build a ViewSpecService with mocked dependencies."""
    if shapes_service_none:
        shapes = None
    else:
        shapes = MagicMock(spec=ShapesService)
        if form_side_effect:
            shapes.get_form_for_type = AsyncMock(side_effect=form_side_effect)
        else:
            shapes.get_form_for_type = AsyncMock(return_value=form_return)

    client = MagicMock()
    if query_bindings is not None:
        client.query = AsyncMock(return_value={
            "results": {"bindings": query_bindings},
        })
    else:
        client.query = AsyncMock(return_value={
            "results": {"bindings": []},
        })

    label_service = MagicMock()

    svc = ViewSpecService(
        client=client,
        label_service=label_service,
        shapes_service=shapes,
    )

    return svc


# ── _detect_quadrant_axes ─────────────────────────────────────


class TestDetectQuadrantAxes:
    """Tests for _detect_quadrant_axes() which finds two SHACL
    properties with exactly 2 sh:in values for quadrant axes."""

    @pytest.mark.asyncio
    async def test_happy_path_urgency_importance(self):
        """Finds urgency (x) and importance (y) axes from sh:in with 2 values."""
        form = _make_form("urn:test:EisenhowerItem", [
            _make_property("urn:test:title", "Title"),
            _make_property(
                "urn:test:urgency", "Urgency",
                in_values=["high", "low"],
            ),
            _make_property(
                "urn:test:importance", "Importance",
                in_values=["high", "low"],
            ),
        ])
        svc = _build_service(form_return=form)
        x_axis, y_axis, x_vals, y_vals = await svc._detect_quadrant_axes(
            "urn:test:EisenhowerItem",
        )
        assert x_axis is not None
        assert y_axis is not None
        assert x_axis.path == "urn:test:urgency"
        assert y_axis.path == "urn:test:importance"
        assert x_vals == ["high", "low"]
        assert y_vals == ["high", "low"]

    @pytest.mark.asyncio
    async def test_keyword_preference_case_insensitive(self):
        """Path matching for 'urgency' and 'importance' is case-insensitive."""
        form = _make_form("urn:test:Item", [
            _make_property(
                "http://example.org/TaskUrgency", "Task Urgency",
                in_values=["high", "low"],
            ),
            _make_property(
                "http://example.org/TaskImportance", "Task Importance",
                in_values=["yes", "no"],
            ),
        ])
        svc = _build_service(form_return=form)
        x_axis, y_axis, x_vals, y_vals = await svc._detect_quadrant_axes(
            "urn:test:Item",
        )
        assert x_axis is not None
        assert y_axis is not None
        assert x_axis.path == "http://example.org/TaskUrgency"
        assert y_axis.path == "http://example.org/TaskImportance"
        assert x_vals == ["high", "low"]
        assert y_vals == ["yes", "no"]

    @pytest.mark.asyncio
    async def test_fallback_no_keyword_match(self):
        """When no property path contains 'urgency' or 'importance',
        uses first two candidates."""
        form = _make_form("urn:test:Item", [
            _make_property(
                "urn:test:axisA", "Axis A",
                in_values=["on", "off"],
            ),
            _make_property(
                "urn:test:axisB", "Axis B",
                in_values=["yes", "no"],
            ),
        ])
        svc = _build_service(form_return=form)
        x_axis, y_axis, x_vals, y_vals = await svc._detect_quadrant_axes(
            "urn:test:Item",
        )
        assert x_axis is not None
        assert y_axis is not None
        assert x_axis.path == "urn:test:axisA"
        assert y_axis.path == "urn:test:axisB"
        assert x_vals == ["on", "off"]
        assert y_vals == ["yes", "no"]

    @pytest.mark.asyncio
    async def test_rejects_sh_in_with_more_than_2_values(self):
        """Properties with 3+ sh:in values are not quadrant candidates."""
        form = _make_form("urn:test:Task", [
            _make_property(
                "urn:test:status", "Status",
                in_values=["todo", "in-progress", "done"],
            ),
            _make_property(
                "urn:test:priority", "Priority",
                in_values=["low", "medium", "high", "critical"],
            ),
        ])
        svc = _build_service(form_return=form)
        x_axis, y_axis, x_vals, y_vals = await svc._detect_quadrant_axes(
            "urn:test:Task",
        )
        assert x_axis is None
        assert y_axis is None
        assert x_vals == []
        assert y_vals == []

    @pytest.mark.asyncio
    async def test_rejects_single_candidate(self):
        """Only one property with 2 sh:in values is not enough."""
        form = _make_form("urn:test:Item", [
            _make_property(
                "urn:test:urgency", "Urgency",
                in_values=["high", "low"],
            ),
            _make_property("urn:test:title", "Title"),
        ])
        svc = _build_service(form_return=form)
        x_axis, y_axis, x_vals, y_vals = await svc._detect_quadrant_axes(
            "urn:test:Item",
        )
        assert x_axis is None
        assert y_axis is None
        assert x_vals == []
        assert y_vals == []

    @pytest.mark.asyncio
    async def test_no_shapes_service(self):
        """Returns None tuple when shapes_service is None."""
        svc = _build_service(shapes_service_none=True)
        x_axis, y_axis, x_vals, y_vals = await svc._detect_quadrant_axes(
            "urn:test:Item",
        )
        assert x_axis is None
        assert y_axis is None
        assert x_vals == []
        assert y_vals == []

    @pytest.mark.asyncio
    async def test_no_form_for_type(self):
        """Returns None tuple when get_form_for_type returns None."""
        svc = _build_service(form_return=None)
        x_axis, y_axis, x_vals, y_vals = await svc._detect_quadrant_axes(
            "urn:test:Unknown",
        )
        assert x_axis is None
        assert y_axis is None
        assert x_vals == []
        assert y_vals == []

    @pytest.mark.asyncio
    async def test_shapes_lookup_exception(self):
        """Returns None tuple when shapes lookup raises an exception."""
        svc = _build_service(form_side_effect=RuntimeError("shapes broken"))
        x_axis, y_axis, x_vals, y_vals = await svc._detect_quadrant_axes(
            "urn:test:Item",
        )
        assert x_axis is None
        assert y_axis is None
        assert x_vals == []
        assert y_vals == []

    @pytest.mark.asyncio
    async def test_three_candidates_picks_urgency_importance(self):
        """When 3+ properties have exactly 2 sh:in values, urgency/importance
        are preferred over the third candidate."""
        form = _make_form("urn:test:Item", [
            _make_property(
                "urn:test:color", "Color",
                in_values=["red", "blue"],
            ),
            _make_property(
                "urn:test:urgency", "Urgency",
                in_values=["high", "low"],
            ),
            _make_property(
                "urn:test:importance", "Importance",
                in_values=["high", "low"],
            ),
        ])
        svc = _build_service(form_return=form)
        x_axis, y_axis, x_vals, y_vals = await svc._detect_quadrant_axes(
            "urn:test:Item",
        )
        assert x_axis.path == "urn:test:urgency"
        assert y_axis.path == "urn:test:importance"


# ── _build_quadrant_select ────────────────────────────────────


class TestBuildQuadrantSelect:
    """Tests for _build_quadrant_select() static method."""

    def test_basic(self):
        """Produces correct SPARQL with type and both axis paths."""
        query = ViewSpecService._build_quadrant_select(
            "urn:test:EisenhowerItem",
            "urn:test:urgency",
            "urn:test:importance",
        )
        assert "SELECT ?s ?label ?xValue ?yValue" in query
        assert "rdf:type <urn:test:EisenhowerItem>" in query
        assert "<urn:test:urgency> ?xValue" in query
        assert "<urn:test:importance> ?yValue" in query
        assert "rdfs:label|dcterms:title" in query
        # No scope sub-select
        assert "{ SELECT ?s WHERE" not in query

    def test_with_scope_filter(self):
        """Scope filter injected as sub-select."""
        query = ViewSpecService._build_quadrant_select(
            "urn:test:Item",
            "urn:test:x",
            "urn:test:y",
            scope_filter="?s <urn:ex:tag> 'urgent' .",
        )
        assert "{ SELECT ?s WHERE { ?s <urn:ex:tag> 'urgent' . } }" in query
        assert "rdf:type <urn:test:Item>" in query

    def test_no_scope_filter_none(self):
        """Explicitly passing None for scope_filter produces no sub-select."""
        query = ViewSpecService._build_quadrant_select(
            "urn:test:Item", "urn:test:x", "urn:test:y", scope_filter=None,
        )
        assert "{ SELECT ?s WHERE" not in query

    def test_axis_bindings_non_optional(self):
        """Both axis bindings are required (not wrapped in OPTIONAL)."""
        query = ViewSpecService._build_quadrant_select(
            "urn:test:Item", "urn:test:x", "urn:test:y",
        )
        # The xValue and yValue bindings should NOT be inside OPTIONAL
        lines = query.split("\n")
        for line in lines:
            if "?xValue" in line and "OPTIONAL" in line:
                pytest.fail("xValue binding should not be OPTIONAL")
            if "?yValue" in line and "OPTIONAL" in line:
                pytest.fail("yValue binding should not be OPTIONAL")


# ── _quadrant_label ───────────────────────────────────────────


class TestQuadrantLabel:
    """Tests for _quadrant_label() which generates human-readable
    quadrant cell labels."""

    def test_eisenhower_do_first(self):
        svc = _build_service()
        assert svc._quadrant_label("high", "high", "Urgency", "Importance") == "Do First"

    def test_eisenhower_schedule(self):
        svc = _build_service()
        assert svc._quadrant_label("low", "high", "Urgency", "Importance") == "Schedule"

    def test_eisenhower_delegate(self):
        svc = _build_service()
        assert svc._quadrant_label("high", "low", "Urgency", "Importance") == "Delegate"

    def test_eisenhower_eliminate(self):
        svc = _build_service()
        assert svc._quadrant_label("low", "low", "Urgency", "Importance") == "Eliminate"

    def test_generic_fallback(self):
        """Non-Eisenhower value combinations use generic label."""
        svc = _build_service()
        label = svc._quadrant_label("on", "off", "Power", "Speed")
        assert label == "Power: on / Speed: off"


# ── execute_quadrant_query ────────────────────────────────────


class TestExecuteQuadrantQuery:
    """Tests for execute_quadrant_query() grouping logic."""

    @pytest.mark.asyncio
    async def test_groups_items_into_4_quadrants(self):
        """Mock SPARQL results grouped into 4 quadrant buckets."""
        bindings = [
            {
                "s": {"value": "urn:item:1"},
                "label": {"value": "Item One"},
                "xValue": {"value": "high"},
                "yValue": {"value": "high"},
            },
            {
                "s": {"value": "urn:item:2"},
                "label": {"value": "Item Two"},
                "xValue": {"value": "low"},
                "yValue": {"value": "high"},
            },
            {
                "s": {"value": "urn:item:3"},
                "label": {"value": "Item Three"},
                "xValue": {"value": "high"},
                "yValue": {"value": "low"},
            },
            {
                "s": {"value": "urn:item:4"},
                "label": {"value": "Item Four"},
                "xValue": {"value": "low"},
                "yValue": {"value": "low"},
            },
        ]
        svc = _build_service(query_bindings=bindings)
        x_axis = _make_property("urn:test:urgency", "Urgency", in_values=["high", "low"])
        y_axis = _make_property("urn:test:importance", "Importance", in_values=["high", "low"])

        result = await svc.execute_quadrant_query(
            "urn:test:EisenhowerItem",
            x_axis, y_axis,
            ["high", "low"], ["high", "low"],
        )

        assert result["total"] == 4
        assert len(result["quadrants"]) == 4  # no unclassified

        # Check axes metadata
        assert result["axes"]["x"]["path"] == "urn:test:urgency"
        assert result["axes"]["y"]["path"] == "urn:test:importance"

        # Check each quadrant
        q_map = {(q["x_value"], q["y_value"]): q for q in result["quadrants"]}

        do_first = q_map[("high", "high")]
        assert do_first["label"] == "Do First"
        assert len(do_first["items"]) == 1
        assert do_first["items"][0]["iri"] == "urn:item:1"

        schedule = q_map[("low", "high")]
        assert schedule["label"] == "Schedule"
        assert len(schedule["items"]) == 1

        delegate = q_map[("high", "low")]
        assert delegate["label"] == "Delegate"
        assert len(delegate["items"]) == 1

        eliminate = q_map[("low", "low")]
        assert eliminate["label"] == "Eliminate"
        assert len(eliminate["items"]) == 1

    @pytest.mark.asyncio
    async def test_unclassified_bucket(self):
        """Items with axis values not matching any bucket go to Unclassified."""
        bindings = [
            {
                "s": {"value": "urn:item:1"},
                "label": {"value": "Item One"},
                "xValue": {"value": "high"},
                "yValue": {"value": "high"},
            },
            {
                "s": {"value": "urn:item:2"},
                "label": {"value": "Item Two"},
                "xValue": {"value": "medium"},
                "yValue": {"value": "high"},
            },
        ]
        svc = _build_service(query_bindings=bindings)
        x_axis = _make_property("urn:test:urgency", "Urgency", in_values=["high", "low"])
        y_axis = _make_property("urn:test:importance", "Importance", in_values=["high", "low"])

        result = await svc.execute_quadrant_query(
            "urn:test:EisenhowerItem",
            x_axis, y_axis,
            ["high", "low"], ["high", "low"],
        )

        assert result["total"] == 2
        # 4 quadrant buckets + 1 unclassified
        assert len(result["quadrants"]) == 5

        unclassified = result["quadrants"][-1]
        assert unclassified["x_value"] == "__unclassified__"
        assert unclassified["y_value"] == "__unclassified__"
        assert unclassified["label"] == "Unclassified"
        assert len(unclassified["items"]) == 1
        assert unclassified["items"][0]["iri"] == "urn:item:2"

    @pytest.mark.asyncio
    async def test_quadrant_order_follows_x_then_y(self):
        """Quadrant order follows x_values × y_values iteration order."""
        svc = _build_service(query_bindings=[])
        x_axis = _make_property("urn:test:urgency", "Urgency", in_values=["high", "low"])
        y_axis = _make_property("urn:test:importance", "Importance", in_values=["high", "low"])

        result = await svc.execute_quadrant_query(
            "urn:test:Item",
            x_axis, y_axis,
            ["high", "low"], ["high", "low"],
        )

        expected = [
            ("high", "high"),
            ("high", "low"),
            ("low", "high"),
            ("low", "low"),
        ]
        actual = [(q["x_value"], q["y_value"]) for q in result["quadrants"]]
        assert actual == expected

    @pytest.mark.asyncio
    async def test_deduplicates_subjects(self):
        """Duplicate subjects (same ?s) are counted only once."""
        bindings = [
            {
                "s": {"value": "urn:item:1"},
                "label": {"value": "Item One"},
                "xValue": {"value": "high"},
                "yValue": {"value": "high"},
            },
            {
                "s": {"value": "urn:item:1"},
                "label": {"value": "Item One Alt"},
                "xValue": {"value": "high"},
                "yValue": {"value": "high"},
            },
        ]
        svc = _build_service(query_bindings=bindings)
        x_axis = _make_property("urn:test:urgency", "Urgency", in_values=["high", "low"])
        y_axis = _make_property("urn:test:importance", "Importance", in_values=["high", "low"])

        result = await svc.execute_quadrant_query(
            "urn:test:Item",
            x_axis, y_axis,
            ["high", "low"], ["high", "low"],
        )

        assert result["total"] == 1
        do_first = result["quadrants"][0]
        assert len(do_first["items"]) == 1

    @pytest.mark.asyncio
    async def test_empty_results(self):
        """No bindings returns empty quadrant buckets."""
        svc = _build_service(query_bindings=[])
        x_axis = _make_property("urn:test:urgency", "Urgency", in_values=["high", "low"])
        y_axis = _make_property("urn:test:importance", "Importance", in_values=["high", "low"])

        result = await svc.execute_quadrant_query(
            "urn:test:Item",
            x_axis, y_axis,
            ["high", "low"], ["high", "low"],
        )

        assert result["total"] == 0
        assert len(result["quadrants"]) == 4
        assert all(len(q["items"]) == 0 for q in result["quadrants"])

    @pytest.mark.asyncio
    async def test_axes_metadata_in_result(self):
        """Result includes axes metadata (path and name)."""
        svc = _build_service(query_bindings=[])
        x_axis = _make_property("urn:test:urgency", "Urgency", in_values=["high", "low"])
        y_axis = _make_property("urn:test:importance", "Importance", in_values=["high", "low"])

        result = await svc.execute_quadrant_query(
            "urn:test:Item",
            x_axis, y_axis,
            ["high", "low"], ["high", "low"],
        )

        assert result["axes"]["x"]["path"] == "urn:test:urgency"
        assert result["axes"]["x"]["name"] == "Urgency"
        assert result["axes"]["y"]["path"] == "urn:test:importance"
        assert result["axes"]["y"]["name"] == "Importance"

    @pytest.mark.asyncio
    async def test_query_failure_returns_empty_quadrants(self):
        """When the SPARQL query fails, returns empty quadrants without crashing."""
        svc = _build_service()
        svc._client.query = AsyncMock(side_effect=RuntimeError("triplestore down"))

        x_axis = _make_property("urn:test:urgency", "Urgency", in_values=["high", "low"])
        y_axis = _make_property("urn:test:importance", "Importance", in_values=["high", "low"])

        result = await svc.execute_quadrant_query(
            "urn:test:Item",
            x_axis, y_axis,
            ["high", "low"], ["high", "low"],
        )

        assert result["total"] == 0
        assert len(result["quadrants"]) == 4
        assert result["quadrants"][0]["label"] == "Do First"

    @pytest.mark.asyncio
    async def test_label_fallback_to_local_name(self):
        """When label binding is absent, uses local name from IRI."""
        bindings = [
            {
                "s": {"value": "urn:item:my-task"},
                "xValue": {"value": "high"},
                "yValue": {"value": "high"},
            },
        ]
        svc = _build_service(query_bindings=bindings)
        x_axis = _make_property("urn:test:urgency", "Urgency", in_values=["high", "low"])
        y_axis = _make_property("urn:test:importance", "Importance", in_values=["high", "low"])

        result = await svc.execute_quadrant_query(
            "urn:test:Item",
            x_axis, y_axis,
            ["high", "low"], ["high", "low"],
        )

        do_first = result["quadrants"][0]
        assert do_first["items"][0]["label"] == "my-task"

    @pytest.mark.asyncio
    async def test_multiple_items_in_same_quadrant(self):
        """Multiple items can land in the same quadrant bucket."""
        bindings = [
            {
                "s": {"value": "urn:item:1"},
                "label": {"value": "Item One"},
                "xValue": {"value": "high"},
                "yValue": {"value": "high"},
            },
            {
                "s": {"value": "urn:item:2"},
                "label": {"value": "Item Two"},
                "xValue": {"value": "high"},
                "yValue": {"value": "high"},
            },
            {
                "s": {"value": "urn:item:3"},
                "label": {"value": "Item Three"},
                "xValue": {"value": "high"},
                "yValue": {"value": "high"},
            },
        ]
        svc = _build_service(query_bindings=bindings)
        x_axis = _make_property("urn:test:urgency", "Urgency", in_values=["high", "low"])
        y_axis = _make_property("urn:test:importance", "Importance", in_values=["high", "low"])

        result = await svc.execute_quadrant_query(
            "urn:test:Item",
            x_axis, y_axis,
            ["high", "low"], ["high", "low"],
        )

        assert result["total"] == 3
        do_first = result["quadrants"][0]
        assert len(do_first["items"]) == 3

    @pytest.mark.asyncio
    async def test_generic_labels_for_non_eisenhower_values(self):
        """Non-standard axis values get generic 'Name: val / Name: val' labels."""
        bindings = [
            {
                "s": {"value": "urn:item:1"},
                "label": {"value": "Item One"},
                "xValue": {"value": "on"},
                "yValue": {"value": "yes"},
            },
        ]
        svc = _build_service(query_bindings=bindings)
        x_axis = _make_property("urn:test:power", "Power", in_values=["on", "off"])
        y_axis = _make_property("urn:test:speed", "Speed", in_values=["yes", "no"])

        result = await svc.execute_quadrant_query(
            "urn:test:Widget",
            x_axis, y_axis,
            ["on", "off"], ["yes", "no"],
        )

        on_yes = result["quadrants"][0]
        assert on_yes["label"] == "Power: on / Speed: yes"


# ── New framework label tests ─────────────────────────────────


class TestQuadrantLabelSWOT:
    """SWOT label mapping: nature × valence → quadrant name."""

    def test_strengths(self):
        svc = _build_service()
        assert svc._quadrant_label("internal", "positive", "Nature", "Valence") == "Strengths"

    def test_weaknesses(self):
        svc = _build_service()
        assert svc._quadrant_label("internal", "negative", "Nature", "Valence") == "Weaknesses"

    def test_opportunities(self):
        svc = _build_service()
        assert svc._quadrant_label("external", "positive", "Nature", "Valence") == "Opportunities"

    def test_threats(self):
        svc = _build_service()
        assert svc._quadrant_label("external", "negative", "Nature", "Valence") == "Threats"


class TestQuadrantLabelBCG:
    """BCG label mapping: growth × share → quadrant name."""

    def test_stars(self):
        svc = _build_service()
        assert svc._quadrant_label("high", "high", "Market Growth", "Market Share") == "Stars"

    def test_question_marks(self):
        svc = _build_service()
        assert svc._quadrant_label("low", "high", "Market Growth", "Market Share") == "Question Marks"

    def test_cash_cows(self):
        svc = _build_service()
        assert svc._quadrant_label("high", "low", "Market Growth", "Market Share") == "Cash Cows"

    def test_dogs(self):
        svc = _build_service()
        assert svc._quadrant_label("low", "low", "Market Growth", "Market Share") == "Dogs"


class TestQuadrantLabelAnsoff:
    """Ansoff label mapping: market novelty × product novelty."""

    def test_market_development(self):
        svc = _build_service()
        assert svc._quadrant_label("existing", "new", "Market Novelty", "Product Novelty") == "Market Development"


class TestQuadrantLabelStakeholder:
    """Stakeholder label mapping: power × interest."""

    def test_keep_informed(self):
        svc = _build_service()
        assert svc._quadrant_label("high", "low", "Stakeholder Power", "Stakeholder Interest") == "Keep Informed"


class TestQuadrantLabelRisk:
    """Risk label mapping: likelihood × impact."""

    def test_accept(self):
        svc = _build_service()
        assert svc._quadrant_label("low", "low", "Risk Likelihood", "Risk Impact") == "Accept"

    def test_critical(self):
        svc = _build_service()
        assert svc._quadrant_label("high", "high", "Risk Likelihood", "Risk Impact") == "Critical"


# ── New framework axis detection tests ────────────────────────


class TestDetectQuadrantAxesSWOT:
    """Keyword matching for SWOT axes: nature → x, valence → y."""

    @pytest.mark.asyncio
    async def test_swot_keyword_preference(self):
        form = _make_form("urn:test:SWOTItem", [
            _make_property("urn:test:title", "Title"),
            _make_property(
                "urn:bp:swotNature", "Nature",
                in_values=["internal", "external"],
            ),
            _make_property(
                "urn:bp:swotValence", "Valence",
                in_values=["positive", "negative"],
            ),
        ])
        svc = _build_service(form_return=form)
        x_axis, y_axis, x_vals, y_vals = await svc._detect_quadrant_axes(
            "urn:test:SWOTItem",
        )
        assert x_axis is not None
        assert y_axis is not None
        assert x_axis.path == "urn:bp:swotNature"
        assert y_axis.path == "urn:bp:swotValence"
        assert x_vals == ["internal", "external"]
        assert y_vals == ["positive", "negative"]


class TestDetectQuadrantAxesBCG:
    """Keyword matching for BCG axes: growth → x, share → y."""

    @pytest.mark.asyncio
    async def test_bcg_keyword_preference(self):
        form = _make_form("urn:test:BCGItem", [
            _make_property("urn:test:title", "Title"),
            _make_property(
                "urn:bp:marketGrowth", "Market Growth",
                in_values=["high", "low"],
            ),
            _make_property(
                "urn:bp:marketShare", "Market Share",
                in_values=["high", "low"],
            ),
        ])
        svc = _build_service(form_return=form)
        x_axis, y_axis, x_vals, y_vals = await svc._detect_quadrant_axes(
            "urn:test:BCGItem",
        )
        assert x_axis is not None
        assert y_axis is not None
        assert x_axis.path == "urn:bp:marketGrowth"
        assert y_axis.path == "urn:bp:marketShare"
        assert x_vals == ["high", "low"]
        assert y_vals == ["high", "low"]
