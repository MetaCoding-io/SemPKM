"""Tests for user-defined class creation and deletion.

Covers:
- ShapesService FROM clause includes urn:sempkm:user-types
- OWL class triple generation (owl:Class, rdfs:label, rdfs:subClassOf)
- SHACL NodeShape triple generation (sh:targetClass, sh:property blocks)
- Round-trip: generated SHACL → rdflib → _extract_node_shape() → NodeShapeForm
- IRI minting with UUID suffix
- Input validation (empty name, invalid parent IRI)
- Icon/color triple generation
- Delete SPARQL for class + shape triples
- POST create-class endpoint validation and success
- DELETE delete-class endpoint access control and success
- IconService user-type icon lookup
"""

import json
import re
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from rdflib import Graph, URIRef, Literal, BNode
from rdflib.namespace import OWL, RDF, RDFS, SH, XSD

from app.ontology.service import (
    OntologyService,
    USER_TYPES_GRAPH,
    _build_insert_data_sparql,
)
from app.services.shapes import ShapesService, NodeShapeForm, PropertyShape

SEMPKM_NS = "urn:sempkm:"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_ontology_service() -> OntologyService:
    """Create OntologyService with a mocked triplestore client."""
    client = AsyncMock()
    return OntologyService(client)


def _make_shapes_service() -> ShapesService:
    """Create ShapesService with a mocked triplestore client."""
    client = AsyncMock()
    return ShapesService(client)


# ---------------------------------------------------------------------------
# ShapesService FROM clause
# ---------------------------------------------------------------------------

class TestShapesFromClauses:
    """Verify _fetch_shapes_graph() includes urn:sempkm:user-types."""

    @pytest.mark.asyncio
    async def test_shapes_from_clauses_include_user_types(self):
        """The CONSTRUCT query must include FROM <urn:sempkm:user-types>."""
        svc = _make_shapes_service()

        # Mock the model registry query to return one model
        svc._client.query = AsyncMock(return_value={
            "results": {
                "bindings": [
                    {"modelId": {"value": "basic-pkm"}}
                ]
            }
        })
        # Mock the CONSTRUCT to return empty turtle
        svc._client.construct = AsyncMock(return_value="")

        await svc._fetch_shapes_graph()

        # Check the CONSTRUCT call included user-types FROM clause
        construct_call = svc._client.construct.call_args
        sparql = construct_call[0][0]
        assert "FROM <urn:sempkm:user-types>" in sparql, (
            f"user-types FROM clause missing from CONSTRUCT:\n{sparql}"
        )


# ---------------------------------------------------------------------------
# OWL class triple generation
# ---------------------------------------------------------------------------

class TestGenerateOwlClassTriples:
    """Verify OWL class triples contain required predicates."""

    def test_generate_owl_class_triples(self):
        """Output must contain owl:Class type, rdfs:label, rdfs:subClassOf."""
        svc = _make_ontology_service()
        triples = svc._generate_class_triples(
            class_iri="urn:sempkm:user-types:TestTask-abcd1234",
            name="Test Task",
            parent_iri="https://w3id.org/semanticarts/ns/ontology/gist/Task",
        )

        class_uri = URIRef("urn:sempkm:user-types:TestTask-abcd1234")

        # Check owl:Class type triple
        type_triples = [(s, p, o) for s, p, o in triples if p == RDF.type and o == OWL.Class]
        assert len(type_triples) == 1, "Must have exactly one owl:Class type triple"

        # Check rdfs:label triple
        label_triples = [(s, p, o) for s, p, o in triples if p == RDFS.label]
        assert len(label_triples) == 1
        assert str(label_triples[0][2]) == "Test Task"

        # Check rdfs:subClassOf triple
        subclass_triples = [(s, p, o) for s, p, o in triples if p == RDFS.subClassOf]
        assert len(subclass_triples) == 1
        assert str(subclass_triples[0][2]) == "https://w3id.org/semanticarts/ns/ontology/gist/Task"


# ---------------------------------------------------------------------------
# SHACL NodeShape triple generation
# ---------------------------------------------------------------------------

class TestGenerateShaclShapeTriples:
    """Verify SHACL shape triples have required structure."""

    def test_generate_shacl_shape_triples(self):
        """Output must include sh:NodeShape, sh:targetClass, sh:property blocks."""
        svc = _make_ontology_service()
        properties = [
            {
                "name": "Title",
                "predicate_iri": "http://purl.org/dc/terms/title",
                "datatype_iri": str(XSD.string),
            },
            {
                "name": "Due Date",
                "predicate_iri": "http://schema.org/endDate",
                "datatype_iri": str(XSD.date),
            },
        ]

        triples = svc._generate_shape_triples(
            class_iri="urn:sempkm:user-types:TestTask-abcd1234",
            shape_iri="urn:sempkm:user-types:TestTaskShape-abcd1234",
            name="Test Task",
            properties=properties,
        )

        shape_uri = URIRef("urn:sempkm:user-types:TestTaskShape-abcd1234")
        class_uri = URIRef("urn:sempkm:user-types:TestTask-abcd1234")

        # sh:NodeShape type
        ns_triples = [(s, p, o) for s, p, o in triples if p == RDF.type and o == SH.NodeShape]
        assert len(ns_triples) == 1
        assert ns_triples[0][0] == shape_uri

        # sh:targetClass
        tc_triples = [(s, p, o) for s, p, o in triples if p == SH.targetClass]
        assert len(tc_triples) == 1
        assert tc_triples[0][2] == class_uri

        # sh:property links (should be 2 for 2 properties)
        prop_triples = [(s, p, o) for s, p, o in triples if p == SH.property]
        assert len(prop_triples) == 2

        # Each property bnode should have sh:path, sh:name, sh:datatype, sh:order
        prop_bnodes = [o for s, p, o in prop_triples]
        for bnode in prop_bnodes:
            paths = [o for s, p, o in triples if s == bnode and p == SH.path]
            names = [o for s, p, o in triples if s == bnode and p == SH.name]
            datatypes = [o for s, p, o in triples if s == bnode and p == SH.datatype]
            orders = [o for s, p, o in triples if s == bnode and p == SH.order]
            assert len(paths) == 1, f"Property bnode {bnode} missing sh:path"
            assert len(names) == 1, f"Property bnode {bnode} missing sh:name"
            assert len(datatypes) == 1, f"Property bnode {bnode} missing sh:datatype"
            assert len(orders) == 1, f"Property bnode {bnode} missing sh:order"


