from abc import ABC, abstractmethod
from enum import Enum
import uuid
import time
import jwt
import random
import string
from datetime import datetime
from typing import Dict, Any, Optional
from Utilities.database_manager import DatabaseManager

class DeviceType(Enum):
    LIGHT = "LIGHT"
    THERMOSTAT = "THERMOSTAT"
    PLUG = "PLUG"

class BaseDevice(ABC):
    """Base class for all smart devices"""
    
    def __init__(self, device_type: DeviceType):
        self.id = f"DEV_{str(uuid.uuid4())}"
        self.type = device_type  # Set device type in constructor
        # Generate a unique default name with device type prefix and random alphanumeric suffix
        suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
        self.name = f"{self.type.value}_{suffix}"
        self.hub_id: Optional[str] = None
        self.state: bool = False
        self.power_usage: float = 0.0
        self.db_manager = DatabaseManager()

    @classmethod
    def from_db_data(cls, device_data: Dict[str, Any]) -> 'BaseDevice':
        """Create device instance from database data"""
        device = cls()
        device.id = device_data["id"]
        device.name = device_data.get("name", device.name)  # Use generated name as fallback
        device.hub_id = device_data.get("hub_id")
        device.state = device_data.get("state", True)
        device.power_usage = device_data.get("power_usage", 0.0)
        return device

    def info(self) -> Dict[str, Any]:
        """Get device information for database storage"""
        return {
            "id": self.id,
            "type": self.type.value,
            "name": self.name,
            "hub_id": self.hub_id,
            "state": self.state,
            "power_usage": self.power_usage,
        }

    def sync_from_db(self) -> bool:
        """Sync device state with database"""
        try:
            device_data = self.db_manager.read_document("devices", self.id)
            if device_data:
                self.name = device_data.get("name", self.name)
                self.hub_id = device_data.get("hub_id")
                self.state = device_data.get("state", self.state)
                self.power_usage = device_data.get("power_usage", self.power_usage)
                return True
            return False
        except Exception as e:
            print(f"Error syncing device {self.id}: {e}")
            return False

    @abstractmethod
    def toggle_state(self) -> bool:
        """Toggle device state and update power usage"""
        pass

    @abstractmethod
    def update_energy_usage(self) -> None:
        """Update current power usage based on device state and settings"""
        pass

    def get_mqtt_msg(self) -> dict:
        """
        Returns device data formatted for MQTT publishing.
        Should be overridden by specific device types to include their unique properties.
        
        Returns:
            dict: Device data ready for MQTT publishing
        """
        return {
            "device_id": self.id,
            "type": self.type.value,
            "name": self.name,
            "state": self.state,
            "power_usage": self.power_usage,
            "timestamp": datetime.now().isoformat()
        }

    def generate_linking_token(self, secret_key: str, expiry_minutes: int = 60) -> str:
        """Generate QR code linking token"""
        linking_data = {
            "id": self.id,
            "type": self.type.value,
            "exp": int(time.time()) + (expiry_minutes * 60)
        }
        return jwt.encode(linking_data, secret_key, algorithm="HS256")