"""
Astarte API Client Module

This module provides centralized authentication and API access
for retrieving counters and settings from the Astarte platform.
"""

import requests
import json
import os
from typing import Dict, Any, Optional
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class AstarteAPIClient:
    """
    Centralized client for Astarte API operations with JWT authentication.
    Includes proper connection management and timeout handling to prevent system-wide network issues.
    """
    
    def __init__(self):
        # Load configuration from environment variables
        self.realm = os.getenv('ASTARTE_REALM')
        self.device_id = os.getenv('ASTARTE_DEVICE_ID')
        
        # Build URLs using the realm variable
        self.auth_url = f'https://kc-iceberg-1.kalpa.it/realms/{self.realm}/protocol/openid-connect/token'
        self.api_base_url = f'https://api-iceberg-1.kalpa.it/appengine/v1/{self.realm}/devices'
        
        self.auth_data = {
            'username': os.getenv('ASTARTE_USERNAME'),
            'password': os.getenv('ASTARTE_PASSWORD'),
            'grant_type': os.getenv('ASTARTE_GRANT_TYPE', 'password'),
            'client_id': os.getenv('ASTARTE_CLIENT_ID')
        }
        
        # Validate that all required environment variables are set
        required_vars = [
            ('username', self.auth_data['username']),
            ('password', self.auth_data['password']),
            ('client_id', self.auth_data['client_id']),
            ('realm', self.realm),
            ('device_id', self.device_id)
        ]
        
        missing_vars = [var_name for var_name, var_value in required_vars if not var_value]
        if missing_vars:
            raise ValueError(f"Missing required environment variables: {missing_vars}. Please check your .env file.")
        self.access_token = None
        
        # Create a session with proper configuration
        self.session = self._create_configured_session()
    
    def _create_configured_session(self) -> requests.Session:
        """
        Create a properly configured requests session with timeouts and retry logic.
        
        Returns:
            requests.Session: Configured session
        """
        session = requests.Session()
        
        # Configure retry strategy
        retry_strategy = Retry(
            total=3,  # Total number of retries
            status_forcelist=[429, 500, 502, 503, 504],  # HTTP status codes to retry on
            backoff_factor=1,  # Wait time between retries
            raise_on_status=False  # Don't raise exception on retry failure
        )
        
        # Configure HTTP adapter with retry strategy
        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=10,  # Number of connection pools to cache
            pool_maxsize=10,  # Maximum number of connections to save in the pool
            pool_block=False  # Don't block when pool is full
        )
        
        # Mount adapter for both HTTP and HTTPS
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        return session
    
    def __del__(self):
        """
        Cleanup method to properly close the session when the object is destroyed.
        """
        if hasattr(self, 'session'):
            self.session.close()
        
    def _get_jwt_token(self) -> Optional[str]:
        """
        Get JWT token for API authentication.
        
        Returns:
            str: Access token if successful, None otherwise
        """
        try:
            # Use session with timeout for authentication
            response = self.session.post(
                self.auth_url, 
                data=self.auth_data,
                timeout=(10, 30)  # 10s connect, 30s read timeout
            )
            print("JWT request response:\t", response.status_code)
            
            if response.status_code == 200:
                jwt_data = response.json()
                self.access_token = jwt_data['access_token']
                return self.access_token
            else:
                print("Authentication failed:", response.text)
                return None
                
        except requests.exceptions.Timeout as e:
            print(f"Timeout error getting JWT token: {e}")
            return None
        except requests.exceptions.ConnectionError as e:
            print(f"Connection error getting JWT token: {e}")
            return None
        except Exception as e:
            print(f"Error getting JWT token: {e}")
            return None
    
    def _make_authenticated_request(self, endpoint: str) -> Optional[Dict[str, Any]]:
        """
        Make an authenticated GET request to the Astarte API.
        
        Args:
            endpoint: API endpoint (e.g., 'interfaces/it.d8pro.device.Counters02/')
            
        Returns:
            dict: Response data if successful, None otherwise
        """
        try:
            # Get fresh token if needed
            if not self.access_token:
                if not self._get_jwt_token():
                    return None
            
            headers = {
                'Authorization': f'Bearer {self.access_token}'
            }
            
            url = f"{self.api_base_url}/{self.device_id}/{endpoint}"
            print(f"Making request to: {url}")
            
            # Use session with timeout
            response = self.session.get(
                url, 
                headers=headers,
                timeout=(10, 30)  # 10s connect, 30s read timeout
            )
            print(f'GET {endpoint} return code:', response.status_code)
            
            if response.status_code == 200:
                data = response.json()
                return data
            elif response.status_code == 401:
                # Token might be expired, try to refresh
                print("Token expired, refreshing...")
                if self._get_jwt_token():
                    headers['Authorization'] = f'Bearer {self.access_token}'
                    response = self.session.get(
                        url, 
                        headers=headers,
                        timeout=(10, 30)
                    )
                    if response.status_code == 200:
                        return response.json()
                
                print('Authentication error:', response.text)
                return None
            else:
                print(f'Error getting {endpoint}:', response.text)
                return None
                
        except requests.exceptions.Timeout as e:
            print(f"Timeout error for {endpoint}: {e}")
            return None
        except requests.exceptions.ConnectionError as e:
            print(f"Connection error for {endpoint}: {e}")
            return None
        except requests.exceptions.RequestException as e:
            print(f"Request error for {endpoint}: {e}")
            return None
        except Exception as e:
            print(f"Unexpected error for {endpoint}: {e}")
            return None
    
    def get_current_counters(self) -> Optional[Dict[str, Any]]:
        """
        Get current counters from the Counters02 interface.
        
        Returns:
            dict: Counter data if successful, None otherwise
        """
        print(f"\nCurrent Riseberg deviceID:\t{self.device_id}")
        data = self._make_authenticated_request('interfaces/it.d8pro.device.Counters02/')
        if data:
            print('Counters data:', data)
        return data
    
    def get_current_settings(self) -> Optional[Dict[str, Any]]:
        """
        Get current settings from the Settings03 interface.
        
        Returns:
            dict: Settings data if successful, None otherwise
        """
        print(f"\nGetting settings for deviceID:\t{self.device_id}")
        data = self._make_authenticated_request('interfaces/it.d8pro.device.Settings03/')
        if data:
            print('Settings data:', data)
        return data
    
    def get_current_doses(self) -> Optional[Dict[str, Any]]:
        """
        Get current doses from the Doses02 interface.
        
        Returns:
            dict: Doses data if successful, None otherwise
        """
        print(f"\nGetting doses for deviceID:\t{self.device_id}")
        data = self._make_authenticated_request('interfaces/it.d8pro.device.Doses02/')
        if data:
            print('Doses data:', data)
        return data
    
    def get_recipes_for_group(self, group: str) -> Optional[Dict[str, Any]]:
        """
        Get recipes for a specific group from the recipe service.
        
        Args:
            group: Group name (group1, group2, group3)
            
        Returns:
            dict: Recipe data if successful, None otherwise
        """
        try:
            # Get fresh token if needed
            if not self.access_token:
                if not self._get_jwt_token():
                    return None
            
            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Connection': 'close'  # Force connection close to prevent connection pooling issues
            }

            url = f"https://services.sanremomachines.com/backend/recipe-definition/device/{self.device_id}?erogationGroup={group}"
            print(f"Getting recipes for {group} from: {url}")
            
            # Use session with timeout and proper error handling
            response = self.session.get(
                url, 
                headers=headers,
                timeout=(10, 30)  # 10s connect, 30s read timeout
            )
            print(f'GET recipes for {group} return code:', response.status_code)
            
            if response.status_code == 200:
                data = response.json()
                print(f'Recipes data for {group}:', data)
                return data
            elif response.status_code == 401:
                # Token might be expired, try to refresh
                print("Token expired, refreshing...")
                if self._get_jwt_token():
                    headers['Authorization'] = f'Bearer {self.access_token}'
                    response = self.session.get(
                        url, 
                        headers=headers,
                        timeout=(10, 30)
                    )
                    if response.status_code == 200:
                        return response.json()
                
                print('Authentication error:', response.text)
                return None
            else:
                print(f'Error getting recipes for {group}:', response.text)
                return None
                
        except requests.exceptions.Timeout as e:
            print(f"Timeout error for recipes {group}: {e}")
            # Force close any lingering connections
            self.session.close()
            self.session = self._create_configured_session()
            return None
        except requests.exceptions.ConnectionError as e:
            print(f"Connection error for recipes {group}: {e}")
            # Force close any lingering connections
            self.session.close()
            self.session = self._create_configured_session()
            return None
        except requests.exceptions.RequestException as e:
            print(f"Request error for recipes {group}: {e}")
            return None
        except Exception as e:
            print(f"Unexpected error for recipes {group}: {e}")
            return None
