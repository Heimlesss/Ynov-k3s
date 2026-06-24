from shared.config import Config
from shared.redis_connector import RedisConnector
from shared.rabbitmq_connector import RabbitMQConnector
from shared.models.ReservationModel import ReservationModel

import flask
import logging

# Setup logging
Config().setup_logging("reservation.log")

# Initialize Tracing
from shared.tracing import init_tracer, instrument_flask
init_tracer("reservation_service")

app = flask.Flask(__name__)
instrument_flask(app)

# Prometheus metrics endpoint (/metrics)
from prometheus_flask_exporter import PrometheusMetrics
PrometheusMetrics(app)

@app.route("/reservations", methods=["POST"])
def make_reservation():
    data = flask.request.json
    if not data:
        return flask.jsonify({"error": "No reservation data provided"}), 400
    
    try:
        reservation = ReservationModel.from_dict(data)
    except Exception as e:
        return flask.jsonify({"error": f"Invalid reservation data: {e}"}), 400
    
    res_id_str = str(reservation.reservation_id)
    
    try:
        RedisConnector().set(res_id_str, reservation.to_dict())
        RabbitMQConnector().publish(Config().get_queue("reservations"), reservation.to_dict())
        logging.info(f"Reservation {res_id_str} created and published")
    except Exception as e:
        logging.error(f"Failed to process reservation {res_id_str}: {e}")
        return flask.jsonify({"error": "External service error"}), 500
        
    return flask.jsonify({"reservation_id": res_id_str}), 200

@app.route("/reservations", methods=["GET"])
def get_reservations():
    reservations = RedisConnector().get_all()
    return flask.jsonify(reservations), 200

@app.route("/reservations/<id>", methods=["GET"])
def get_reservation(id):
    reservation = RedisConnector().get(id)
    if not reservation:
        return flask.jsonify({"error": "Not found"}), 404
    return flask.jsonify(reservation), 200

@app.route("/reservations/<id>/status", methods=["GET"])
def get_reservation_status(id):
    reservation = RedisConnector().get(id)
    if not reservation:
        return flask.jsonify({"error": "Not found"}), 404
    return flask.jsonify({"status": reservation.get("status")}), 200

if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=5004)