# hub.py
from enum import Enum
import uuid
import time
import jwt
from typing import Optional, List, Dict, Any
from Utilities.database_manager import DatabaseManager

class HubType(Enum):
    HUB_R = "HUB_R"  # Regular hub type

class Hub:
    def __init__(self, owner_id: Optional[str] = None, name: str = "Default Hub"):
        """
        Default constructor for creating a new hub.
        Hub starts unlinked (in device pool) until linked to an owner.
        
        Args:
            owner_id: Optional ID of the hub owner (None if unlinked)
            name: Name of the hub
        """
        self.id = f"HUB_{str(uuid.uuid4())}"
        self.type = HubType.HUB_R
        self.owner_id = owner_id
        self.name = name
        self.devices = []
        self.db_manager = DatabaseManager()

    @classmethod
    def from_db_data(cls, hub_data: Dict[str, Any]) -> 'Hub':
        """
        Alternative constructor to create a hub instance from database data.
        
        Args:
            hub_data: Dictionary containing hub data from database
            
        Returns:
            Hub: New hub instance with data from database
        """
        hub = cls()  # Create empty hub
        hub.id = hub_data["id"]
        hub.type = HubType(hub_data.get("type", HubType.HUB_R.value))
        hub.owner_id = hub_data.get("owner_id")
        hub.name = hub_data.get("name", "Default Hub")
        hub.devices = hub_data.get("devices", [])
        return hub

    def info(self) -> Dict[str, Any]:
        """
        Get hub information as a dictionary for database storage.
        
        Returns:
            Dict[str, Any]: Hub information
        """
        return {
            "id": self.id,
            "type": self.type.value,
            "owner_id": self.owner_id,
            "name": self.name,
            "devices": self.devices
        }

    def sync_from_db(self) -> bool:
        """
        Sync local hub state with database.
        
        Returns:
            bool: True if sync successful, False otherwise
        """
        try:
            hub_data = self.db_manager.read_document("hubs", self.id)
            if hub_data:
                self.owner_id = hub_data.get("owner_id", self.owner_id)
                self.name = hub_data.get("name", self.name)
                self.devices = hub_data.get("devices", [])
                return True
            return False
        except Exception as e:
            print(f"Error syncing hub {self.id}: {e}")
            return False

    def add_device(self, device_id: str) -> bool:
        """
        Add a device from the pool to this hub.
        
        Args:
            device_id: The ID of the device to add
            
        Returns:
            bool: True if successful, False otherwise
        """
        if self.db_manager.assign_device_to_hub(device_id, self.id):
            self.devices.append(device_id)
            return True
        return False

    def remove_device(self, device_id: str) -> bool:
        """
        Remove and delete a device from the hub.
        
        Args:
            device_id: The ID of the device to remove
            
        Returns:
            bool: True if successful, False otherwise
        """
        if device_id in self.devices:
            # Remove from hub's device list
            self.devices.remove(device_id)
            
            # Delete from database
            return self.db_manager.delete_device(device_id)
        return False

    def get_devices(self) -> List[str]:
        """
        Get list of all devices connected to this hub.
        
        Returns:
            List[str]: List of device IDs
        """
        return self.devices

    def share_with_user(self, user_id: str) -> bool:
        """
        Share hub access with another user.
        
        Args:
            user_id: ID of user to share with
            
        Returns:
            bool: True if successful, False otherwise
        """
        return self.db_manager.share_hub_access(self.id, user_id)

    def generate_linking_token(self, secret_key: str, expiry_minutes: int = 60) -> str:
        """
        Generate a signed token for secure QR code linking.
        
        Args:
            secret_key: Secret key for signing the token
            expiry_minutes: Token validity period in minutes
            
        Returns:
            str: Signed JWT token for QR code
        """
        linking_data = {
            "id": self.id,
            "type": self.type.value,
            "exp": int(time.time()) + (expiry_minutes * 60)
        }
        return jwt.encode(linking_data, secret_key, algorithm="HS256")