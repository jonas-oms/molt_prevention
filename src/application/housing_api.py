from flask import Blueprint, request, jsonify, current_app
from datetime import datetime
from src.virtualization.digital_replica.dr_factory import DRFactory
from bson import ObjectId

house_api = Blueprint('house_api', __name__,url_prefix = '/api/house')

def register_housing_blueprint(app):
    app.register_blueprint(house_api)


@house_api.route("/",methods=['POST'])
def create_house():
    try:
        data = request.get_json()
        if not all(k in data for k in ["name", "longitude", "latitude"]):
            return jsonify({"error": "Missing name, longitute or latitude"}), 400
        house_id = current_app.config["HOUSE_FACTORY"].create_dt(
            name=data['name'],
            longitude=float(data['longitude']),
            latitude=float(data['latitude'])
        )
        current_app.config["HOUSE_FACTORY"].add_service(house_id, "FetchWeatherService")
        return jsonify({"status":"success","message":"House created successfully","house_id":house_id}), 201
    except Exception as e:
        return jsonify({"error":str(e)}),500
    
@house_api.route("/<house_id>", methods=['GET'])
def get_house(house_id):
    "Get house details"
    try:
        house = current_app.config["DT_FACTORY"].get_dt(house_id)
        if not house:
            return jsonify({"error":"House not found"}), 404
        return jsonify(house), 200
    except Exception as e:
        return jsonify({"error":str(e)}),500

@house_api.route("/",methods=['GET'])
def list_houses():
    "Get all houses"
    try:
        houses = current_app.config["DT_FACTORY"].list_dts()
        return jsonify({"houses":houses}), 200
    except Exception as e:
        return jsonify({"error":str(e)}),500

@house_api.route("/<house_id>/rooms", methods=['POST'])
def create_room(house_id):
    try:
        data = request.get_json()
        dr_factory = DRFactory("src/virtualization/templates/room.yaml")
        room = dr_factory.create_dr('room', data)
        # Save to database
        room_id = current_app.config["DB_SERVICE"].save_dr("room", room)
        if not room:
            return jsonify({"error": "Room not found"}), 404
        
        #Add the room to the house dt
        house = current_app.config["DT_FACTORY"].get_dt(house_id)
        if not house:
            return jsonify({"error":"House not found"}), 404
        current_app.config["DT_FACTORY"].add_room(house_id, "room", room_id)

        # Add the house id to the room data
        room['house_id'] = house_id
        room_update = {
            "house_id": house_id,
            "metadata": {"updated_at": datetime.utcnow()}
        }
        current_app.config['DB_SERVICE'].update_dr("room", room_id, room_update)

        return jsonify({"status": "success", "message": "Room created successfully", "room_id": room_id}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@house_api.route("/<house_id>/rooms/<room_id>", methods=['GET'])
def get_room(room_id):
    """Get room details"""
    try:
        room = current_app.config["DB_SERVICE"].get_dr("room",room_id)
        if not room:
            return jsonify({"error":"Room not found"}), 404
        return jsonify(room),200
    except Exception as e:
        return jsonify({"error":str(e)}),500

@house_api.route("/<house_id>/rooms/<room_id>", methods=['PUT'])
def update_room(room_id):
    """Update room details"""
    try:
        data = request.get_json()
        update_data = {}

        #Handle profile updates
        if "profile" in data:
            update_data["profile"] = data["profile"]
        #Handle data updates
        if "data" in data:
            update_data["data"] = data["data"]

        #Always update the 'updated at' timestamp
        update_data["metadata"] = {"updated_at":datetime.utcnow()}

        current_app.config["DB_SERVICE"].update_dr("room",room_id,update_data)
        return jsonify({"status":"success","message":"Room updated successfully"}), 200
    except Exception as e:
        return jsonify({"error":str(e)}),500
    
@house_api.route("/<house_id>/rooms/<room_id>", methods=['DELETE'])
def delete_room(room_id,house_id):
    """Delete a room"""
    try:
        room = current_app.config["DB_SERVICE"].get_dr("room",room_id)
        if not room:
            return jsonify({"error":"Room not found"}), 404
        current_app.config["DB_SERVICE"].delete_dr("room",room_id)
        # delete room_id in house->data->rooms
        current_app.config["DT_FACTORY"].remove_room(house_id, room_id)
                
        return jsonify({"status":"success","message":"Room deleted successfully"}), 200
    except Exception as e:
        return jsonify({"error":str(e)}),500
    #TODO room needs to be removed from user-->data-->assigned rooms

@house_api.route("/<house_id>/rooms", methods=['GET'])
def list_rooms(house_id):
    """List all rooms with optional filtering"""
    try:
        filters = {}
        if request.args.get('status'):
            filters["data.status"] = request.args.get('status')
        if request.args.get('floor'):
            filters["profile.floor"] = int(request.args.get('floor'))
        room = current_app.config["DB_SERVICE"].query_drs("room",filters)
        return jsonify({"rooms":room}), 200
    except Exception as e:
        return jsonify({"error":str(e)}),500

@house_api.route("/<room_id>/measurements", methods=['POST'])
def add_room_measurements(room_id):
    """
    Add a new measurement to a room
    Expected JSON-Body:
    {
        'measure_type': "temperature"       # or "humidity"
        'value': "25"                       # Temperature: °C, Humidity: %
    }
    
    """
    try:
        data = request.get_json()
        if not data.get('measure_type') or 'value' not in data:
            return jsonify({"error":"Missing required measurement fields"}), 400
        #get current room data
        room = current_app.config["DB_SERVICE"].get_dr("room",room_id)
        if not room:
            return jsonify({"error":"Room not found"}), 404
        #initilize fields if they do not exist
        if 'data' not in room:
            room['data'] = {}
        if 'measurements' not in room['data']:
            room['data']['measurements'] = {}
        #We need to register the measurement
        measurement = {
            "measure_type": data['measure_type'],
            "value": data['value'],
            "timestamp": datetime.utcnow()
        }
        update_data = {
            "data": {
                "measurements": room['data']['measurements'] + [measurement],
            },
            "metadata": {
                "updated_at": datetime.utcnow()
            }
        }

        if data['measure_type'] == 'temperature':
            room['data']['temperature'] = data['value']
            update_data['data']['temperature'] = data['value']
        elif data['measure_type'] == 'humidity':
            room['data']['humidity'] = data['value']
            update_data['data']['humidity'] = data['value']
        else:
            return jsonify({"error":"Wrong measure_type. Use 'temperature' or 'humidity"}), 404

        current_app.config['DB_SERVICE'].update_dr("room", room_id, update_data)
        return jsonify({
            "status": "success",
            "message": "Measurement processed successfully"
        }), 200
    except Exception as e:
        return jsonify({"error":str(e)}),500