# ---------------------------------------------------------------------------
# Round-trip: generated SHACL → rdflib → _extract_node_shape() → NodeShapeForm
# ---------------------------------------------------------------------------

class TestShaclRoundTrip:
    """Critical test: generated shapes must be parseable by ShapesService."""

    def test_shacl_round_trip_through_shapes_service(self):
        """Generate triples → load into rdflib → _extract_node_shape() → valid form."""
        ont_svc = _make_ontology_service()
        shapes_svc = _make_shapes_service()

        class_iri = "urn:sempkm:user-types:ResearchNote-abc12345"
        shape_iri = "urn:sempkm:user-types:ResearchNoteShape-abc12345"
        properties = [
            {
                "name": "Title",
                "predicate_iri": "http://purl.org/dc/terms/title",
                "datatype_iri": str(XSD.string),
            },
            {
                "name": "Priority",
                "predicate_iri": "urn:sempkm:user-types:priority",
                "datatype_iri": str(XSD.integer),
            },
            {
                "name": "Due Date",
                "predicate_iri": "http://schema.org/endDate",
                "datatype_iri": str(XSD.date),
            },
        ]

        # Generate triples
        class_triples = ont_svc._generate_class_triples(
            class_iri=class_iri,
            name="Research Note",
            parent_iri="http://www.w3.org/2002/07/owl#Thing",
        )
        shape_triples = ont_svc._generate_shape_triples(
            class_iri=class_iri,
            shape_iri=shape_iri,
            name="Research Note",
            properties=properties,
        )

        # Load into rdflib Graph
        g = Graph()
        for s, p, o in class_triples + shape_triples:
            g.add((s, p, o))

        # Extract via ShapesService
        form = shapes_svc._extract_node_shape(g, URIRef(shape_iri))

        # Validate the resulting NodeShapeForm
        assert form is not None, "_extract_node_shape returned None"
        assert form.target_class == class_iri
        assert form.label == "Research Note Shape"
        assert form.shape_iri == shape_iri

        # Validate properties
        assert len(form.properties) == 3
        prop_names = [p.name for p in form.properties]
        assert "Title" in prop_names
        assert "Priority" in prop_names
        assert "Due Date" in prop_names

        # Validate property details
        title_prop = next(p for p in form.properties if p.name == "Title")
        assert title_prop.path == "http://purl.org/dc/terms/title"
        assert title_prop.datatype == str(XSD.string)

        priority_prop = next(p for p in form.properties if p.name == "Priority")
        assert priority_prop.datatype == str(XSD.integer)

        due_date_prop = next(p for p in form.properties if p.name == "Due Date")
        assert due_date_prop.datatype == str(XSD.date)

        # Verify ordering (sh:order should be 1, 2, 3)
        orders = [p.order for p in form.properties]
        assert orders == sorted(orders), "Properties should be sorted by sh:order"


# ---------------------------------------------------------------------------
# IRI minting
# ---------------------------------------------------------------------------

class TestIriMinting:
    """Verify IRI minting uses UUID suffix."""

    def test_iri_minting_uses_uuid(self):
        """Class IRI must contain a UUID hex segment under urn:sempkm:user-types:."""
        svc = _make_ontology_service()
        class_iri, shape_iri = svc._mint_class_iris("My Custom Task")

        # Must start with user-types namespace
        assert class_iri.startswith("urn:sempkm:user-types:")
        assert shape_iri.startswith("urn:sempkm:user-types:")

        # Must contain a UUID hex segment (8 chars)
        local_name = class_iri.split("urn:sempkm:user-types:")[1]
        # Pattern: Slug-hexchars
        assert re.match(r"^[A-Za-z0-9]+-[a-f0-9]{8}$", local_name), (
            f"Class IRI local name doesn't match expected pattern: {local_name}"
        )

        # Shape IRI should have Shape suffix
        shape_local = shape_iri.split("urn:sempkm:user-types:")[1]
        assert "Shape" in shape_local

    def test_iri_minting_unique(self):
        """Two calls with the same name produce different IRIs."""
        svc = _make_ontology_service()
        iri1, _ = svc._mint_class_iris("Test")
        iri2, _ = svc._mint_class_iris("Test")
        assert iri1 != iri2


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------

