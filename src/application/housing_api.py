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
        dr_factory = DRFactory("src/virtualization/templates/house.yaml")
        house = dr_factory.create_dr('house',data)
        house_id = current_app.config["DB_SERVICE"].save_dr("house",house)
        return jsonify({"status":"success","message":"Bottle created successfully","bottle_id":house_id}), 201
    except Exception as e:
        return jsonify({"error":str(e)}),500
    
@house_api.route("/<house_id>", methods=['GET'])
def get_house(house_id):
    "Get house details"
    try:
        house = current_app.config["DB_SERVICE"].get_dr("house",house_id)
        if not house:
            return jsonify({"error":"House not found"}), 404
        return jsonify(house), 200
    except Exception as e:
        return jsonify({"error":str(e)}),500

@house_api.route("/",methods=['GET'])
def list_houses():
    "Get all houses with optional filtering"
    try:
        filters = {}
        if request.args.get('status'):
            filters["metadata.status"] = request.args.get('status')
        houses = current_app.config["DB_SERVICE"].query_drs("house",filters)
        return jsonify({"houses":houses}), 200
    except Exception as e:
        return jsonify({"error":str(e)}),500

@house_api.route("/<house_id>/rooms", methods=['POST'])
def create_room(house_id):
    try:
        data = request.get_json()
        dr_factory = DRFactory("src/virtualization/templates/room.yaml")
        room = dr_factory.create_dr('room',data)
        #Save to database
        room_id = current_app.config["DB_SERVICE"].save_dr("room",room)
        # Add the room to the house
        house = current_app.config["DB_SERVICE"].get_dr("house",house_id)
        if not room:
            return jsonify({"error":"Room not found"}), 404
        if room_id not in house['data']['rooms']:
            room['data']['rooms'].append(room_id)
        return jsonify({"status":"success","message":"Room created successfully","room_id":room_id}), 201
    except Exception as e:
        return jsonify({"error":str(e)}),500

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
        house = current_app["DB_SERVICE"].get_dr("room",house_id)
        if house and 'data' in house and 'rooms' in house['data']:
            if room_id in house['data']['bottles']:
                house['data']['rooms'].remove(room_id)
                house_update = {
                    "data": {"rooms": house['data']['rooms']},
                    "metadata": {"updated_at": datetime.utcnow()}
                }
                current_app.config['DB_SERVICE'].update_dr("room", house_id, house_update)
                
        return jsonify({"status":"success","message":"Room deleted successfully"}), 200
    except Exception as e:
        return jsonify({"error":str(e)}),500

@house_api.route("/<house_id>/rooms", methods=['GET'])
def list_rooms():
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

@house_api.route("/<house_id>/rooms/<room_id>/measurements", methods=['POST'])
def add_room_measurements(room_id):
    """Add a new measurement to a room"""
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
        if 'bottles' not in room['data']:
            room['data']['bottles'] = []
        # if the measure type is RFID
        if data['measure_type'] == 'rfid':
            rfid_tag=data['value']
            #Find the bottle with this RFID tag
            bottles = current_app.config["DB_SERVICE"].query_drs("bottle",{'profile.rfid_tag':rfid_tag})
            bottle = bottles[0] #take the first - TODO add a bottle check for univocity
            bottle_id = bottle['_id']
            old_room_id = bottle['data'].get('room_id') if 'data' in bottle else None
            # if the bottle was in another room, remove it from there
            if old_room_id and old_room_id != room_id:
                old_room = current_app["DB_SERVICE"].get_dr("room",old_room_id)
                if old_room and 'data' in old_room and 'bottles' in old_room['data']:
                    if bottle_id in old_room['data']['bottles']:
                        old_room['data']['bottles'].remove(bottle_id)
                        old_room_update = {
                            "data": {"bottles": old_room['data']['bottles']},
                            "metadata": {"updated_at": datetime.utcnow()}
                        }
                        current_app.config['DB_SERVICE'].update_dr("room", old_room_id, old_room_update)
            # Update the bottle with the new room
            bottle_update = {
                "data": {"room_id": room_id},
                "metadata": {"updated_at": datetime.utcnow()}
            }
            current_app.config['DB_SERVICE'].update_dr("bottle", bottle_id, bottle_update)
            # Add the bottle at new room
            if bottle_id not in room['data']['bottles']:
                room['data']['bottles'].append(bottle_id)
        #We need to register the measurement
        measurement = {
            "measure_type": data['measure_type'],
            "value": data['value'],
            "timestamp": datetime.utcnow()
        }

        update_data = {
            "data": {
                "measurements": room['data']['measurements'] + [measurement],
                "bottles": room['data']['bottles']  # Include sempre la lista bottles aggiornata
            },
            "metadata": {
                "updated_at": datetime.utcnow()
            }
        }
        current_app.config['DB_SERVICE'].update_dr("room", room_id, update_data)
        return jsonify({
            "status": "success",
            "message": "Measurement processed successfully"
        }), 200
    except Exception as e:
        return jsonify({"error":str(e)}),500


@house_api.route('/temperature-prediction/<dt_id>', methods=['POST'])
def predict_bottle_temperature(dt_id):
    """
    Predict optimal room temperature for a bottle within a Digital Twin

    Expected JSON body:
    {
        "bottle_id": "string"  # ID of the bottle to analyze
    }
    """
    try:
        data = request.get_json()
        if not data or 'bottle_id' not in data:
            return jsonify({'error': 'bottle_id is required in request body'}), 400

        # Get DT instance
        dt = current_app.config['DT_FACTORY'].get_dt_instance(dt_id)
        if not dt:
            return jsonify({'error': 'Digital Twin not found'}), 404

        # Execute temperature prediction service
        try:
            prediction = dt.execute_service(
                'TemperaturePredictionService',
                bottle_id=data['bottle_id']
            )
            return jsonify(prediction), 200
        except ValueError as ve:
            return jsonify({'error': str(ve)}), 400
        except Exception as e:
            return jsonify({'error': f'Service execution failed: {str(e)}'}), 500

    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
