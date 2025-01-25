from fastapi import FastAPI, HTTPException, Depends, Header
from typing import Optional, Dict, Any, List
from datetime import datetime
import uvicorn
import os
from dotenv import load_dotenv

from Utilities.manipulator import Manipulator
from Utilities.database_manager import DatabaseManager

# Load environment variables
load_dotenv()

app = FastAPI(title="Smart Home API")

# Initialize our core services
db_manager = DatabaseManager()
manipulator = Manipulator()


# Get API key from environment variable
API_KEY = os.getenv("API_KEY", "test_api_key_123")

# Dependency for API key verification
async def verify_api_key(x_api_key: str = Header(...)):
    if x_api_key != API_KEY:
        raise HTTPException(
            status_code=401,
            detail="Invalid API key"
        )
    return x_api_key

@app.get("/health")
async def health_check():
    """Basic health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.post("/device/{device_id}/toggle")
async def toggle_device(
    device_id: str,
    hub_id: str,
    new_state: bool,
    api_key: str = Depends(verify_api_key)
):
    """
    Toggle device state
    
    Args:
        device_id: Device identifier
        hub_id: Hub identifier
        new_state: Desired state (true/false)
    """
    try:
        # Update device state in Firebase
        success = db_manager.update_device(device_id, {"state": new_state})
        if not success:
            raise HTTPException(status_code=404, detail="Device not found")
            
        # Update state in manipulator for power tracking
        manipulator.update_device_state(hub_id, device_id, new_state)
        
        return {"success": True, "device_id": device_id, "new_state": new_state}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/device/{device_id}")
async def get_device_status(
    device_id: str,
    api_key: str = Depends(verify_api_key)
):
    """
    Get current device status from Firebase
    
    Args:
        device_id: Device identifier
    """
    try:
        device_data = db_manager.get_device(device_id)
        if not device_data:
            raise HTTPException(status_code=404, detail="Device not found")
            
        return device_data
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/device/{device_id}/power_usage")
async def get_device_power_usage(
    device_id: str,
    hub_id: str,
    api_key: str = Depends(verify_api_key)
):
    """
    Get latest power usage data for device from Firebase
    
    Args:
        device_id: Device identifier
        hub_id: Hub identifier
    """
    try:
        # Get latest hub log from Firebase
        hub_logs = db_manager.read_document(f"hub_logs/{hub_id}/current_day")
        if not hub_logs:
            return {
                "device_id": device_id,
                "power_usage": 0.0,
                "active_minutes": 0,
                "timestamp": datetime.now().isoformat()
            }
        
        # Find the latest log entry
        latest_timestamp = max(hub_logs.keys())
        latest_log = hub_logs[latest_timestamp]
        
        # Get device specific data
        device_data = latest_log.get("devices", {}).get(device_id, {})
        
        return {
            "device_id": device_id,
            "power_usage": device_data.get("power_usage", 0.0),
            "active_minutes": device_data.get("active_minutes", 0),
            "timestamp": latest_log.get("timestamp")
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/hub/{hub_id}/devices")
async def get_hub_devices(
    hub_id: str,
    api_key: str = Depends(verify_api_key)
):
    """
    Get all devices for a hub from Firebase
    
    Args:
        hub_id: Hub identifier
    """
    try:
        hub_data = db_manager.read_document("hubs", hub_id)
        if not hub_data:
            raise HTTPException(status_code=404, detail="Hub not found")
            
        # Get details for each device
        devices = []
        for device_id in hub_data.get("devices", []):
            device_data = db_manager.get_device(device_id)
            if device_data:
                devices.append(device_data)
                
        return devices
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/hub/{hub_id}/power_usage")
async def get_hub_power_usage(
    hub_id: str,
    api_key: str = Depends(verify_api_key)
):
    """
    Get latest power usage data for entire hub from Firebase
    
    Args:
        hub_id: Hub identifier
    """
    try:
        # Get latest hub log
        hub_logs = db_manager.read_document(f"hub_logs/{hub_id}/current_day")
        if not hub_logs:
            return {
                "hub_id": hub_id,
                "total_usage": 0.0,
                "timestamp": datetime.now().isoformat(),
                "devices": []
            }
        
        # Find the latest log entry
        latest_timestamp = max(hub_logs.keys())
        latest_log = hub_logs[latest_timestamp]
        
        # Format device data
        device_logs = []
        for device_id, device_data in latest_log.get("devices", {}).items():
            device_logs.append({
                "device_id": device_id,
                "power_usage": device_data.get("power_usage", 0.0),
                "active_minutes": device_data.get("active_minutes", 0)
            })
            
        return {
            "hub_id": hub_id,
            "total_usage": latest_log.get("total_usage", 0.0),
            "timestamp": latest_log.get("timestamp"),
            "devices": device_logs
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)