from Utilities.manipulator import Manipulator
from Utilities.database_setup import init_db
import time

def load_test_ids():
    """Load device IDs from file"""
    ids = {}
    with open('test_device_ids.txt', 'r') as f:
        for line in f:
            key, value = line.strip().split('=')
            if key == 'LIGHT_IDS':
                ids[key] = value.split(',')
            else:
                ids[key] = value
    return ids

def test_manipulator():
    """Test the manipulator with our test devices"""
    # Initialize SQLite database first
    print("Initializing SQLite database...")
    init_db()
    
    # Load device IDs
    ids = load_test_ids()
    hub_id = ids['HUB_ID']
    light_ids = ids['LIGHT_IDS']
    thermo_id = ids['THERMO_ID']
    
    # Initialize manipulator
    print("Initializing manipulator...")
    manipulator = Manipulator()
    
    try:
        # Test cycle: toggle devices on and off
        print("\nStarting test cycle...")
        for _ in range(3):  # Run 3 cycles
            # Turn everything on
            print("\nTurning devices on...")
            for light_id in light_ids:
                manipulator.update_device_state(hub_id, light_id, True)
            manipulator.update_device_state(hub_id, thermo_id, True)
            
            # Wait for 2 minutes
            print("Waiting 2 minutes...")
            time.sleep(120)
            
            # Turn everything off
            print("\nTurning devices off...")
            for light_id in light_ids:
                manipulator.update_device_state(hub_id, light_id, False)
            manipulator.update_device_state(hub_id, thermo_id, False)
            
            # Wait for 1 minute
            print("Waiting 1 minute...")
            time.sleep(60)
    
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
    finally:
        # Clean up
        print("\nStopping manipulator...")
        manipulator.stop_all()
        print("Test complete!")

if __name__ == "__main__":
    test_manipulator()