class TestInputValidation:
    """Verify input validation rejects invalid inputs."""

    def test_validate_empty_name_rejected(self):
        """Empty/whitespace name must raise ValueError."""
        svc = _make_ontology_service()
        with pytest.raises(ValueError, match="[Nn]ame"):
            svc._validate_class_input(
                name="",
                parent_iri="http://www.w3.org/2002/07/owl#Thing",
                properties=[],
            )
        with pytest.raises(ValueError, match="[Nn]ame"):
            svc._validate_class_input(
                name="   ",
                parent_iri="http://www.w3.org/2002/07/owl#Thing",
                properties=[],
            )

    def test_validate_invalid_parent_iri_rejected(self):
        """Non-IRI parent must raise ValueError."""
        svc = _make_ontology_service()
        with pytest.raises(ValueError, match="[Pp]arent"):
            svc._validate_class_input(
                name="Valid Name",
                parent_iri="not-a-valid-iri",
                properties=[],
            )

    def test_validate_valid_input_passes(self):
        """Valid input should not raise."""
        svc = _make_ontology_service()
        # Should not raise
        svc._validate_class_input(
            name="My Task",
            parent_iri="http://www.w3.org/2002/07/owl#Thing",
            properties=[
                {
                    "name": "Title",
                    "predicate_iri": "http://purl.org/dc/terms/title",
                    "datatype_iri": str(XSD.string),
                }
            ],
        )

    def test_validate_empty_property_name_rejected(self):
        """Property with empty name must raise ValueError."""
        svc = _make_ontology_service()
        with pytest.raises(ValueError, match="[Pp]roperty.*name"):
            svc._validate_class_input(
                name="Valid Name",
                parent_iri="http://www.w3.org/2002/07/owl#Thing",
                properties=[
                    {
                        "name": "",
                        "predicate_iri": "http://purl.org/dc/terms/title",
                        "datatype_iri": str(XSD.string),
                    }
                ],
            )

    def test_validate_invalid_datatype_rejected(self):
        """Datatype not in allowlist must raise ValueError."""
        svc = _make_ontology_service()
        with pytest.raises(ValueError, match="[Dd]atatype"):
            svc._validate_class_input(
                name="Valid Name",
                parent_iri="http://www.w3.org/2002/07/owl#Thing",
                properties=[
                    {
                        "name": "Field",
                        "predicate_iri": "http://example.org/field",
                        "datatype_iri": "http://example.org/not-a-real-datatype",
                    }
                ],
            )


# ---------------------------------------------------------------------------
# Icon / color triples
# ---------------------------------------------------------------------------

class TestIconTriples:
    """Verify icon and color triples are generated when provided."""

    def test_generate_icon_triples(self):
        """sempkm:typeIcon and sempkm:typeColor triples when icon provided."""
        svc = _make_ontology_service()
        triples = svc._generate_class_triples(
            class_iri="urn:sempkm:user-types:Task-abcd1234",
            name="Task",
            parent_iri="http://www.w3.org/2002/07/owl#Thing",
            icon_name="check-square",
            icon_color="#4CAF50",
        )

        class_uri = URIRef("urn:sempkm:user-types:Task-abcd1234")
        icon_pred = URIRef(f"{SEMPKM_NS}typeIcon")
        color_pred = URIRef(f"{SEMPKM_NS}typeColor")

        icon_triples = [(s, p, o) for s, p, o in triples if p == icon_pred]
        assert len(icon_triples) == 1
        assert str(icon_triples[0][2]) == "check-square"

        color_triples = [(s, p, o) for s, p, o in triples if p == color_pred]
        assert len(color_triples) == 1
        assert str(color_triples[0][2]) == "#4CAF50"

    def test_no_icon_triples_when_not_provided(self):
        """No icon/color triples when icon_name is None."""
        svc = _make_ontology_service()
        triples = svc._generate_class_triples(
            class_iri="urn:sempkm:user-types:Task-abcd1234",
            name="Task",
            parent_iri="http://www.w3.org/2002/07/owl#Thing",
        )

        icon_pred = URIRef(f"{SEMPKM_NS}typeIcon")
        color_pred = URIRef(f"{SEMPKM_NS}typeColor")

        icon_triples = [(s, p, o) for s, p, o in triples if p == icon_pred]
        color_triples = [(s, p, o) for s, p, o in triples if p == color_pred]
        assert len(icon_triples) == 0
        assert len(color_triples) == 0


# ---------------------------------------------------------------------------
# Delete SPARQL
# ---------------------------------------------------------------------------

class TestDeleteClass:
    """Verify delete generates correct SPARQL."""

    def test_delete_class_sparql(self):
        """DELETE WHERE targets correct subject in urn:sempkm:user-types."""
        svc = _make_ontology_service()
        class_iri = "urn:sempkm:user-types:Task-abcd1234"
        sparql = svc._build_delete_class_sparql(class_iri)

        assert f"<{class_iri}>" in sparql
        assert f"GRAPH <{USER_TYPES_GRAPH}>" in sparql
        assert "DELETE" in sparql

    def test_delete_class_shape_sparql(self):
        """DELETE WHERE returns two queries: blank-node cleanup + shape removal."""
        svc = _make_ontology_service()
        shape_iri = "urn:sempkm:user-types:TaskShape-abcd1234"
        bn_sparql, shape_sparql = svc._build_delete_shape_sparql(shape_iri)

        # First query: delete blank-node property triples
        assert f"<{shape_iri}>" in bn_sparql
        assert f"GRAPH <{USER_TYPES_GRAPH}>" in bn_sparql
        assert "DELETE" in bn_sparql
        assert "?bn" in bn_sparql

        # Second query: delete the shape node itself
        assert f"<{shape_iri}>" in shape_sparql
        assert "DELETE" in shape_sparql
        assert "?p" in shape_sparql


# ---------------------------------------------------------------------------
# Endpoint tests — create-class and delete-class
# ---------------------------------------------------------------------------

def _make_fake_app_state(ontology_service=None):
    """Build a mock app.state with ontology_service and user_type_icons."""
    state = SimpleNamespace()
    state.ontology_service = ontology_service or _make_ontology_service()
    state.user_type_icons = {}
    return state


