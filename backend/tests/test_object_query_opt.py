"""Tests for get_object query optimization.

Verifies that the UNION query replaces 3 separate graph queries and
that label resolution is consolidated into a single batch call.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.rdf.namespaces import CURRENT_GRAPH


# --- Helpers ---

TEST_IRI = "http://example.org/obj/1"
RDF_TYPE = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"
SEMPKM_BODY = "urn:sempkm:body"
TEST_TYPE = "http://example.org/ontology/Note"


def make_union_bindings(
    user_triples: list[tuple[str, str]],
    inferred_triples: list[tuple[str, str]] | None = None,
    mirrored_triples: list[tuple[str, str]] | None = None,
) -> dict:
    """Build SPARQL JSON result for the UNION query (SELECT ?p ?o ?source)."""
    bindings = []
    for pred, obj in user_triples:
        bindings.append({
            "p": {"type": "uri", "value": pred},
            "o": {"type": "literal" if not obj.startswith("http") else "uri", "value": obj},
            "source": {"type": "literal", "value": "user"},
        })
    for pred, obj in (inferred_triples or []):
        bindings.append({
            "p": {"type": "uri", "value": pred},
            "o": {"type": "literal" if not obj.startswith("http") else "uri", "value": obj},
            "source": {"type": "literal", "value": "inferred"},
        })
    for pred, obj in (mirrored_triples or []):
        bindings.append({
            "p": {"type": "uri", "value": pred},
            "o": {"type": "literal" if not obj.startswith("http") else "uri", "value": obj},
            "source": {"type": "literal", "value": "mirrored"},
        })
    return {"results": {"bindings": bindings}}


def empty_result():
    return {"results": {"bindings": []}}


# --- Fixtures ---

@pytest.fixture
def mock_client():
    """Mock TriplestoreClient."""
    client = AsyncMock()
    client.query = AsyncMock(return_value=empty_result())
    return client


@pytest.fixture
def mock_label_service():
    """Mock LabelService that returns IRI as label."""
    svc = AsyncMock()
    # resolve_batch returns a dict mapping each IRI to itself (fallback)
    svc.resolve_batch = AsyncMock(side_effect=lambda iris: {iri: iri.split("/")[-1] for iri in iris})
    return svc


@pytest.fixture
def mock_shapes_service():
    """Mock ShapesService that returns no form."""
    svc = AsyncMock()
    svc.get_form_for_type = AsyncMock(return_value=None)
    return svc


@pytest.fixture
def mock_icon_service():
    svc = MagicMock()
    svc.get_type_icon = MagicMock(return_value=None)
    return svc


@pytest.fixture
def mock_db_session():
    """Mock async DB session for favorites check."""
    session = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none = MagicMock(return_value=None)
    session.execute = AsyncMock(return_value=result)
    return session


@pytest.fixture
def mock_request(mock_label_service, mock_shapes_service, mock_icon_service, mock_db_session):
    """Mock FastAPI Request with templates."""
    request = MagicMock()
    templates = MagicMock()
    env = MagicMock()
    env.filters = {}
    templates.env = env
    # Capture the context passed to TemplateResponse
    templates.TemplateResponse = MagicMock()
    request.app.state.templates = templates
    return request


# --- Tests ---

class TestUnionQueryOptimization:
    """Verify that get_object uses a single UNION query instead of 3 separate queries."""

    async def test_single_sparql_query_for_properties(self, mock_client, mock_label_service,
                                                       mock_shapes_service, mock_icon_service,
                                                       mock_db_session, mock_request):
        """Only 1 SPARQL query should be made for all property graphs (not 3)."""
        from app.browser.objects import get_object

        mock_client.query.return_value = make_union_bindings(
            user_triples=[
                (RDF_TYPE, TEST_TYPE),
                ("http://purl.org/dc/terms/title", "Test Note"),
            ],
        )

        user = MagicMock()
        user.id = 1

        await get_object(
            request=mock_request,
            object_iri=TEST_IRI,
            mode="read",
            embed=0,
            user=user,
            shapes_service=mock_shapes_service,
            label_service=mock_label_service,
            client=mock_client,
            icon_svc=mock_icon_service,
            db=mock_db_session,
        )

        # Should be exactly 1 SPARQL query (the UNION), not 3
        assert mock_client.query.call_count == 1, (
            f"Expected 1 SPARQL query, got {mock_client.query.call_count}"
        )
        # Verify it's a UNION query
        query_text = mock_client.query.call_args[0][0]
        assert "UNION" in query_text, "Query should use UNION to combine graphs"
        assert "urn:sempkm:current" in query_text
        assert "urn:sempkm:inferred" in query_text
        assert "urn:sempkm:mirrored" in query_text

    async def test_single_label_batch_call(self, mock_client, mock_label_service,
                                           mock_shapes_service, mock_icon_service,
                                           mock_db_session, mock_request):
        """Only 1 label batch call should be made (not 5)."""
        from app.browser.objects import get_object

        mock_client.query.return_value = make_union_bindings(
            user_triples=[
                (RDF_TYPE, TEST_TYPE),
                ("http://purl.org/dc/terms/title", "Test Note"),
                ("http://purl.org/dc/terms/subject", "http://example.org/topic/1"),
            ],
            inferred_triples=[
                ("http://example.org/onto/score", "0.95"),
            ],
            mirrored_triples=[
                ("http://example.org/onto/mirrorProp", "http://example.org/ext/1"),
            ],
        )

        user = MagicMock()
        user.id = 1

        await get_object(
            request=mock_request,
            object_iri=TEST_IRI,
            mode="read",
            embed=0,
            user=user,
            shapes_service=mock_shapes_service,
            label_service=mock_label_service,
            client=mock_client,
            icon_svc=mock_icon_service,
            db=mock_db_session,
        )

        # Should be exactly 1 label batch call (not 5)
        assert mock_label_service.resolve_batch.call_count == 1, (
            f"Expected 1 label batch call, got {mock_label_service.resolve_batch.call_count}"
        )


class TestDeduplicationPreserved:
    """Verify that the deduplication logic (user > inferred > mirrored) still works."""

    async def test_inferred_deduped_against_user(self, mock_client, mock_label_service,
                                                  mock_shapes_service, mock_icon_service,
                                                  mock_db_session, mock_request):
        """Inferred values that duplicate user values should be excluded."""
        from app.browser.objects import get_object

        dcterms_title = "http://purl.org/dc/terms/title"
        mock_client.query.return_value = make_union_bindings(
            user_triples=[
                (RDF_TYPE, TEST_TYPE),
                (dcterms_title, "User Title"),
            ],
            inferred_triples=[
                (dcterms_title, "User Title"),  # exact duplicate
                (dcterms_title, "Inferred Extra"),  # unique
            ],
        )

        user = MagicMock()
        user.id = 1

        templates = mock_request.app.state.templates
        captured_ctx = {}

        def capture_template(request, name, context):
            captured_ctx.update(context)
            resp = MagicMock()
            resp.headers = {}
            return resp

        templates.TemplateResponse = capture_template

        await get_object(
            request=mock_request,
            object_iri=TEST_IRI,
            mode="read",
            embed=0,
            user=user,
            shapes_service=mock_shapes_service,
            label_service=mock_label_service,
            client=mock_client,
            icon_svc=mock_icon_service,
            db=mock_db_session,
        )

        # User values should have "User Title" only
        assert captured_ctx["values"][dcterms_title] == ["User Title"]
        # Inferred should only have "Inferred Extra" (duplicate excluded)
        assert captured_ctx["inferred_values"][dcterms_title] == ["Inferred Extra"]

    async def test_mirrored_deduped_against_user_and_inferred(self, mock_client, mock_label_service,
                                                               mock_shapes_service, mock_icon_service,
                                                               mock_db_session, mock_request):
        """Mirrored values that duplicate user or inferred values should be excluded."""
        from app.browser.objects import get_object

        pred = "http://example.org/onto/tag"
        mock_client.query.return_value = make_union_bindings(
            user_triples=[
                (RDF_TYPE, TEST_TYPE),
                (pred, "user-val"),
            ],
            inferred_triples=[
                (pred, "inferred-val"),
            ],
            mirrored_triples=[
                (pred, "user-val"),       # duplicate of user
                (pred, "inferred-val"),   # duplicate of inferred
                (pred, "mirror-only"),    # unique
            ],
        )

        user = MagicMock()
        user.id = 1

        captured_ctx = {}

        def capture_template(request, name, context):
            captured_ctx.update(context)
            resp = MagicMock()
            resp.headers = {}
            return resp

        mock_request.app.state.templates.TemplateResponse = capture_template

        await get_object(
            request=mock_request,
            object_iri=TEST_IRI,
            mode="read",
            embed=0,
            user=user,
            shapes_service=mock_shapes_service,
            label_service=mock_label_service,
            client=mock_client,
            icon_svc=mock_icon_service,
            db=mock_db_session,
        )

        assert captured_ctx["values"][pred] == ["user-val"]
        assert captured_ctx["inferred_values"][pred] == ["inferred-val"]
        # mirrored_values is folded into read_values with source tag, not passed directly
        mirrored_items = [
            item for item in captured_ctx["read_values"].get(pred, [])
            if item["source"] == "mirrored"
        ]
        assert len(mirrored_items) == 1
        assert mirrored_items[0]["value"] == "mirror-only"

    async def test_type_and_body_from_user_graph_only(self, mock_client, mock_label_service,
                                                       mock_shapes_service, mock_icon_service,
                                                       mock_db_session, mock_request):
        """rdf:type and urn:sempkm:body should only come from user graph."""
        from app.browser.objects import get_object

        mock_client.query.return_value = make_union_bindings(
            user_triples=[
                (RDF_TYPE, TEST_TYPE),
                (SEMPKM_BODY, "User body text"),
            ],
            inferred_triples=[
                (RDF_TYPE, "http://example.org/ontology/InferredType"),
                (SEMPKM_BODY, "Inferred body"),
            ],
        )

        user = MagicMock()
        user.id = 1

        captured_ctx = {}

        def capture_template(request, name, context):
            captured_ctx.update(context)
            resp = MagicMock()
            resp.headers = {}
            return resp

        mock_request.app.state.templates.TemplateResponse = capture_template

        await get_object(
            request=mock_request,
            object_iri=TEST_IRI,
            mode="read",
            embed=0,
            user=user,
            shapes_service=mock_shapes_service,
            label_service=mock_label_service,
            client=mock_client,
            icon_svc=mock_icon_service,
            db=mock_db_session,
        )

        # type_iris should only contain user-graph types
        # (inferred rdf:type and body are skipped)
        assert captured_ctx["body_text"] == "User body text"
        # Inferred values should NOT contain rdf:type or body
        assert RDF_TYPE not in captured_ctx.get("inferred_values", {})
        assert SEMPKM_BODY not in captured_ctx.get("inferred_values", {})


class TestUnionQueryOrdering:
    """Verify dedup works regardless of SPARQL result ordering."""

    async def test_dedup_works_when_inferred_arrives_first(self, mock_client, mock_label_service,
                                                            mock_shapes_service, mock_icon_service,
                                                            mock_db_session, mock_request):
        """Dedup should work even if UNION returns inferred bindings before user bindings.

        This tests the two-pass partitioning approach: user bindings are processed
        first regardless of their position in the SPARQL results.
        """
        from app.browser.objects import get_object

        pred = "http://example.org/onto/status"

        # Manually construct bindings with inferred FIRST (simulates UNION reorder)
        bindings = [
            # Inferred binding arrives first
            {"p": {"type": "uri", "value": pred},
             "o": {"type": "literal", "value": "active"},
             "source": {"type": "literal", "value": "inferred"}},
            # User binding arrives second
            {"p": {"type": "uri", "value": RDF_TYPE},
             "o": {"type": "uri", "value": TEST_TYPE},
             "source": {"type": "literal", "value": "user"}},
            {"p": {"type": "uri", "value": pred},
             "o": {"type": "literal", "value": "active"},
             "source": {"type": "literal", "value": "user"}},
        ]
        mock_client.query.return_value = {"results": {"bindings": bindings}}

        user = MagicMock()
        user.id = 1

        captured_ctx = {}

        def capture_template(request, name, context):
            captured_ctx.update(context)
            resp = MagicMock()
            resp.headers = {}
            return resp

        mock_request.app.state.templates.TemplateResponse = capture_template

        await get_object(
            request=mock_request,
            object_iri=TEST_IRI,
            mode="read",
            embed=0,
            user=user,
            shapes_service=mock_shapes_service,
            label_service=mock_label_service,
            client=mock_client,
            icon_svc=mock_icon_service,
            db=mock_db_session,
        )

        # User should have the value
        assert captured_ctx["values"][pred] == ["active"]
        # Inferred should NOT have it (deduped despite arriving first in results)
        assert pred not in captured_ctx.get("inferred_values", {})
