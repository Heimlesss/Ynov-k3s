import flask
import logging
from shared.redis_connector import RedisConnector
from shared.database_connector import DatabaseConnector
from shared.config import Config

# Setup logging
Config().setup_logging("payment.log")

# Initialize Tracing
from shared.tracing import init_tracer, instrument_flask
init_tracer("payment_service")

app = flask.Flask(__name__)
instrument_flask(app)

# Prometheus metrics endpoint (/metrics)
from prometheus_flask_exporter import PrometheusMetrics
PrometheusMetrics(app)

@app.route("/pay", methods=["POST"])
def pay():
    data = flask.request.json
    if not data:
        return flask.jsonify({"error": "No payment data provided"}), 400
    
    reservation_id = data.get("reservation_id")
    if not reservation_id:
        return flask.jsonify({"error": "Missing reservation_id"}), 400
    
    logging.info(f"Processing payment for reservation {reservation_id}")
    
    # --- CHAOS SIMULATOR ---
    # Cette panne est introduite volontairement pour le TP d'observabilité.
    # Elle génère des erreurs aléatoires (25% de chance) avec une latence.
    import random
    import time
    if random.random() < 0.25:
        time.sleep(2.5) # Simule une latence anormale du réseau vers la banque
        error_msg = "CRITICAL: Payment Gateway Timeout. Connection refused by the external bank API."
        logging.error(error_msg)
        return flask.jsonify({"error": error_msg}), 503
    # -----------------------
    
    # Calculate price if menus exist
    menus = data.get("menus", [])
    total_price = sum(item.get("price", 0) for item in menus)
    
    # Save to PostgreSQL
    try:
        DatabaseConnector().save_order(reservation_id, total_price)
    except Exception as e:
        logging.error(f"Error saving order for {reservation_id}: {e}")
        # We process the payment anyway for this demo
    
    # Cleanup Redis
    RedisConnector().delete(reservation_id)
    
    logging.info(f"Payment successful for {reservation_id}: {total_price}€")
    return flask.jsonify({
        "message": "Payment successful",
        "reservation_id": reservation_id,
        "total_price": total_price
    }), 200

if __name__ == "__main__":
    # Ensure tables exist
    DatabaseConnector().init_db()
    
    app.run(debug=False, host="0.0.0.0", port=5003) # nosec B104