class TestCreateClassEndpoint:
    """Verify POST /ontology/create-class endpoint behavior."""

    @pytest.mark.asyncio
    async def test_create_class_missing_name_returns_422(self):
        """Empty name must return 422."""
        from app.ontology.router import create_class

        mock_svc = _make_ontology_service()
        # create_class calls ontology_service.create_class which calls
        # _validate_class_input and raises ValueError on empty name
        mock_svc.create_class = AsyncMock(
            side_effect=ValueError("Class name must not be empty")
        )

        request = MagicMock()
        request.app.state = _make_fake_app_state(mock_svc)

        # Call with empty name (stripped to empty)
        user = MagicMock()
        response = await create_class(
            request=request,
            name="  ",
<<<<<<< HEAD
<<<<<<< HEAD
            description="",
            example="",
=======
>>>>>>> gsd/M003/S08
=======
            description="",
            example="",
>>>>>>> gsd/M004/S05
            icon="",
            icon_color="",
            parent_iri="http://www.w3.org/2002/07/owl#Thing",
            properties="[]",
            user=user,
        )

        assert response.status_code == 422
        assert b"name" in response.body.lower() or b"error" in response.body.lower()

    @pytest.mark.asyncio
    async def test_create_class_invalid_properties_json_returns_422(self):
        """Malformed properties JSON must return 422."""
        from app.ontology.router import create_class

        request = MagicMock()
        request.app.state = _make_fake_app_state()

        response = await create_class(
            request=request,
            name="Test Class",
<<<<<<< HEAD
<<<<<<< HEAD
            description="",
            example="",
=======
>>>>>>> gsd/M003/S08
=======
            description="",
            example="",
>>>>>>> gsd/M004/S05
            icon="",
            icon_color="",
            parent_iri="http://www.w3.org/2002/07/owl#Thing",
            properties="not valid json{{{",
            user=MagicMock(),
        )

        assert response.status_code == 422
        assert b"properties" in response.body.lower() or b"Invalid" in response.body

    @pytest.mark.asyncio
    async def test_create_class_success_returns_hx_trigger(self):
        """Successful creation must return 200 with HX-Trigger: classCreated."""
        from app.ontology.router import create_class

        mock_svc = _make_ontology_service()
        mock_svc.create_class = AsyncMock(return_value={
            "class_iri": "urn:sempkm:user-types:TestTask-abcd1234",
            "shape_iri": "urn:sempkm:user-types:TestTaskShape-abcd1234",
            "triple_count": 10,
            "property_count": 1,
        })

        request = MagicMock()
        request.app.state = _make_fake_app_state(mock_svc)

        props = json.dumps([{
            "name": "Title",
            "predicate_iri": "http://purl.org/dc/terms/title",
            "datatype_iri": str(XSD.string),
        }])

        response = await create_class(
            request=request,
            name="Test Task",
<<<<<<< HEAD
<<<<<<< HEAD
            description="",
            example="",
=======
>>>>>>> gsd/M003/S08
=======
            description="",
            example="",
>>>>>>> gsd/M004/S05
            icon="check-square",
            icon_color="#4CAF50",
            parent_iri="http://www.w3.org/2002/07/owl#Thing",
            properties=props,
            user=MagicMock(),
        )

        assert response.status_code == 200
        assert response.headers.get("HX-Trigger") == "classCreated"
        assert b"Test Task" in response.body
        assert b"urn:sempkm:user-types:TestTask-abcd1234" in response.body

        # Verify ontology_service.create_class was called with correct args
        mock_svc.create_class.assert_awaited_once_with(
            name="Test Task",
            parent_iri="http://www.w3.org/2002/07/owl#Thing",
            properties=[{
                "name": "Title",
                "predicate_iri": "http://purl.org/dc/terms/title",
                "datatype_iri": str(XSD.string),
            }],
            icon_name="check-square",
            icon_color="#4CAF50",
<<<<<<< HEAD
<<<<<<< HEAD
            description=None,
            example=None,
=======
>>>>>>> gsd/M003/S08
=======
            description=None,
            example=None,
>>>>>>> gsd/M004/S05
        )

    @pytest.mark.asyncio
    async def test_create_class_updates_icon_cache(self):
        """Successful creation with icon must populate app.state.user_type_icons."""
        from app.ontology.router import create_class

        mock_svc = _make_ontology_service()
        mock_svc.create_class = AsyncMock(return_value={
            "class_iri": "urn:sempkm:user-types:Note-abcd1234",
            "shape_iri": "urn:sempkm:user-types:NoteShape-abcd1234",
            "triple_count": 8,
            "property_count": 0,
        })

        request = MagicMock()
        request.app.state = _make_fake_app_state(mock_svc)

        response = await create_class(
            request=request,
            name="Note",
<<<<<<< HEAD
<<<<<<< HEAD
            description="",
            example="",
=======
>>>>>>> gsd/M003/S08
=======
            description="",
            example="",
>>>>>>> gsd/M004/S05
            icon="file-text",
            icon_color="#2196F3",
            parent_iri="http://www.w3.org/2002/07/owl#Thing",
            properties="[]",
            user=MagicMock(),
        )

        assert response.status_code == 200
        icon_cache = request.app.state.user_type_icons
        assert "urn:sempkm:user-types:Note-abcd1234" in icon_cache
        assert icon_cache["urn:sempkm:user-types:Note-abcd1234"]["icon"] == "file-text"
        assert icon_cache["urn:sempkm:user-types:Note-abcd1234"]["color"] == "#2196F3"


