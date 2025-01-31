from typing import Dict, Any
from src.services.base import BaseService
from datetime import datetime
from flask import current_app

# open-meteo imports
import openmeteo_requests
import requests_cache
import pandas as pd
from retry_requests import retry

class FetchWeatherService(BaseService):
    """Service to fetch weather data from a weather API"""

    def __init__(self):
        self.name = "FetchWeatherService"

        # Setup the Open-Meteo API client with cache and retry on error
        self.cache_session = requests_cache.CachedSession('.cache', expire_after = 3600)
        self.retry_session = retry(self.cache_session, retries = 5, backoff_factor = 0.2)
        self.openmeteo = openmeteo_requests.Client(session = self.retry_session)

        self.url = "https://api.open-meteo.com/v1/forecast"

    def execute(self, data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """
        Execute the service to fetch weather data from a weather API.

        Args:
            data: Dictionary containing digital replicas data
            kwargs: Must include 'longitude' and 'latitude' to fetch weather data

        Returns:
            Dict containing the weather data
        """

        # Fetch weather data from the weather API
        longitude = kwargs.get('longitude')
        latitude = kwargs.get('latitude')
        weather_data = self.fetch_weather(longitude, latitude)
        return weather_data

    def fetch_weather(self, longitude, latitude) -> Dict[str, Any]:
        """
        Fetch weather data from a weather API.

        Args:
            city: The city to fetch weather data for

        Returns:
            Dict containing the weather data
        """
        # Call the weather API here
        params = {
            "latitude": longitude,
            "longitude": latitude,
            "current": ["temperature_2m", "relative_humidity_2m", "rain"]
        }
        responses = self.openmeteo.weather_api(self.url, params=params)

        # Process first location. Add a for-loop for multiple locations or weather models
        response = responses[0]
        print(f"Coordinates {response.Latitude()}°N {response.Longitude()}°E")
        print(f"Elevation {response.Elevation()} m asl")
        print(f"Timezone {response.Timezone()} {response.TimezoneAbbreviation()}")
        print(f"Timezone difference to GMT+0 {response.UtcOffsetSeconds()} s")


        # Current values. The order of variables needs to be the same as requested.
        current = response.Current()

        current_temperature_2m = current.Variables(0).Value()

        current_relative_humidity_2m = current.Variables(1).Value()

        current_rain = current.Variables(2).Value()

        print(f"Current time {current.Time()}")

        print(f"Current temperature_2m {current_temperature_2m}")
        print(f"Current relative_humidity_2m {current_relative_humidity_2m}")
        print(f"Current rain {current_rain}")



        data = {
            "temperature": current_temperature_2m,
            "humidity": current_relative_humidity_2m,
        }

        return data

    