"""
Coffee Machine Counters Module

This module provides functionality to get current coffee counters
for the coffee machine simulator using the centralized API client.
"""

from astarte_api_client import AstarteAPIClient
from typing import Dict, Any, Optional
import time


def getCurrentCounters(max_retries: int = 3, retry_delay: float = 2.0) -> Optional[Dict[str, Any]]:
    """
    Get the current coffee counters for the coffee machine with retry logic.

    This function retrieves current counters from the it.d8pro.device.Counters02
    interface using the centralized Astarte API client. It implements exponential
    backoff retry strategy to handle transient network failures.

    Args:
        max_retries: Maximum number of retry attempts (default: 3)
        retry_delay: Initial delay between retries in seconds (default: 2.0)

    Returns:
        dict: Dictionary containing current counter values, or None if failed
    """
    for attempt in range(max_retries):
        try:
            print(f"Attempting to retrieve counters from server (attempt {attempt + 1}/{max_retries})...")

            # Create API client instance
            api_client = AstarteAPIClient()

            # Get current counters
            counters_data = api_client.get_current_counters()

            if counters_data and 'data' in counters_data:
                print(f"✓ Counters retrieved successfully from server on attempt {attempt + 1}")
                return counters_data
            else:
                print(f"✗ Failed to retrieve counters (attempt {attempt + 1}/{max_retries}): Empty or invalid response")

        except Exception as e:
            print(f"✗ Error retrieving counters (attempt {attempt + 1}/{max_retries}): {e}")

        # If not last attempt, wait before retrying with exponential backoff
        if attempt < max_retries - 1:
            wait_time = retry_delay * (2 ** attempt)  # Exponential backoff: 2s, 4s, 8s
            print(f"  Retrying in {wait_time:.1f} seconds...")
            time.sleep(wait_time)

    print(f"✗ Failed to retrieve counters from server after {max_retries} attempts")
    return None
