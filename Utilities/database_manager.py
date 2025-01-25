import os
from typing import Dict, Any, Optional, List
import firebase_admin
from firebase_admin import credentials, db
from dotenv import load_dotenv

class DatabaseManager:
    """
    A class to handle all Firebase Realtime Database operations.
    """
    _instance = None

    def __new__(cls):
        """Implement singleton pattern to ensure only one database connection."""
        if cls._instance is None:
            cls._instance = super(DatabaseManager, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize Firebase connection using environment variables."""
        if not hasattr(self, 'initialized'):
            load_dotenv()
            
            # Load Firebase credentials from environment variables
            cred_dict = {
                "type": os.getenv("FIREBASE_TYPE"),
                "project_id": os.getenv("FIREBASE_PROJECT_ID"),
                "private_key_id": os.getenv("FIREBASE_PRIVATE_KEY_ID"),
                "private_key": os.getenv("FIREBASE_PRIVATE_KEY").replace('\\n', '\n'),
                "client_email": os.getenv("FIREBASE_CLIENT_EMAIL"),
                "client_id": os.getenv("FIREBASE_CLIENT_ID"),
                "auth_uri": os.getenv("FIREBASE_AUTH_URI"),
                "token_uri": os.getenv("FIREBASE_TOKEN_URI"),
                "auth_provider_x509_cert_url": os.getenv("FIREBASE_AUTH_PROVIDER_CERT_URL"),
                "client_x509_cert_url": os.getenv("FIREBASE_CLIENT_CERT_URL")
            }
            
            cred = credentials.Certificate(cred_dict)
            firebase_admin.initialize_app(cred, {
                'databaseURL': os.getenv("FIREBASE_DATABASE_URL")
            })
            
            self.db = db.reference()
            self.initialized = True

    def add_device(self, device_id: str, data: Dict[str, Any]) -> bool:
        """
        Add a new device to the database.
        
        Args:
            device_id: Unique identifier for the device
            data: Dictionary containing device data
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            self.db.child('devices').child(device_id).set(data)
            return True
        except Exception as e:
            print(f"Error adding device: {e}")
            return False

    def update_device(self, device_id: str, data: Dict[str, Any]) -> bool:
        """
        Update an existing device's data.
        
        Args:
            device_id: Device identifier
            data: Dictionary containing updated device data
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            self.db.child('devices').child(device_id).update(data)
            return True
        except Exception as e:
            print(f"Error updating device: {e}")
            return False

    def delete_device(self, device_id: str) -> bool:
        """
        Delete a device from the database.
        
        Args:
            device_id: Device identifier
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            self.db.child('devices').child(device_id).delete()
            return True
        except Exception as e:
            print(f"Error deleting device: {e}")
            return False

    def get_device(self, device_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a device's data.
        
        Args:
            device_id: Device identifier
            
        Returns:
            Optional[Dict]: Device data if exists, None otherwise
        """
        try:
            return self.db.child('devices').child(device_id).get()
        except Exception as e:
            print(f"Error getting device: {e}")
            return None

    def get_all_devices(self) -> Optional[List[Dict[str, Any]]]:
        """
        Retrieve all devices.
        
        Returns:
            Optional[List[Dict]]: List of all devices if successful, None otherwise
        """
        try:
            devices = self.db.child('devices').get()
            return [{'id': key, **value} for key, value in devices.items()] if devices else []
        except Exception as e:
            print(f"Error getting all devices: {e}")
            return None

    def add_device_status(self, device_id: str, status_data: Dict[str, Any]) -> bool:
        """
        Add a status update for a device.
        
        Args:
            device_id: Device identifier
            status_data: Dictionary containing status data
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Add timestamp to status data
            status_data['timestamp'] = {'.sv': 'timestamp'}
            self.db.child('device_status').child(device_id).push(status_data)
            return True
        except Exception as e:
            print(f"Error adding device status: {e}")
            return False

    def get_device_status_history(self, device_id: str, limit: int = 100) -> Optional[List[Dict[str, Any]]]:
        """
        Get status history for a device.
        
        Args:
            device_id: Device identifier
            limit: Maximum number of status records to retrieve
            
        Returns:
            Optional[List[Dict]]: List of status records if successful, None otherwise
        """
        try:
            status = self.db.child('device_status').child(device_id).order_by_child('timestamp').limit_to_last(limit).get()
            return [{'id': key, **value} for key, value in status.items()] if status else []
        except Exception as e:
            print(f"Error getting device status history: {e}")
            return None

    # Hub Management Methods
    def create_hub(self, hub_id: str, owner_id: str, hub_data: Dict[str, Any]) -> bool:
        """Create a new hub with owner."""
        try:
            hub_data.update({
                "owner": owner_id,
                "shared_with": [],
                "devices": []
            })
            return self.create_document("hubs", hub_id, hub_data)
        except Exception as e:
            print(f"Error creating hub: {e}")
            return False

    def share_hub_access(self, hub_id: str, user_id: str) -> bool:
        """Add a user to hub's shared_with list."""
        try:
            hub = self.read_document("hubs", hub_id)
            if hub:
                shared_with = hub.get("shared_with", [])
                if user_id not in shared_with:
                    shared_with.append(user_id)
                    return self.update_document("hubs", hub_id, {"shared_with": shared_with})
            return False
        except Exception as e:
            print(f"Error sharing hub: {e}")
            return False

    def check_hub_access(self, hub_id: str, user_id: str) -> bool:
        """Check if user has access to hub."""
        try:
            hub = self.read_document("hubs", hub_id)
            if hub:
                return hub.get("owner") == user_id or user_id in hub.get("shared_with", [])
            return False
        except Exception as e:
            print(f"Error checking hub access: {e}")
            return False

    # Device Pool Management
    def add_to_device_pool(self, device_id: str, device_data: Dict[str, Any]) -> bool:
        """
        Add a new device or hub to the free pool.
        For devices: Adds to devices collection and free_devices pool
        For hubs: Adds to hubs collection and free_devices pool
        
        Args:
            device_id: ID of device/hub
            device_data: Dictionary containing device/hub data
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Check if it's a hub (ID starts with HUB_ or type is HUB_R)
            is_hub = device_id.startswith("HUB_") or device_data.get("type") == "HUB_R"
            
            # Add to appropriate collection first
            if is_hub:
                # For hubs, add to hubs collection
                if not self.create_document("hubs", device_id, {
                    "id": device_id,
                    "name": device_data.get("name", "Default Hub"),
                    "type": "HUB_R",
                    "owner": None,
                    "shared_with": [],
                    "devices": []
                }):
                    return False
            else:
                # For devices, add to devices collection
                if not self.create_document("devices", device_id, device_data):
                    return False
            
            # Then add to free_devices pool
            return self.create_document("free_devices", device_id, True)
                
        except Exception as e:
            print(f"Error adding to device pool: {e}")
            return False

    def assign_device_to_hub(self, device_id: str, hub_id: str) -> bool:
        """Move device from pool to hub."""
        try:
            # Update device
            success = self.update_document("devices", device_id, {"hub_id": hub_id})
            if not success:
                return False
            
            # Remove from free pool
            self.delete_document("free_devices", device_id)
            
            # Add to hub's device list
            hub = self.read_document("hubs", hub_id)
            if hub:
                devices = hub.get("devices", [])
                if device_id not in devices:
                    devices.append(device_id)
                    return self.update_document("hubs", hub_id, {"devices": devices})
            return False
        except Exception as e:
            print(f"Error assigning device: {e}")
            return False

    # User Management
    def setup_new_user(self, user_id: str, user_data: Dict[str, Any]) -> bool:
        """Setup a new user record if it doesn't exist."""
        try:
            existing_user = self.read_document("users", user_id)
            if not existing_user:
                user_data["hubs_access"] = []
                return self.create_document("users", user_id, user_data)
            return True
        except Exception as e:
            print(f"Error setting up user: {e}")
            return False

    # Generic CRUD Operations
    def create_document(self, collection: str, doc_id: str, data: Dict[str, Any]) -> bool:
        """
        Create a new document in any collection.
        
        Args:
            collection: Name of the collection
            doc_id: Document identifier
            data: Document data
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            self.db.child(collection).child(doc_id).set(data)
            return True
        except Exception as e:
            print(f"Error creating document: {e}")
            return False

    def read_document(self, collection: str, doc_id: str) -> Optional[Dict[str, Any]]:
        """
        Read a document from any collection.
        
        Args:
            collection: Name of the collection
            doc_id: Document identifier
            
        Returns:
            Optional[Dict]: Document data if exists, None otherwise
        """
        try:
            return self.db.child(collection).child(doc_id).get()
        except Exception as e:
            print(f"Error reading document: {e}")
            return None

    def update_document(self, collection: str, doc_id: str, data: Dict[str, Any]) -> bool:
        """
        Update a document in any collection.
        
        Args:
            collection: Name of the collection
            doc_id: Document identifier
            data: Updated document data
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            self.db.child(collection).child(doc_id).update(data)
            return True
        except Exception as e:
            print(f"Error updating document: {e}")
            return False

    def delete_document(self, collection: str, doc_id: str) -> bool:
        """
        Delete a document from any collection.
        
        Args:
            collection: Name of the collection
            doc_id: Document identifier
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            self.db.child(collection).child(doc_id).delete()
            return True
        except Exception as e:
            print(f"Error deleting document: {e}")
            return False

    def list_collection(self, collection: str) -> Optional[List[Dict[str, Any]]]:
        """
        List all documents in a collection.
        
        Args:
            collection: Name of the collection
            
        Returns:
            Optional[List[Dict]]: List of documents if successful, None otherwise
        """
        try:
            documents = self.db.child(collection).get()
            return [{'id': key, **value} for key, value in documents.items()] if documents else []
        except Exception as e:
            print(f"Error listing collection: {e}")
            return None

    def query_collection(self, collection: str, order_by: str, limit: int = 100) -> Optional[List[Dict[str, Any]]]:
        """
        Query documents in a collection with ordering and limit.
        
        Args:
            collection: Name of the collection
            order_by: Field to order by
            limit: Maximum number of documents to retrieve
            
        Returns:
            Optional[List[Dict]]: List of documents if successful, None otherwise
        """
        try:
            documents = self.db.child(collection).order_by_child(order_by).limit_to_last(limit).get()
            return [{'id': key, **value} for key, value in documents.items()] if documents else []
        except Exception as e:
            print(f"Error querying collection: {e}")
            return None