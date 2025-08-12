"""
Astarte API Client Module - FIXED VERSION

This module provides centralized authentication and API access
with aggressive connection isolation to prevent system-wide network issues.
"""

import json
import socket
import ssl
import urllib.request
import urllib.parse
import urllib.error
from typing import Dict, Any, Optional
import time


class AstarteAPIClient:
    """
    Centralized client for Astarte API operations with JWT authentication.
    Uses urllib instead of requests to avoid connection pooling issues.
    """
    
    def __init__(self):
        self.auth_url = 'https://kc-iceberg-1.kalpa.it/realms/sanremodev/protocol/openid-connect/token'
        self.api_base_url = 'https://api-iceberg-1.kalpa.it/appengine/v1/sanremodev/devices'
        self.device_id = 'RDh2VjFfcXF1cGNjc2Uxbw'
        self.auth_data = {
            'username': 'samuele.vecchi',
            'password': '12.T1rzan.21',
            'grant_type': 'password',
            'client_id': 'riseberg-web'
        }
        self.access_token = None
        
        # Set aggressive timeouts
        socket.setdefaulttimeout(10)  # 10 second timeout for all socket operations
        
    def _make_isolated_request(self, url: str, data: Optional[Dict] = None, headers: Optional[Dict] = None, method: str = 'GET') -> Optional[Dict[str, Any]]:
        """
        Make an isolated HTTP request using urllib to avoid connection pooling issues.
        
        Args:
            url: The URL to request
            data: POST data (if any)
            headers: HTTP headers
            method: HTTP method
            
        Returns:
            dict: Response data if successful, None otherwise
        """
        try:
            # Prepare headers
            req_headers = headers or {}
            req_headers.update({
                'User-Agent': 'AstarteAPIClient/1.0',
                'Connection': 'close',  # Force connection close
                'Cache-Control': 'no-cache',
                'Pragma': 'no-cache'
            })
            
            # Prepare request
            if data and method == 'POST':
                # Encode POST data
                post_data = urllib.parse.urlencode(data).encode('utf-8')
                req_headers['Content-Type'] = 'application/x-www-form-urlencoded'
                req_headers['Content-Length'] = str(len(post_data))
            else:
                post_data = None
            
            # Create request
            request = urllib.request.Request(url, data=post_data, headers=req_headers, method=method)
            
            # Create SSL context that doesn't reuse connections
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = True
            ssl_context.verify_mode = ssl.CERT_REQUIRED
            
            # Make request with timeout
            print(f"Making isolated {method} request to: {url}")
            with urllib.request.urlopen(request, timeout=30, context=ssl_context) as response:
                response_data = response.read().decode('utf-8')
                
                if response.status == 200:
                    try:
                        return json.loads(response_data)
                    except json.JSONDecodeError:
                        print(f"Invalid JSON response: {response_data[:200]}...")
                        return None
                else:
                    print(f"HTTP {response.status}: {response_data}")
                    return None
                    
        except urllib.error.HTTPError as e:
            print(f"HTTP Error {e.code}: {e.reason}")
            if e.code == 401:
                return {'http_error': 401}  # Special marker for auth errors
            return None
        except urllib.error.URLError as e:
            print(f"URL Error: {e.reason}")
            return None
        except socket.timeout:
            print(f"Socket timeout for {url}")
            return None
        except Exception as e:
            print(f"Unexpected error for {url}: {e}")
            return None
        finally:
            # Force garbage collection to clean up any lingering connections
            import gc
            gc.collect()
        
    def _get_jwt_token(self) -> Optional[str]:
        """
        Get JWT token for API authentication using isolated request.
        
        Returns:
            str: Access token if successful, None otherwise
        """
        try:
            print("Getting JWT token with isolated request...")
            response_data = self._make_isolated_request(
                self.auth_url, 
                data=self.auth_data, 
                method='POST'
            )
            
            if response_data and 'access_token' in response_data:
                self.access_token = response_data['access_token']
                print("JWT token obtained successfully")
                return self.access_token
            else:
                print("Failed to get JWT token")
                return None
                
        except Exception as e:
            print(f"Error getting JWT token: {e}")
            return None
    
    def _make_authenticated_request(self, endpoint: str) -> Optional[Dict[str, Any]]:
        """
        Make an authenticated GET request to the Astarte API using isolated requests.
        
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
            response_data = self._make_isolated_request(url, headers=headers)
            
            # Handle auth errors
            if response_data and response_data.get('http_error') == 401:
                print("Token expired, refreshing...")
                if self._get_jwt_token():
                    headers['Authorization'] = f'Bearer {self.access_token}'
                    response_data = self._make_isolated_request(url, headers=headers)
                    return response_data
                else:
                    print('Failed to refresh token')
                    return None
            
            return response_data
                
        except Exception as e:
            print(f"Unexpected error for {endpoint}: {e}")
            return None
    
    def get_current_counters(self) -> Optional[Dict[str, Any]]:
        """
        Get current counters from the Counters02 interface.
        
        Returns:
            dict: Counter data if successful, None otherwise
        """
        print("\nCurrent Riseberg deviceID:\t" + self.device_id)
        data = self._make_authenticated_request('interfaces/it.d8pro.device.Counters02/')
        if data:
            print('Counters data retrieved successfully')
        return data
    
    def get_current_settings(self) -> Optional[Dict[str, Any]]:
        """
        Get current settings from the Settings03 interface.
        
        Returns:
            dict: Settings data if successful, None otherwise
        """
        print("\nGetting settings for deviceID:\t" + self.device_id)
        data = self._make_authenticated_request('interfaces/it.d8pro.device.Settings03/')
        if data:
            print('Settings data retrieved successfully')
        return data
    
    def get_current_doses(self) -> Optional[Dict[str, Any]]:
        """
        Get current doses from the Doses02 interface.
        
        Returns:
            dict: Doses data if successful, None otherwise
        """
        print("\nGetting doses for deviceID:\t" + self.device_id)
        data = self._make_authenticated_request('interfaces/it.d8pro.device.Doses02/')
        if data:
            print('Doses data retrieved successfully')
        return data
    
    def get_recipes_for_group(self, group: str) -> Optional[Dict[str, Any]]:
        """
        Get recipes for a specific group from the recipe service using isolated request.
        
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
                'Authorization': f'Bearer {self.access_token}'
            }

            url = f"https://services.sanremomachines.com/backend/recipe-definition/device/{self.device_id}?erogationGroup={group}"
            print(f"Getting recipes for {group} with isolated request...")
            
            response_data = self._make_isolated_request(url, headers=headers)
            
            # Handle auth errors
            if response_data and response_data.get('http_error') == 401:
                print("Token expired, refreshing...")
                if self._get_jwt_token():
                    headers['Authorization'] = f'Bearer {self.access_token}'
                    response_data = self._make_isolated_request(url, headers=headers)
            
            if response_data:
                print(f'Recipes for {group} retrieved successfully')
                return response_data
            else:
                print(f'Failed to retrieve recipes for {group}')
                return None
                
        except Exception as e:
            print(f"Unexpected error getting recipes for {group}: {e}")
            return None
