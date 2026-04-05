"""Tests for OpenTelemetry tracing infrastructure.

Covers setup/shutdown lifecycle, custom TriplestoreClient span attributes,
query text truncation, and disabled-mode behavior.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _force_set_tracer_provider(provider: TracerProvider) -> None:
    """Force-set the global OTel tracer provider, bypassing the 'set once' guard.

    OTel's set_tracer_provider() uses a Once guard that blocks subsequent
    calls after the first. For tests we need to swap providers per-test.

    Also re-creates the module-level tracer in client.py so it uses the
    new provider. Once a real TracerProvider is set, get_tracer() returns
    a concrete Tracer bound to that specific provider (not a ProxyTracer),
    so it must be re-obtained when the provider changes.
    """
    trace._TRACER_PROVIDER_SET_ONCE._done = False
    trace._TRACER_PROVIDER = None
    trace.set_tracer_provider(provider)

    # Re-bind the module-level tracer in client.py to the new provider
    from app.triplestore import client as client_mod
    client_mod.tracer = trace.get_tracer("sempkm.triplestore")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _reset_otel_global_state():
    """Reset the global OTel tracer provider before and after each test."""
    _force_set_tracer_provider(TracerProvider())
    yield
    _force_set_tracer_provider(TracerProvider())


@pytest.fixture()
def memory_exporter():
    """Set up an InMemorySpanExporter on the global TracerProvider.

    Returns the exporter so tests can inspect captured spans.
    """
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    _force_set_tracer_provider(provider)
    return exporter


@pytest.fixture()
def triplestore_client():
    """Create a TriplestoreClient with mocked httpx internals."""
    from app.triplestore.client import TriplestoreClient

    client = TriplestoreClient(
        base_url="http://localhost:8080/rdf4j-server",
        repository_id="test",
    )
    # Replace the real httpx.AsyncClient with a mock
    client._client = MagicMock()
    return client


def _mock_json_response(json_data=None, status_code=200, content=b""):
    """Build a mock httpx.Response for TriplestoreClient tests."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data if json_data is not None else {}
    resp.content = content
    resp.raise_for_status = MagicMock()
    return resp


# ---------------------------------------------------------------------------
# setup_tracing / shutdown_tracing lifecycle
# ---------------------------------------------------------------------------

class TestSetupTracing:
    """Tests for app.monitoring.tracing.setup_tracing()."""

    @patch("app.monitoring.tracing.settings")
    @patch("app.monitoring.tracing.HTTPXClientInstrumentor")
    @patch("app.monitoring.tracing.FastAPIInstrumentor")
    def test_returns_none_when_disabled(self, mock_fastapi_inst, mock_httpx_inst, mock_settings):
        """When otel_enabled=False, setup_tracing returns None and skips instrumentation."""
        from app.monitoring.tracing import setup_tracing

        mock_settings.otel_enabled = False
        mock_app = MagicMock(spec_set=["state"])

        result = setup_tracing(mock_app)

        assert result is None
        mock_fastapi_inst.instrument_app.assert_not_called()
        mock_httpx_inst.return_value.instrument.assert_not_called()

    @patch("app.monitoring.tracing.settings")
    @patch("app.monitoring.tracing.BatchSpanProcessor")
    @patch("app.monitoring.tracing.OTLPSpanExporter")
    @patch("app.monitoring.tracing.HTTPXClientInstrumentor")
    @patch("app.monitoring.tracing.FastAPIInstrumentor")
    def test_returns_provider_when_enabled(
        self, mock_fastapi_inst, mock_httpx_inst, mock_exporter_cls, mock_processor_cls, mock_settings
    ):
        """When otel_enabled=True, setup_tracing returns a TracerProvider and instruments."""
        from app.monitoring.tracing import setup_tracing, shutdown_tracing

        mock_settings.otel_enabled = True
        mock_settings.otel_exporter_endpoint = "http://localhost:4318/v1/traces"
        mock_settings.app_version = "0.0.0-test"
        mock_app = MagicMock(spec_set=["state"])

        provider = setup_tracing(mock_app)

        assert isinstance(provider, TracerProvider)
        mock_fastapi_inst.instrument_app.assert_called_once()
        # First positional arg should be the app
        assert mock_fastapi_inst.instrument_app.call_args[0][0] is mock_app
        mock_httpx_inst.return_value.instrument.assert_called_once()

        # Clean up
        shutdown_tracing(provider)


class TestShutdownTracing:
    """Tests for app.monitoring.tracing.shutdown_tracing()."""

    def test_handles_none_provider(self):
        """shutdown_tracing(None) must not raise."""
        from app.monitoring.tracing import shutdown_tracing

        shutdown_tracing(None)  # should be a no-op

    def test_calls_shutdown_on_provider(self):
        """shutdown_tracing calls .shutdown() on a real provider."""
        from app.monitoring.tracing import shutdown_tracing

        provider = TracerProvider()
        shutdown_tracing(provider)
        # TracerProvider.shutdown() is idempotent — calling it again is fine.
        # We just confirm no exception was raised above.


