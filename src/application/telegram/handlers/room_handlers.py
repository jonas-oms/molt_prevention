from telegram import Update
from telegram.ext import ContextTypes, CommandHandler
from datetime import datetime
import re
from flask import current_app
from src.application.telegram.handlers.login_handlers import (
    check_auth,
    logged_users,
)

async def humidity_alert_handler(update: Update, context: ContextTypes.DEFAULT_TYPE, humidity: float, room_id: str):
    """Handler to inform the user when the humidity is above 60"""
    room = current_app.config["DB_SERVICE"].get_dr("room", room_id)
    for user in room['data']['users']:
        if user in logged_users:
            if update.effective_user.id == user:
                await update.message.reply_text(f"Alert! The humidity is above 60: {humidity}%")

async def list_rooms(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler to list all the rooms assigned to the user"""
    user_id = context.user_data["user_id"]
    user = current_app.config["DB_SERVICE"].get_dr("user", user_id)
    if not user:
        await update.message.reply_text("User not found")
        return
    assigned_rooms = user["data"]["assigned_rooms"]
    if not assigned_rooms:
        await update.message.reply_text("No rooms assigned to the user")
        return
    room_list = []
    for room_id in assigned_rooms:
        room = current_app.config["DB_SERVICE"].get_dr("room", room_id)
        if room:
            room_list.append(room["profile"]["name"])
    await update.message.reply_text(f"Rooms assigned to user: {', '.join(room_list)}")
    