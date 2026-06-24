import os
import sys
import logging

CONSTANTS = {
    "SERVICE_TIME": 60 * 60, # 1 hour
}

class Config:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        env = os.environ
        self.services = {
            "db": env.get("DB_URL", "postgresql://user:password@db:5432/restaurant"),
            "redis": env.get("REDIS_URL", "redis://redis:6379"),
            "rabbitmq": env.get("RABBITMQ_URL", "amqp://guest:guest@rabbitmq:5672/"),
            "waiter": env.get("WAITER_URL", "http://waiter:5001"),
            "payment": env.get("PAYMENT_URL", "http://payment:5003"),
            "reservation": env.get("RESERVATION_URL", "http://reservation:5004"),
            "kitchen": env.get("KITCHEN_URL", "http://kitchen:5002"),
        }
        self.queues = {
            "reservations": "reservations_queue",
            "confirmations": "confirmations_queue",
            "orders": "orders_queue",
            "kitchen": "kitchen_queue",
            "ready": "ready_queue",
            "payments": "payments_queue"
        }
        self.reservation_statuses = {
            "pending": "PENDING",
            "confirmed": "CONFIRMED",
            "ordering": "ORDERING",
            "menu_received": "MENU_RECEIVED",
            "cooking": "COOKING",
            "ready": "READY",
            "served": "SERVED",
            "paid": "PAID"
        }
        self.service_time = CONSTANTS["SERVICE_TIME"]

    def setup_logging(self, log_file="app.log"):
        """Configure logging to both stdout and a file with Trace/Span IDs."""
        # Note: TraceID and SpanID are injected by OTel LoggingInstrumentor
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - [trace_id: %(otelTraceID)s, span_id: %(otelSpanID)s] - %(module)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler(sys.stdout)
            ],
            force=True
        )

    def get_service(self, service_name):
        return self.services.get(service_name)

    def get_queue(self, queue_name):
        return self.queues.get(queue_name)

    def get_reservation_status(self, status_name):
        return self.reservation_statuses.get(status_name)

    def get_service_time(self):
        return self.service_time
