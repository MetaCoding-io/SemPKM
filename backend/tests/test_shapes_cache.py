"""Tests for ShapesService TTL caching.

Covers:
- Shapes graph cache: repeated calls avoid re-fetching from triplestore
- Per-type form cache: repeated get_form_for_type calls are served from cache
- clear_cache(): forces re-fetch on next call
- TTL expiry: entries expire after the configured TTL
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest
from cachetools import TTLCache

from app.services.shapes import ShapesService, NodeShapeForm, PropertyShape


# ---------------------------------------------------------------------------
# Fixtures & helpers
# ---------------------------------------------------------------------------

# Minimal Turtle for a shapes graph with one NodeShape
SAMPLE_SHAPES_TURTLE = """\
@prefix sh: <http://www.w3.org/ns/shacl#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

<urn:shape:NoteShape>
    a sh:NodeShape ;
    sh:targetClass <urn:type:Note> ;
    sh:name "Note" ;
    sh:property [
        sh:path <http://purl.org/dc/terms/title> ;
        sh:name "Title" ;
        sh:datatype xsd:string ;
        sh:order 1.0 ;
        sh:minCount 1 ;
        sh:maxCount 1 ;
    ] .
"""

SPARQL_MODEL_BINDINGS = {
    "results": {
        "bindings": [
            {"modelId": {"value": "basic-pkm"}}
        ]
    }
}


def _make_client(turtle: str = SAMPLE_SHAPES_TURTLE) -> AsyncMock:
    """Build a mock TriplestoreClient that returns fixed SPARQL results."""
    client = AsyncMock()
    client.query = AsyncMock(return_value=SPARQL_MODEL_BINDINGS)
    client.construct = AsyncMock(return_value=turtle)
    return client


# ---------------------------------------------------------------------------
# Shapes graph cache
# ---------------------------------------------------------------------------

class TestShapesGraphCache:
    """_fetch_shapes_graph() uses TTLCache — second call is free."""

    @pytest.mark.asyncio
    async def test_second_call_uses_cache(self):
        """Calling _fetch_shapes_graph twice triggers SPARQL only once."""
        client = _make_client()
        svc = ShapesService(client, ttl=600)

        g1 = await svc._fetch_shapes_graph()
        g2 = await svc._fetch_shapes_graph()

        # SPARQL construct called exactly once
        assert client.construct.call_count == 1
        # Both calls return the same graph object (identity, not equality)
        assert g1 is g2

    @pytest.mark.asyncio
    async def test_cache_miss_fetches_from_triplestore(self):
        """First call always goes to the triplestore."""
        client = _make_client()
        svc = ShapesService(client, ttl=600)

        g = await svc._fetch_shapes_graph()
        assert client.construct.call_count == 1
        assert len(g) > 0

    @pytest.mark.asyncio
    async def test_no_models_returns_empty_graph_cached(self):
        """When no models are installed, empty graph is still cached."""
        client = AsyncMock()
        client.query = AsyncMock(return_value={"results": {"bindings": []}})
        svc = ShapesService(client, ttl=600)

        g1 = await svc._fetch_shapes_graph()
        g2 = await svc._fetch_shapes_graph()

        assert len(g1) == 0
        assert g1 is g2
        # query called once for the SELECT, construct never called
        assert client.query.call_count == 1
        assert client.construct.call_count == 0


# ---------------------------------------------------------------------------
# Per-type form cache
# ---------------------------------------------------------------------------

class TestFormCache:
    """get_form_for_type() caches per type_iri."""

    @pytest.mark.asyncio
    async def test_repeated_calls_same_type_cached(self):
        """Two calls for the same type_iri trigger only 1 SPARQL CONSTRUCT."""
        client = _make_client()
        svc = ShapesService(client, ttl=600)

        form1 = await svc.get_form_for_type("urn:type:Note")
        form2 = await svc.get_form_for_type("urn:type:Note")

        assert form1 is not None
        assert form1 is form2
        # construct called once (from the graph cache miss on first call)
        assert client.construct.call_count == 1

    @pytest.mark.asyncio
    async def test_different_types_each_resolve(self):
        """Different type_iris each get resolved (graph is shared)."""
        client = _make_client()
        svc = ShapesService(client, ttl=600)

        note_form = await svc.get_form_for_type("urn:type:Note")
        unknown_form = await svc.get_form_for_type("urn:type:Unknown")

        assert note_form is not None
        assert note_form.target_class == "urn:type:Note"
        assert unknown_form is None
        # Still only 1 construct call — graph was cached after first call
        assert client.construct.call_count == 1

    @pytest.mark.asyncio
    async def test_form_has_correct_properties(self):
        """Cached form retains its property shapes."""
        client = _make_client()
        svc = ShapesService(client, ttl=600)

        form = await svc.get_form_for_type("urn:type:Note")
        assert form is not None
        assert len(form.properties) == 1
        assert form.properties[0].name == "Title"


# ---------------------------------------------------------------------------
# clear_cache()
# ---------------------------------------------------------------------------

class TestClearCache:
    """clear_cache() forces a re-fetch on the next call."""

    @pytest.mark.asyncio
    async def test_clear_forces_refetch(self):
        """After clear_cache(), the next call goes to SPARQL again."""
        client = _make_client()
        svc = ShapesService(client, ttl=600)

        await svc._fetch_shapes_graph()
        assert client.construct.call_count == 1

        svc.clear_cache()
        await svc._fetch_shapes_graph()
        assert client.construct.call_count == 2

    @pytest.mark.asyncio
    async def test_clear_also_clears_form_cache(self):
        """clear_cache() clears form cache so type lookups re-resolve."""
        client = _make_client()
        svc = ShapesService(client, ttl=600)

        form1 = await svc.get_form_for_type("urn:type:Note")
        svc.clear_cache()
        form2 = await svc.get_form_for_type("urn:type:Note")

        # Both should be valid forms but NOT the same object (re-fetched)
        assert form1 is not None
        assert form2 is not None
        assert form1 is not form2
        # construct called twice — once per fetch
        assert client.construct.call_count == 2


# ---------------------------------------------------------------------------
# TTL expiry
# ---------------------------------------------------------------------------

class TestTTLExpiry:
    """Cache entries expire after the configured TTL."""

    @pytest.mark.asyncio
    async def test_shapes_graph_expires(self):
        """Shapes graph cache expires after TTL, triggering a re-fetch."""
        client = _make_client()
        # Use a very short TTL so we can test expiry
        svc = ShapesService(client, ttl=0)

        await svc._fetch_shapes_graph()
        assert client.construct.call_count == 1

        # TTL=0 means expired immediately
        await svc._fetch_shapes_graph()
        assert client.construct.call_count == 2

    @pytest.mark.asyncio
    async def test_form_cache_expires(self):
        """Form cache expires after TTL, triggering re-resolution."""
        client = _make_client()
        svc = ShapesService(client, ttl=0)

        form1 = await svc.get_form_for_type("urn:type:Note")
        form2 = await svc.get_form_for_type("urn:type:Note")

        assert form1 is not None
        assert form2 is not None
        # With TTL=0 both graph and form caches expire immediately
        # so construct is called at least twice
        assert client.construct.call_count >= 2


# ---------------------------------------------------------------------------
# Debug logging
# ---------------------------------------------------------------------------

class TestCacheLogging:
    """DEBUG-level logging on cache hit/miss."""

    @pytest.mark.asyncio
    async def test_logs_cache_miss_then_hit(self, caplog):
        """First call logs MISS, second logs HIT."""
        import logging
        client = _make_client()
        svc = ShapesService(client, ttl=600)

        with caplog.at_level(logging.DEBUG, logger="app.services.shapes"):
            await svc._fetch_shapes_graph()
            await svc._fetch_shapes_graph()

        messages = [r.message for r in caplog.records]
        assert any("MISS" in m for m in messages), f"Expected MISS log, got: {messages}"
        assert any("HIT" in m for m in messages), f"Expected HIT log, got: {messages}"

    @pytest.mark.asyncio
    async def test_form_logs_cache_miss_then_hit(self, caplog):
        """Form cache logs MISS on first call, HIT on second."""
        import logging
        client = _make_client()
        svc = ShapesService(client, ttl=600)

        with caplog.at_level(logging.DEBUG, logger="app.services.shapes"):
            await svc.get_form_for_type("urn:type:Note")
            await svc.get_form_for_type("urn:type:Note")

        messages = [r.message for r in caplog.records]
        miss_msgs = [m for m in messages if "form cache MISS" in m]
        hit_msgs = [m for m in messages if "form cache HIT" in m]
        assert len(miss_msgs) >= 1, f"Expected form MISS log, got: {messages}"
        assert len(hit_msgs) >= 1, f"Expected form HIT log, got: {messages}"
