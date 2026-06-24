from shared.config import Config
from shared.redis_connector import RedisConnector
from shared.database_connector import DatabaseConnector
from shared.rabbitmq_connector import RabbitMQConnector
from shared.models.ReservationModel import ReservationModel

import flask
import threading
import json
import logging
from typing import List

# Setup logging
Config().setup_logging("waiter.log")

# Initialize Tracing
from shared.tracing import init_tracer, instrument_flask, instrument_requests
init_tracer("waiter_service")
instrument_requests()

def callback(ch, method, properties, body):
    try:
        if not body:
            return
        
        data = json.loads(body)
        reservation_id = data.get("reservation_id")
        if not reservation_id:
            return

        reservation_data = RedisConnector().get(reservation_id)
        if not reservation_data:
            logging.warning(f"Waiter callback: Reservation {reservation_id} not found in Redis")
            return
        
        # Redis returns a dict, so we update it directly
        status = reservation_data.get("status")
        
        if status == Config().get_reservation_status("pending"):
            reservation_data["status"] = Config().get_reservation_status("confirmed")
            RedisConnector().set(reservation_id, reservation_data)
            RabbitMQConnector().publish(Config().get_queue("confirmations"), reservation_data)
            logging.info(f"Reservation {reservation_id} CONFIRMED")
            
        elif status == Config().get_reservation_status("cooking"):
            reservation_data["status"] = Config().get_reservation_status("ready")
            RedisConnector().set(reservation_id, reservation_data)
            RabbitMQConnector().publish(Config().get_queue("ready"), reservation_data)
            logging.info(f"Reservation {reservation_id} READY")

    except Exception as e:
        reservation_id = locals().get('reservation_id', 'unknown')
        status = locals().get('status', 'unknown')
        logging.error(f"Error in waiter callback for status {status} and reservation {reservation_id}: {e}")

# Threads to listen
def listen_reservations():
    RabbitMQConnector().listen(Config().get_queue("reservations"), callback)

def listen_kitchen():
    RabbitMQConnector().listen(Config().get_queue("kitchen"), callback)

app = flask.Flask(__name__)
instrument_flask(app)

# Prometheus metrics endpoint (/metrics)
from prometheus_flask_exporter import PrometheusMetrics
PrometheusMetrics(app)

@app.route("/menu", methods=["GET"])
def get_menu():
    reservation_id = flask.request.headers.get("X-Reservation-Id")
    if not reservation_id:
        logging.error(f"Missing header in /menu! Received headers: {dict(flask.request.headers)}")
        return flask.jsonify({"error": "X-Reservation-Id not found in header"}), 400
    
    reservation = RedisConnector().get(reservation_id)
    if not reservation:
        return flask.jsonify({"error": "Reservation not found"}), 404
    
    menu = DatabaseConnector().get_menu()
    
    # Update status
    reservation["status"] = Config().get_reservation_status("menu_received")
    RedisConnector().set(reservation_id, reservation)
    
    return flask.jsonify([m.to_dict() for m in menu])

@app.route("/orders", methods=["POST"])
def make_order():
    reservation_id = flask.request.headers.get("X-Reservation-Id")    
    if not reservation_id:
        logging.error(f"Missing header in /orders! Received headers: {dict(flask.request.headers)}")
        return flask.jsonify({"error": "X-Reservation-Id not found in header"}), 400
    
    reservation = RedisConnector().get(reservation_id)
    if not reservation:
        return flask.jsonify({"error": "Reservation not found"}), 404
    
    order = flask.request.json
    if not order:
        return flask.jsonify({"error": "Order data not found"}), 400
    
    # Ensure ID is in order
    order["reservation_id"] = reservation_id
    
    RabbitMQConnector().publish(Config().get_queue("orders"), order)
    return flask.jsonify({"status": "order_received"}), 200

if __name__ == "__main__":
    logging.info("Waiter service starting...")
    
    # Initialize database
    DatabaseConnector().init_db()
    
    # Start listeners
    threading.Thread(target=listen_reservations, daemon=True).start()
    threading.Thread(target=listen_kitchen, daemon=True).start()
    
    app.run(debug=False, host="0.0.0.0", port=5001, use_reloader=False) # nosec B104
