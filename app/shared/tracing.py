import os
import logging
from opentelemetry import trace, propagate
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource

def init_tracer(service_name):
    """
    Initialize OpenTelemetry tracer and instrumentations.
    """
    # Create a resource with service name
    resource = Resource.create({
        "service.name": service_name,
        "compose_service": service_name
    })
    
    # Initialize the Tracer Provider
    provider = TracerProvider(resource=resource)
    
    # Configure OTLP Exporter (to Jaeger)
    otlp_endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "http://jaeger:4317")
    otlp_exporter = OTLPSpanExporter(endpoint=otlp_endpoint, insecure=True)
    
    # Add Span Processor
    processor = BatchSpanProcessor(otlp_exporter)
    provider.add_span_processor(processor)
    
    # Set the global tracer provider
    trace.set_tracer_provider(provider)
    
    # Initialize logging instrumentation early
    instrument_logging()
    
    logging.info(f"OpenTelemetry initialized for {service_name}")
    return trace.get_tracer(service_name)

def get_external_tracer(service_name):
    """
    Creates a dedicated tracer provider for an external service 
    to make it appear separately in Jaeger's service list.
    """
    resource = Resource.create({"service.name": service_name})
    provider = TracerProvider(resource=resource)
    
    otlp_endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "http://jaeger:4317")
    otlp_exporter = OTLPSpanExporter(endpoint=otlp_endpoint, insecure=True)
    
    provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
    return provider

def instrument_flask(app):
    from opentelemetry.instrumentation.flask import FlaskInstrumentor
    FlaskInstrumentor().instrument_app(app)

def instrument_requests():
    from opentelemetry.instrumentation.requests import RequestsInstrumentor
    RequestsInstrumentor().instrument()

def instrument_sqlalchemy(engine, tracer_provider=None):
    from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
    SQLAlchemyInstrumentor().instrument(
        engine=engine,
        tracer_provider=tracer_provider
    )

def instrument_pika(tracer_provider=None):
    from opentelemetry.instrumentation.pika import PikaInstrumentor
    PikaInstrumentor().instrument(tracer_provider=tracer_provider)

def instrument_redis(tracer_provider=None):
    from opentelemetry.instrumentation.redis import RedisInstrumentor
    RedisInstrumentor().instrument(tracer_provider=tracer_provider)

def instrument_logging():
    from opentelemetry.instrumentation.logging import LoggingInstrumentor
    # This hooks into logging and injects the trace/span IDs
    LoggingInstrumentor().instrument(set_logging_format=True)
