"""OpenTelemetry distributed tracing setup for SemPKM.

Configures a TracerProvider with OTLP/HTTP export to Jaeger,
auto-instruments FastAPI and httpx, and provides clean shutdown.
When otel_enabled is False, no provider is created and all
trace.get_tracer() calls elsewhere return no-op tracers (~1μs overhead).
"""

import logging

from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from app.config import settings

logger = logging.getLogger(__name__)


def setup_tracing(app: FastAPI) -> TracerProvider | None:
    """Initialize OpenTelemetry tracing with OTLP/HTTP export.

    Must be called BEFORE any httpx.AsyncClient is created so the
    HTTPXClientInstrumentor can monkey-patch the class globally.

    Returns the TracerProvider (for shutdown) or None if disabled.
    """
    if not settings.otel_enabled:
        logger.debug("OpenTelemetry tracing disabled (otel_enabled=False)")
        return None

    resource = Resource.create(
        {
            "service.name": "sempkm-api",
            "service.version": settings.app_version,
        }
    )

    provider = TracerProvider(resource=resource)
    exporter = OTLPSpanExporter(endpoint=settings.otel_exporter_endpoint)
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)

    FastAPIInstrumentor.instrument_app(
        app, excluded_urls="api/health,api/monitoring"
    )
    HTTPXClientInstrumentor().instrument()

    logger.info(
        "OpenTelemetry tracing initialized, exporting to %s",
        settings.otel_exporter_endpoint,
    )
    return provider


def shutdown_tracing(provider: TracerProvider | None) -> None:
    """Flush buffered spans and shut down the tracer provider."""
    if provider is None:
        return
    provider.shutdown()
    logger.info("OpenTelemetry tracing shut down")
