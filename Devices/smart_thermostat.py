from Devices.device_baseClass import BaseDevice, DeviceType
from typing import Dict, Any

class SmartThermostat(BaseDevice):
    """Smart thermostat implementation"""
    
    def __init__(self):
        super().__init__(DeviceType.THERMOSTAT)  # Pass device type to parent
        # Thermostat-specific properties
        self.current_temp: float = 20.0
        self.target_temp: float = 22.0
        self.mode: str = "HEAT"
        self.power_rating: float = 1000.0
        
    @classmethod
    def from_db_data(cls, device_data: Dict[str, Any]) -> 'SmartThermostat':
        device = super().from_db_data(device_data)
        device.current_temp = device_data.get("current_temp", 20.0)
        device.target_temp = device_data.get("target_temp", 22.0)
        device.mode = device_data.get("mode", "HEAT")
        device.power_rating = device_data.get("power_rating", 1000.0)
        return device

    def info(self) -> Dict[str, Any]:
        """Get device information including thermostat-specific properties"""
        info_dict = super().info()
        info_dict.update({
            "current_temp": self.current_temp,
            "target_temp": self.target_temp,
            "mode": self.mode,
            "power_rating": self.power_rating
        })
        return info_dict

    def toggle_state(self) -> bool:
        """Toggle thermostat on/off and update power usage"""
        try:
            self.state = not self.state
            if not self.state:
                self.mode = "OFF"
            else:
                # Default to heating if temperature is below target
                self.mode = "HEAT" if self.current_temp < self.target_temp else "COOL"
            self.update_energy_usage()
            return self.db_manager.update_device(self.id, self.info())
        except Exception as e:
            print(f"Error toggling thermostat state: {e}")
            return False

    def set_target_temp(self, temp: float) -> bool:
        """Set target temperature"""
        try:
            self.target_temp = round(max(10.0, min(30.0, temp)), 1)  # Clamp between 10-30°C
            self.update_energy_usage()
            return self.db_manager.update_device(self.id, self.info())
        except Exception as e:
            print(f"Error setting target temperature: {e}")
            return False

    def set_mode(self, mode: str) -> bool:
        """Set thermostat mode (HEAT/COOL/OFF)"""
        try:
            if mode in ["HEAT", "COOL", "OFF"]:
                self.mode = mode
                self.state = mode != "OFF"
                self.update_energy_usage()
                return self.db_manager.update_device(self.id, self.info())
            return False
        except Exception as e:
            print(f"Error setting mode: {e}")
            return False

    def update_energy_usage(self) -> None:
        """Update power usage based on state and temperature differential"""
        if not self.state or self.mode == "OFF":
            self.power_usage = 0.0
            return

        # Calculate power usage based on temperature differential
        temp_diff = abs(self.current_temp - self.target_temp)
        if (self.mode == "HEAT" and self.current_temp < self.target_temp) or \
           (self.mode == "COOL" and self.current_temp > self.target_temp):
            # Power usage increases with temperature differential
            # Using a simple linear model here
            usage_factor = min(1.0, temp_diff / 5.0)  # Max power at 5°C difference
            self.power_usage = self.power_rating * usage_factor
        else:
            self.power_usage = 0.0

    def update_current_temp(self, temp: float) -> bool:
        """Update current temperature reading"""
        try:
            self.current_temp = round(temp, 1)
            self.update_energy_usage()
            return self.db_manager.update_device(self.id, self.info())
        except Exception as e:
            print(f"Error updating current temperature: {e}")
            return False

    def get_mqtt_msg(self) -> dict:
        """Get MQTT message with thermostat-specific properties"""
        msg = super().get_mqtt_msg()
        msg.update({
            "current_temp": self.current_temp,
            "target_temp": self.target_temp,
            "mode": self.mode
        })
        return msg