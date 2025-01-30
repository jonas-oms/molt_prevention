from src.digital_twin.dt_factory import DTFactory
from typing import Dict, List, Optional
from datetime import datetime
from bson import ObjectId
from src.services.database_service import DatabaseService
from src.virtualization.digital_replica.schema_registry import SchemaRegistry
from src.digital_twin.core import DigitalTwin

class HouseFactory(DTFactory):
    def __init__(self, db_service: DatabaseService, schema_registry: SchemaRegistry):
        super().__init__(db_service, schema_registry)
        self.name = "HouseFactory"

    def create_dt(self, name: str, longitude: float, latitude: float, description: str = "") -> str:
        """
        Create a new Digital Twin

        Args:
            name: Name of the Digital Twin
            longitude: Position
            latitude: Position
            description: Optional description

        Returns:
            str: ID of the created Digital Twin
        """
        dt_data = {
            "_id": str(ObjectId()),
            "name": name,
            "description": description,
            "digital_replicas": [],  # List of DR references
            "services": [],  # List of service references
            "rooms": [],  # List of room references
            "longitude": longitude,
            "latitude": latitude,
            "temperature": None,
            "relative_humidity": None,
            "absolute_humdity:": None, 
            "metadata": {
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
                "status": "active",
            },
        }

        try:
            dt_collection = self.db_service.db["digital_twins"]
            result = dt_collection.insert_one(dt_data)
            return str(result.inserted_id)
        except Exception as e:
            raise Exception(f"Failed to create Digital Twin: {str(e)}")

    def _get_service_module_mapping(self) -> Dict[str, str]:
        """
        Returns a mapping of service names to their module paths
        """
        return {
            "FetchWeatherService": "src.services.fetch_weather",
        }

    def add_room(self, dt_id: str, dr_type: str, dr_id: str) -> None:
        """
        Add a Room reference to a Digital Twin

        Args:
            dt_id: Digital Twin ID
            dr_type: Type of Digital Replica
            dr_id: Digital Replica ID
        """
        try:
            dt_collection = self.db_service.db["digital_twins"]

            # Verify DR exists
            dr = self.db_service.get_dr(dr_type, dr_id)
            if not dr:
                raise ValueError(f"Digital Replica not found: {dr_id}")

            # Add DR reference
            dt_collection.update_one(
                {"_id": dt_id},
                {
                    "$push": {"rooms": {"type": dr_type, "id": dr_id}},
                    "$set": {"metadata.updated_at": datetime.utcnow()},
                },
            )
        except Exception as e:
            raise Exception(f"Failed to add Room: {str(e)}")
        
    def remove_room(self, dt_id: str, dr_id: str) -> None:
        """
        Remove a Room reference from a Digital Twin

        Args:
            dt_id: Digital Twin ID
            dr_id: Room ID
        """
        try:
            dt_collection = self.db_service.db["digital_twins"]

            dt_collection.update_one(
                {"_id": dt_id},
                {
                    "$pull": {
                        "rooms": {
                            "id": dr_id
                        }
                    },
                    "$set": {
                        "metadata.updated_at": datetime.utcnow()
                    }
                }
            )
        except Exception as e:
            raise Exception(f"Failed to remove Room: {str(e)}")

    def create_dt_from_data(self, dt_data: dict) -> DigitalTwin:
        """
        Create a DigitalTwin instance from database data with enhanced debugging
        """
        print("\n=== Creating DT Instance ===")
        try:
            # Create new DT instance
            dt = DigitalTwin()
            print(f"Created new DT instance for {dt_data.get('name', 'unnamed')}")

            # Add Digital Replicas
            for dr_ref in dt_data.get("digital_replicas", []):
                dr = self.db_service.get_dr(dr_ref["type"], dr_ref["id"])
                if dr:
                    dt.add_digital_replica(dr)
                    print(f"Added DR: {dr_ref['type']} - {dr_ref['id']}")

            # Add Services
            print("\nLoading services...")
            service_mapping = self._get_service_module_mapping()
            print(f"Service mapping: {service_mapping}")

            for service_data in dt_data.get("services", []):
                service_name = service_data["name"]
                print(f"\nProcessing service: {service_name}")

                if service_name in service_mapping:
                    try:
                        module_name = service_mapping[service_name]
                        print(f"Loading module: {module_name}")

                        service_module = __import__(
                            module_name, fromlist=[service_name]
                        )
                        print(f"Module loaded successfully")

                        service_class = getattr(service_module, service_name)
                        print(f"Got service class: {service_class}")

                        service = service_class()
                        print(f"Service instance created")

                        if hasattr(service, "configure") and "config" in service_data:
                            service.configure(service_data["config"])
                            print(f"Service configured with: {service_data['config']}")

                        dt.add_service(service)
                        print(f"Service added to DT")
                        print(f"Current DT services: {dt.list_services()}")
                    except Exception as e:
                        print(f"Error adding service {service_name}: {str(e)}")
                        print(f"Exception type: {type(e)}")
                else:
                    print(f"Warning: Service {service_name} not found in mapping")

            return dt

        except Exception as e:
            print(f"Error creating DT: {str(e)}")
            print(f"Exception type: {type(e)}")
            raise Exception(f"Failed to create DT from data: {str(e)}")

    def get_dt_instance(self, dt_id: str) -> Optional[DigitalTwin]:
        """
        Get a fully initialized DigitalTwin instance by ID

        Args:
            dt_id: Digital Twin ID

        Returns:
            Optional[DigitalTwin]: Digital Twin instance if found, None otherwise
        """
        try:
            # Get DT data from database
            dt_data = self.get_dt(dt_id)
            if not dt_data:
                return None

            # Create and return DT instance
            return self.create_dt_from_data(dt_data)

        except Exception as e:
            raise Exception(f"Failed to get DT instance: {str(e)}")