class TestDeleteClassEndpoint:
    """Verify DELETE /ontology/delete-class endpoint behavior."""

    @pytest.mark.asyncio
    async def test_delete_rejects_non_user_types_iri(self):
        """IRIs not starting with urn:sempkm:user-types: must get 403."""
        from app.ontology.router import delete_class

        request = MagicMock()
        request.app.state = _make_fake_app_state()

        response = await delete_class(
            request=request,
            class_iri="https://w3id.org/semanticarts/ns/ontology/gist/Task",
            user=MagicMock(),
        )

        assert response.status_code == 403
        assert b"user-created" in response.body.lower() or b"Only" in response.body

    @pytest.mark.asyncio
    async def test_delete_success_returns_hx_trigger(self):
        """Successful deletion must return 200 with HX-Trigger: classDeleted."""
        from app.ontology.router import delete_class

        mock_svc = _make_ontology_service()
        mock_svc.delete_class = AsyncMock(return_value={
            "class_iri": "urn:sempkm:user-types:Task-abcd1234",
            "shape_iri": "urn:sempkm:user-types:TaskShape-abcd1234",
            "status": "deleted",
        })

        request = MagicMock()
        request.app.state = _make_fake_app_state(mock_svc)
        # Pre-populate icon cache so we can verify removal
        request.app.state.user_type_icons["urn:sempkm:user-types:Task-abcd1234"] = {
            "icon": "check-square",
            "color": "#4CAF50",
        }

        response = await delete_class(
            request=request,
            class_iri="urn:sempkm:user-types:Task-abcd1234",
            user=MagicMock(),
        )

        assert response.status_code == 200
        assert response.headers.get("HX-Trigger") == "classDeleted"
        mock_svc.delete_class.assert_awaited_once_with("urn:sempkm:user-types:Task-abcd1234")

        # Verify icon cache was cleaned up
        assert "urn:sempkm:user-types:Task-abcd1234" not in request.app.state.user_type_icons


# ---------------------------------------------------------------------------
# IconService user-type icon lookup
# ---------------------------------------------------------------------------

class TestIconServiceUserTypes:
    """Verify IconService resolves user-type icons."""

    def test_get_type_icon_returns_user_type_icon(self):
        """get_type_icon must return user-type icon when set."""
        from app.services.icons import IconService

        svc = IconService()
        svc.set_user_type_icons({
            "urn:sempkm:user-types:Task-abcd1234": {
                "icon": "check-square",
                "color": "#4CAF50",
            },
        })

        result = svc.get_type_icon("urn:sempkm:user-types:Task-abcd1234")
        assert result["icon"] == "check-square"
        assert result["color"] == "#4CAF50"

    def test_get_type_icon_falls_back_for_unknown(self):
        """get_type_icon must return fallback for unknown IRIs."""
        from app.services.icons import IconService, FALLBACK_ICON, FALLBACK_COLOR

        svc = IconService()
        svc.set_user_type_icons({})

        result = svc.get_type_icon("urn:sempkm:user-types:Unknown-00000000")
        assert result["icon"] == FALLBACK_ICON
        assert result["color"] == FALLBACK_COLOR

    def test_get_icon_map_includes_user_type_icons(self):
        """get_icon_map must merge user-type icons."""
        from app.services.icons import IconService

        svc = IconService()
        svc.set_user_type_icons({
            "urn:sempkm:user-types:Note-abcd1234": {
                "icon": "file-text",
                "color": "#2196F3",
            },
        })

        icon_map = svc.get_icon_map(context="tree")
        assert "urn:sempkm:user-types:Note-abcd1234" in icon_map
        assert icon_map["urn:sempkm:user-types:Note-abcd1234"]["icon"] == "file-text"

    def test_user_type_icons_dont_override_manifest_icons(self):
        """User-type icons must not override manifest-based icons."""
        from app.services.icons import IconService, TypeIconMap, IconContextDef

        svc = IconService()
        # Simulate a manifest-based icon in the cache
        svc._cache = {
            "urn:example:ManifestClass": TypeIconMap(
                tree=IconContextDef(icon="box", color="#FF0000"),
                graph=IconContextDef(icon="box", color="#FF0000"),
                tab=IconContextDef(icon="box", color="#FF0000"),
            )
        }
        svc.set_user_type_icons({
            "urn:example:ManifestClass": {
                "icon": "override-icon",
                "color": "#000000",
            },
        })

        # get_icon_map should use manifest icon, not user-type override
        icon_map = svc.get_icon_map(context="tree")
        assert icon_map["urn:example:ManifestClass"]["icon"] == "box"

        # get_type_icon should also use manifest icon
        result = svc.get_type_icon("urn:example:ManifestClass")
        assert result["icon"] == "box"


# ---------------------------------------------------------------------------
# load_user_type_icons async loader
# ---------------------------------------------------------------------------

