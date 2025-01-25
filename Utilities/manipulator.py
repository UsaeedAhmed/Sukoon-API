# Utilities/manipulator.py
import threading
import time
from datetime import datetime
from typing import Dict, Optional, List
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from .database_setup import HubLog, DeviceLog
from .database_manager import DatabaseManager
from Devices.device_baseClass import BaseDevice
from Devices.lightbulb import SmartBulb
from Devices.smart_thermostat import SmartThermostat

class DeviceStateTracker:
    """Tracks state and active minutes for a single device within a 15-min block"""
    def __init__(self, device_id: str, initial_state: bool):
        self.device_id = device_id
        self.state = initial_state
        self.active_minutes = 0
        self.last_state_change = datetime.now()
    
    def update_state(self, new_state: bool):
        """Update device state and calculate active minutes"""
        now = datetime.now()
        if self.state:  # If device was on, add the active time
            delta = now - self.last_state_change
            self.active_minutes += delta.total_seconds() / 60
        
        self.state = new_state
        self.last_state_change = now
    
    def finalize_block(self) -> float:
        """Calculate final active minutes for current block and reset"""
        if self.state:  # If still on, add time until now
            self.update_state(self.state)  # This will update active_minutes
        
        total_minutes = min(15.0, self.active_minutes)  # Cap at 15 minutes
        self.active_minutes = 0  # Reset for next block
        return total_minutes

class HubThread:
    """Manages devices and logging for a single hub"""
    def __init__(self, hub_id: str, db_manager: DatabaseManager, sql_session):
        self.hub_id = hub_id
        self.db_manager = db_manager
        self.sql_session = sql_session
        self.devices: Dict[str, DeviceStateTracker] = {}
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.initialize_devices()
    
    def initialize_devices(self):
        """Load all devices for this hub and initialize trackers"""
        hub_data = self.db_manager.read_document("hubs", self.hub_id)
        if hub_data and "devices" in hub_data:
            for device_id in hub_data["devices"]:
                device_data = self.db_manager.get_device(device_id)
                if device_data:
                    self.devices[device_id] = DeviceStateTracker(
                        device_id=device_id,
                        initial_state=device_data.get("state", False)
                    )
    
    def update_device_state(self, device_id: str, new_state: bool):
        """Update state for a specific device"""
        if device_id in self.devices:
            self.devices[device_id].update_state(new_state)
    
# Inside Utilities/manipulator.py, in the HubThread class:

    def process_block(self):
        """Process and log a 15-minute block of data"""
        try:
            timestamp = datetime.now().replace(microsecond=0)  # Remove microseconds
            total_hub_usage = 0.0
            device_logs = []

            # Process each device
            for device_id, tracker in self.devices.items():
                device_data = self.db_manager.get_device(device_id)
                if not device_data:
                    continue
                    
                active_minutes = tracker.finalize_block()
                power_rating = device_data.get("power_rating", 0)
                power_usage = (power_rating * active_minutes) / 60
                
                total_hub_usage += power_usage
                device_logs.append({
                    "device_id": device_id,
                    "active_minutes": active_minutes,
                    "power_usage": power_usage
                })

            # Check for existing log at this timestamp
            existing_log = self.sql_session.query(HubLog).filter_by(
                hub_id=self.hub_id, 
                timestamp=timestamp
            ).first()

            if existing_log:
                # Update existing log
                existing_log.total_usage = total_hub_usage
                # Delete existing device logs
                self.sql_session.query(DeviceLog).filter_by(hub_log_id=existing_log.id).delete()
                hub_log = existing_log
            else:
                # Create new hub log
                hub_log = HubLog(
                    hub_id=self.hub_id,
                    timestamp=timestamp,
                    total_usage=total_hub_usage
                )
                self.sql_session.add(hub_log)
                
            self.sql_session.flush()

            # Create device log entries
            for log in device_logs:
                device_log = DeviceLog(
                    hub_log_id=hub_log.id,
                    device_id=log["device_id"],
                    active_minutes=log["active_minutes"],
                    power_usage=log["power_usage"]
                )
                self.sql_session.add(device_log)

            # Commit all changes
            self.sql_session.commit()

            # Update Firebase
            firebase_timestamp = timestamp.strftime("%Y_%m_%d_%H_%M_%S")
            collection_path = f"hub_logs/{self.hub_id}/current_day"
            block_data = {
                "total_usage": total_hub_usage,
                "timestamp": timestamp.isoformat(),
                "devices": {
                    log["device_id"]: {
                        "active_minutes": log["active_minutes"],
                        "power_usage": log["power_usage"]
                    } for log in device_logs
                }
            }
            
            self.db_manager.create_document(collection_path, firebase_timestamp, block_data)
            
        except Exception as e:
            print(f"Error processing block: {e}")
            self.sql_session.rollback()
    
    def run(self):
        """Main loop for processing 15-minute blocks"""
        while self.running:
            self.process_block()
            # Sleep until next 15-minute mark
            now = datetime.now()
            next_block = now.replace(
                minute=(now.minute // 15 * 15 + 15) % 60,
                second=0,
                microsecond=0
            )
            if next_block < now:  # If we've passed the hour mark
                next_block = next_block.replace(hour=next_block.hour + 1)
            sleep_time = (next_block - now).total_seconds()
            time.sleep(sleep_time)
    
    def start(self):
        """Start the hub processing thread"""
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self.run)
            self.thread.start()
    
    def stop(self):
        """Stop the hub processing thread"""
        self.running = False
        if self.thread:
            self.thread.join()

class Manipulator:
    """Main class for managing all hubs and their devices"""
    def __init__(self):
        self.db_manager = DatabaseManager()
        self.engine = create_engine('sqlite:///smart_home.db')
        self.Session = sessionmaker(bind=self.engine)
        self.hubs: Dict[str, HubThread] = {}
        self.initialize_hubs()
    
    def initialize_hubs(self):
        """Load all active hubs and start their threads"""
        hubs = self.db_manager.list_collection("hubs")
        if hubs:
            for hub in hubs:
                self.add_hub(hub["id"])
    
    def add_hub(self, hub_id: str):
        """Add and start a new hub thread"""
        if hub_id not in self.hubs:
            session = self.Session()
            self.hubs[hub_id] = HubThread(hub_id, self.db_manager, session)
            self.hubs[hub_id].start()
    
    def update_device_state(self, hub_id: str, device_id: str, new_state: bool):
        """Update state for a specific device in a hub"""
        if hub_id in self.hubs:
            self.hubs[hub_id].update_device_state(device_id, new_state)
    
    def stop_all(self):
        """Stop all hub threads"""
        for hub in self.hubs.values():
            hub.stop()