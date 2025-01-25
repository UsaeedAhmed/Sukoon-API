import paho.mqtt.client as mqtt
import json
from typing import Dict, Optional, Any
import threading
import time
from datetime import datetime

class MQTTService:
    """
    Handles MQTT communication for device power usage streaming.
    Implements singleton pattern to ensure single broker connection.
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(MQTTService, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize MQTT client and connect to broker."""
        if not hasattr(self, 'initialized'):
            # MQTT Client setup
            self.client = mqtt.Client()
            self.client.on_connect = self._on_connect
            self.client.on_publish = self._on_publish
            self.client.on_disconnect = self._on_disconnect

            # Track active device streams
            self.active_streams: Dict[str, threading.Event] = {}
            self.stream_threads: Dict[str, threading.Thread] = {}
            
            # Connect to test broker (replace with your own later)
            try:
                self.client.connect("test.mosquitto.org", 1883, 60)
                self.client.loop_start()
                print("Connected to MQTT broker")
            except Exception as e:
                print(f"Failed to connect to MQTT broker: {e}")
            
            self.initialized = True

    def _on_connect(self, client, userdata, flags, rc):
        """Callback for when the client connects to the broker."""
        if rc == 0:
            print("Connected to MQTT broker successfully")
        else:
            print(f"Failed to connect to MQTT broker with code: {rc}")

    def _on_publish(self, client, userdata, mid):
        """Callback for when a message is published."""
        pass  # Can be used for debugging if needed

    def _on_disconnect(self, client, userdata, rc):
        """Callback for when the client disconnects from the broker."""
        if rc != 0:
            print(f"Unexpected disconnection from MQTT broker: {rc}")
            # Could add reconnection logic here if needed

    def start_device_stream(self, device: Any, interval: float = 1.0):
        """
        Start streaming power usage data for a device.
        
        Args:
            device: Device object with at least id and get_power_usage method
            interval: Update interval in seconds
        """
        if device.id in self.active_streams:
            print(f"Stream already active for device {device.id}")
            return

        # Create stop event for this stream
        stop_event = threading.Event()
        self.active_streams[device.id] = stop_event

        # Start publishing thread for this device
        thread = threading.Thread(
            target=self._publish_device_data,
            args=(device, interval, stop_event),
            daemon=True
        )
        self.stream_threads[device.id] = thread
        thread.start()

        print(f"Started power usage stream for device {device.id}")

    def stop_device_stream(self, device_id: str):
        """Stop streaming data for a device."""
        if device_id in self.active_streams:
            # Signal thread to stop
            self.active_streams[device_id].set()
            
            # Wait for thread to finish
            if device_id in self.stream_threads:
                self.stream_threads[device_id].join(timeout=2.0)
                del self.stream_threads[device_id]
            
            del self.active_streams[device_id]
            print(f"Stopped power usage stream for device {device_id}")

    def _publish_device_data(self, device: Any, interval: float, stop_event: threading.Event):
        """
        Continuously publish device data until stopped.
        
        Args:
            device: Device object
            interval: Update interval in seconds
            stop_event: Event to signal when to stop publishing
        """
        topic = f"smart_home/devices/{device.id}/power_usage"
        
        while not stop_event.is_set():
            try:
                # Get device message - already formatted with all needed data
                message = device.get_mqtt_msg()
                
                # Publish
                self.client.publish(topic, json.dumps(message))
                
                # Wait for next interval or until stopped
                stop_event.wait(interval)
            
            except Exception as e:
                print(f"Error publishing data for device {device.id}: {e}")
                # Add small delay before retry
                time.sleep(1)

    def publish_aggregate(self, hub_id: str, aggregate_data: Dict[str, Any]):
        """
        Publish aggregate power usage data for a hub.
        
        Args:
            hub_id: ID of the hub
            aggregate_data: Dictionary containing aggregate data
        """
        topic = f"smart_home/hubs/{hub_id}/aggregate"
        try:
            message = {
                "hub_id": hub_id,
                **aggregate_data,
                "timestamp": datetime.now().isoformat()
            }
            self.client.publish(topic, json.dumps(message))
        except Exception as e:
            print(f"Error publishing aggregate data for hub {hub_id}: {e}")

    def cleanup(self):
        """Stop all active streams and disconnect."""
        # Stop all active streams
        for device_id in list(self.active_streams.keys()):
            self.stop_device_stream(device_id)
        
        # Disconnect from broker
        self.client.loop_stop()
        self.client.disconnect()
        print("MQTT service cleaned up")