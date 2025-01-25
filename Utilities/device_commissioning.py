from typing import Optional, Dict, Any
from enum import Enum
import jwt
from datetime import datetime, timedelta

from Utilities.database_manager import DatabaseManager
from Devices.device_baseClass import DeviceType, BaseDevice
from Devices.lightbulb import SmartBulb
from Devices.smart_thermostat import SmartThermostat
from Hubs.residential_hub import Hub, HubType

class HubVariant(Enum):
    """Enum for different hub types"""
    RESIDENTIAL = "HUB_R"
    MANAGER = "HUB_M"  # For future manager hub implementation

class DeviceCommissioning:
    """Handles device and hub commissioning operations"""
    
    def __init__(self):
        """Initialize with database manager"""
        self.db_manager = DatabaseManager()
        self._secret_key = "your-secret-key-here"  # Should be loaded from env vars

    def spawn_device(self, device_type: DeviceType) -> Optional[str]:
        """
        Spawn a new device of specified type into the free devices pool.
        
        Args:
            device_type: Type of device to create
            
        Returns:
            Optional[str]: Device ID if successful, None otherwise
        """
        try:
            # Create appropriate device instance
            device: Optional[BaseDevice] = None
            
            if device_type == DeviceType.LIGHT:
                device = SmartBulb()
            elif device_type == DeviceType.THERMOSTAT:
                device = SmartThermostat()
            else:
                print(f"Unsupported device type: {device_type}")
                return None
            
            # Get device info for database
            device_data = device.info()
            
            # Add to free devices pool
            if self.db_manager.add_to_device_pool(device.id, device_data):
                return device.id
            return None
            
        except Exception as e:
            print(f"Error spawning device: {e}")
            return None

    def create_hub(self, variant: HubVariant, name: str = "Default Hub") -> Optional[str]:
        """
        Create a new hub instance.
        
        Args:
            variant: Type of hub to create
            name: Name for the hub
            
        Returns:
            Optional[str]: Hub ID if successful, None otherwise
        """
        try:
            # Currently only supporting residential hubs
            if variant != HubVariant.RESIDENTIAL:
                print("Only residential hubs currently supported")
                return None
                
            # Create new hub
            hub = Hub(name=name)
            hub_data = hub.info()
            
            # Add to free devices pool (unassigned hubs)
            if self.db_manager.add_to_device_pool(hub.id, hub_data):
                return hub.id
            return None
            
        except Exception as e:
            print(f"Error creating hub: {e}")
            return None

    def generate_linking_token(self, device_id: str, expiry_minutes: int = 60) -> Optional[str]:
        """
        Generate a linking token for QR code.
        
        Args:
            device_id: ID of device/hub to link
            expiry_minutes: Token validity period
            
        Returns:
            Optional[str]: JWT token if successful, None otherwise
        """
        try:
            # Verify device exists in free pool
            if not self.db_manager.read_document("free_devices", device_id):
                print(f"Device {device_id} not found in free pool")
                return None
                
            # Get device/hub data
            device_data = self.db_manager.read_document("devices", device_id)
            if not device_data:
                print(f"Device {device_id} not found")
                return None
                
            # Create token payload
            payload = {
                "id": device_id,
                "type": device_data.get("type"),
                "exp": datetime.utcnow() + timedelta(minutes=expiry_minutes)
            }
            
            # Generate and return token
            return jwt.encode(payload, self._secret_key, algorithm="HS256")
            
        except Exception as e:
            print(f"Error generating linking token: {e}")
            return None

    def process_linking(self, token: str, user_id: str) -> bool:
        """
        Process device/hub linking from QR code.
        
        Args:
            token: JWT token from QR code
            user_id: ID of user claiming the device
            
        Returns:
            bool: True if linking successful, False otherwise
        """
        try:
            # Decode and verify token
            try:
                payload = jwt.decode(token, self._secret_key, algorithms=["HS256"])
            except jwt.ExpiredSignatureError:
                print("Linking token has expired")
                return False
            except jwt.InvalidTokenError:
                print("Invalid linking token")
                return False
                
            device_id = payload.get("id")
            device_type = payload.get("type")
            
            # Verify device exists in free pool
            if not self.db_manager.read_document("free_devices", device_id):
                print(f"Device {device_id} not found in free pool")
                return False
                
            # Handle differently based on type
            if device_type.startswith("HUB_"):
                # Link hub to user
                return self._link_hub(device_id, user_id)
            else:
                # Link device to user's default hub
                return self._link_device(device_id, user_id)
                
        except Exception as e:
            print(f"Error processing linking: {e}")
            return False
            
    def _link_hub(self, hub_id: str, user_id: str) -> bool:
        """Internal method to link hub to user"""
        try:
            # Get hub data
            hub_data = self.db_manager.read_document("devices", hub_id)
            if not hub_data:
                return False
                
            # Update hub with owner
            hub_data["owner_id"] = user_id
            
            # Move to active hubs collection
            if not self.db_manager.create_hub(hub_id, user_id, hub_data):
                return False
                
            # Remove from free pool
            return self.db_manager.delete_document("free_devices", hub_id)
            
        except Exception as e:
            print(f"Error linking hub: {e}")
            return False
            
    def _link_device(self, device_id: str, user_id: str) -> bool:
        """Internal method to link device to user's default hub"""
        try:
            # Find user's default hub
            user_data = self.db_manager.read_document("users", user_id)
            if not user_data or not user_data.get("default_hub_id"):
                print("User has no default hub")
                return False
                
            default_hub_id = user_data["default_hub_id"]
            
            # Assign device to hub
            return self.db_manager.assign_device_to_hub(device_id, default_hub_id)
            
        except Exception as e:
            print(f"Error linking device: {e}")
            return False