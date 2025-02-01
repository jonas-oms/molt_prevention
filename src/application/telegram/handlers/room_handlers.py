from telegram import Update
from telegram.ext import ContextTypes, CommandHandler
from datetime import datetime
import re
from flask import current_app
from src.application.telegram.handlers.login_handlers import (
    check_auth,
    logged_users,
)

async def list_rooms(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler to list all the rooms assigned to the user"""
    telegram_id = update.effective_user.id
    user_id = logged_users[telegram_id]
    user = current_app.config["DB_SERVICE"].get_dr("user", user_id)
    if not user:
        await update.message.reply_text("User not found")
        return
    assigned_rooms = user["data"]["assigned_rooms"]
    if not assigned_rooms:
        await update.message.reply_text("No rooms assigned to the user")
        return
    room_list_str = "\n".join([f"- {room_id}" for room_id in assigned_rooms])
    await update.message.reply_text(f"Rooms assigned to user:\n{room_list_str}")

async def get_room_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler to get the status of a room"""
    telegram_id = update.effective_user.id
    user_id = logged_users[telegram_id]
    user = current_app.config["DB_SERVICE"].get_dr("user", user_id)
    if not user:
        await update.message.reply_text("User not found")
        return
    assigned_rooms = user["data"]["assigned_rooms"]
    if not assigned_rooms:
        await update.message.reply_text("No rooms assigned to the user")
        return
    for room_id in assigned_rooms:
        room = current_app.config["DB_SERVICE"].get_dr("room", room_id)
        if room:
            await update.message.reply_text(f"Room {room_id}")
            await update.message.reply_text(f"Name: {room['profile']['name']}, Floor: {room['profile']['floor']}, Room number: {room['profile']['room_number']}")
            if room['data']['temperature'] is None or room['data']['humidity'] is None:
                await update.message.reply_text("Temperature and humidity data not available")
                continue
            else:
                await update.message.reply_text(f"Temperature: {room['data']['temperature']}")
                await update.message.reply_text(f"Humidity: {room['data']['humidity']}")
                await update.message.reply_text(f"Last updated: {room['metadata']['updated_at']}")
