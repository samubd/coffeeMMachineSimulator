"""
Coffee Machine Settings Module

This module provides functionality to get current settings
for the coffee machine simulator using the centralized API client.
"""

from astarte_api_client import AstarteAPIClient
from typing import Dict, Any, Optional


def getCurrentSettings() -> Optional[Dict[str, Any]]:
    """
    Get the current coffee machine settings.
    
    This function retrieves current settings from the it.d8pro.device.Settings03
    interface using the centralized Astarte API client.
    
    Returns:
        dict: Dictionary containing current settings values, or None if failed
    """
    try:
        # Create API client instance
        api_client = AstarteAPIClient()
        
        # Get current settings
        settings_data = api_client.get_current_settings()
        
        if settings_data:
            print("Settings retrieved successfully")
            return settings_data
        else:
            print("Failed to retrieve settings")
            return None
            
    except Exception as e:
        print(f"Error in getCurrentSettings: {e}")
        return None
