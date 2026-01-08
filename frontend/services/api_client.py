"""
Base API client for communicating with the backend.

Provides HTTP methods with error handling, timeout management,
and response parsing.
"""

import requests
from typing import Optional, Dict, Any
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import config


class APIClient:
    """
    Base API client for backend communication.
    
    Handles all HTTP requests with consistent error handling,
    timeout management, and response parsing.
    """
    
    def __init__(self, base_url: Optional[str] = None, timeout: Optional[int] = None):
        """
        Initialize API client.
        
        Args:
            base_url: Backend base URL (defaults to config)
            timeout: Request timeout in seconds (defaults to config)
        """
        self.base_url = base_url or config.get_backend_url()
        self.timeout = timeout or config.get_api_timeout()
        self.session = requests.Session()
    
    def _build_url(self, endpoint: str) -> str:
        """
        Build full URL from endpoint.
        
        Args:
            endpoint: API endpoint (e.g., '/api/session')
            
        Returns:
            Full URL
        """
        # Remove leading slash if present
        endpoint = endpoint.lstrip('/')
        return f"{self.base_url}/{endpoint}"
    
    def _handle_response(self, response: requests.Response) -> Dict[str, Any]:
        """
        Handle API response and extract JSON data.
        
        Args:
            response: HTTP response object
            
        Returns:
            Parsed JSON response
            
        Raises:
            requests.HTTPError: If response status is not successful
        """
        try:
            response.raise_for_status()
            return response.json()
        except requests.exceptions.JSONDecodeError:
            # If response is not JSON, return empty dict
            return {"success": True, "message": "Operation completed"}
        except requests.exceptions.HTTPError as e:
            # Try to extract error message from response
            try:
                error_data = response.json()
                error_msg = error_data.get('message', str(e))
            except:
                error_msg = str(e)
            
            raise requests.HTTPError(f"API Error: {error_msg}", response=response)
    
    def get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Make GET request to API.
        
        Args:
            endpoint: API endpoint
            params: Query parameters
            
        Returns:
            Parsed JSON response
            
        Raises:
            requests.RequestException: If request fails
        """
        url = self._build_url(endpoint)
        
        try:
            response = self.session.get(
                url,
                params=params,
                timeout=self.timeout
            )
            return self._handle_response(response)
        except requests.exceptions.Timeout:
            raise requests.Timeout(f"Request to {endpoint} timed out after {self.timeout} seconds")
        except requests.exceptions.ConnectionError:
            raise requests.ConnectionError(f"Failed to connect to backend at {self.base_url}")
        except requests.exceptions.RequestException as e:
            raise requests.RequestException(f"Request failed: {str(e)}")
    
    def post(
        self,
        endpoint: str,
        json_data: Optional[Dict[str, Any]] = None,
        files: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Make POST request to API.
        
        Args:
            endpoint: API endpoint
            json_data: JSON data to send
            files: Files to upload
            data: Form data to send
            
        Returns:
            Parsed JSON response
            
        Raises:
            requests.RequestException: If request fails
        """
        url = self._build_url(endpoint)
        
        try:
            response = self.session.post(
                url,
                json=json_data,
                files=files,
                data=data,
                timeout=self.timeout
            )
            return self._handle_response(response)
        except requests.exceptions.Timeout:
            raise requests.Timeout(f"Request to {endpoint} timed out after {self.timeout} seconds")
        except requests.exceptions.ConnectionError:
            raise requests.ConnectionError(f"Failed to connect to backend at {self.base_url}")
        except requests.exceptions.RequestException as e:
            raise requests.RequestException(f"Request failed: {str(e)}")
    
    def delete(self, endpoint: str) -> Dict[str, Any]:
        """
        Make DELETE request to API.
        
        Args:
            endpoint: API endpoint
            
        Returns:
            Parsed JSON response
            
        Raises:
            requests.RequestException: If request fails
        """
        url = self._build_url(endpoint)
        
        try:
            response = self.session.delete(
                url,
                timeout=self.timeout
            )
            return self._handle_response(response)
        except requests.exceptions.Timeout:
            raise requests.Timeout(f"Request to {endpoint} timed out after {self.timeout} seconds")
        except requests.exceptions.ConnectionError:
            raise requests.ConnectionError(f"Failed to connect to backend at {self.base_url}")
        except requests.exceptions.RequestException as e:
            raise requests.RequestException(f"Request failed: {str(e)}")
    
    def health_check(self) -> bool:
        """
        Check if backend is reachable and healthy.
        
        Returns:
            True if backend is healthy, False otherwise
        """
        try:
            response = self.get("/health")
            return response.get("status") == "healthy"
        except:
            return False


# Global API client instance
api_client = APIClient()
