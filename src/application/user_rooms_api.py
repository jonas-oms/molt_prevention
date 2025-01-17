from flask import Blueprint, request, jsonify, current_app
from datetime import datetime
from src.virtualization.digital_replica.dr_factory import DRFactory

user_api = Blueprint("user_api", __name__, url_prefix="/api/user")


def register_user_blueprint(app):
    app.register_blueprint(user_api)


@user_api.route("/register", methods=["POST"])
def register_user():
    """Register a new user"""
    try:
        data = request.get_json()
        if not all(k in data for k in ["username", "password"]):
            return jsonify({"error": "Missing username or password"}), 400

        # Check if the user exists
        existing = current_app.config["DB_SERVICE"].query_drs(
            "user", {"profile.username": data["username"]}
        )
        if existing:
            return jsonify({"error": "Username already exists"}), 400

        initial_data = {
            "profile": {
                "username": data["username"],
                "password": data["password"],  # In produzione usa hash!
            },
            "metadata": {"status": "active"},
            "data": {"assigned_rooms": []},
        }

        # create a new dr user
        dr_factory = DRFactory("src/virtualization/templates/user.yaml")
        user = dr_factory.create_dr("user", initial_data)

        # Salva nel database
        user_id = current_app.config["DB_SERVICE"].save_dr("user", user)

        return (
            jsonify(
                {
                    "status": "success",
                    "message": "User registered successfully",
                    "user_id": user_id,
                }
            ),
            201,
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@user_api.route("/<user_id>/assign/<room_id>", methods=["POST"])
def assign_user(user_id, room_id):
    """Assign a Room to a user"""
    try:
        # Check if the user exists
        user = current_app.config["DB_SERVICE"].get_dr("user", user_id)
        if not user:
            return jsonify({"error": "User not found"}), 404

        # Check if the room exists
        room = current_app.config["DB_SERVICE"].get_dr("room", room_id)
        if not room:
            return jsonify({"error": "Room not found"}), 404

        # Assign the Room to the user, if it's not present
        assigned_rooms = user["data"]["assigned_rooms"]
        if room_id not in assigned_rooms:
            assigned_rooms.append(room_id)

            # Aggiorna i dati dell'utente
            current_app.config["DB_SERVICE"].update_dr(
                "user",
                user_id,
                {
                    "data": {"assigned_rooms": assigned_rooms},
                    "metadata": {"updated_at": datetime.utcnow()},
                },
            )

        return (
            jsonify(
                {
                    "status": "success",
                    "message": "Rooms assigned to user",
                    "assigned_rooms": assigned_rooms,
                }
            ),
            200,
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500
