"""Unit tests for map renderer backend: geo field detection,
SPARQL query building, and marker mapping.

Tests cover _detect_geo_fields(), _build_map_select(), and
execute_map_query() on ViewSpecService.
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
    datatype: str | None = None,
    in_values: list[str] | None = None,
) -> PropertyShape:
    return PropertyShape(
        path=path,
        name=name,
        order=order,
        datatype=datatype,
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


# ── _detect_geo_fields ────────────────────────────────────────


class TestDetectGeoFields:
    """Tests for _detect_geo_fields() which finds lat/lng property
    pairs for map rendering."""

    @pytest.mark.asyncio
    async def test_wgs84_iri_pair(self):
        """wgs84:lat / wgs84:long detected by full IRI match."""
        form = _make_form("urn:test:Place", [
            _make_property("http://purl.org/dc/terms/title", "Title"),
            _make_property("http://www.w3.org/2003/01/geo/wgs84_pos#lat", "Latitude"),
            _make_property("http://www.w3.org/2003/01/geo/wgs84_pos#long", "Longitude"),
        ])
        svc = _build_service(form_return=form)
        lat, lng = await svc._detect_geo_fields("urn:test:Place")
        assert lat is not None
        assert lat.path == "http://www.w3.org/2003/01/geo/wgs84_pos#lat"
        assert lng is not None
        assert lng.path == "http://www.w3.org/2003/01/geo/wgs84_pos#long"

    @pytest.mark.asyncio
    async def test_schema_org_iri_pair(self):
        """schema:latitude / schema:longitude detected by full IRI match."""
        form = _make_form("urn:test:Location", [
            _make_property("http://purl.org/dc/terms/title", "Title"),
            _make_property("http://schema.org/latitude", "Latitude"),
            _make_property("http://schema.org/longitude", "Longitude"),
        ])
        svc = _build_service(form_return=form)
        lat, lng = await svc._detect_geo_fields("urn:test:Location")
        assert lat is not None
        assert lat.path == "http://schema.org/latitude"
        assert lng is not None
        assert lng.path == "http://schema.org/longitude"

    @pytest.mark.asyncio
    async def test_heuristic_local_name_match(self):
        """Custom properties with lat/longitude local names detected by heuristic."""
        form = _make_form("urn:test:Site", [
            _make_property("http://purl.org/dc/terms/title", "Title"),
            _make_property("urn:custom:lat", "Lat"),
            _make_property("urn:custom:longitude", "Longitude"),
        ])
        svc = _build_service(form_return=form)
        lat, lng = await svc._detect_geo_fields("urn:test:Site")
        assert lat is not None
        assert lat.path == "urn:custom:lat"
        assert lng is not None
        assert lng.path == "urn:custom:longitude"

    @pytest.mark.asyncio
    async def test_heuristic_latitude_lng(self):
        """Properties with 'latitude' and 'lng' local names match."""
        form = _make_form("urn:test:Waypoint", [
            _make_property("urn:custom:latitude", "Latitude"),
            _make_property("urn:custom:lng", "Lng"),
        ])
        svc = _build_service(form_return=form)
        lat, lng = await svc._detect_geo_fields("urn:test:Waypoint")
        assert lat is not None
        assert lat.path == "urn:custom:latitude"
        assert lng is not None
        assert lng.path == "urn:custom:lng"

    @pytest.mark.asyncio
    async def test_no_geo_properties(self):
        """No geo properties → returns (None, None)."""
        form = _make_form("urn:test:Note", [
            _make_property("http://purl.org/dc/terms/title", "Title"),
            _make_property("urn:test:body", "Body"),
            _make_property("urn:test:tags", "Tags"),
        ])
        svc = _build_service(form_return=form)
        lat, lng = await svc._detect_geo_fields("urn:test:Note")
        assert lat is None
        assert lng is None

    @pytest.mark.asyncio
    async def test_no_shapes_service(self):
        """Returns (None, None) when shapes_service is None."""
        svc = _build_service(shapes_service_none=True)
        lat, lng = await svc._detect_geo_fields("urn:test:Place")
        assert lat is None
        assert lng is None

    @pytest.mark.asyncio
    async def test_no_form_for_type(self):
        """Returns (None, None) when get_form_for_type returns None."""
        svc = _build_service(form_return=None)
        lat, lng = await svc._detect_geo_fields("urn:test:Unknown")
        assert lat is None
        assert lng is None

    @pytest.mark.asyncio
    async def test_shapes_lookup_exception(self):
        """Returns (None, None) when shapes lookup raises."""
        svc = _build_service(form_side_effect=RuntimeError("shapes broken"))
        lat, lng = await svc._detect_geo_fields("urn:test:Place")
        assert lat is None
        assert lng is None

    @pytest.mark.asyncio
    async def test_only_lat_found_returns_none(self):
        """Only latitude property found (no longitude) → returns (None, None)."""
        form = _make_form("urn:test:Partial", [
            _make_property("http://purl.org/dc/terms/title", "Title"),
            _make_property("http://www.w3.org/2003/01/geo/wgs84_pos#lat", "Latitude"),
            _make_property("urn:test:description", "Description"),
        ])
        svc = _build_service(form_return=form)
        lat, lng = await svc._detect_geo_fields("urn:test:Partial")
        assert lat is None
        assert lng is None

    @pytest.mark.asyncio
    async def test_only_lng_found_returns_none(self):
        """Only longitude property found (no latitude) → returns (None, None)."""
        form = _make_form("urn:test:Partial", [
            _make_property("http://purl.org/dc/terms/title", "Title"),
            _make_property("urn:test:description", "Description"),
            _make_property("http://www.w3.org/2003/01/geo/wgs84_pos#long", "Longitude"),
        ])
        svc = _build_service(form_return=form)
        lat, lng = await svc._detect_geo_fields("urn:test:Partial")
        assert lat is None
        assert lng is None

    @pytest.mark.asyncio
    async def test_iri_match_takes_priority_over_heuristic(self):
        """Well-known IRI match is preferred over heuristic local-name match."""
        form = _make_form("urn:test:Mixed", [
            _make_property("urn:custom:lat", "Custom Lat"),  # heuristic match
            _make_property("urn:custom:lng", "Custom Lng"),  # heuristic match
            _make_property("http://schema.org/latitude", "Schema Latitude"),  # IRI match
            _make_property("http://schema.org/longitude", "Schema Longitude"),  # IRI match
        ])
        svc = _build_service(form_return=form)
        lat, lng = await svc._detect_geo_fields("urn:test:Mixed")
        assert lat is not None
        assert lat.path == "http://schema.org/latitude"
        assert lng is not None
        assert lng.path == "http://schema.org/longitude"


# ── _build_map_select ─────────────────────────────────────────


class TestBuildMapSelect:
    """Tests for _build_map_select() static method."""

    def test_basic_query_structure(self):
        """Produces correct SPARQL with type, lat, and lng paths."""
        query = ViewSpecService._build_map_select(
            "urn:test:Place",
            "http://www.w3.org/2003/01/geo/wgs84_pos#lat",
            "http://www.w3.org/2003/01/geo/wgs84_pos#long",
        )
        assert "SELECT ?s ?label ?lat ?lng" in query
        assert "rdf:type <urn:test:Place>" in query
        assert "<http://www.w3.org/2003/01/geo/wgs84_pos#lat> ?lat" in query
        assert "<http://www.w3.org/2003/01/geo/wgs84_pos#long> ?lng" in query
        assert "OPTIONAL { ?s rdfs:label|dcterms:title ?label }" in query

    def test_lat_lng_are_required_not_optional(self):
        """Both lat and lng are required (non-OPTIONAL) in the query."""
        query = ViewSpecService._build_map_select(
            "urn:test:Place",
            "urn:test:lat",
            "urn:test:lng",
        )
        # lat and lng lines should NOT be wrapped in OPTIONAL
        lines = query.split("\n")
        for line in lines:
            stripped = line.strip()
            if "?lat" in stripped and "SELECT" not in stripped:
                assert "OPTIONAL" not in stripped, "lat should be required, not OPTIONAL"
            if "?lng" in stripped and "SELECT" not in stripped:
                assert "OPTIONAL" not in stripped, "lng should be required, not OPTIONAL"

    def test_with_scope_filter(self):
        """Scope filter injected as sub-select."""
        query = ViewSpecService._build_map_select(
            "urn:test:Place",
            "urn:test:lat",
            "urn:test:lng",
            scope_filter="?s <urn:ex:tag> 'city' .",
        )
        assert "{ SELECT ?s WHERE { ?s <urn:ex:tag> 'city' . } }" in query

    def test_no_scope(self):
        """No scope → no sub-select."""
        query = ViewSpecService._build_map_select(
            "urn:test:Place",
            "urn:test:lat",
            "urn:test:lng",
        )
        assert "{ SELECT ?s WHERE" not in query


# ── execute_map_query ─────────────────────────────────────────


class TestExecuteMapQuery:
    """Tests for execute_map_query() marker mapping."""

    @pytest.mark.asyncio
    async def test_maps_to_marker_format(self):
        """Mock SPARQL results mapped to marker objects with float coords."""
        bindings = [
            {
                "s": {"value": "urn:place:1"},
                "label": {"value": "Paris"},
                "lat": {"value": "48.8566"},
                "lng": {"value": "2.3522"},
            },
            {
                "s": {"value": "urn:place:2"},
                "label": {"value": "London"},
                "lat": {"value": "51.5074"},
                "lng": {"value": "-0.1278"},
            },
        ]
        svc = _build_service(query_bindings=bindings)
        lat_field = _make_property("http://www.w3.org/2003/01/geo/wgs84_pos#lat", "Latitude")
        lng_field = _make_property("http://www.w3.org/2003/01/geo/wgs84_pos#long", "Longitude")

        result = await svc.execute_map_query("urn:test:Place", lat_field, lng_field)

        assert len(result["markers"]) == 2

        m1 = result["markers"][0]
        assert m1["iri"] == "urn:place:1"
        assert m1["title"] == "Paris"
        assert m1["lat"] == 48.8566
        assert m1["lng"] == 2.3522

        m2 = result["markers"][1]
        assert m2["iri"] == "urn:place:2"
        assert m2["title"] == "London"
        assert m2["lat"] == 51.5074
        assert m2["lng"] == -0.1278

    @pytest.mark.asyncio
    async def test_deduplicates_by_iri(self):
        """Duplicate subjects (same ?s) are counted only once."""
        bindings = [
            {
                "s": {"value": "urn:place:1"},
                "label": {"value": "Paris"},
                "lat": {"value": "48.8566"},
                "lng": {"value": "2.3522"},
            },
            {
                "s": {"value": "urn:place:1"},
                "label": {"value": "Paris Alt"},
                "lat": {"value": "48.8566"},
                "lng": {"value": "2.3522"},
            },
        ]
        svc = _build_service(query_bindings=bindings)
        lat_field = _make_property("urn:test:lat", "Lat")
        lng_field = _make_property("urn:test:lng", "Lng")

        result = await svc.execute_map_query("urn:test:Place", lat_field, lng_field)

        assert len(result["markers"]) == 1

    @pytest.mark.asyncio
    async def test_skips_missing_lat_lng(self):
        """Entries missing lat or lng values are skipped."""
        bindings = [
            {
                "s": {"value": "urn:place:1"},
                "label": {"value": "Valid"},
                "lat": {"value": "48.8566"},
                "lng": {"value": "2.3522"},
            },
            {
                "s": {"value": "urn:place:2"},
                "label": {"value": "No Lat"},
                "lat": {"value": ""},
                "lng": {"value": "2.3522"},
            },
            {
                "s": {"value": "urn:place:3"},
                "label": {"value": "No Lng"},
                "lat": {"value": "48.8566"},
                "lng": {"value": ""},
            },
        ]
        svc = _build_service(query_bindings=bindings)
        lat_field = _make_property("urn:test:lat", "Lat")
        lng_field = _make_property("urn:test:lng", "Lng")

        result = await svc.execute_map_query("urn:test:Place", lat_field, lng_field)

        assert len(result["markers"]) == 1
        assert result["markers"][0]["iri"] == "urn:place:1"

    @pytest.mark.asyncio
    async def test_empty_results(self):
        """No bindings returns empty markers list."""
        svc = _build_service(query_bindings=[])
        lat_field = _make_property("urn:test:lat", "Lat")
        lng_field = _make_property("urn:test:lng", "Lng")

        result = await svc.execute_map_query("urn:test:Place", lat_field, lng_field)

        assert result["markers"] == []
        assert result["geo_fields"]["lat"]["path"] == "urn:test:lat"
        assert result["geo_fields"]["lng"]["path"] == "urn:test:lng"

    @pytest.mark.asyncio
    async def test_geo_fields_metadata(self):
        """Result includes geo_fields metadata (paths and names)."""
        svc = _build_service(query_bindings=[])
        lat_field = _make_property("http://schema.org/latitude", "Latitude")
        lng_field = _make_property("http://schema.org/longitude", "Longitude")

        result = await svc.execute_map_query("urn:test:Location", lat_field, lng_field)

        assert result["geo_fields"]["lat"]["path"] == "http://schema.org/latitude"
        assert result["geo_fields"]["lat"]["name"] == "Latitude"
        assert result["geo_fields"]["lng"]["path"] == "http://schema.org/longitude"
        assert result["geo_fields"]["lng"]["name"] == "Longitude"

    @pytest.mark.asyncio
    async def test_query_failure_returns_empty(self):
        """When the SPARQL query fails, returns empty markers without crashing."""
        svc = _build_service()
        svc._client.query = AsyncMock(side_effect=RuntimeError("triplestore down"))

        lat_field = _make_property("urn:test:lat", "Lat")
        lng_field = _make_property("urn:test:lng", "Lng")

        result = await svc.execute_map_query("urn:test:Place", lat_field, lng_field)

        assert result["markers"] == []
        assert result["geo_fields"]["lat"]["path"] == "urn:test:lat"

    @pytest.mark.asyncio
    async def test_label_fallback_to_local_name(self):
        """When label binding is absent, uses local name from IRI."""
        bindings = [
            {
                "s": {"value": "urn:place:my-cafe"},
                "lat": {"value": "40.7128"},
                "lng": {"value": "-74.0060"},
            },
        ]
        svc = _build_service(query_bindings=bindings)
        lat_field = _make_property("urn:test:lat", "Lat")
        lng_field = _make_property("urn:test:lng", "Lng")

        result = await svc.execute_map_query("urn:test:Place", lat_field, lng_field)

        assert result["markers"][0]["title"] == "my-cafe"

    @pytest.mark.asyncio
    async def test_invalid_float_coords_skipped(self):
        """Entries with non-numeric lat/lng values are skipped."""
        bindings = [
            {
                "s": {"value": "urn:place:1"},
                "label": {"value": "Valid"},
                "lat": {"value": "48.8566"},
                "lng": {"value": "2.3522"},
            },
            {
                "s": {"value": "urn:place:2"},
                "label": {"value": "Bad Coords"},
                "lat": {"value": "not-a-number"},
                "lng": {"value": "also-bad"},
            },
        ]
        svc = _build_service(query_bindings=bindings)
        lat_field = _make_property("urn:test:lat", "Lat")
        lng_field = _make_property("urn:test:lng", "Lng")

        result = await svc.execute_map_query("urn:test:Place", lat_field, lng_field)

        assert len(result["markers"]) == 1
        assert result["markers"][0]["iri"] == "urn:place:1"
