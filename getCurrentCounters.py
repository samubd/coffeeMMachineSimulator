"""
Coffee Machine Counters Module

This module provides functionality to get current coffee counters
for the coffee machine simulator using the centralized API client.
"""

from astarte_api_client import AstarteAPIClient
from typing import Dict, Any, Optional


def getCurrentCounters() -> Optional[Dict[str, Any]]:
    """
    Get the current coffee counters for the coffee machine.
    
    This function retrieves current counters from the it.d8pro.device.Counters02
    interface using the centralized Astarte API client.
    
    Returns:
        dict: Dictionary containing current counter values, or None if failed
    """
    try:
        # Create API client instance
        api_client = AstarteAPIClient()
        
        # Get current counters
        counters_data = api_client.get_current_counters()
        
        if counters_data:
            print("Counters retrieved successfully")
            return counters_data
        else:
            print("Failed to retrieve counters")
            return None
            
    except Exception as e:
        print(f"Error in getCurrentCounters: {e}")
        return None
