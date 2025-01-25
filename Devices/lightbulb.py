from Devices.device_baseClass import BaseDevice, DeviceType
from typing import Dict, Any

class SmartBulb(BaseDevice):
    """Smart light bulb implementation"""
    
    def __init__(self):
        super().__init__(DeviceType.LIGHT)  # Pass device type to parent
        # Light-specific properties
        self.brightness: int = 100
        self.color: str = "#FFFFFF"
        self.power_rating: float = 10.0
        
    @classmethod
    def from_db_data(cls, device_data: Dict[str, Any]) -> 'SmartBulb':
        device = super().from_db_data(device_data)
        device.brightness = device_data.get("brightness", 100)
        device.color = device_data.get("color", "#FFFFFF")
        device.power_rating = device_data.get("power_rating", 10.0)
        return device

    def info(self) -> Dict[str, Any]:
        """Get device information including light-specific properties"""
        info_dict = super().info()
        info_dict.update({
            "brightness": self.brightness,
            "color": self.color,
            "power_rating": self.power_rating
        })
        return info_dict

    def toggle_state(self) -> bool:
        """Toggle light on/off and update power usage"""
        try:
            self.state = not self.state
            self.update_energy_usage()
            return self.db_manager.update_device(self.id, self.info())
        except Exception as e:
            print(f"Error toggling light state: {e}")
            return False

    def set_brightness(self, brightness: int) -> bool:
        """Set light brightness (0-100%)"""
        try:
            self.brightness = max(0, min(100, brightness))  # Clamp between 0-100
            self.update_energy_usage()
            return self.db_manager.update_device(self.id, self.info())
        except Exception as e:
            print(f"Error setting brightness: {e}")
            return False

    def set_color(self, color: str) -> bool:
        """Set light color (hex format)"""
        try:
            # Basic hex color validation
            if len(color) == 7 and color.startswith("#"):
                self.color = color.upper()
                return self.db_manager.update_device(self.id, self.info())
            return False
        except Exception as e:
            print(f"Error setting color: {e}")
            return False

    def update_energy_usage(self) -> None:
        """Update power usage based on state and brightness"""
        if self.state:
            # Power usage scales with brightness
            self.power_usage = self.power_rating * (self.brightness / 100)
        else:
            self.power_usage = 0.0

    def get_mqtt_msg(self) -> dict:
        """Get MQTT message with light-specific properties"""
        msg = super().get_mqtt_msg()
        msg.update({
            "brightness": self.brightness,
            "color": self.color
        })
        return msg  