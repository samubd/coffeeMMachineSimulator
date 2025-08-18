"""
Coffee Machine Recipes Module

This module provides functionality to get current recipes
for all groups using the centralized API client.
"""

from astarte_api_client import AstarteAPIClient
from typing import Dict, Any, Optional


def getCurrentRecipes() -> Optional[Dict[str, Any]]:
    """
    Get the current coffee machine recipes for all groups.
    
    This function retrieves recipes from the recipe service
    for all three groups (group1, group2, group3).
    
    Returns:
        dict: Dictionary containing recipes for all groups, or None if failed
    """
    try:
        # Create API client instance
        api_client = AstarteAPIClient()
        
        # Get recipes for all groups
        all_recipes = {}
        groups = ['group1', 'group2', 'group3']
        
        for group in groups:
            print(f"Getting recipes for {group}...")
            recipes_data = api_client.get_recipes_for_group(group)
            
            if recipes_data:
                all_recipes[group] = recipes_data
                print(f"Recipes for {group} retrieved successfully")
            else:
                print(f"Failed to retrieve recipes for {group}")
                all_recipes[group] = {}
        
        if all_recipes:
            print("All recipes retrieved successfully")
            return all_recipes
        else:
            print("Failed to retrieve any recipes")
            return None
            
    except Exception as e:
        print(f"Error in getCurrentRecipes: {e}")
        return None


if __name__ == "__main__":
    print("Starting recipe retrieval test...")
    recipes = getCurrentRecipes()
    
    if recipes:
        print("\n=== RECIPE RETRIEVAL SUCCESS ===")
        for group, data in recipes.items():
            print(f"\n{group.upper()} recipes:")
            if data:
                print(f"  - Found {len(data)} recipe items" if isinstance(data, (list, dict)) else f"  - Data: {data}")
            else:
                print("  - No recipes found")
    else:
        print("\n=== RECIPE RETRIEVAL FAILED ===")
        print("No recipes were retrieved")
