import logging
from collections.abc import Iterator
from contextlib import contextmanager

import structlog
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from agentverse.core.config import Settings


def configure_telemetry(settings: Settings) -> None:
    """Configure structured logs and optional OTLP tracing once at process startup."""

    logging.basicConfig(level=settings.log_level, format="%(message)s")
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.JSONRenderer(),
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
    )
    if settings.otel_exporter_otlp_endpoint:
        provider = TracerProvider(
            resource=Resource.create({"service.name": settings.otel_service_name})
        )
        exporter = OTLPSpanExporter(endpoint=settings.otel_exporter_otlp_endpoint, insecure=True)
        provider.add_span_processor(BatchSpanProcessor(exporter))
        trace.set_tracer_provider(provider)


@contextmanager
def span(name: str, **attributes: str | int | float | bool) -> Iterator[trace.Span]:
    """Small stable tracing boundary used by framework-independent code."""

    tracer = trace.get_tracer("agentverse")
    with tracer.start_as_current_span(name, attributes=attributes) as current:
        yield current
