from shared.connector import Connector
from shared.config import Config

import pika
import json
import logging
import time
from opentelemetry import trace, propagate

# Initialize logging for RabbitMQ
Config().setup_logging("rabbitmq.log")

class RabbitMQConnector(Connector):
    def __init__(self):
        super().__init__(Config().get_service("rabbitmq"))
        self.connection = None
        self.channel = None
        self.connect()

    def connect(self):
        for attempt in range(1, 11):
            try:
                if not self.connection or self.connection.is_closed:
                    self.connection = pika.BlockingConnection(pika.URLParameters(self.url))
                    self.channel = self.connection.channel()
                    
                    from shared.tracing import instrument_pika, get_external_tracer
                    instrument_pika(tracer_provider=get_external_tracer("rabbitmq"))
                    
                    logging.info("RabbitMQ connected, channel created and instrumented")
                return
            except Exception as e:
                logging.error(f"RabbitMQ connection failed (attempt {attempt}/10): {e}")
                if attempt < 10:
                    time.sleep(5)
        logging.error("Could not connect to RabbitMQ after multiple attempts.")

    def disconnect(self):
        try:
            if self.channel and self.channel.is_open:
                self.channel.close()
            if self.connection and self.connection.is_open:
                self.connection.close()
                logging.info("RabbitMQ disconnected")
        except Exception as e:
            logging.error(f"RabbitMQ disconnection failed: {e}")

    def publish(self, queue, message):
        try:
            if not self.channel or self.channel.is_closed:
                self.connect()
            self.channel.queue_declare(queue=queue)
            
            # Ensure message is serialized to JSON string
            if isinstance(message, (dict, list)):
                body = json.dumps(message)
            elif isinstance(message, str):
                body = message
            else:
                body = str(message)

            # Inject trace context into headers for propagation
            headers = {}
            propagate.inject(headers)

            self.channel.basic_publish(
                exchange='', 
                routing_key=queue, 
                body=body,
                properties=pika.BasicProperties(headers=headers)
            )
            logging.info(f"RabbitMQ message sent to {queue}")
        except Exception as e:
            logging.error(f"RabbitMQ send failed: {e}")
    
    def listen(self, queue, callback):
        attempts = 0
        while attempts < 10:
            try:
                if not self.channel or self.channel.is_closed:
                    self.connect()
                
                logging.info(f"RabbitMQ listener starting on queue: {queue}")
                self.channel.queue_declare(queue=queue)
                
                # Internal wrapper to handle context extraction
                def callback_wrapper(ch, method, properties, body):
                    # Extract context from headers
                    ctx = propagate.extract(properties.headers or {})
                    tracer = trace.get_tracer(__name__)
                    # Create a span for the processing and activate context
                    with tracer.start_as_current_span(f"process_{queue}", context=ctx):
                        callback(ch, method, properties, body)

                self.channel.basic_consume(queue=queue, auto_ack=True, on_message_callback=callback_wrapper)
                self.channel.start_consuming()
            except Exception as e:
                logging.error(f"RabbitMQ listener failed on queue {queue}: {e}")
                attempts += 1
                time.sleep(5)
                self.connect()
        logging.error(f"Could not maintain RabbitMQ listener on {queue} after multiple attempts.")