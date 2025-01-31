from typing import Dict, List, Optional
from datetime import datetime
from src.services.base import BaseService
from src.application.telegram.handlers.login_handlers import logged_users
from src.application.telegram.config.settings import (TELEGRAM_TOKEN)
import asyncio
import requests


class UserNotificationService(BaseService):
    """Service to predict the best room for a bottle based on temperature requirements"""

    def __init__(self):
        self.name = "NotifyUserService"

    def execute(self, data: Dict, **kwargs) -> None:
        """
        Notify the user if the data are out of bounds

        Args:
            data: Dictionary containing room_id, user_id and text
            kwargs: 
        """

        room_id = data['room_id']
        if not room_id:
            raise ValueError("room_id is required")
        
        # check if user is connected in telegram otherwise do nothing
        if data["user_id"] not in logged_users.values():
            return

        # get the telegram user from a reverse dict search by values
        telegram_user_id = list(logged_users.keys())[list(logged_users.values()).index(data["user_id"])]

        asyncio.run(telegram_message(telegram_user_id, text=data["text"]))

        return


async def telegram_message(chat_id, text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    print(f"sending message: {payload}")
    requests.post(url, json=payload)