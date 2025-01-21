import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

#MQTT Configuration
MQTT_USERNAME = os.getenv("MQTT_USERNAME")
if not MQTT_USERNAME:
    raise ValueError("MQTT_USERNAME not found in .env file")

MQTT_PASSWORD = os.getenv("MQTT_PASSWORD")
if not MQTT_PASSWORD:
    raise ValueError("MQTT_PASSWORD not found in .env file")

MQTT_BROKER_URL = os.getenv("MQTT_BROKER_URL")
if not MQTT_BROKER_URL:
    raise ValueError("MQTT_BROKER_URL not found in .env file")


