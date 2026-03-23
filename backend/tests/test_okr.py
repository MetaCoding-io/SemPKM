"""Unit tests for OKR renderer backend: structure detection,
SPARQL query building, progress computation, objective grouping,
and edge cases (div-by-zero, clamping, deduplication).

Tests cover _detect_okr_structure(), _build_okr_select(),
and execute_okr_query() on ViewSpecService.
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
    datatype: str | None = None,
    target_class: str | None = None,
) -> PropertyShape:
    return PropertyShape(
        path=path,
        name=name,
        order=order,
        in_values=in_values or [],
        datatype=datatype,
        target_class=target_class,
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
    query_side_effect: Exception | None = None,
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
    if query_side_effect:
        client.query = AsyncMock(side_effect=query_side_effect)
    elif query_bindings is not None:
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


# ── Constants ──────────────────────────────────────────────────

XSD_DECIMAL = "http://www.w3.org/2001/XMLSchema#decimal"
XSD_STRING = "http://www.w3.org/2001/XMLSchema#string"
XSD_INTEGER = "http://www.w3.org/2001/XMLSchema#integer"


# ── _detect_okr_structure ─────────────────────────────────────


class TestDetectOkrStructure:
    """Tests for _detect_okr_structure() which finds currentValue,
    targetValue decimal properties, optional unit, and optional
    belongsToObjective ObjectProperty."""

    @pytest.mark.asyncio
    async def test_happy_path_finds_all_four(self):
        """Finds currentValue, targetValue, unit, and belongsToObjective."""
        form = _make_form("urn:test:KeyResult", [
            _make_property("urn:test:title", "Title"),
            _make_property(
                "urn:bp:currentValue", "Current Value",
                datatype=XSD_DECIMAL,
            ),
            _make_property(
                "urn:bp:targetValue", "Target Value",
                datatype=XSD_DECIMAL,
            ),
            _make_property(
                "urn:bp:unit", "Unit",
                datatype=XSD_STRING,
            ),
            _make_property(
                "urn:bp:belongsToObjective", "Objective",
                target_class="urn:bp:Objective",
            ),
        ])
        svc = _build_service(form_return=form)
        current, target, unit, objective = await svc._detect_okr_structure(
            "urn:test:KeyResult",
        )
        assert current is not None
        assert current.path == "urn:bp:currentValue"
        assert target is not None
        assert target.path == "urn:bp:targetValue"
        assert unit is not None
        assert unit.path == "urn:bp:unit"
        assert objective is not None
        assert objective.path == "urn:bp:belongsToObjective"

    @pytest.mark.asyncio
    async def test_prefers_paths_containing_currentvalue_targetvalue(self):
        """Prefers paths containing 'currentvalue' / 'targetvalue' over
        other decimal properties."""
        form = _make_form("urn:test:KR", [
            _make_property(
                "urn:bp:amount", "Amount",
                datatype=XSD_DECIMAL,
            ),
            _make_property(
                "urn:bp:currentValue", "Current Value",
                datatype=XSD_DECIMAL,
            ),
            _make_property(
                "urn:bp:targetValue", "Target Value",
                datatype=XSD_DECIMAL,
            ),
        ])
        svc = _build_service(form_return=form)
        current, target, unit, objective = await svc._detect_okr_structure(
            "urn:test:KR",
        )
        assert current.path == "urn:bp:currentValue"
        assert target.path == "urn:bp:targetValue"

    @pytest.mark.asyncio
    async def test_rejects_non_decimal_datatypes(self):
        """Properties with non-decimal datatypes are ignored for
        currentValue / targetValue detection."""
        form = _make_form("urn:test:KR", [
            _make_property(
                "urn:bp:currentValue", "Current Value",
                datatype=XSD_STRING,
            ),
            _make_property(
                "urn:bp:targetValue", "Target Value",
                datatype=XSD_INTEGER,
            ),
        ])
        svc = _build_service(form_return=form)
        current, target, unit, objective = await svc._detect_okr_structure(
            "urn:test:KR",
        )
        assert current is None
        assert target is None

    @pytest.mark.asyncio
    async def test_returns_none_when_only_one_decimal(self):
        """Only one matching decimal property is not enough."""
        form = _make_form("urn:test:KR", [
            _make_property(
                "urn:bp:currentValue", "Current Value",
                datatype=XSD_DECIMAL,
            ),
            _make_property("urn:bp:title", "Title"),
        ])
        svc = _build_service(form_return=form)
        current, target, unit, objective = await svc._detect_okr_structure(
            "urn:test:KR",
        )
        assert current is None
        assert target is None

    @pytest.mark.asyncio
    async def test_shapes_service_none(self):
        """Returns None tuple when shapes_service is None."""
        svc = _build_service(shapes_service_none=True)
        current, target, unit, objective = await svc._detect_okr_structure(
            "urn:test:KR",
        )
        assert current is None
        assert target is None
        assert unit is None
        assert objective is None

    @pytest.mark.asyncio
    async def test_shapes_lookup_exception(self):
        """Returns None tuple when shapes lookup raises."""
        svc = _build_service(form_side_effect=RuntimeError("broken"))
        current, target, unit, objective = await svc._detect_okr_structure(
            "urn:test:KR",
        )
        assert current is None
        assert target is None

    @pytest.mark.asyncio
    async def test_form_returns_none(self):
        """Returns None tuple when get_form_for_type returns None."""
        svc = _build_service(form_return=None)
        current, target, unit, objective = await svc._detect_okr_structure(
            "urn:test:Unknown",
        )
        assert current is None
        assert target is None

    @pytest.mark.asyncio
    async def test_without_unit_and_objective(self):
        """currentValue and targetValue are found even without unit and objective."""
        form = _make_form("urn:test:KR", [
            _make_property(
                "urn:bp:currentValue", "Current Value",
                datatype=XSD_DECIMAL,
            ),
            _make_property(
                "urn:bp:targetValue", "Target Value",
                datatype=XSD_DECIMAL,
            ),
        ])
        svc = _build_service(form_return=form)
        current, target, unit, objective = await svc._detect_okr_structure(
            "urn:test:KR",
        )
        assert current is not None
        assert target is not None
        assert unit is None
        assert objective is None


# ── _build_okr_select ─────────────────────────────────────────


class TestBuildOkrSelect:
    """Tests for _build_okr_select() static method."""

    def test_basic_query_structure(self):
        """Produces correct SPARQL with type filter and OPTIONAL bindings."""
        query = ViewSpecService._build_okr_select(
            "urn:bp:KeyResult",
            "urn:bp:currentValue",
            "urn:bp:targetValue",
        )
        assert "SELECT ?s ?title ?currentValue ?targetValue ?unit ?objective ?objTitle" in query
        assert "rdf:type <urn:bp:KeyResult>" in query
        assert "OPTIONAL { ?s <urn:bp:currentValue> ?currentValue }" in query
        assert "OPTIONAL { ?s <urn:bp:targetValue> ?targetValue }" in query
        assert "rdfs:label|dcterms:title ?title" in query
        # No scope sub-select
        assert "{ SELECT ?s WHERE" not in query

    def test_with_unit_and_objective(self):
        """Unit and objective clauses appear when paths are provided."""
        query = ViewSpecService._build_okr_select(
            "urn:bp:KeyResult",
            "urn:bp:currentValue",
            "urn:bp:targetValue",
            unit_path="urn:bp:unit",
            objective_path="urn:bp:belongsToObjective",
        )
        assert "OPTIONAL { ?s <urn:bp:unit> ?unit }" in query
        assert "?s <urn:bp:belongsToObjective> ?objective" in query
        assert "?objective rdfs:label|dcterms:title ?objTitle" in query

    def test_scope_filter_injection(self):
        """Scope filter injected as sub-select."""
        query = ViewSpecService._build_okr_select(
            "urn:bp:KeyResult",
            "urn:bp:currentValue",
            "urn:bp:targetValue",
            scope_filter="?s <urn:ex:tag> 'active' .",
        )
        assert "{ SELECT ?s WHERE { ?s <urn:ex:tag> 'active' . } }" in query

    def test_no_objective_join_when_none(self):
        """No objective OPTIONAL block when objective_path is None."""
        query = ViewSpecService._build_okr_select(
            "urn:bp:KeyResult",
            "urn:bp:currentValue",
            "urn:bp:targetValue",
            objective_path=None,
        )
        # The SELECT line always lists ?objective ?objTitle, but the
        # WHERE body should not contain an objective join pattern.
        assert "belongsToObjective" not in query
        # No OPTIONAL block for objective join
        lines = [l.strip() for l in query.split("\n")]
        objective_lines = [l for l in lines if "?objective ." in l]
        assert len(objective_lines) == 0


# ── execute_okr_query ─────────────────────────────────────────


class TestExecuteOkrQuery:
    """Tests for execute_okr_query() progress computation and grouping."""

    @pytest.mark.asyncio
    async def test_progress_50_percent(self):
        """50/100 = 50% progress."""
        bindings = [
            {
                "s": {"value": "urn:kr:1"},
                "title": {"value": "KR One"},
                "currentValue": {"value": "50"},
                "targetValue": {"value": "100"},
            },
        ]
        svc = _build_service(query_bindings=bindings)
        current = _make_property("urn:bp:currentValue", "Current", datatype=XSD_DECIMAL)
        target = _make_property("urn:bp:targetValue", "Target", datatype=XSD_DECIMAL)

        result = await svc.execute_okr_query("urn:bp:KeyResult", current, target)

        assert result["total"] == 1
        kr = result["ungrouped"][0]
        assert kr["progress"] == 50.0
        assert kr["current_value"] == 50.0
        assert kr["target_value"] == 100.0

    @pytest.mark.asyncio
    async def test_div_by_zero(self):
        """0/0 = 0% progress (division by zero)."""
        bindings = [
            {
                "s": {"value": "urn:kr:1"},
                "title": {"value": "Zero KR"},
                "currentValue": {"value": "0"},
                "targetValue": {"value": "0"},
            },
        ]
        svc = _build_service(query_bindings=bindings)
        current = _make_property("urn:bp:currentValue", "Current", datatype=XSD_DECIMAL)
        target = _make_property("urn:bp:targetValue", "Target", datatype=XSD_DECIMAL)

        result = await svc.execute_okr_query("urn:bp:KeyResult", current, target)

        assert result["ungrouped"][0]["progress"] == 0.0

    @pytest.mark.asyncio
    async def test_over_target_clamped_to_100(self):
        """120/100 = 100% (clamped)."""
        bindings = [
            {
                "s": {"value": "urn:kr:1"},
                "title": {"value": "Overachiever"},
                "currentValue": {"value": "120"},
                "targetValue": {"value": "100"},
            },
        ]
        svc = _build_service(query_bindings=bindings)
        current = _make_property("urn:bp:currentValue", "Current", datatype=XSD_DECIMAL)
        target = _make_property("urn:bp:targetValue", "Target", datatype=XSD_DECIMAL)

        result = await svc.execute_okr_query("urn:bp:KeyResult", current, target)

        assert result["ungrouped"][0]["progress"] == 100.0

    @pytest.mark.asyncio
    async def test_negative_current_clamped_to_0(self):
        """-10/100 = 0% (clamped at lower bound)."""
        bindings = [
            {
                "s": {"value": "urn:kr:1"},
                "title": {"value": "Negative KR"},
                "currentValue": {"value": "-10"},
                "targetValue": {"value": "100"},
            },
        ]
        svc = _build_service(query_bindings=bindings)
        current = _make_property("urn:bp:currentValue", "Current", datatype=XSD_DECIMAL)
        target = _make_property("urn:bp:targetValue", "Target", datatype=XSD_DECIMAL)

        result = await svc.execute_okr_query("urn:bp:KeyResult", current, target)

        assert result["ungrouped"][0]["progress"] == 0.0

    @pytest.mark.asyncio
    async def test_negative_target_treated_as_zero(self):
        """Negative targetValue is treated as division by zero → 0%."""
        bindings = [
            {
                "s": {"value": "urn:kr:1"},
                "title": {"value": "Negative Target"},
                "currentValue": {"value": "50"},
                "targetValue": {"value": "-100"},
            },
        ]
        svc = _build_service(query_bindings=bindings)
        current = _make_property("urn:bp:currentValue", "Current", datatype=XSD_DECIMAL)
        target = _make_property("urn:bp:targetValue", "Target", datatype=XSD_DECIMAL)

        result = await svc.execute_okr_query("urn:bp:KeyResult", current, target)

        assert result["ungrouped"][0]["progress"] == 0.0

    @pytest.mark.asyncio
    async def test_grouping_by_objective(self):
        """KRs grouped under objectives with aggregate progress."""
        bindings = [
            {
                "s": {"value": "urn:kr:1"},
                "title": {"value": "KR 1"},
                "currentValue": {"value": "80"},
                "targetValue": {"value": "100"},
                "objective": {"value": "urn:obj:A"},
                "objTitle": {"value": "Objective A"},
            },
            {
                "s": {"value": "urn:kr:2"},
                "title": {"value": "KR 2"},
                "currentValue": {"value": "40"},
                "targetValue": {"value": "100"},
                "objective": {"value": "urn:obj:A"},
                "objTitle": {"value": "Objective A"},
            },
            {
                "s": {"value": "urn:kr:3"},
                "title": {"value": "KR 3"},
                "currentValue": {"value": "100"},
                "targetValue": {"value": "100"},
                "objective": {"value": "urn:obj:B"},
                "objTitle": {"value": "Objective B"},
            },
        ]
        svc = _build_service(query_bindings=bindings)
        current = _make_property("urn:bp:currentValue", "Current", datatype=XSD_DECIMAL)
        target = _make_property("urn:bp:targetValue", "Target", datatype=XSD_DECIMAL)
        objective = _make_property("urn:bp:belongsToObjective", "Objective", target_class="urn:bp:Objective")

        result = await svc.execute_okr_query(
            "urn:bp:KeyResult", current, target,
            objective_prop=objective,
        )

        assert result["total"] == 3
        assert len(result["objectives"]) == 2
        assert len(result["ungrouped"]) == 0

        # Find objectives by IRI
        obj_map = {o["iri"]: o for o in result["objectives"]}

        obj_a = obj_map["urn:obj:A"]
        assert len(obj_a["key_results"]) == 2
        # Average of 80% and 40% = 60%
        assert obj_a["progress"] == 60.0

        obj_b = obj_map["urn:obj:B"]
        assert len(obj_b["key_results"]) == 1
        assert obj_b["progress"] == 100.0

    @pytest.mark.asyncio
    async def test_ungrouped_krs(self):
        """KRs without objective link go to ungrouped."""
        bindings = [
            {
                "s": {"value": "urn:kr:1"},
                "title": {"value": "Standalone KR"},
                "currentValue": {"value": "30"},
                "targetValue": {"value": "100"},
            },
        ]
        svc = _build_service(query_bindings=bindings)
        current = _make_property("urn:bp:currentValue", "Current", datatype=XSD_DECIMAL)
        target = _make_property("urn:bp:targetValue", "Target", datatype=XSD_DECIMAL)

        result = await svc.execute_okr_query("urn:bp:KeyResult", current, target)

        assert result["total"] == 1
        assert len(result["objectives"]) == 0
        assert len(result["ungrouped"]) == 1
        assert result["ungrouped"][0]["progress"] == 30.0

    @pytest.mark.asyncio
    async def test_empty_results(self):
        """No bindings returns empty structure."""
        svc = _build_service(query_bindings=[])
        current = _make_property("urn:bp:currentValue", "Current", datatype=XSD_DECIMAL)
        target = _make_property("urn:bp:targetValue", "Target", datatype=XSD_DECIMAL)

        result = await svc.execute_okr_query("urn:bp:KeyResult", current, target)

        assert result["total"] == 0
        assert result["objectives"] == []
        assert result["ungrouped"] == []

    @pytest.mark.asyncio
    async def test_query_failure(self):
        """Query exception returns empty result without crashing."""
        svc = _build_service(query_side_effect=RuntimeError("triplestore down"))
        current = _make_property("urn:bp:currentValue", "Current", datatype=XSD_DECIMAL)
        target = _make_property("urn:bp:targetValue", "Target", datatype=XSD_DECIMAL)

        result = await svc.execute_okr_query("urn:bp:KeyResult", current, target)

        assert result["total"] == 0
        assert result["objectives"] == []
        assert result["ungrouped"] == []

    @pytest.mark.asyncio
    async def test_deduplication_by_iri(self):
        """Duplicate subjects are counted only once."""
        bindings = [
            {
                "s": {"value": "urn:kr:1"},
                "title": {"value": "KR One"},
                "currentValue": {"value": "50"},
                "targetValue": {"value": "100"},
            },
            {
                "s": {"value": "urn:kr:1"},
                "title": {"value": "KR One Dup"},
                "currentValue": {"value": "50"},
                "targetValue": {"value": "100"},
            },
        ]
        svc = _build_service(query_bindings=bindings)
        current = _make_property("urn:bp:currentValue", "Current", datatype=XSD_DECIMAL)
        target = _make_property("urn:bp:targetValue", "Target", datatype=XSD_DECIMAL)

        result = await svc.execute_okr_query("urn:bp:KeyResult", current, target)

        assert result["total"] == 1
        assert len(result["ungrouped"]) == 1

    @pytest.mark.asyncio
    async def test_missing_values_default_to_zero(self):
        """Missing currentValue/targetValue bindings default to 0."""
        bindings = [
            {
                "s": {"value": "urn:kr:1"},
                "title": {"value": "Empty KR"},
            },
        ]
        svc = _build_service(query_bindings=bindings)
        current = _make_property("urn:bp:currentValue", "Current", datatype=XSD_DECIMAL)
        target = _make_property("urn:bp:targetValue", "Target", datatype=XSD_DECIMAL)

        result = await svc.execute_okr_query("urn:bp:KeyResult", current, target)

        kr = result["ungrouped"][0]
        assert kr["current_value"] == 0.0
        assert kr["target_value"] == 0.0
        assert kr["progress"] == 0.0

    @pytest.mark.asyncio
    async def test_label_fallback_to_local_name(self):
        """When title binding is absent, uses local name from IRI."""
        bindings = [
            {
                "s": {"value": "urn:kr:my-kr-item"},
                "currentValue": {"value": "10"},
                "targetValue": {"value": "100"},
            },
        ]
        svc = _build_service(query_bindings=bindings)
        current = _make_property("urn:bp:currentValue", "Current", datatype=XSD_DECIMAL)
        target = _make_property("urn:bp:targetValue", "Target", datatype=XSD_DECIMAL)

        result = await svc.execute_okr_query("urn:bp:KeyResult", current, target)

        assert result["ungrouped"][0]["title"] == "my-kr-item"

    @pytest.mark.asyncio
    async def test_unit_field_captured(self):
        """Unit value is captured in the KR item."""
        bindings = [
            {
                "s": {"value": "urn:kr:1"},
                "title": {"value": "Sales KR"},
                "currentValue": {"value": "75"},
                "targetValue": {"value": "100"},
                "unit": {"value": "%"},
            },
        ]
        svc = _build_service(query_bindings=bindings)
        current = _make_property("urn:bp:currentValue", "Current", datatype=XSD_DECIMAL)
        target = _make_property("urn:bp:targetValue", "Target", datatype=XSD_DECIMAL)
        unit = _make_property("urn:bp:unit", "Unit", datatype=XSD_STRING)

        result = await svc.execute_okr_query(
            "urn:bp:KeyResult", current, target, unit_prop=unit,
        )

        assert result["ungrouped"][0]["unit"] == "%"
