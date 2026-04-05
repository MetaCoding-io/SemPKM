"""Tests for ViewSpecService.get_compatible_types() renderer-based type filtering."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.shapes import NodeShapeForm, PropertyShape
from app.views.service import ViewSpecService


def _make_property(path: str, datatype: str = "", in_values: list[str] | None = None) -> PropertyShape:
    """Create a minimal PropertyShape for testing."""
    return PropertyShape(
        path=path,
        name=path.rsplit("/", 1)[-1].rsplit(":", 1)[-1],
        datatype=datatype or None,
        in_values=in_values or [],
    )


def _make_form(target_class: str, properties: list[PropertyShape]) -> NodeShapeForm:
    """Create a minimal NodeShapeForm for testing."""
    return NodeShapeForm(
        shape_iri=f"urn:test:shape:{target_class.rsplit(':', 1)[-1]}",
        target_class=target_class,
        label=target_class.rsplit(":", 1)[-1],
        properties=properties,
    )


ALL_TYPES = [
    {"iri": "urn:test:Task", "label": "Task"},
    {"iri": "urn:test:Note", "label": "Note"},
    {"iri": "urn:test:Event", "label": "Event"},
    {"iri": "urn:test:Place", "label": "Place"},
]


# ── Shapes by type ──────────────────────────────────────────

SHAPES = {
    "urn:test:Task": _make_form("urn:test:Task", [
        _make_property("urn:test:taskStatus", in_values=["todo", "in-progress", "done"]),
        _make_property("http://purl.org/dc/terms/created", datatype="http://www.w3.org/2001/XMLSchema#dateTime"),
    ]),
    "urn:test:Note": _make_form("urn:test:Note", [
        _make_property("http://purl.org/dc/terms/description"),
    ]),
    "urn:test:Event": _make_form("urn:test:Event", [
        _make_property("http://schema.org/startDate", datatype="http://www.w3.org/2001/XMLSchema#dateTime"),
        _make_property("http://schema.org/endDate", datatype="http://www.w3.org/2001/XMLSchema#dateTime"),
    ]),
    "urn:test:Place": _make_form("urn:test:Place", [
        _make_property("http://www.w3.org/2003/01/geo/wgs84_pos#lat", datatype="http://www.w3.org/2001/XMLSchema#decimal"),
        _make_property("http://www.w3.org/2003/01/geo/wgs84_pos#long", datatype="http://www.w3.org/2001/XMLSchema#decimal"),
    ]),
}


@pytest.fixture
def service():
    """Create a ViewSpecService with mocked dependencies."""
    client = AsyncMock()
    label_service = MagicMock()

    shapes_service = AsyncMock()

    async def mock_get_types(exclude_iris: set[str] | None = None):
        types = list(ALL_TYPES)
        if exclude_iris:
            types = [t for t in types if t["iri"] not in exclude_iris]
        return types

    shapes_service.get_types = mock_get_types

    async def mock_get_form(type_iri: str):
        return SHAPES.get(type_iri)

    shapes_service.get_form_for_type = mock_get_form

    svc = ViewSpecService(
        client=client,
        label_service=label_service,
        shapes_service=shapes_service,
    )
    return svc


@pytest.mark.asyncio
async def test_table_returns_all_types(service):
    """Table renderer should return all types without filtering."""
    result = await service.get_compatible_types("table")
    assert len(result) == 4
    iris = {t["iri"] for t in result}
    assert iris == {"urn:test:Task", "urn:test:Note", "urn:test:Event", "urn:test:Place"}


@pytest.mark.asyncio
async def test_card_returns_all_types(service):
    """Card renderer should return all types without filtering."""
    result = await service.get_compatible_types("card")
    assert len(result) == 4


@pytest.mark.asyncio
async def test_graph_returns_all_types(service):
    """Graph renderer should return all types without filtering."""
    result = await service.get_compatible_types("graph")
    assert len(result) == 4


@pytest.mark.asyncio
async def test_kanban_filters_to_status_types(service):
    """Kanban renderer should only return types with sh:in status fields."""
    result = await service.get_compatible_types("kanban")
    assert len(result) == 1
    assert result[0]["iri"] == "urn:test:Task"


@pytest.mark.asyncio
async def test_calendar_filters_to_date_types(service):
    """Calendar renderer should return types with date/dateTime fields."""
    result = await service.get_compatible_types("calendar")
    iris = {t["iri"] for t in result}
    # Task has dcterms:created (dateTime), Event has startDate (dateTime)
    assert "urn:test:Event" in iris
    assert "urn:test:Task" in iris
    assert "urn:test:Note" not in iris


@pytest.mark.asyncio
async def test_timeline_filters_same_as_calendar(service):
    """Timeline renderer should filter identically to calendar."""
    result = await service.get_compatible_types("timeline")
    iris = {t["iri"] for t in result}
    assert "urn:test:Event" in iris
    assert "urn:test:Task" in iris


@pytest.mark.asyncio
async def test_map_filters_to_geo_types(service):
    """Map renderer should only return types with lat/lng property pairs."""
    result = await service.get_compatible_types("map")
    assert len(result) == 1
    assert result[0]["iri"] == "urn:test:Place"


@pytest.mark.asyncio
async def test_exclude_iris_respected(service):
    """exclude_iris should remove types before compatibility checks."""
    result = await service.get_compatible_types(
        "table",
        exclude_iris={"urn:test:Note", "urn:test:Place"},
    )
    iris = {t["iri"] for t in result}
    assert "urn:test:Note" not in iris
    assert "urn:test:Place" not in iris
    assert len(result) == 2


@pytest.mark.asyncio
async def test_no_shapes_service_returns_empty(service):
    """When shapes_service is None, should return empty list."""
    service._shapes_service = None
    result = await service.get_compatible_types("kanban")
    assert result == []


@pytest.mark.asyncio
async def test_unknown_renderer_returns_all(service):
    """Unknown renderer names should return all types as safe fallback."""
    result = await service.get_compatible_types("some-future-renderer")
    assert len(result) == 4
