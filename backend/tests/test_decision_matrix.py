"""Unit tests for Decision Matrix renderer backend: structure
detection, SPARQL query building, weighted scoring computation,
tie-aware ranking, and edge cases (missing scores, single
alternative, error handling).

Tests cover _detect_decision_matrix_structure(),
_build_decision_matrix_select(), and
execute_decision_matrix_query() on ViewSpecService.
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


# ── _detect_decision_matrix_structure ─────────────────────────


class TestDetectDecisionMatrixStructure:
    """Tests for _detect_decision_matrix_structure() which finds value
    decimal property and alternative/criterion ObjectProperties on a
    Score shape."""

    @pytest.mark.asyncio
    async def test_happy_path_finds_value_alt_crit(self):
        """Finds value, alternative, and criterion properties."""
        form = _make_form("urn:bp:Score", [
            _make_property(
                "urn:bp:value", "Value",
                datatype=XSD_DECIMAL,
            ),
            _make_property(
                "urn:bp:belongsToAlternative", "Alternative",
                target_class="urn:bp:Alternative",
            ),
            _make_property(
                "urn:bp:belongsToCriterion", "Criterion",
                target_class="urn:bp:Criterion",
            ),
        ])
        svc = _build_service(form_return=form)
        value, alt, crit, _ = await svc._detect_decision_matrix_structure(
            "urn:bp:Score",
        )
        assert value is not None
        assert value.path == "urn:bp:value"
        assert alt is not None
        assert alt.path == "urn:bp:belongsToAlternative"
        assert crit is not None
        assert crit.path == "urn:bp:belongsToCriterion"

    @pytest.mark.asyncio
    async def test_prefers_path_containing_value(self):
        """Prefers decimal property whose path contains 'value'."""
        form = _make_form("urn:bp:Score", [
            _make_property(
                "urn:bp:amount", "Amount",
                datatype=XSD_DECIMAL,
            ),
            _make_property(
                "urn:bp:scoreValue", "Score Value",
                datatype=XSD_DECIMAL,
            ),
            _make_property(
                "urn:bp:forAlternative", "Alternative",
                target_class="urn:bp:Alternative",
            ),
            _make_property(
                "urn:bp:forCriterion", "Criterion",
                target_class="urn:bp:Criterion",
            ),
        ])
        svc = _build_service(form_return=form)
        value, alt, crit, _ = await svc._detect_decision_matrix_structure(
            "urn:bp:Score",
        )
        assert value.path == "urn:bp:scoreValue"

    @pytest.mark.asyncio
    async def test_missing_alternative_object_property(self):
        """Returns None tuple when no alternative ObjectProperty found."""
        form = _make_form("urn:bp:Score", [
            _make_property(
                "urn:bp:value", "Value",
                datatype=XSD_DECIMAL,
            ),
            _make_property(
                "urn:bp:forCriterion", "Criterion",
                target_class="urn:bp:Criterion",
            ),
        ])
        svc = _build_service(form_return=form)
        value, alt, crit, _ = await svc._detect_decision_matrix_structure(
            "urn:bp:Score",
        )
        assert value is None
        assert alt is None
        assert crit is None

    @pytest.mark.asyncio
    async def test_missing_criterion_object_property(self):
        """Returns None tuple when no criterion ObjectProperty found."""
        form = _make_form("urn:bp:Score", [
            _make_property(
                "urn:bp:value", "Value",
                datatype=XSD_DECIMAL,
            ),
            _make_property(
                "urn:bp:forAlternative", "Alternative",
                target_class="urn:bp:Alternative",
            ),
        ])
        svc = _build_service(form_return=form)
        value, alt, crit, _ = await svc._detect_decision_matrix_structure(
            "urn:bp:Score",
        )
        assert value is None

    @pytest.mark.asyncio
    async def test_no_decimal_property(self):
        """Returns None tuple when no decimal property found."""
        form = _make_form("urn:bp:Score", [
            _make_property(
                "urn:bp:rating", "Rating",
                datatype=XSD_STRING,
            ),
            _make_property(
                "urn:bp:forAlternative", "Alternative",
                target_class="urn:bp:Alternative",
            ),
            _make_property(
                "urn:bp:forCriterion", "Criterion",
                target_class="urn:bp:Criterion",
            ),
        ])
        svc = _build_service(form_return=form)
        value, alt, crit, _ = await svc._detect_decision_matrix_structure(
            "urn:bp:Score",
        )
        assert value is None

    @pytest.mark.asyncio
    async def test_shapes_service_none(self):
        """Returns None tuple when shapes_service is None."""
        svc = _build_service(shapes_service_none=True)
        value, alt, crit, _ = await svc._detect_decision_matrix_structure(
            "urn:bp:Score",
        )
        assert value is None
        assert alt is None

    @pytest.mark.asyncio
    async def test_shapes_lookup_exception(self):
        """Returns None tuple when shapes lookup raises."""
        svc = _build_service(form_side_effect=RuntimeError("broken"))
        value, alt, crit, _ = await svc._detect_decision_matrix_structure(
            "urn:bp:Score",
        )
        assert value is None

    @pytest.mark.asyncio
    async def test_form_returns_none(self):
        """Returns None tuple when get_form_for_type returns None."""
        svc = _build_service(form_return=None)
        value, alt, crit, _ = await svc._detect_decision_matrix_structure(
            "urn:bp:Score",
        )
        assert value is None


# ── _build_decision_matrix_select ─────────────────────────────


class TestBuildDecisionMatrixSelect:
    """Tests for _build_decision_matrix_select() static method."""

    def test_basic_query_with_3_type_join(self):
        """Produces query with score→alt, score→crit, and criterion weight."""
        query = ViewSpecService._build_decision_matrix_select(
            "urn:bp:Score",
            "urn:bp:value",
            "urn:bp:belongsToAlternative",
            "urn:bp:belongsToCriterion",
        )
        assert "SELECT ?score ?alt ?altTitle ?crit ?critTitle ?critWeight ?scoreValue" in query
        assert "rdf:type <urn:bp:Score>" in query
        assert "?score <urn:bp:value> ?scoreValue" in query
        assert "?score <urn:bp:belongsToAlternative> ?alt" in query
        assert "?score <urn:bp:belongsToCriterion> ?crit" in query
        # Weight path: urn:bp:value has no # or / before "value",
        # so rsplit("/") splits on the last / in "urn:bp:" → "urn:bp" + "/weight"
        # giving "urn:bp/weight". Check the query contains a critWeight binding.
        assert "?critWeight" in query
        # Joins are required (not OPTIONAL)
        for line in query.split("\n"):
            if "?scoreValue" in line and "?score <urn:bp:value>" in line:
                assert "OPTIONAL" not in line
            if "?alt" in line and "?score <urn:bp:belongsToAlternative>" in line:
                assert "OPTIONAL" not in line
            if "?crit" in line and "?score <urn:bp:belongsToCriterion>" in line:
                assert "OPTIONAL" not in line

    def test_weight_path_derived_from_hash_namespace(self):
        """Weight predicate derived from # namespace: ex#value → ex#weight."""
        query = ViewSpecService._build_decision_matrix_select(
            "urn:bp:Score",
            "http://example.org/schema#value",
            "http://example.org/schema#alt",
            "http://example.org/schema#crit",
        )
        assert "?crit <http://example.org/schema#weight> ?critWeight" in query

    def test_scope_filter_injection(self):
        """Scope filter injected as sub-select."""
        query = ViewSpecService._build_decision_matrix_select(
            "urn:bp:Score",
            "urn:bp:value",
            "urn:bp:alt",
            "urn:bp:crit",
            scope_filter="?score <urn:ex:tag> 'active' .",
        )
        assert "{ SELECT ?score WHERE { ?score <urn:ex:tag> 'active' . } }" in query

    def test_no_scope_filter_none(self):
        """No sub-select when scope_filter is None."""
        query = ViewSpecService._build_decision_matrix_select(
            "urn:bp:Score",
            "urn:bp:value",
            "urn:bp:alt",
            "urn:bp:crit",
            scope_filter=None,
        )
        assert "{ SELECT ?score WHERE" not in query

    def test_label_bindings_are_optional(self):
        """altTitle and critTitle are wrapped in OPTIONAL."""
        query = ViewSpecService._build_decision_matrix_select(
            "urn:bp:Score",
            "urn:bp:value",
            "urn:bp:alt",
            "urn:bp:crit",
        )
        assert "OPTIONAL { ?alt rdfs:label|dcterms:title ?altTitle }" in query
        assert "OPTIONAL { ?crit rdfs:label|dcterms:title ?critTitle }" in query


