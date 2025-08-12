"""
Coffee Machine Doses Module

This module provides functionality to get current doses
for the coffee machine simulator using the centralized API client.
"""

from astarte_api_client import AstarteAPIClient
from typing import Dict, Any, Optional


def getCurrentDoses() -> Optional[Dict[str, Any]]:
    """
    Get the current coffee machine doses.
    
    This function retrieves current doses from the it.d8pro.device.Doses02
    interface using the centralized Astarte API client.
    
    Returns:
        dict: Dictionary containing current dose values, or None if failed
    """
    try:
        # Create API client instance
        api_client = AstarteAPIClient()
        
        # Get current doses
        doses_data = api_client.get_current_doses()
        
        if doses_data:
            print("Doses retrieved successfully")
            return doses_data
        else:
            print("Failed to retrieve doses")
            return None
            
    except Exception as e:
        print(f"Error in getCurrentDoses: {e}")
        return None
