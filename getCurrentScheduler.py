"""
Get current scheduler settings from Astarte cloud.

This script fetches the current scheduler configuration from the cloud.
If no data exists, it will return default values.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from astarte_api_client_fixed import AstarteAPIClient
import tomllib
from datetime import datetime, timezone

def get_default_scheduler_values():
    """Return default scheduler values."""
    return {
        "/calendarEnabled": False,
        "/ev1Time": 0,
        "/ev1Data": 0,
        "/ev2Time": 0,
        "/ev2Data": 0,
        "/ev3Time": 0,
        "/ev3Data": 0,
        "/ev4Time": 0,
        "/ev4Data": 0,
        "/ev5Time": 0,
        "/ev5Data": 0,
        "/ev6Time": 0,
        "/ev6Data": 0,
        "/ev7Time": 0,
        "/ev7Data": 0,
        "/ev8Time": 0,
        "/ev8Data": 0,
        "/ev9Time": 0,
        "/ev9Data": 0,
        "/ev10Time": 0,
        "/ev10Data": 0
    }

def main():
    # Load configuration
    with open('config.toml', 'rb') as f:
        config = tomllib.load(f)
    
    client = AstarteAPIClient()
    
    interface_name = "it.d8pro.device.Scheduler01"
    device_id = config['DEVICE_ID']
    
    try:
        print(f"Fetching scheduler settings for device {device_id}...")
        
        # Get current scheduler properties from cloud
        current_data = client.get_device_interface_data(device_id, interface_name)
        
        if current_data and 'data' in current_data:
            print("Scheduler settings found in cloud:")
            scheduler_data = current_data['data']
            
            # Ensure all required fields exist, fill missing ones with defaults
            default_values = get_default_scheduler_values()
            for endpoint, default_value in default_values.items():
                if endpoint not in scheduler_data:
                    scheduler_data[endpoint] = default_value
                    print(f"  Added missing {endpoint}: {default_value}")
                else:
                    print(f"  {endpoint}: {scheduler_data[endpoint]}")
            
            return scheduler_data
        else:
            print("No scheduler settings found in cloud, using defaults:")
            default_values = get_default_scheduler_values()
            for endpoint, value in default_values.items():
                print(f"  {endpoint}: {value}")
            return default_values
            
    except Exception as e:
        print(f"Error fetching scheduler settings: {e}")
        print("Using default values:")
        default_values = get_default_scheduler_values()
        for endpoint, value in default_values.items():
            print(f"  {endpoint}: {value}")
        return default_values

if __name__ == "__main__":
    scheduler_data = main()