class TestLoadUserTypeIcons:
    """Verify SPARQL-based user-type icon loading."""

    @pytest.mark.asyncio
    async def test_load_user_type_icons_parses_sparql_result(self):
        """Correctly parses SPARQL SELECT results into icon dict."""
        from app.services.icons import load_user_type_icons

        mock_client = AsyncMock()
        mock_client.query = AsyncMock(return_value={
            "results": {
                "bindings": [
                    {
                        "class": {"value": "urn:sempkm:user-types:Task-aaaa1111"},
                        "icon": {"value": "check-square"},
                        "color": {"value": "#4CAF50"},
                    },
                    {
                        "class": {"value": "urn:sempkm:user-types:Note-bbbb2222"},
                        "icon": {"value": "file-text"},
                        # No color — should use fallback
                    },
                ]
            }
        })

        result = await load_user_type_icons(mock_client)

        assert len(result) == 2
        assert result["urn:sempkm:user-types:Task-aaaa1111"]["icon"] == "check-square"
        assert result["urn:sempkm:user-types:Task-aaaa1111"]["color"] == "#4CAF50"
        assert result["urn:sempkm:user-types:Note-bbbb2222"]["icon"] == "file-text"

    @pytest.mark.asyncio
    async def test_load_user_type_icons_handles_empty_result(self):
        """Empty triplestore returns empty dict."""
        from app.services.icons import load_user_type_icons

        mock_client = AsyncMock()
        mock_client.query = AsyncMock(return_value={
            "results": {"bindings": []}
        })

        result = await load_user_type_icons(mock_client)
        assert result == {}

    @pytest.mark.asyncio
    async def test_load_user_type_icons_handles_error(self):
        """Triplestore errors return empty dict, don't raise."""
        from app.services.icons import load_user_type_icons

        mock_client = AsyncMock()
        mock_client.query = AsyncMock(side_effect=Exception("connection refused"))

        result = await load_user_type_icons(mock_client)
        assert result == {}


# ------------------------------------------------------------------
# TBox class search
# ------------------------------------------------------------------


class TestSearchClasses:
    """Tests for OntologyService.search_classes()."""

    @pytest.mark.asyncio
    async def test_search_classes_returns_matching(self):
        """search_classes returns classes whose label matches the query."""
        mock_client = AsyncMock()
        # First query: get_ontology_graph_iris
        mock_client.query = AsyncMock(side_effect=[
            {"results": {"bindings": []}},  # get_ontology_graph_iris
            {"results": {"bindings": [
                {"class": {"value": "http://example.org/Book"}, "label": {"value": "Book"}},
                {"class": {"value": "http://example.org/Notebook"}, "label": {"value": "Notebook"}},
            ]}},
        ])

        svc = OntologyService(mock_client)
        results = await svc.search_classes("book")

        assert len(results) == 2
        assert results[0]["iri"] == "http://example.org/Book"
        assert results[0]["label"] == "Book"
        # Verify the SPARQL contains CONTAINS filter
        search_call = mock_client.query.call_args_list[1]
        sparql = search_call[0][0]
        assert "CONTAINS" in sparql
        assert "book" in sparql.lower()

    @pytest.mark.asyncio
    async def test_search_classes_empty_query_returns_empty(self):
        """Empty search query returns empty list without hitting triplestore."""
        mock_client = AsyncMock()
        svc = OntologyService(mock_client)

        results = await svc.search_classes("")
        assert results == []
        mock_client.query.assert_not_called()

    @pytest.mark.asyncio
    async def test_search_classes_escapes_quotes(self):
        """Single quotes in query are escaped to prevent SPARQL injection."""
        mock_client = AsyncMock()
        mock_client.query = AsyncMock(side_effect=[
            {"results": {"bindings": []}},  # get_ontology_graph_iris
            {"results": {"bindings": []}},
        ])

        svc = OntologyService(mock_client)
        results = await svc.search_classes("test's query")

        assert results == []
        search_call = mock_client.query.call_args_list[1]
        sparql = search_call[0][0]
        assert "test\\'s query" in sparql


class TestTboxSearchEndpoint:
    """Tests for GET /browser/ontology/tbox/search endpoint."""

    @pytest.mark.asyncio
    async def test_search_endpoint_returns_html_results(self):
        """Search endpoint returns HTML with matching class options."""
        from app.ontology.router import tbox_search

        mock_svc = _make_ontology_service()
        mock_svc.search_classes = AsyncMock(return_value=[
            {"iri": "http://example.org/Book", "label": "Book"},
        ])

        request = MagicMock()
        request.app.state = _make_fake_app_state(mock_svc)

        response = await tbox_search(
            request=request,
            q="book",
            user=MagicMock(),
        )

        assert response.status_code == 200
        body = response.body.decode()
        assert "Book" in body
        assert "parent-class-option" in body
        mock_svc.search_classes.assert_awaited_once_with("book")

    @pytest.mark.asyncio
    async def test_search_endpoint_empty_query_returns_empty(self):
        """Empty query returns empty response without touching service."""
        from app.ontology.router import tbox_search

        mock_svc = _make_ontology_service()
        mock_svc.search_classes = AsyncMock()

        request = MagicMock()
        request.app.state = _make_fake_app_state(mock_svc)

        response = await tbox_search(
            request=request,
            q="",
            user=MagicMock(),
        )

        assert response.status_code == 200
        assert response.body == b""
        mock_svc.search_classes.assert_not_called()

    @pytest.mark.asyncio
    async def test_search_endpoint_no_results(self):
        """No results returns 'No classes found' message."""
        from app.ontology.router import tbox_search

        mock_svc = _make_ontology_service()
        mock_svc.search_classes = AsyncMock(return_value=[])

        request = MagicMock()
        request.app.state = _make_fake_app_state(mock_svc)

        response = await tbox_search(
            request=request,
            q="nonexistent",
            user=MagicMock(),
        )

        assert response.status_code == 200
        body = response.body.decode()
        assert "No classes found" in body
<<<<<<< HEAD


# ---------------------------------------------------------------------------
# _property_source for user-types IRIs
# ---------------------------------------------------------------------------

