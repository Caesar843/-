import logging
import os

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

logger = logging.getLogger(__name__)

_OTEL_CONFIGURED = False


def _parse_bool(value, default=False):
    if value is None:
        return default
    return str(value).strip().lower() in {'1', 'true', 'yes', 'on'}


def configure_otel(instrument_django=False, instrument_celery=False):
    global _OTEL_CONFIGURED

    if _OTEL_CONFIGURED:
        return

    if not _parse_bool(os.getenv('OTEL_ENABLED'), default=False):
        return

    service_name = os.getenv('OTEL_SERVICE_NAME', 'store-management')
    environment = os.getenv('OTEL_ENVIRONMENT', os.getenv('ENV', 'development'))
    resource = Resource.create(
        {
            'service.name': service_name,
            'deployment.environment': environment,
        }
    )

    provider = TracerProvider(resource=resource)
    trace.set_tracer_provider(provider)

    exporter = _build_exporter()
    provider.add_span_processor(BatchSpanProcessor(exporter))

    if instrument_django:
        try:
            from opentelemetry.instrumentation.django import DjangoInstrumentor

            DjangoInstrumentor().instrument()
        except Exception as exc:
            logger.warning('OpenTelemetry Django instrumentation skipped: %s', exc)

    if instrument_celery:
        try:
            from opentelemetry.instrumentation.celery import CeleryInstrumentor

            CeleryInstrumentor().instrument()
        except Exception as exc:
            logger.warning('OpenTelemetry Celery instrumentation skipped: %s', exc)

    _OTEL_CONFIGURED = True


def _build_exporter():
    endpoint = os.getenv('OTEL_EXPORTER_OTLP_ENDPOINT')
    if endpoint:
        try:
            from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
                OTLPSpanExporter,
            )

            return OTLPSpanExporter(endpoint=endpoint)
        except Exception as exc:
            logger.warning('OpenTelemetry OTLP exporter unavailable: %s', exc)

    return ConsoleSpanExporter()
