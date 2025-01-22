from flask import current_app
import paho.mqtt.client as mqtt
from datetime import datetime
import json
import logging
import time
from threading import Thread, Event
from paho import mqtt as paho

logger = logging.getLogger(__name__)


class MeasurementMQTTHandler:
    def __init__(self, app):
        self.app = app
        self.client = mqtt.Client()
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self.client.on_disconnect = self._on_disconnect
        self._setup_mqtt()
        self.connected = False
        self.stopping = Event()
        self.reconnect_thread = None

    def _setup_mqtt(self):
        """Setup MQTT client with configuration from app"""
        mqtt_config = self.app.config["MQTT_CONFIG"]
        self.broker_url = mqtt_config["broker_url"]
        self.port = mqtt_config["port"]
        username = mqtt_config["username"]
        password = mqtt_config["password"]

        self.client.username_pw_set(username, password)
        self.client.tls_set(tls_version=paho.client.ssl.PROTOCOL_TLS)

        self.topic = "measurement"


    def start(self):
        """Start MQTT client in non-blocking way"""
        try:
            # Start MQTT loop in background thread
            self.client.loop_start()

            # Try to connect
            self._connect()

            # Start reconnection thread
            self.reconnect_thread = Thread(target=self._reconnection_loop)
            self.reconnect_thread.daemon = True
            self.reconnect_thread.start()

            logger.info("MQTT handler started")
        except Exception as e:
            logger.error(f"Error starting MQTT handler: {e}")
            # Don't raise the exception - allow the application to continue

    def stop(self):
        """Stop MQTT client"""
        self.stopping.set()
        if self.reconnect_thread:
            self.reconnect_thread.join(timeout=1.0)
        self.client.loop_stop()
        if self.connected:
            self.client.disconnect()
        logger.info("MQTT handler stopped")

    def _connect(self):
        """Attempt to connect to the broker"""
        try:
            self.client.connect(self.broker_url, self.port, 60)
            logger.info(f"Attempting connection to {self.broker_url}:{self.port}")
        except Exception as e:
            logger.error(f"Connection attempt failed: {e}")
            self.connected = False

    def _reconnection_loop(self):
        """Background thread that handles reconnection"""
        while not self.stopping.is_set():
            if not self.connected:
                logger.info("Attempting to reconnect...")
                try:
                    self._connect()
                except Exception as e:
                    logger.error(f"Reconnection attempt failed: {e}")
            time.sleep(5)  # Wait 5 seconds between reconnection attempts

    def _on_connect(self, client, userdata, flags, rc):
        """Handle connection to broker"""
        if rc == 0:
            self.connected = True
            logger.info("Connected to MQTT broker")
            # Subscribe to temperature topics
            client.subscribe(self.topic)
            logger.info(f"Subscribed to {self.topic}")
        else:
            self.connected = False
            logger.error(f"Failed to connect to MQTT broker with code: {rc}")

    def _on_disconnect(self, client, userdata, rc):
        """Handle disconnection from broker"""
        self.connected = False
        if rc != 0:
            logger.warning(f"Unexpected disconnection from MQTT broker: {rc}")

    def _on_message(self, client, userdata, msg):
        """Handle incoming temperature measurements"""
        try:
            # Parse the JSON payload
            payload = msg.payload.decode()
            data = json.loads(payload)

            with self.app.app_context():
                # Add temperature to room
                room = current_app.config["DB_SERVICE"].get_dr("room",data['room_id'])
                if not room:
                    logger.error(f"Room not found with ID: {data['room_id']}")
                    return
                #initilize fields if they do not exist
                if 'data' not in room:
                    room['data'] = {}
                if 'measurements' not in room['data']:
                    room['data']['measurements'] = []
                #We need to register the measurement
                measurement = {
                    "temperature": data['temperature'],
                    "humidity": data['humidity'],
                    "timestamp": datetime.utcnow()
                }
                update_data = {
                    "data": {
                        "measurements": room['data']['measurements'] + [measurement],
                        "temperature": data['temperature'],
                        "humidity": data['humidity']
                    },
                    "metadata": {
                        "updated_at": datetime.utcnow()
                    }
                }
                current_app.config['DB_SERVICE'].update_dr("room", data['room_id'], update_data)

        except json.JSONDecodeError:
            logger.error(f"Invalid JSON payload: {msg.payload}")
        except Exception as e:
            logger.error(f"Error processing message: {e}")

    @property
    def is_connected(self):
        """Check if client is currently connected"""
        return self.connected
    
    