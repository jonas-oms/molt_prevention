from flask import current_app
import paho.mqtt.client as mqtt
from datetime import datetime
import json
import logging
import time
from threading import Thread, Event
from paho import mqtt as paho
import math
from src.services.comparing_humidity import HumidityComparisonService

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
                # Check if data contains room_id or house_id
                if 'room_id' in data:
                    dt = current_app.config["DB_SERVICE"].get_dr("room",data['room_id'])
                    type = "room"	
                elif 'house_id' in data:
                    dt = current_app.config["DB_SERVICE"].get_dr("house",data['house_id'])
                    type = "house"
                else:
                    logger.error("Room or house id not found in data")
                    return
                if not dt:
                    logger.error(f"Room not found: {data['room_id']}")
                    return
                absolute_humidity = self.calculate_ah(data['temperature'], data['humidity'])
                #initilize fields if they do not exist
                if 'data' not in dt:
                    dt['data'] = {}
                if 'measurements' not in dt['data']:
                    dt['data']['measurements'] = []
                #We need to register the measurement
                measurement = {
                    "temperature": data['temperature'],
                    "humidity": data['humidity'],
                    "timestamp": datetime.utcnow()
                }
                update_data = {
                    "data": {
                        "measurements": dt['data']['measurements'] + [measurement],
                        "temperature": data['temperature'],
                        "humidity": data['humidity'],
                        "absolute_humidity": absolute_humidity
                    },
                    "metadata": {
                        "updated_at": datetime.utcnow()
                    }
                }
                if type == "room":
                    current_app.config['DB_SERVICE'].update_dr("room", data['room_id'], update_data)	
                elif type == "house":
                    current_app.config['DB_SERVICE'].update_dr("house", data['house_id'], update_data)

                if type == "room":
                    # Execute the HumidityComparisonService
                    self.humidity_comparison_service.execute(data, room_id=data['room_id'], house_id=dt['data']['house_id'])

        except json.JSONDecodeError:
            logger.error(f"Invalid JSON payload: {msg.payload}")
        except Exception as e:
            logger.error(f"Error processing message: {e}")

    def calculate_ah(self, temperature, relative_humidity):
        """
        Calculates the absolute humidity (AH) in g/m³.

        :param temperature: Temperature in degrees Celsius (°C)
        :param relative_humidity: Relative humidity in percentage (%)
        :return: Absolute humidity (AH) in g/m³
        """
        # Constants
        A = 6.11
        B = 17.67
        C = 243.5
        D = 2.1674

        # Saturation vapor pressure (in hPa)
        saturation_vapor_pressure = A * math.exp((B * temperature) / (C + temperature))

        # Actual vapor pressure (in hPa)
        actual_vapor_pressure = saturation_vapor_pressure * (relative_humidity / 100.0)

        # Absolute humidity (in g/m³)
        absolute_humidity = (D * actual_vapor_pressure) / (273.15 + temperature)

        return absolute_humidity

    @property
    def is_connected(self):
        """Check if client is currently connected"""
        return self.connected
    

    
    