# ── execute_decision_matrix_query ─────────────────────────────


class TestExecuteDecisionMatrixQuery:
    """Tests for execute_decision_matrix_query() weighted scoring and ranking."""

    def _make_score_binding(
        self,
        score_iri: str,
        alt_iri: str,
        crit_iri: str,
        score_value: str,
        alt_title: str = "",
        crit_title: str = "",
        crit_weight: str = "1",
    ) -> dict:
        """Helper to build a SPARQL binding row for a score."""
        b: dict = {
            "score": {"value": score_iri},
            "alt": {"value": alt_iri},
            "crit": {"value": crit_iri},
            "scoreValue": {"value": score_value},
            "critWeight": {"value": crit_weight},
        }
        if alt_title:
            b["altTitle"] = {"value": alt_title}
        if crit_title:
            b["critTitle"] = {"value": crit_title}
        return b

    @pytest.mark.asyncio
    async def test_weighted_scoring_3_alternatives(self):
        """3 alternatives × 2 criteria: Σ(weight × value) computed correctly."""
        bindings = [
            # Alt A: C1(w=3)*8 + C2(w=2)*5 = 24+10 = 34
            self._make_score_binding("urn:s:1", "urn:alt:A", "urn:crit:C1", "8", "Alt A", "Cost", "3"),
            self._make_score_binding("urn:s:2", "urn:alt:A", "urn:crit:C2", "5", "Alt A", "Speed", "2"),
            # Alt B: C1(w=3)*6 + C2(w=2)*9 = 18+18 = 36
            self._make_score_binding("urn:s:3", "urn:alt:B", "urn:crit:C1", "6", "Alt B", "Cost", "3"),
            self._make_score_binding("urn:s:4", "urn:alt:B", "urn:crit:C2", "9", "Alt B", "Speed", "2"),
            # Alt C: C1(w=3)*4 + C2(w=2)*3 = 12+6 = 18
            self._make_score_binding("urn:s:5", "urn:alt:C", "urn:crit:C1", "4", "Alt C", "Cost", "3"),
            self._make_score_binding("urn:s:6", "urn:alt:C", "urn:crit:C2", "3", "Alt C", "Speed", "2"),
        ]
        svc = _build_service(query_bindings=bindings)
        value = _make_property("urn:bp:value", "Value", datatype=XSD_DECIMAL)
        alt = _make_property("urn:bp:alt", "Alt", target_class="urn:bp:Alternative")
        crit = _make_property("urn:bp:crit", "Crit", target_class="urn:bp:Criterion")

        result = await svc.execute_decision_matrix_query("urn:bp:Score", value, alt, crit)

        assert result["total_scores"] == 6
        assert len(result["alternatives"]) == 3

        # Ranked: B(36) > A(34) > C(18)
        assert result["alternatives"][0]["title"] == "Alt B"
        assert result["alternatives"][0]["weighted_score"] == 36.0
        assert result["alternatives"][0]["rank"] == 1

        assert result["alternatives"][1]["title"] == "Alt A"
        assert result["alternatives"][1]["weighted_score"] == 34.0
        assert result["alternatives"][1]["rank"] == 2

        assert result["alternatives"][2]["title"] == "Alt C"
        assert result["alternatives"][2]["weighted_score"] == 18.0
        assert result["alternatives"][2]["rank"] == 3

    @pytest.mark.asyncio
    async def test_tie_handling(self):
        """Two alternatives with same weighted score get same rank."""
        bindings = [
            # Alt A: 3*5 = 15
            self._make_score_binding("urn:s:1", "urn:alt:A", "urn:crit:C1", "5", "Alt A", "Cost", "3"),
            # Alt B: 3*5 = 15
            self._make_score_binding("urn:s:2", "urn:alt:B", "urn:crit:C1", "5", "Alt B", "Cost", "3"),
            # Alt C: 3*2 = 6
            self._make_score_binding("urn:s:3", "urn:alt:C", "urn:crit:C1", "2", "Alt C", "Cost", "3"),
        ]
        svc = _build_service(query_bindings=bindings)
        value = _make_property("urn:bp:value", "Value", datatype=XSD_DECIMAL)
        alt = _make_property("urn:bp:alt", "Alt", target_class="urn:bp:Alternative")
        crit = _make_property("urn:bp:crit", "Crit", target_class="urn:bp:Criterion")

        result = await svc.execute_decision_matrix_query("urn:bp:Score", value, alt, crit)

        # A and B tied at rank 1, C at rank 3
        assert result["alternatives"][0]["rank"] == 1
        assert result["alternatives"][1]["rank"] == 1
        assert result["alternatives"][2]["rank"] == 3

    @pytest.mark.asyncio
    async def test_single_alternative(self):
        """Single alternative gets rank 1."""
        bindings = [
            self._make_score_binding("urn:s:1", "urn:alt:A", "urn:crit:C1", "7", "Only Option", "Cost", "2"),
        ]
        svc = _build_service(query_bindings=bindings)
        value = _make_property("urn:bp:value", "Value", datatype=XSD_DECIMAL)
        alt = _make_property("urn:bp:alt", "Alt", target_class="urn:bp:Alternative")
        crit = _make_property("urn:bp:crit", "Crit", target_class="urn:bp:Criterion")

        result = await svc.execute_decision_matrix_query("urn:bp:Score", value, alt, crit)

        assert len(result["alternatives"]) == 1
        assert result["alternatives"][0]["rank"] == 1
        assert result["alternatives"][0]["weighted_score"] == 14.0

    @pytest.mark.asyncio
    async def test_empty_results(self):
        """No bindings returns empty structure."""
        svc = _build_service(query_bindings=[])
        value = _make_property("urn:bp:value", "Value", datatype=XSD_DECIMAL)
        alt = _make_property("urn:bp:alt", "Alt", target_class="urn:bp:Alternative")
        crit = _make_property("urn:bp:crit", "Crit", target_class="urn:bp:Criterion")

        result = await svc.execute_decision_matrix_query("urn:bp:Score", value, alt, crit)

        assert result["total_scores"] == 0
        assert result["alternatives"] == []
        assert result["criteria"] == []

    @pytest.mark.asyncio
    async def test_query_failure(self):
        """Query exception returns empty result without crashing."""
        svc = _build_service(query_side_effect=RuntimeError("triplestore down"))
        value = _make_property("urn:bp:value", "Value", datatype=XSD_DECIMAL)
        alt = _make_property("urn:bp:alt", "Alt", target_class="urn:bp:Alternative")
        crit = _make_property("urn:bp:crit", "Crit", target_class="urn:bp:Criterion")

        result = await svc.execute_decision_matrix_query("urn:bp:Score", value, alt, crit)

        assert result["total_scores"] == 0
        assert result["alternatives"] == []
        assert result["criteria"] == []

    @pytest.mark.asyncio
    async def test_partial_scoring_missing_criterion(self):
        """Alternative with score for only one of two criteria
        still computes partial weighted score."""
        bindings = [
            # Alt A scores on C1 and C2
            self._make_score_binding("urn:s:1", "urn:alt:A", "urn:crit:C1", "8", "Alt A", "Cost", "3"),
            self._make_score_binding("urn:s:2", "urn:alt:A", "urn:crit:C2", "6", "Alt A", "Speed", "2"),
            # Alt B scores on C1 only — no C2 score
            self._make_score_binding("urn:s:3", "urn:alt:B", "urn:crit:C1", "9", "Alt B", "Cost", "3"),
        ]
        svc = _build_service(query_bindings=bindings)
        value = _make_property("urn:bp:value", "Value", datatype=XSD_DECIMAL)
        alt = _make_property("urn:bp:alt", "Alt", target_class="urn:bp:Alternative")
        crit = _make_property("urn:bp:crit", "Crit", target_class="urn:bp:Criterion")

        result = await svc.execute_decision_matrix_query("urn:bp:Score", value, alt, crit)

        # Alt A: 3*8 + 2*6 = 36
        # Alt B: 3*9 = 27
        alt_map = {a["iri"]: a for a in result["alternatives"]}
        assert alt_map["urn:alt:A"]["weighted_score"] == 36.0
        assert alt_map["urn:alt:B"]["weighted_score"] == 27.0
        assert alt_map["urn:alt:A"]["rank"] == 1
        assert alt_map["urn:alt:B"]["rank"] == 2

    @pytest.mark.asyncio
    async def test_criteria_list_extraction(self):
        """Criteria are extracted with title and weight, sorted by weight desc."""
        bindings = [
            self._make_score_binding("urn:s:1", "urn:alt:A", "urn:crit:C1", "5", "Alt A", "Cost", "3"),
            self._make_score_binding("urn:s:2", "urn:alt:A", "urn:crit:C2", "5", "Alt A", "Speed", "1"),
            self._make_score_binding("urn:s:3", "urn:alt:A", "urn:crit:C3", "5", "Alt A", "Quality", "2"),
        ]
        svc = _build_service(query_bindings=bindings)
        value = _make_property("urn:bp:value", "Value", datatype=XSD_DECIMAL)
        alt = _make_property("urn:bp:alt", "Alt", target_class="urn:bp:Alternative")
        crit = _make_property("urn:bp:crit", "Crit", target_class="urn:bp:Criterion")

        result = await svc.execute_decision_matrix_query("urn:bp:Score", value, alt, crit)

        criteria = result["criteria"]
        assert len(criteria) == 3
        # Sorted by weight descending: Cost(3), Quality(2), Speed(1)
        assert criteria[0]["title"] == "Cost"
        assert criteria[0]["weight"] == 3.0
        assert criteria[1]["title"] == "Quality"
        assert criteria[1]["weight"] == 2.0
        assert criteria[2]["title"] == "Speed"
        assert criteria[2]["weight"] == 1.0

    @pytest.mark.asyncio
    async def test_default_weight_when_missing(self):
        """Missing critWeight defaults to 1.0."""
        bindings = [
            {
                "score": {"value": "urn:s:1"},
                "alt": {"value": "urn:alt:A"},
                "crit": {"value": "urn:crit:C1"},
                "scoreValue": {"value": "7"},
                "altTitle": {"value": "Alt A"},
                "critTitle": {"value": "Cost"},
                # No critWeight binding
            },
        ]
        svc = _build_service(query_bindings=bindings)
        value = _make_property("urn:bp:value", "Value", datatype=XSD_DECIMAL)
        alt = _make_property("urn:bp:alt", "Alt", target_class="urn:bp:Alternative")
        crit = _make_property("urn:bp:crit", "Crit", target_class="urn:bp:Criterion")

        result = await svc.execute_decision_matrix_query("urn:bp:Score", value, alt, crit)

        # 1.0 * 7 = 7.0
        assert result["alternatives"][0]["weighted_score"] == 7.0
        assert result["criteria"][0]["weight"] == 1.0

    @pytest.mark.asyncio
    async def test_score_values_in_alternative(self):
        """Each alternative's scores dict is keyed by criterion IRI."""
        bindings = [
            self._make_score_binding("urn:s:1", "urn:alt:A", "urn:crit:C1", "8", "Alt A", "Cost", "3"),
            self._make_score_binding("urn:s:2", "urn:alt:A", "urn:crit:C2", "6", "Alt A", "Speed", "2"),
        ]
        svc = _build_service(query_bindings=bindings)
        value = _make_property("urn:bp:value", "Value", datatype=XSD_DECIMAL)
        alt = _make_property("urn:bp:alt", "Alt", target_class="urn:bp:Alternative")
        crit = _make_property("urn:bp:crit", "Crit", target_class="urn:bp:Criterion")

        result = await svc.execute_decision_matrix_query("urn:bp:Score", value, alt, crit)

        scores = result["alternatives"][0]["scores"]
        assert scores["urn:crit:C1"] == 8.0
        assert scores["urn:crit:C2"] == 6.0

    @pytest.mark.asyncio
    async def test_label_fallback_to_local_name(self):
        """When title bindings are absent, uses local name from IRI."""
        bindings = [
            {
                "score": {"value": "urn:s:1"},
                "alt": {"value": "urn:alt:my-option"},
                "crit": {"value": "urn:crit:my-criterion"},
                "scoreValue": {"value": "5"},
                "critWeight": {"value": "1"},
            },
        ]
        svc = _build_service(query_bindings=bindings)
        value = _make_property("urn:bp:value", "Value", datatype=XSD_DECIMAL)
        alt = _make_property("urn:bp:alt", "Alt", target_class="urn:bp:Alternative")
        crit = _make_property("urn:bp:crit", "Crit", target_class="urn:bp:Criterion")

        result = await svc.execute_decision_matrix_query("urn:bp:Score", value, alt, crit)

        assert result["alternatives"][0]["title"] == "my-option"
        assert result["criteria"][0]["title"] == "my-criterion"

    @pytest.mark.asyncio
    async def test_skips_binding_without_alt_or_crit(self):
        """Bindings missing alt or crit IRI are skipped."""
        bindings = [
            {
                "score": {"value": "urn:s:1"},
                "alt": {"value": ""},
                "crit": {"value": "urn:crit:C1"},
                "scoreValue": {"value": "5"},
                "critWeight": {"value": "1"},
            },
            {
                "score": {"value": "urn:s:2"},
                "alt": {"value": "urn:alt:A"},
                "crit": {"value": ""},
                "scoreValue": {"value": "5"},
                "critWeight": {"value": "1"},
            },
            {
                "score": {"value": "urn:s:3"},
                "alt": {"value": "urn:alt:B"},
                "crit": {"value": "urn:crit:C1"},
                "scoreValue": {"value": "7"},
                "critWeight": {"value": "2"},
                "altTitle": {"value": "Alt B"},
                "critTitle": {"value": "Cost"},
            },
        ]
        svc = _build_service(query_bindings=bindings)
        value = _make_property("urn:bp:value", "Value", datatype=XSD_DECIMAL)
        alt = _make_property("urn:bp:alt", "Alt", target_class="urn:bp:Alternative")
        crit = _make_property("urn:bp:crit", "Crit", target_class="urn:bp:Criterion")

        result = await svc.execute_decision_matrix_query("urn:bp:Score", value, alt, crit)

        # Only the third binding is valid
        assert len(result["alternatives"]) == 1
        assert result["alternatives"][0]["title"] == "Alt B"
        assert result["alternatives"][0]["weighted_score"] == 14.0

    @pytest.mark.asyncio
    async def test_invalid_score_value_defaults_to_zero(self):
        """Non-numeric scoreValue defaults to 0.0."""
        bindings = [
            {
                "score": {"value": "urn:s:1"},
                "alt": {"value": "urn:alt:A"},
                "crit": {"value": "urn:crit:C1"},
                "scoreValue": {"value": "not-a-number"},
                "critWeight": {"value": "3"},
                "altTitle": {"value": "Alt A"},
                "critTitle": {"value": "Cost"},
            },
        ]
        svc = _build_service(query_bindings=bindings)
        value = _make_property("urn:bp:value", "Value", datatype=XSD_DECIMAL)
        alt = _make_property("urn:bp:alt", "Alt", target_class="urn:bp:Alternative")
        crit = _make_property("urn:bp:crit", "Crit", target_class="urn:bp:Criterion")

        result = await svc.execute_decision_matrix_query("urn:bp:Score", value, alt, crit)

        assert result["alternatives"][0]["weighted_score"] == 0.0

    @pytest.mark.asyncio
    async def test_invalid_weight_defaults_to_one(self):
        """Non-parseable critWeight defaults to 1.0 via ValueError."""
        bindings = [
            {
                "score": {"value": "urn:s:1"},
                "alt": {"value": "urn:alt:A"},
                "crit": {"value": "urn:crit:C1"},
                "scoreValue": {"value": "5"},
                "critWeight": {"value": "not-a-number"},
                "altTitle": {"value": "Alt A"},
                "critTitle": {"value": "Cost"},
            },
        ]
        svc = _build_service(query_bindings=bindings)
        value = _make_property("urn:bp:value", "Value", datatype=XSD_DECIMAL)
        alt = _make_property("urn:bp:alt", "Alt", target_class="urn:bp:Alternative")
        crit = _make_property("urn:bp:crit", "Crit", target_class="urn:bp:Criterion")

        result = await svc.execute_decision_matrix_query("urn:bp:Score", value, alt, crit)

        # Default weight 1.0 * 5.0 = 5.0
        assert result["alternatives"][0]["weighted_score"] == 5.0
