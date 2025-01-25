from Devices.device_baseClass import DeviceType
from Utilities.device_commissioning import DeviceCommissioning, HubVariant
from Utilities.database_manager import DatabaseManager

def setup_test_environment():
    """Set up test environment with hub and devices"""
    # Initialize managers
    commissioning = DeviceCommissioning()
    db_manager = DatabaseManager()
    
    print("Starting test environment setup...\n")
    
    # 1. Create hub
    print("Creating hub...")
    hub_id = commissioning.create_hub(HubVariant.RESIDENTIAL, "Test Hub")
    if not hub_id:
        print("Failed to create hub!")
        return
    print(f"Created hub with ID: {hub_id}")
    
    # 2. Create devices
    print("\nCreating devices...")
    
    # Create 3 light bulbs
    light_ids = []
    for i in range(3):
        light_id = commissioning.spawn_device(DeviceType.LIGHT)
        if light_id:
            light_ids.append(light_id)
            print(f"Created light bulb {i+1} with ID: {light_id}")
            
            # Link directly to hub using DatabaseManager
            if db_manager.assign_device_to_hub(light_id, hub_id):
                print(f"Light bulb {i+1} linked to hub!")
            else:
                print(f"Failed to link light bulb {i+1}!")
    
    # Create thermostat
    thermo_id = commissioning.spawn_device(DeviceType.THERMOSTAT)
    if thermo_id:
        print(f"Created thermostat with ID: {thermo_id}")
        
        # Link directly to hub using DatabaseManager
        if db_manager.assign_device_to_hub(thermo_id, hub_id):
            print("Thermostat linked to hub!")
        else:
            print("Failed to link thermostat!")
    
    print("\nSetup complete! Environment ready for testing.")
    print(f"\nHub ID: {hub_id}")
    print("Light IDs:", light_ids)
    print(f"Thermostat ID: {thermo_id}")
    
    # Save IDs to file for manipulator testing
    with open('test_device_ids.txt', 'w') as f:
        f.write(f"HUB_ID={hub_id}\n")
        f.write(f"LIGHT_IDS={','.join(light_ids)}\n")
        f.write(f"THERMO_ID={thermo_id}\n")

if __name__ == "__main__":
    setup_test_environment()