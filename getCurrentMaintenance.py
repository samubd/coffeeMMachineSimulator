"""
Get Current Maintenance Counters

This module retrieves the current alarm states from the local status file
for the coffee machine simulator.
"""

from astarte_api_client import AstarteAPIClient
from typing import Dict, Any, Optional


def getCurrentMaintenance() -> Optional[Dict[str, Any]]:
    """
    Get the current maintenance counters for the coffee machine getting the interface telemetry slow.
    
    This function retrieves current counters from the it.d8pro.device.TelemetrySlow01
    interface using the centralized Astarte API client.
    
    Returns:
        dict: Dictionary containing current counter values, or None if failed
    """
    try:
        # Create API client instance
        api_client = AstarteAPIClient()
        
        # Get current counters
        maintenance_data = api_client.get_current_maintenance()
        
        if maintenance_data:
            print("maintenance_data retrieved successfully")
            return maintenance_data
        else:
            print("Failed to retrieve maintenance_data")
            return None
            
    except Exception as e:
        print(f"Error in getCurrentMaintenance: {e}")
        return None