# ---------------------------------------------------------------------------
# TriplestoreClient span tests
# ---------------------------------------------------------------------------

class TestTriplestoreClientSpans:
    """Verify custom spans and attributes on TriplestoreClient methods."""

    @pytest.mark.asyncio
    async def test_query_creates_span(self, memory_exporter, triplestore_client):
        """client.query() emits a sparql.query span with correct attributes."""
        sparql = 'SELECT ?s WHERE { ?s a <http://example.org/Foo> }'
        triplestore_client._client.post = AsyncMock(
            return_value=_mock_json_response({"results": {"bindings": []}})
        )

        await triplestore_client.query(sparql)

        spans = memory_exporter.get_finished_spans()
        assert len(spans) == 1
        span = spans[0]
        assert span.name == "sparql.query"
        attrs = dict(span.attributes)
        assert attrs["sparql.type"] == "SELECT"
        assert attrs["sparql.text"] == sparql
        assert attrs["sparql.result_count"] == 0

    @pytest.mark.asyncio
    async def test_update_creates_span(self, memory_exporter, triplestore_client):
        """client.update() emits a sparql.update span."""
        sparql = "INSERT DATA { <s> <p> <o> . }"
        triplestore_client._client.post = AsyncMock(
            return_value=_mock_json_response()
        )

        await triplestore_client.update(sparql)

        spans = memory_exporter.get_finished_spans()
        assert len(spans) == 1
        span = spans[0]
        assert span.name == "sparql.update"
        assert span.attributes["sparql.type"] == "UPDATE"
        assert span.attributes["sparql.text"] == sparql

    @pytest.mark.asyncio
    async def test_construct_creates_span(self, memory_exporter, triplestore_client):
        """client.construct() emits a sparql.construct span."""
        sparql = "CONSTRUCT { ?s ?p ?o } WHERE { ?s ?p ?o }"
        triplestore_client._client.post = AsyncMock(
            return_value=_mock_json_response(content=b"<s> <p> <o> .")
        )

        await triplestore_client.construct(sparql)

        spans = memory_exporter.get_finished_spans()
        assert len(spans) == 1
        span = spans[0]
        assert span.name == "sparql.construct"
        assert span.attributes["sparql.type"] == "CONSTRUCT"
        assert span.attributes["sparql.text"] == sparql

    @pytest.mark.asyncio
    async def test_insert_graph_creates_span(self, memory_exporter, triplestore_client):
        """client.insert_graph() emits a sparql.insert_graph span with graph IRI and data size."""
        turtle = "<s> <p> <o> ."
        graph = "http://example.org/graph"
        triplestore_client._client.post = AsyncMock(
            return_value=_mock_json_response()
        )

        await triplestore_client.insert_graph(turtle, graph)

        spans = memory_exporter.get_finished_spans()
        assert len(spans) == 1
        span = spans[0]
        assert span.name == "sparql.insert_graph"
        attrs = dict(span.attributes)
        assert attrs["sparql.type"] == "INSERT_GRAPH"
        assert attrs["sparql.graph_iri"] == graph
        assert isinstance(attrs["sparql.data_size"], int)
        assert attrs["sparql.data_size"] == len(turtle)

    @pytest.mark.asyncio
    async def test_query_text_truncated_to_500(self, memory_exporter, triplestore_client):
        """sparql.text attribute is truncated to 500 characters for long queries."""
        long_query = "SELECT ?s WHERE { " + "?s a <http://example.org/Type> . " * 50 + "}"
        assert len(long_query) > 500, "Test query must exceed 500 chars"

        triplestore_client._client.post = AsyncMock(
            return_value=_mock_json_response({"results": {"bindings": []}})
        )

        await triplestore_client.query(long_query)

        spans = memory_exporter.get_finished_spans()
        assert len(spans) == 1
        text_attr = spans[0].attributes["sparql.text"]
        assert len(text_attr) <= 500

    @pytest.mark.asyncio
    async def test_query_result_count_reflects_bindings(self, memory_exporter, triplestore_client):
        """sparql.result_count reflects the actual number of result bindings."""
        sparql = "SELECT ?s WHERE { ?s a <http://example.org/Foo> }"
        bindings = [{"s": {"type": "uri", "value": f"http://example.org/{i}"}} for i in range(5)]
        triplestore_client._client.post = AsyncMock(
            return_value=_mock_json_response({"results": {"bindings": bindings}})
        )

        await triplestore_client.query(sparql)

        spans = memory_exporter.get_finished_spans()
        assert spans[0].attributes["sparql.result_count"] == 5