class TestPropertySource:
    """Verify _property_source returns correct source labels."""

    def test_user_types_iri_returns_user(self):
        """user-types IRI must return 'user'."""
        from app.ontology.service import _property_source

        result = _property_source("urn:sempkm:user-types:MyProp-abc123")
        assert result == "user"

    def test_user_types_class_iri_returns_user(self):
        """user-types class IRI must also return 'user'."""
        from app.ontology.service import _property_source

        result = _property_source("urn:sempkm:user-types:MyClass-def456")
        assert result == "user"

    def test_sempkm_ns_returns_sempkm(self):
        """Other sempkm namespace IRIs still return 'sempkm'."""
        from app.ontology.service import _property_source

        result = _property_source("urn:sempkm:someProp")
        assert result == "sempkm"

    def test_gist_iri_returns_gist(self):
        """Gist IRIs return 'gist'."""
        from app.ontology.service import _property_source

        result = _property_source(
            "https://w3id.org/semanticarts/ns/ontology/gist/hasMember"
        )
        assert result == "gist"

    def test_model_iri_returns_model_name(self):
        """Model IRIs return the model id segment."""
        from app.ontology.service import _property_source

        result = _property_source("urn:sempkm:model:basic-pkm:HasNote")
        assert result == "basic-pkm"

    def test_other_iri_returns_other(self):
        """Unknown IRIs return 'other'."""
        from app.ontology.service import _property_source

        result = _property_source("http://example.org/someProp")
        assert result == "other"


# ---------------------------------------------------------------------------
# delete_property() service method
# ---------------------------------------------------------------------------

class TestDeleteProperty:
    """Verify delete_property() generates correct SPARQL."""

    @pytest.mark.asyncio
    async def test_delete_property_sparql(self):
        """delete_property generates DELETE WHERE targeting user-types graph."""
        svc = _make_ontology_service()
        prop_iri = "urn:sempkm:user-types:myProp-abcd1234"

        result = await svc.delete_property(prop_iri)

        assert result == {"property_iri": prop_iri, "status": "deleted"}

        # Verify the SPARQL passed to client.update
        svc._client.update.assert_awaited_once()
        sparql = svc._client.update.call_args[0][0]
        assert f"<{prop_iri}>" in sparql
        assert f"GRAPH <{USER_TYPES_GRAPH}>" in sparql
        assert "DELETE WHERE" in sparql
        assert "?p ?o" in sparql

    @pytest.mark.asyncio
    async def test_delete_property_different_iri(self):
        """delete_property works with different property IRIs."""
        svc = _make_ontology_service()
        prop_iri = "urn:sempkm:user-types:anotherProp-99990000"

        result = await svc.delete_property(prop_iri)

        assert result["property_iri"] == prop_iri
        assert result["status"] == "deleted"

        sparql = svc._client.update.call_args[0][0]
        assert f"<{prop_iri}>" in sparql


# ---------------------------------------------------------------------------
# get_delete_class_info() service method
# ---------------------------------------------------------------------------

class TestGetDeleteClassInfo:
    """Verify get_delete_class_info() parses counts correctly."""

    @pytest.mark.asyncio
    async def test_get_delete_class_info_parses_counts(self):
        """get_delete_class_info returns correct instance/subclass counts."""
        mock_client = AsyncMock()

        # Side effects: get_ontology_graph_iris, then 3 parallel queries
        mock_client.query = AsyncMock(side_effect=[
            # get_ontology_graph_iris
            {"results": {"bindings": []}},
            # label query
            {"results": {"bindings": [
                {"label": {"value": "My Task"}}
            ]}},
            # subclass count
            {"results": {"bindings": [
                {"cnt": {"value": "3"}}
            ]}},
            # instance count
            {"results": {"bindings": [
                {"cnt": {"value": "42"}}
            ]}},
        ])

        svc = OntologyService(mock_client)
        result = await svc.get_delete_class_info(
            "urn:sempkm:user-types:Task-abcd1234"
        )

        assert result["class_iri"] == "urn:sempkm:user-types:Task-abcd1234"
        assert result["label"] == "My Task"
        assert result["instance_count"] == 42
        assert result["subclass_count"] == 3

    @pytest.mark.asyncio
    async def test_get_delete_class_info_zero_counts(self):
        """get_delete_class_info returns 0 when no instances/subclasses."""
        mock_client = AsyncMock()

        mock_client.query = AsyncMock(side_effect=[
            # get_ontology_graph_iris
            {"results": {"bindings": []}},
            # label query
            {"results": {"bindings": [
                {"label": {"value": "Empty Class"}}
            ]}},
            # subclass count — zero
            {"results": {"bindings": [
                {"cnt": {"value": "0"}}
            ]}},
            # instance count — zero
            {"results": {"bindings": [
                {"cnt": {"value": "0"}}
            ]}},
        ])

        svc = OntologyService(mock_client)
        result = await svc.get_delete_class_info(
            "urn:sempkm:user-types:EmptyClass-00001111"
        )

        assert result["instance_count"] == 0
        assert result["subclass_count"] == 0
        assert result["label"] == "Empty Class"

    @pytest.mark.asyncio
    async def test_get_delete_class_info_fallback_label(self):
        """get_delete_class_info falls back to local name when no label."""
        mock_client = AsyncMock()

        mock_client.query = AsyncMock(side_effect=[
            # get_ontology_graph_iris
            {"results": {"bindings": []}},
            # label query — empty bindings (no label found)
            {"results": {"bindings": []}},
            # subclass count
            {"results": {"bindings": [
                {"cnt": {"value": "0"}}
            ]}},
            # instance count
            {"results": {"bindings": [
                {"cnt": {"value": "0"}}
            ]}},
        ])

        svc = OntologyService(mock_client)
        result = await svc.get_delete_class_info(
            "urn:sempkm:user-types:NoLabel-ff001122"
        )

        # Should extract local name from IRI
        assert result["label"] == "NoLabel-ff001122"


