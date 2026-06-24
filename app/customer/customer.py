import logging
import datetime
import random
import time
import uuid
import json
import threading
import requests
from faker import Faker
from opentelemetry import trace

from shared.config import Config
from shared.models.ReservationModel import ReservationModel
from shared.rabbitmq_connector import RabbitMQConnector
from shared.redis_connector import RedisConnector
from shared.tracing import init_tracer, instrument_requests

# Initialize Tracing FIRST
init_tracer("customer_service")
instrument_requests()
tracer = trace.get_tracer(__name__)

# Then setup logging
Config().setup_logging("customer.log")
fake = Faker()

def make_reservation():
    with tracer.start_as_current_span("make_reservation_loop"):
        logging.info("Making new reservation Request")
        url = Config().get_service("reservation") + "/reservations"

        reservation = ReservationModel(
            fake.name(),
            fake.email(),
            fake.phone_number(),
            datetime.datetime.now().strftime("%d-%m-%Y"),
            datetime.datetime.now().strftime("%H:%M:%S"),
            random.randint(1, 6),
            Config().get_reservation_status("pending"),
            uuid.uuid4()
        )

        try:
            response = requests.post(url, json=reservation.to_dict())
            logging.info(f"Reservation POST status: {response.status_code}")
        except Exception as e:
            logging.error(f"Failed to make reservation: {e}")

def get_menus(reservation_id):
    logging.info(f"Customer {reservation_id} requesting menu")
    url = Config().get_service("waiter") + "/menu"
    headers = {"X-Reservation-Id": str(reservation_id)}
    try:
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            logging.error(f"Get menus failed: {response.status_code} - {response.text}")
        return response.json()
    except Exception as e:
        logging.error(f"Failed to get menus: {e}")
        return []

def generate_menu_order(menus, nb_guests):
    order = []
    # If menus is a dict (error response), return empty
    if isinstance(menus, dict):
        return []
        
    for _ in range(nb_guests):
        if menus:
            menu = random.choice(menus)
            order.append({"name": menu["name"], "price": menu["price"]})
    return order

def make_order(reservation_id, menus):
    logging.info(f"Customer {reservation_id} making order")
    url = Config().get_service("waiter") + "/orders"
    headers = {"X-Reservation-Id": str(reservation_id)}
    data = {"reservation_id": str(reservation_id), "items": menus}
    try:
        requests.post(url, json=data, headers=headers)
    except Exception as e:
        logging.error(f"Failed to make order: {e}")

def make_payment(reservation_data):
    logging.info(f"Customer {reservation_data['reservation_id']} making payment")
    url = Config().get_service("payment") + "/pay"
    try:
        requests.post(url, json=reservation_data)
    except Exception as e:
        logging.error(f"Failed to make payment: {e}")

def callback(ch, method, properties, body):
    try:
        if not body: return
        data = json.loads(body)
        res_id = data.get("reservation_id")
        status = data.get("status")

        if status == Config().get_reservation_status("confirmed"):
            logging.info(f"Customer {res_id} received confirmed status")
            menus = get_menus(res_id)
            logging.info(f"Customer {res_id} received menus: {menus}")
            order_items = generate_menu_order(menus, data.get("guests", 1))
            logging.info(f"Customer {res_id} generated order items: {order_items}")
            
            if not order_items:
                logging.error(f"Customer {res_id} could not generate order (empty menus)")
                return

            # Update local state in Redis
            data["menus"] = order_items
            data["status"] = Config().get_reservation_status("ordering")
            RedisConnector().set(res_id, data)
            logging.info(f"Customer {res_id} updated local state in Redis")
            
            # Place order
            make_order(res_id, order_items)
            logging.info(f"Customer {res_id} placed order")
            
        elif status == Config().get_reservation_status("ready"):
            # Fetch latest data from Redis
            current_data = RedisConnector().get(res_id)
            if current_data:
                current_data["status"] = Config().get_reservation_status("served")
                RedisConnector().set(res_id, current_data)
                make_payment(current_data)

    except Exception as e:
        res_id = locals().get('res_id', 'unknown')
        status = locals().get('status', 'unknown')
        logging.error(f"Error in customer callback for status {status} and reservation {res_id}: {e}")

def listen_loop(queue):
    RabbitMQConnector().listen(queue, callback)

if __name__ == "__main__":
    # Start listeners
    threading.Thread(target=listen_loop, args=(Config().get_queue("confirmations"),), daemon=True).start()
    threading.Thread(target=listen_loop, args=(Config().get_queue("ready"),), daemon=True).start()

    start_time = time.time()
    while True:
        # Check if service time is exceeded
        if time.time() - start_time > Config().get_service_time():
            logging.info("Service time exceeded, customer generator stopping...")
            break
            
        make_reservation()
        time.sleep(random.randint(3, 15))