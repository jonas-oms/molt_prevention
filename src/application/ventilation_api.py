from flask import Blueprint, request, jsonify, current_app
from datetime import datetime
import json
from src.virtualization.digital_replica.dr_factory import DRFactory

ventilation_api = Blueprint("ventilation_api", __name__, url_prefix="/api/ventilation")


def register_led_blueprint(app):
    """Register LED API blueprint with Flask app"""
    app.register_blueprint(ventilation_api)


@ventilation_api.route("/", methods=["POST"])
def create_device():
    """Create a new Ventilation Digital Replica"""
    try:
        data = request.get_json()
        required_fields = ["name", "room_id"]
        if not all(field in data for field in required_fields):
            return jsonify({"error": "Missing required fields"}), 400

        initial_data = {
            "profile": {
                "name": data["name"],
                "room_id": data["room_id"],
                "description": data.get("description", ""),
            },
            "metadata": {"status": "active", "last_state_change": datetime.utcnow()},
            "data": {
                "state": "off",
                "brightness": 0,
                "controlled_by": "system",
            },
        }

        # Use DRFactory to create LED
        dr_factory = DRFactory("src/virtualization/templates/ventilation.yaml")
        ventilation = dr_factory.create_dr("ventilation", initial_data)

        # Save to database
        ventilation_id = current_app.config["DB_SERVICE"].save_dr("ventilation", ventilation)
        return (
            jsonify(
                {
                    "status": "success",
                    "message": "Ventilation created successfully",
                    "ventilation_id": ventilation_id,
                }
            ),
            201,
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@ventilation_api.route("/<ventilation_id>", methods=["GET"])
def get_led(ventilation_id):
    """Get Ventilation details"""
    try:
        ventilation = current_app.config["DB_SERVICE"].get_dr("ventilation", ventilation_id)
        if not ventilation:
            return jsonify({"error": "Ventilation not found"}), 404
        return jsonify(ventilation), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@ventilation_api.route("/", methods=["GET"])
def list_leds():
    """List all Ventilation Devices with optional filtering"""
    try:
        filters = {}
        if request.args.get("status"):
            filters["metadata.status"] = request.args.get("status")
        if request.args.get("state"):
            filters["data.state"] = request.args.get("state")

        devices = current_app.config["DB_SERVICE"].query_drs("ventilation", filters)
        return jsonify({"devices": devices}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@ventilation_api.route("/<ventilation_id>/toggle", methods=["POST"])
def toggle_led(ventilation_id):
    """Toggle Ventilation state between on and off"""
    try:
        # Get current LED state
        ventilation = current_app.config["DB_SERVICE"].get_dr("ventilation", ventilation_id)
        if not ventilation:
            return jsonify({"error": "Ventilation not found"}), 404

        # Get controller information
        data = request.get_json() or {}
        controlled_by = data.get("controlled_by", "api")

        # Toggle state
        new_state = "off" if ventilation["data"]["state"] == "on" else "on"

        # Create measurement for state change
        measurement = {
            "type": "state_change",
            "value": 1.0 if new_state == "on" else 0.0,
            "timestamp": datetime.utcnow(),
        }

        # Update Ventilation data
        update_data = {
            "data": {
                "state": new_state,
                "controlled_by": controlled_by,
                "measurements": ventilation["data"]["measurements"] + [measurement],
            },
            "metadata": {
                "updated_at": datetime.utcnow(),
                "last_state_change": datetime.utcnow(),
            },
        }

        # Update in database
        current_app.config["DB_SERVICE"].update_dr("ventilation", ventilation_id, update_data)

        # Publish state change to MQTT if handler exists
        if (
            hasattr(current_app, "mqtt_handler")
            and current_app.mqtt_handler.is_connected
        ):
            topic = f"ventilation/{ventilation_id}/state"
            payload = {"state": new_state, "timestamp": datetime.utcnow().isoformat()}
            current_app.mqtt_handler.client.publish(topic, json.dumps(payload))

        return (
            jsonify(
                {
                    "status": "success",
                    "message": f"Ventilation state changed to {new_state}",
                    "current_state": new_state,
                }
            ),
            200,
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500
