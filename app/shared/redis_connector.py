from shared.connector import Connector
from shared.config import Config

import redis
import json
import logging
import time

class RedisConnector(Connector):
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        super().__init__(Config().get_service("redis"))
        self.redis = None
        self.connect()

    def connect(self):
        for attempt in range(1, 11):
            try:
                self.redis = redis.from_url(Config().get_service("redis"))
                self.redis.ping()
                
                from shared.tracing import instrument_redis
                from shared.tracing import get_external_tracer
                instrument_redis(tracer_provider=get_external_tracer("redis"))
                
                logging.info("Redis connected and instrumented")
                return
            except Exception as e:
                logging.error(f"Redis connection failed (attempt {attempt}/10): {e}")
                if attempt < 10:
                    time.sleep(5)
        logging.error("Could not connect to Redis after multiple attempts.")

    def disconnect(self):
        try:
            self.redis.close()
            logging.info("Redis disconnected")
        except Exception as e:
            logging.error(f"Redis disconnection failed: {e}")

    def get_all(self):
        try:
            keys = self.redis.keys("*")
            if not keys:
                return []
            values = self.redis.mget(keys)
            return [json.loads(v) for v in values if v]
        except Exception as e:
            logging.error(f"Redis get all failed: {e}")
            return None
    
    def get(self, key):
        try:
            value = self.redis.get(str(key))
            return json.loads(value) if value else None
        except Exception as e:
            logging.error(f"Redis get failed: {e}")
            return None
    
    def set(self, key, value):
        try:
            self.redis.set(str(key), json.dumps(value))
            logging.info("Redis set successful")
        except Exception as e:
            logging.error(f"Redis set failed: {e}")
    
    def delete(self, key):
        try:
            self.redis.delete(key)
            logging.info("Redis delete successful")
        except Exception as e:
            logging.error(f"Redis delete failed: {e}")