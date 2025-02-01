from telegram import Update
from telegram.ext import ContextTypes, CommandHandler
from datetime import datetime
import re
from flask import current_app
from src.application.telegram.handlers.login_handlers import (
    check_auth,
    logged_users,
)


async def ventilation_on_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /ON command"""
    try:
        # Check if user is authenticated
        telegram_id = update.effective_user.id
        if not check_auth(telegram_id):
            await update.message.reply_text(
                "Please login first using /login username password"
            )
            return

        # Extract LED ID from command
        message = update.message.text.strip()
        command_pattern = r"/ON\s+([^\s]+)"  # Pattern for ON command
        match = re.match(command_pattern, message)

        if not match:
            await update.message.reply_text(
                "Invalid format! Use: /ON <device_id>\n"
                "Example: /ON 47a0c269-5f20-4209-97ea-d360f347941c"
            )
            return

        ventilation_id = match.group(1)

        # Verify ownership
        db_service = current_app.config["DB_SERVICE"]
        user = db_service.get_dr("user", logged_users[telegram_id])

        devices_list = []
        for room_id in user["data"]["assigned_rooms"]:
            room = db_service.get_dr("room", room_id)
            if "devices" in room["data"]:
                devices_list.extend(room["data"]["devices"])

        if ventilation_id not in devices_list:
            await update.message.reply_text("You don't own this Device!")
            return

        # Get status
        ventilation = db_service.get_dr("ventilation", ventilation_id)
        if not ventilation:
            await update.message.reply_text("Ventilation Device not found!")
            return

        # Update LED state
        current_time = datetime.utcnow()
        update_data = {
            "data": {
                "state": "on",
                "controlled_by": f"telegram_{telegram_id}",
                "measurements": ventilation["data"]["measurements"]
                + [{"type": "state_change", "value": 1.0, "timestamp": current_time}],
            },
            "metadata": {"updated_at": current_time, "last_state_change": current_time},
        }

        db_service.update_dr("ventilation", ventilation_id, update_data)
        if current_app.mqtt_ventilation_handler.is_connected:
            current_app.mqtt_ventilation_handler.publish_ventilation_state(ventilation_id, "on")
            await update.message.reply_text(f"Device {ventilation_id} turned ON!")

    except Exception as e:
        await update.message.reply_text(f"Error: {str(e)}")
        print(f"Ventilation ON error: {str(e)}")

async def ventilation_off_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /OFF command"""
    try:
        # Check if user is authenticated
        telegram_id = update.effective_user.id
        if not check_auth(telegram_id):
            await update.message.reply_text(
                "Please login first using /login username password"
            )
            return

        # Extract Device ID from command
        message = update.message.text.strip()
        command_pattern = r"/OFF\s+([^\s]+)"  # Pattern for OFF command
        match = re.match(command_pattern, message)

        if not match:
            await update.message.reply_text(
                "Invalid format! Use: /OFF <ventilation_id>\n"
                "Example: /OFF 47a0c269-5f20-4209-97ea-d360f347941c"
            )
            return

        ventilation_id = match.group(1)

        # Verify ownership
        db_service = current_app.config["DB_SERVICE"]
        user = db_service.get_dr("user", logged_users[telegram_id])

        devices_list = []
        for room_id in user["data"]["assigned_rooms"]:
            room = db_service.get_dr("room", room_id)
            if "devices" in room["data"]:
                devices_list.extend(room["data"]["devices"])

        if ventilation_id not in devices_list:
            await update.message.reply_text("You don't own this Device!")
            return

        # Get status
        ventilation = db_service.get_dr("ventilation", ventilation_id)
        if not ventilation:
            await update.message.reply_text("Ventilation Device not found!")
            return

        # Update LED state
        current_time = datetime.utcnow()
        update_data = {
            "data": {
                "state": "off",
                "controlled_by": f"telegram_{telegram_id}",
                "measurements": ventilation["data"]["measurements"]
                + [{"type": "state_change", "value": 0.0, "timestamp": current_time}],
            },
            "metadata": {"updated_at": current_time, "last_state_change": current_time},
        }

        db_service.update_dr("ventilation", ventilation_id, update_data)
        if current_app.mqtt_ventilation_handler.is_connected:
            current_app.mqtt_ventilation_handler.publish_ventilation_state(ventilation_id, "off")
            await update.message.reply_text(f"Device {ventilation_id} turned ON!")

    except Exception as e:
        await update.message.reply_text(f"Error: {str(e)}")
        print(f"LED OFF error: {str(e)}")
