from typing import Dict, List, Type, Any
from src.services.base import BaseService
from datetime import datetime
from src.digital_twin.core import DigitalTwin
import math

class HouseTwin(DigitalTwin):
    def __init__(self):
        super().__init__()
        self.name = "HouseTwin"
        self.digital_replicas = []
        self.active_services = {}

    def add_longitude(self, longitude: float):
        self.longitude = longitude

    def add_latitude(self, latitude: float):
        self.latitude = latitude
    
    def add_temperature(self, temperature: float):
        self.temperature = temperature

    def add_relative_humidity(self, relative_humidity: float):
        self.relative_humidity = relative_humidity

    def calculate_absolute_humidity(self):
        relative_humidity = self.relative_humidity
        temperature = self.temperature

        # Calculate absolute humidity
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

        self.absolute_humidity = absolute_humidity
    
    def add_rooms(self, rooms: List):
        self.rooms = rooms