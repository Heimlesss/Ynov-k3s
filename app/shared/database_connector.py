from shared.connector import Connector
from shared.config import Config

from typing import List
from shared.models.MenuModel import MenuModel

import sqlalchemy
from sqlalchemy import text
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
import logging
import time
import uuid

class DatabaseConnector(Connector):
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        super().__init__(Config().get_service("db"))
        self.engine = None
        self.connect()

    def connect(self):
        for attempt in range(1, 11):
            try:
                self.engine = sqlalchemy.create_engine(self.url)
                with self.engine.connect() as conn:
                    conn.execute(text("SELECT 1"))
                
                # Instrument with dedicated provider for 'postgresql' service visibility
                from shared.tracing import instrument_sqlalchemy, get_external_tracer
                instrument_sqlalchemy(self.engine, tracer_provider=get_external_tracer("postgresql"))
                
                logging.info("Database connected and instrumented as 'postgresql' service")
                return
            except Exception as e:
                logging.error(f"Database connection failed (attempt {attempt}/10): {e}")
                if attempt < 10:
                    time.sleep(5)
        logging.error("Could not connect to Database after multiple attempts.")

    def init_db(self):
        try:
            with self.engine.connect() as conn:
                # Menu table
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS menu (
                        menu_id UUID PRIMARY KEY,
                        name VARCHAR(255) NOT NULL,
                        price FLOAT NOT NULL
                    )
                """))
                
                # Orders table
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS orders (
                        order_id UUID PRIMARY KEY,
                        reservation_id UUID NOT NULL,
                        total_price FLOAT NOT NULL,
                        order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """))

                result = conn.execute(text("SELECT COUNT(*) FROM menu"))
                count = result.scalar()
                if count == 0:
                    menus = [
                        (str(uuid.uuid4()), "Pasta Carbonara", 12.50),
                        (str(uuid.uuid4()), "Margherita Pizza", 10.00)
                    ]
                    for m_id, name, price in menus:
                        conn.execute(
                            text("INSERT INTO menu (menu_id, name, price) VALUES (:id, :name, :price)"),
                            {"id": m_id, "name": name, "price": price}
                        )
                    logging.info("Database initialized with 2 default menus")
                conn.commit()
        except Exception as e:
            logging.error(f"Database initialization failed: {e}")

    def save_order(self, reservation_id, total_price):
        """Save a completed order to the database."""
        try:
            order_id = str(uuid.uuid4())
            self.insert(
                "INSERT INTO orders (order_id, reservation_id, total_price) VALUES (:o_id, :r_id, :price)",
                {"o_id": order_id, "r_id": str(reservation_id), "price": total_price}
            )
            logging.info(f"Order {order_id} saved to DB for reservation {reservation_id}")
            return order_id
        except Exception as e:
            logging.error(f"Failed to save order to DB: {e}")
            return None

    def disconnect(self):
        try:
            self.engine.dispose()
            logging.info("Database disconnected")
        except Exception as e:
            logging.error(f"Database disconnection failed: {e}")
    
    def query(self, query_str):
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text(query_str))
                return result
        except Exception as e:
            logging.error(f"Database query failed: {e}")
            return None
    
    def insert(self, query_str, params=None):
        try:
            with self.engine.connect() as conn:
                conn.execute(text(query_str), params or {})
                conn.commit()
            logging.info("Database insert successful")
        except Exception as e:
            logging.error(f"Database insert failed: {e}")
    
    def get_menu(self) -> List[MenuModel]:
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("SELECT * FROM menu"))
                menu_list = []
                for row in result:
                    menu_list.append(MenuModel(row[0], row[1], row[2]))
                return menu_list
        except Exception as e:
            logging.error(f"Database get_menu failed: {e}")
            return []