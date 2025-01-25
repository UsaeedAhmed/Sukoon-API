from Devices.device_baseClass import DeviceType
from Utilities.device_commissioning import DeviceCommissioning, HubVariant

def main():
    """Test device commissioning functionality"""
    
    # Initialize commissioning module
    commissioning = DeviceCommissioning()
    
    print("Starting device commissioning tests...\n")
    
    # Test spawning different types of devices
    print("Testing device spawning:")
    
    # Spawn a light bulb
    light_id = commissioning.spawn_device(DeviceType.LIGHT)
    print(f"Spawned light bulb with ID: {light_id}")
    
    # Spawn a thermostat
    thermo_id = commissioning.spawn_device(DeviceType.THERMOSTAT)
    print(f"Spawned thermostat with ID: {thermo_id}")
    
    # Test hub creation
    print("\nTesting hub creation:")
    hub_id = commissioning.create_hub(HubVariant.RESIDENTIAL, "Test Hub 1")
    print(f"Created hub with ID: {hub_id}")
    
    # Verify devices in free pool
    print("\nVerifying devices in free pool:")
    db = commissioning.db_manager
    
    # Check light
    light_exists = db.read_document("free_devices", light_id)
    print(f"Light in free pool: {light_exists is not None}")
    
    # Check thermostat
    thermo_exists = db.read_document("free_devices", thermo_id)
    print(f"Thermostat in free pool: {thermo_exists is not None}")
    
    # Check hub
    hub_exists = db.read_document("free_devices", hub_id)
    print(f"Hub in free pool: {hub_exists is not None}")
    
    # Get and print full device details
    print("\nFull device details:")
    
    light_data = db.read_document("devices", light_id)
    print(f"\nLight Device:")
    print(light_data)
    
    thermo_data = db.read_document("devices", thermo_id)
    print(f"\nThermostat Device:")
    print(thermo_data)
    
    hub_data = db.read_document("devices", hub_id)
    print(f"\nHub Device:")
    print(hub_data)

if __name__ == "__main__":
    main()