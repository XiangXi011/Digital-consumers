"""OpenTelemetry configuration and instrumentation.

Initializes OTel SDK with OTLP exporter and Prometheus metrics endpoint.
Gracefully degrades if opentelemetry packages are not installed.
"""

import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

_otel_available = False
try:
    from opentelemetry import metrics, trace
    from opentelemetry.sdk.metrics import MeterProvider
    from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    _otel_available = True
except ImportError:
    logger.info("OpenTelemetry packages not installed; observability disabled")

_meter: Optional[object] = None
_tracer: Optional[object] = None


def configure_otel(service_name: str = "market-agent-backend") -> None:
    """Initialize OpenTelemetry SDK with OTLP exporter and Prometheus reader."""
    global _meter, _tracer

    if not _otel_available:
        logger.info("OpenTelemetry not available, skipping configuration")
        return

    otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "")
    prometheus_port = int(os.getenv("PROMETHEUS_METRICS_PORT", "9090"))

    resource = Resource.create({"service.name": service_name})

    # Tracing
    tracer_provider = TracerProvider(resource=resource)
    if otlp_endpoint:
        try:
            from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

            span_exporter = OTLPSpanExporter(endpoint=otlp_endpoint)
            tracer_provider.add_span_processor(BatchSpanProcessor(span_exporter))
            logger.info("OTLP trace exporter configured: %s", otlp_endpoint)
        except Exception as exc:
            logger.warning("Failed to configure OTLP trace exporter: %s", exc)
    trace.set_tracer_provider(tracer_provider)
    _tracer = trace.get_tracer(service_name)

    # Metrics
    readers = []
    if otlp_endpoint:
        try:
            from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter

            readers.append(
                PeriodicExportingMetricReader(OTLPMetricExporter(endpoint=otlp_endpoint))
            )
            logger.info("OTLP metric exporter configured: %s", otlp_endpoint)
        except Exception as exc:
            logger.warning("Failed to configure OTLP metric exporter: %s", exc)

    try:
        from prometheus_client import start_http_server

        start_http_server(prometheus_port)
        logger.info("Prometheus metrics server started on port %d", prometheus_port)
    except Exception as exc:
        logger.warning("Failed to start Prometheus server: %s", exc)

    meter_provider = MeterProvider(resource=resource, metric_readers=readers)
    metrics.set_meter_provider(meter_provider)
    _meter = metrics.get_meter(service_name)
    logger.info("OpenTelemetry configured for service: %s", service_name)


def get_tracer():
    """Get the configured tracer instance, or None if OTel is unavailable."""
    return _tracer


def get_meter():
    """Get the configured meter instance, or None if OTel is unavailable."""
    return _meter
