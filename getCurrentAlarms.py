"""
Get Current Alarm States

This module retrieves the current alarm states from the local status file
for the coffee machine simulator.
"""

import json
import os
from typing import Dict, Any, Optional


def getCurrentAlarms() -> Optional[Dict[str, Any]]:
    """
    Retrieve current alarm states from local status file.
    
    Returns:
        Dict containing alarm states if successful, None if no alarms or error
    """
    
    STATUS_FILE = 'status.json'
    
    try:
        if not os.path.exists(STATUS_FILE):
            print(f"No status file found at {STATUS_FILE}. Starting with no alarms.")
            return {}
            
        with open(STATUS_FILE, 'r') as f:
            status_data = json.load(f)
            
        # Extract alarm states from the status data
        if 'alarms' in status_data:
            alarm_states = status_data['alarms']
            print(f"Alarms data: {alarm_states}")
            return alarm_states
        else:
            print("No alarm states found in status file. Starting with no alarms.")
            return {}
            
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON from {STATUS_FILE}: {e}. Starting with no alarms.")
        return {}
    except Exception as e:
        print(f"Error loading alarm states from {STATUS_FILE}: {e}. Starting with no alarms.")
        return {}


if __name__ == "__main__":
    # Test the function
    alarms = getCurrentAlarms()
    if alarms:
        print("Retrieved alarm states:")
        for alarm_path, state in alarms.items():
            print(f"  {alarm_path}: {state}")
    else:
        print("No alarm states retrieved.")