# ---------------------------------------------------------------------------
# DELETE /ontology/delete-property endpoint
# ---------------------------------------------------------------------------

class TestDeletePropertyEndpoint:
    """Verify DELETE /ontology/delete-property endpoint behavior."""

    @pytest.mark.asyncio
    async def test_delete_property_rejects_non_user_types_iri(self):
        """IRIs not starting with urn:sempkm:user-types: must get 403."""
        from app.ontology.router import delete_property

        request = MagicMock()
        request.app.state = _make_fake_app_state()

        response = await delete_property(
            request=request,
            property_iri="https://w3id.org/semanticarts/ns/ontology/gist/hasMember",
            user=MagicMock(),
        )

        assert response.status_code == 403
        assert b"user-created" in response.body.lower() or b"Only" in response.body

    @pytest.mark.asyncio
    async def test_delete_property_success_returns_hx_trigger(self):
        """Successful deletion must return 200 with HX-Trigger: propertyDeleted."""
        from app.ontology.router import delete_property

        mock_svc = _make_ontology_service()
        mock_svc.delete_property = AsyncMock(return_value={
            "property_iri": "urn:sempkm:user-types:myProp-abcd1234",
            "status": "deleted",
        })

        request = MagicMock()
        request.app.state = _make_fake_app_state(mock_svc)

        response = await delete_property(
            request=request,
            property_iri="urn:sempkm:user-types:myProp-abcd1234",
            user=MagicMock(),
        )

        assert response.status_code == 200
        assert response.headers.get("HX-Trigger") == "propertyDeleted"
        mock_svc.delete_property.assert_awaited_once_with(
            "urn:sempkm:user-types:myProp-abcd1234"
        )

    @pytest.mark.asyncio
    async def test_delete_property_server_error_returns_500(self):
        """SPARQL failure must return 500."""
        from app.ontology.router import delete_property

        mock_svc = _make_ontology_service()
        mock_svc.delete_property = AsyncMock(
            side_effect=Exception("SPARQL connection refused")
        )

        request = MagicMock()
        request.app.state = _make_fake_app_state(mock_svc)

        response = await delete_property(
            request=request,
            property_iri="urn:sempkm:user-types:myProp-abcd1234",
            user=MagicMock(),
        )

        assert response.status_code == 500
        assert b"Server error" in response.body


# ---------------------------------------------------------------------------
# GET /ontology/delete-class-check endpoint
# ---------------------------------------------------------------------------

class TestDeleteClassCheckEndpoint:
    """Verify GET /ontology/delete-class-check endpoint behavior."""

    @pytest.mark.asyncio
    async def test_delete_class_check_rejects_non_user_types_iri(self):
        """IRIs not starting with urn:sempkm:user-types: must get 403."""
        from app.ontology.router import delete_class_check

        request = MagicMock()
        request.app.state = _make_fake_app_state()

        response = await delete_class_check(
            request=request,
            class_iri="https://w3id.org/semanticarts/ns/ontology/gist/Task",
            user=MagicMock(),
        )

        assert response.status_code == 403
        assert b"user-created" in response.body.lower() or b"Only" in response.body

    @pytest.mark.asyncio
    async def test_delete_class_check_success_returns_html(self):
        """Successful check returns HTML with instance/subclass counts."""
        from app.ontology.router import delete_class_check

        mock_svc = _make_ontology_service()
        mock_svc.get_delete_class_info = AsyncMock(return_value={
            "class_iri": "urn:sempkm:user-types:Task-abcd1234",
            "label": "My Task",
            "instance_count": 5,
            "subclass_count": 2,
        })

        # We need a real Jinja2Templates to render the template
        from jinja2 import Environment, FileSystemLoader
        import os

        templates_dir = os.path.join(
            os.path.dirname(__file__), "..", "app", "templates"
        )
        env = Environment(loader=FileSystemLoader(templates_dir))

        # Mock templates.TemplateResponse to render via jinja2
        def fake_template_response(req, template_name, context):
            from fastapi.responses import HTMLResponse

            tmpl = env.get_template(template_name)
            html = tmpl.render(**context)
            return HTMLResponse(content=html, status_code=200)

        state = _make_fake_app_state(mock_svc)
        state.templates = MagicMock()
        state.templates.TemplateResponse = fake_template_response

        request = MagicMock()
        request.app.state = state

        response = await delete_class_check(
            request=request,
            class_iri="urn:sempkm:user-types:Task-abcd1234",
            user=MagicMock(),
        )

        assert response.status_code == 200
        body = response.body.decode()
        # Verify instance count warning is present
        assert "5" in body
        assert "instance" in body.lower()
        # Verify subclass count warning is present
        assert "2" in body
        assert "subclass" in body.lower()
        # Verify both buttons are present
        assert "Cancel" in body
        assert "Confirm Delete" in body
        # Verify the confirm button targets the delete-class endpoint
        assert "delete-class" in body
        assert "My Task" in body

    @pytest.mark.asyncio
    async def test_delete_class_check_server_error_returns_500(self):
        """SPARQL failure must return 500."""
        from app.ontology.router import delete_class_check

        mock_svc = _make_ontology_service()
        mock_svc.get_delete_class_info = AsyncMock(
            side_effect=Exception("SPARQL connection refused")
        )

        request = MagicMock()
        request.app.state = _make_fake_app_state(mock_svc)

        response = await delete_class_check(
            request=request,
            class_iri="urn:sempkm:user-types:Task-abcd1234",
            user=MagicMock(),
        )

        assert response.status_code == 500
        assert b"Server error" in response.body
=======
>>>>>>> gsd/M003/S08
