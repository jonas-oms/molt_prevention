from typing import Dict, Any
from src.services.base import BaseService
from datetime import datetime
from flask import current_app


class HumidityComparisonService(BaseService):
    """Service to compare absolute humidity between a room and a house"""

    def __init__(self):
        self.name = "HumidityComparisonService"

    def execute(self, data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """
        Execute the service to compare absolute humidity between a room and a house.

        Args:
            data: Dictionary containing digital replicas data
            kwargs: Must include 'room_id' and 'house_id' to analyze

        Returns:
            Dict containing the comparison result
        """
        room_id = kwargs.get('room_id')
        house_id = kwargs.get('house_id')
        if not room_id or not house_id:
            raise ValueError("room_id and house_id are required")

        # Get the room from digital replicas
        room = current_app.config["DB_SERVICE"].get_dr("room", room_id)

        # Get House from dt_factory
        house = current_app.config["DT_FACTORY"].get_dt(house_id)


        if not room:
            raise ValueError(f"Room {room_id} not found")
        if not house:
            raise ValueError(f"House {house_id} not found")

        # Validate that both room and house have absolute humidity data
        if 'absolute_humidity' not in room['data']:
            raise ValueError("Room does not have absolute humidity data")
        if 'absolute_humidity' not in house:
            raise ValueError("House does not have absolute humidity data")

        room_ah = room['data']['absolute_humidity']
        house_ah = house['absolute_humidity']

        # Calculate the difference
        ah_difference = room_ah - house_ah

        return {
            'room_id': room_id,
            'house_id': house_id,
            'room_absolute_humidity': room_ah,
            'house_absolute_humidity': house_ah,
            'absolute_humidity_difference': ah_difference,
            'timestamp': datetime.utcnow().isoformat()
        }