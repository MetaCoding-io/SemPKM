"""Unit tests for BMC renderer backend: section detection,
SPARQL query building, and server-side grouping into 9 section buckets.

Tests cover _detect_bmc_sections(), _build_bmc_select(),
and execute_bmc_query() on ViewSpecService.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.services.shapes import NodeShapeForm, PropertyShape, ShapesService
from app.views.service import ViewSpecService


# ── Constants ──────────────────────────────────────────────────

BMC_SECTION_VALUES = [
    "key-partners",
    "key-activities",
    "key-resources",
    "value-propositions",
    "customer-relationships",
    "channels",
    "customer-segments",
    "cost-structure",
    "revenue-streams",
]


# ── Helpers ────────────────────────────────────────────────────


def _make_property(
    path: str,
    name: str,
    order: float = 0.0,
    in_values: list[str] | None = None,
    target_class: str | None = None,
) -> PropertyShape:
    return PropertyShape(
        path=path,
        name=name,
        order=order,
        in_values=in_values or [],
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


# ── _detect_bmc_sections ──────────────────────────────────────


class TestDetectBmcSections:
    """Tests for _detect_bmc_sections() which finds a SHACL property
    with exactly 9 sh:in values for BMC section type."""

    @pytest.mark.asyncio
    async def test_happy_path_9_values(self):
        """Finds section property with 9 sh:in values on sectionType path."""
        form = _make_form("urn:test:BMCSection", [
            _make_property("urn:test:title", "Title"),
            _make_property(
                "urn:bp:sectionType", "Section Type",
                in_values=BMC_SECTION_VALUES,
            ),
            _make_property("urn:test:content", "Content"),
        ])
        svc = _build_service(form_return=form)
        section_prop, canvas_prop = await svc._detect_bmc_sections(
            "urn:test:BMCSection",
        )
        assert section_prop is not None
        assert section_prop.path == "urn:bp:sectionType"
        assert canvas_prop is None

    @pytest.mark.asyncio
    async def test_keyword_preference_case_insensitive(self):
        """Path matching for 'sectiontype' is case-insensitive — prefers it
        over another 9-value property."""
        form = _make_form("urn:test:BMCSection", [
            _make_property(
                "urn:test:otherEnum", "Other Enum",
                in_values=["a", "b", "c", "d", "e", "f", "g", "h", "i"],
            ),
            _make_property(
                "http://example.org/SectionType", "Section Type",
                in_values=BMC_SECTION_VALUES,
            ),
        ])
        svc = _build_service(form_return=form)
        section_prop, _ = await svc._detect_bmc_sections(
            "urn:test:BMCSection",
        )
        assert section_prop is not None
        assert section_prop.path == "http://example.org/SectionType"

    @pytest.mark.asyncio
    async def test_rejects_property_with_not_9_values(self):
        """Properties with != 9 sh:in values are not BMC candidates."""
        form = _make_form("urn:test:Item", [
            _make_property(
                "urn:test:status", "Status",
                in_values=["todo", "in-progress", "done"],
            ),
            _make_property(
                "urn:test:priority", "Priority",
                in_values=["low", "high"],
            ),
        ])
        svc = _build_service(form_return=form)
        section_prop, canvas_prop = await svc._detect_bmc_sections(
            "urn:test:Item",
        )
        assert section_prop is None
        assert canvas_prop is None

    @pytest.mark.asyncio
    async def test_fallback_no_keyword_match(self):
        """When no property path contains 'sectiontype', uses the first
        property with exactly 9 sh:in values."""
        form = _make_form("urn:test:Item", [
            _make_property(
                "urn:test:category", "Category",
                in_values=["a", "b", "c", "d", "e", "f", "g", "h", "i"],
            ),
        ])
        svc = _build_service(form_return=form)
        section_prop, _ = await svc._detect_bmc_sections(
            "urn:test:Item",
        )
        assert section_prop is not None
        assert section_prop.path == "urn:test:category"

    @pytest.mark.asyncio
    async def test_no_shapes_service(self):
        """Returns (None, None) when shapes_service is None."""
        svc = _build_service(shapes_service_none=True)
        section_prop, canvas_prop = await svc._detect_bmc_sections(
            "urn:test:Item",
        )
        assert section_prop is None
        assert canvas_prop is None

    @pytest.mark.asyncio
    async def test_no_form_for_type(self):
        """Returns (None, None) when get_form_for_type returns None."""
        svc = _build_service(form_return=None)
        section_prop, canvas_prop = await svc._detect_bmc_sections(
            "urn:test:Unknown",
        )
        assert section_prop is None
        assert canvas_prop is None

    @pytest.mark.asyncio
    async def test_shapes_lookup_exception(self):
        """Returns (None, None) when shapes lookup raises an exception."""
        svc = _build_service(form_side_effect=RuntimeError("shapes broken"))
        section_prop, canvas_prop = await svc._detect_bmc_sections(
            "urn:test:Item",
        )
        assert section_prop is None
        assert canvas_prop is None

    @pytest.mark.asyncio
    async def test_canvas_property_detection(self):
        """Finds an ObjectProperty targeting BusinessModelCanvas as canvas prop."""
        form = _make_form("urn:test:BMCSection", [
            _make_property(
                "urn:bp:sectionType", "Section Type",
                in_values=BMC_SECTION_VALUES,
            ),
            _make_property(
                "urn:bp:belongsToCanvas", "Belongs To Canvas",
                target_class="urn:bp:BusinessModelCanvas",
            ),
        ])
        svc = _build_service(form_return=form)
        section_prop, canvas_prop = await svc._detect_bmc_sections(
            "urn:test:BMCSection",
        )
        assert section_prop is not None
        assert canvas_prop is not None
        assert canvas_prop.path == "urn:bp:belongsToCanvas"

    @pytest.mark.asyncio
    async def test_canvas_detection_with_generic_canvas_name(self):
        """Canvas detection matches 'canvas' substring in target_class."""
        form = _make_form("urn:test:BMCSection", [
            _make_property(
                "urn:bp:sectionType", "Section Type",
                in_values=BMC_SECTION_VALUES,
            ),
            _make_property(
                "urn:bp:parentCanvas", "Parent Canvas",
                target_class="urn:example:MyCanvas",
            ),
        ])
        svc = _build_service(form_return=form)
        _, canvas_prop = await svc._detect_bmc_sections(
            "urn:test:BMCSection",
        )
        assert canvas_prop is not None
        assert canvas_prop.path == "urn:bp:parentCanvas"

    @pytest.mark.asyncio
    async def test_no_canvas_when_target_class_unrelated(self):
        """Canvas prop is None when no property targets a canvas-like class."""
        form = _make_form("urn:test:BMCSection", [
            _make_property(
                "urn:bp:sectionType", "Section Type",
                in_values=BMC_SECTION_VALUES,
            ),
            _make_property(
                "urn:bp:relatedItem", "Related Item",
                target_class="urn:example:Project",
            ),
        ])
        svc = _build_service(form_return=form)
        section_prop, canvas_prop = await svc._detect_bmc_sections(
            "urn:test:BMCSection",
        )
        assert section_prop is not None
        assert canvas_prop is None


# ── _build_bmc_select ─────────────────────────────────────────


class TestBuildBmcSelect:
    """Tests for _build_bmc_select() static method."""

    def test_basic_query_structure(self):
        """Produces correct SPARQL with type, sectionType, and OPTIONAL sectionContent."""
        query = ViewSpecService._build_bmc_select(
            "urn:test:BMCSection",
            "urn:bp:sectionType",
        )
        assert "SELECT ?s ?label ?sectionType ?sectionContent ?canvas" in query
        assert "rdf:type <urn:test:BMCSection>" in query
        assert "<urn:bp:sectionType> ?sectionType" in query
        # sectionContent is OPTIONAL
        assert "OPTIONAL" in query
        assert "sectionContent" in query
        # No scope sub-select
        assert "{ SELECT ?s WHERE" not in query

    def test_section_type_is_required(self):
        """sectionType binding is NOT wrapped in OPTIONAL."""
        query = ViewSpecService._build_bmc_select(
            "urn:test:BMCSection",
            "urn:bp:sectionType",
        )
        lines = query.split("\n")
        for line in lines:
            if "?sectionType" in line and "OPTIONAL" in line:
                # The sectionContent OPTIONAL line also mentions no sectionType
                if "sectionContent" not in line:
                    pytest.fail("sectionType binding should not be OPTIONAL")

    def test_with_scope_filter(self):
        """Scope filter injected as sub-select."""
        query = ViewSpecService._build_bmc_select(
            "urn:test:BMCSection",
            "urn:bp:sectionType",
            scope_filter="?s <urn:ex:tag> 'business' .",
        )
        assert "{ SELECT ?s WHERE { ?s <urn:ex:tag> 'business' . } }" in query
        assert "rdf:type <urn:test:BMCSection>" in query

    def test_with_canvas_path(self):
        """Canvas path adds OPTIONAL canvas binding."""
        query = ViewSpecService._build_bmc_select(
            "urn:test:BMCSection",
            "urn:bp:sectionType",
            canvas_path="urn:bp:belongsToCanvas",
        )
        assert "OPTIONAL { ?s <urn:bp:belongsToCanvas> ?canvas }" in query

    def test_without_canvas_path(self):
        """No canvas_path means no canvas OPTIONAL clause."""
        query = ViewSpecService._build_bmc_select(
            "urn:test:BMCSection",
            "urn:bp:sectionType",
        )
        assert "belongsToCanvas" not in query

    def test_label_uses_rdfs_label_or_dcterms_title(self):
        """Label binding uses rdfs:label|dcterms:title path."""
        query = ViewSpecService._build_bmc_select(
            "urn:test:BMCSection",
            "urn:bp:sectionType",
        )
        assert "rdfs:label|dcterms:title" in query


# ── execute_bmc_query ─────────────────────────────────────────


class TestExecuteBmcQuery:
    """Tests for execute_bmc_query() grouping logic."""

    @pytest.mark.asyncio
    async def test_groups_items_into_9_section_buckets(self):
        """Mock SPARQL results grouped into 9 section buckets."""
        bindings = [
            {
                "s": {"value": f"urn:item:{st}"},
                "label": {"value": f"Item {lbl}"},
                "sectionType": {"value": st},
                "sectionContent": {"value": f"Content for {lbl}"},
            }
            for st, lbl in ViewSpecService.BMC_SECTION_TYPES.items()
        ]
        svc = _build_service(query_bindings=bindings)
        section_prop = _make_property(
            "urn:bp:sectionType", "Section Type",
            in_values=BMC_SECTION_VALUES,
        )

        result = await svc.execute_bmc_query(
            "urn:test:BMCSection", section_prop, None,
        )

        assert result["total"] == 9
        assert len(result["sections"]) == 9
        for section in result["sections"]:
            assert len(section["items"]) == 1
            assert section["type"] in ViewSpecService.BMC_SECTION_TYPES

    @pytest.mark.asyncio
    async def test_missing_sections_have_empty_items(self):
        """Sections with no matching items appear with empty items list."""
        # Only provide items for 2 of 9 sections
        bindings = [
            {
                "s": {"value": "urn:item:kp"},
                "label": {"value": "Partner One"},
                "sectionType": {"value": "key-partners"},
            },
            {
                "s": {"value": "urn:item:vp"},
                "label": {"value": "Value Prop One"},
                "sectionType": {"value": "value-propositions"},
            },
        ]
        svc = _build_service(query_bindings=bindings)
        section_prop = _make_property(
            "urn:bp:sectionType", "Section Type",
            in_values=BMC_SECTION_VALUES,
        )

        result = await svc.execute_bmc_query(
            "urn:test:BMCSection", section_prop, None,
        )

        assert result["total"] == 2
        assert len(result["sections"]) == 9

        filled = [s for s in result["sections"] if len(s["items"]) > 0]
        empty = [s for s in result["sections"] if len(s["items"]) == 0]
        assert len(filled) == 2
        assert len(empty) == 7

    @pytest.mark.asyncio
    async def test_empty_results(self):
        """No bindings returns 9 sections all with empty items."""
        svc = _build_service(query_bindings=[])
        section_prop = _make_property(
            "urn:bp:sectionType", "Section Type",
            in_values=BMC_SECTION_VALUES,
        )

        result = await svc.execute_bmc_query(
            "urn:test:BMCSection", section_prop, None,
        )

        assert result["total"] == 0
        assert len(result["sections"]) == 9
        assert all(len(s["items"]) == 0 for s in result["sections"])

    @pytest.mark.asyncio
    async def test_total_count_correct(self):
        """Total count reflects unique items across all sections."""
        bindings = [
            {
                "s": {"value": f"urn:item:{i}"},
                "label": {"value": f"Item {i}"},
                "sectionType": {"value": "key-partners"},
            }
            for i in range(5)
        ]
        svc = _build_service(query_bindings=bindings)
        section_prop = _make_property(
            "urn:bp:sectionType", "Section Type",
            in_values=BMC_SECTION_VALUES,
        )

        result = await svc.execute_bmc_query(
            "urn:test:BMCSection", section_prop, None,
        )

        assert result["total"] == 5

    @pytest.mark.asyncio
    async def test_label_mapping_kebab_to_display(self):
        """Section labels map from kebab-case to display names."""
        svc = _build_service(query_bindings=[])
        section_prop = _make_property(
            "urn:bp:sectionType", "Section Type",
            in_values=BMC_SECTION_VALUES,
        )

        result = await svc.execute_bmc_query(
            "urn:test:BMCSection", section_prop, None,
        )

        label_map = {s["type"]: s["label"] for s in result["sections"]}
        assert label_map["key-partners"] == "Key Partners"
        assert label_map["value-propositions"] == "Value Propositions"
        assert label_map["customer-relationships"] == "Customer Relationships"
        assert label_map["cost-structure"] == "Cost Structure"
        assert label_map["revenue-streams"] == "Revenue Streams"

    @pytest.mark.asyncio
    async def test_deduplicates_subjects(self):
        """Duplicate subjects (same ?s) are counted only once."""
        bindings = [
            {
                "s": {"value": "urn:item:1"},
                "label": {"value": "Item One"},
                "sectionType": {"value": "key-partners"},
            },
            {
                "s": {"value": "urn:item:1"},
                "label": {"value": "Item One Alt"},
                "sectionType": {"value": "key-partners"},
            },
        ]
        svc = _build_service(query_bindings=bindings)
        section_prop = _make_property(
            "urn:bp:sectionType", "Section Type",
            in_values=BMC_SECTION_VALUES,
        )

        result = await svc.execute_bmc_query(
            "urn:test:BMCSection", section_prop, None,
        )

        assert result["total"] == 1
        kp = next(s for s in result["sections"] if s["type"] == "key-partners")
        assert len(kp["items"]) == 1

    @pytest.mark.asyncio
    async def test_query_failure_returns_empty_sections(self):
        """When the SPARQL query fails, returns 9 empty sections without crashing."""
        svc = _build_service()
        svc._client.query = AsyncMock(side_effect=RuntimeError("triplestore down"))

        section_prop = _make_property(
            "urn:bp:sectionType", "Section Type",
            in_values=BMC_SECTION_VALUES,
        )

        result = await svc.execute_bmc_query(
            "urn:test:BMCSection", section_prop, None,
        )

        assert result["total"] == 0
        assert len(result["sections"]) == 9
        assert result["sections"][0]["label"] == "Key Partners"

    @pytest.mark.asyncio
    async def test_items_have_expected_fields(self):
        """Each item in a section bucket has iri, label, content fields."""
        bindings = [
            {
                "s": {"value": "urn:item:kp1"},
                "label": {"value": "Acme Corp"},
                "sectionType": {"value": "key-partners"},
                "sectionContent": {"value": "Strategic supplier"},
            },
        ]
        svc = _build_service(query_bindings=bindings)
        section_prop = _make_property(
            "urn:bp:sectionType", "Section Type",
            in_values=BMC_SECTION_VALUES,
        )

        result = await svc.execute_bmc_query(
            "urn:test:BMCSection", section_prop, None,
        )

        kp = next(s for s in result["sections"] if s["type"] == "key-partners")
        item = kp["items"][0]
        assert item["iri"] == "urn:item:kp1"
        assert item["label"] == "Acme Corp"
        assert item["content"] == "Strategic supplier"

    @pytest.mark.asyncio
    async def test_section_ordering_follows_bmc_canonical_order(self):
        """Sections are ordered following the canonical BMC_SECTION_TYPES dict order."""
        svc = _build_service(query_bindings=[])
        section_prop = _make_property(
            "urn:bp:sectionType", "Section Type",
            in_values=BMC_SECTION_VALUES,
        )

        result = await svc.execute_bmc_query(
            "urn:test:BMCSection", section_prop, None,
        )

        actual_order = [s["type"] for s in result["sections"]]
        expected_order = list(ViewSpecService.BMC_SECTION_TYPES.keys())
        assert actual_order == expected_order

    @pytest.mark.asyncio
    async def test_multiple_items_in_same_section(self):
        """Multiple items can land in the same section bucket."""
        bindings = [
            {
                "s": {"value": f"urn:item:kp{i}"},
                "label": {"value": f"Partner {i}"},
                "sectionType": {"value": "key-partners"},
            }
            for i in range(3)
        ]
        svc = _build_service(query_bindings=bindings)
        section_prop = _make_property(
            "urn:bp:sectionType", "Section Type",
            in_values=BMC_SECTION_VALUES,
        )

        result = await svc.execute_bmc_query(
            "urn:test:BMCSection", section_prop, None,
        )

        kp = next(s for s in result["sections"] if s["type"] == "key-partners")
        assert len(kp["items"]) == 3
        assert result["total"] == 3

    @pytest.mark.asyncio
    async def test_unknown_section_type_skipped(self):
        """Items with a sectionType not in BMC_SECTION_TYPES are skipped."""
        bindings = [
            {
                "s": {"value": "urn:item:valid"},
                "label": {"value": "Valid Item"},
                "sectionType": {"value": "key-partners"},
            },
            {
                "s": {"value": "urn:item:unknown"},
                "label": {"value": "Unknown Item"},
                "sectionType": {"value": "made-up-section"},
            },
        ]
        svc = _build_service(query_bindings=bindings)
        section_prop = _make_property(
            "urn:bp:sectionType", "Section Type",
            in_values=BMC_SECTION_VALUES,
        )

        result = await svc.execute_bmc_query(
            "urn:test:BMCSection", section_prop, None,
        )

        # Both are in `seen` set but only one lands in a bucket
        assert result["total"] == 2
        kp = next(s for s in result["sections"] if s["type"] == "key-partners")
        assert len(kp["items"]) == 1
        # No section should have the unknown item
        all_items = [item for s in result["sections"] for item in s["items"]]
        assert len(all_items) == 1

    @pytest.mark.asyncio
    async def test_label_fallback_to_local_name(self):
        """When label binding is absent, uses local name from IRI."""
        bindings = [
            {
                "s": {"value": "urn:item:my-section"},
                "sectionType": {"value": "channels"},
            },
        ]
        svc = _build_service(query_bindings=bindings)
        section_prop = _make_property(
            "urn:bp:sectionType", "Section Type",
            in_values=BMC_SECTION_VALUES,
        )

        result = await svc.execute_bmc_query(
            "urn:test:BMCSection", section_prop, None,
        )

        ch = next(s for s in result["sections"] if s["type"] == "channels")
        assert ch["items"][0]["label"] == "my-section"

    @pytest.mark.asyncio
    async def test_section_types_dict_in_result(self):
        """Result includes section_types mapping dict."""
        svc = _build_service(query_bindings=[])
        section_prop = _make_property(
            "urn:bp:sectionType", "Section Type",
            in_values=BMC_SECTION_VALUES,
        )

        result = await svc.execute_bmc_query(
            "urn:test:BMCSection", section_prop, None,
        )

        assert "section_types" in result
        assert result["section_types"]["key-partners"] == "Key Partners"
        assert len(result["section_types"]) == 9

    @pytest.mark.asyncio
    async def test_content_defaults_to_empty_string(self):
        """When sectionContent binding is absent, content defaults to empty string."""
        bindings = [
            {
                "s": {"value": "urn:item:1"},
                "label": {"value": "No Content"},
                "sectionType": {"value": "key-activities"},
            },
        ]
        svc = _build_service(query_bindings=bindings)
        section_prop = _make_property(
            "urn:bp:sectionType", "Section Type",
            in_values=BMC_SECTION_VALUES,
        )

        result = await svc.execute_bmc_query(
            "urn:test:BMCSection", section_prop, None,
        )

        ka = next(s for s in result["sections"] if s["type"] == "key-activities")
        assert ka["items"][0]["content"] == ""

    @pytest.mark.asyncio
    async def test_canvas_field_captured(self):
        """Canvas binding is captured in item dict when present."""
        bindings = [
            {
                "s": {"value": "urn:item:1"},
                "label": {"value": "Section One"},
                "sectionType": {"value": "key-partners"},
                "canvas": {"value": "urn:canvas:main"},
            },
        ]
        svc = _build_service(query_bindings=bindings)
        section_prop = _make_property(
            "urn:bp:sectionType", "Section Type",
            in_values=BMC_SECTION_VALUES,
        )
        canvas_prop = _make_property(
            "urn:bp:belongsToCanvas", "Belongs To Canvas",
            target_class="urn:bp:BusinessModelCanvas",
        )

        result = await svc.execute_bmc_query(
            "urn:test:BMCSection", section_prop, canvas_prop,
        )

        kp = next(s for s in result["sections"] if s["type"] == "key-partners")
        assert kp["items"][0]["canvas"] == "urn:canvas:main"
