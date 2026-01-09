"""
Content service for the Cognitive AI Learning Platform frontend.

Handles API calls for generating and retrieving module content (notes and cheat sheets).
"""

from typing import Dict, Any, Optional
from .api_client import api_client


class ContentService:
    """Service for content-related API operations."""
    
    def __init__(self):
        """Initialize the content service."""
        self.client = api_client
    
    def generate_notes(self, module_id: str) -> Dict[str, Any]:
        """
        Generate detailed notes for a module.
        
        Args:
            module_id: The module ID to generate notes for
            
        Returns:
            Dictionary containing:
                - success: bool
                - module_id: str
                - notes: str (markdown formatted)
                - cached: bool
                
        Raises:
            Exception: If API call fails
        """
        endpoint = f"/api/content/notes/{module_id}"
        response = self.client.post(endpoint)
        return response
    
    def generate_cheatsheet(self, module_id: str) -> Dict[str, Any]:
        """
        Generate a cheat sheet for a module.
        
        Args:
            module_id: The module ID to generate cheat sheet for
            
        Returns:
            Dictionary containing:
                - success: bool
                - module_id: str
                - cheat_sheet: str (markdown formatted)
                - cached: bool
                
        Raises:
            Exception: If API call fails
        """
        endpoint = f"/api/content/cheatsheet/{module_id}"
        response = self.client.post(endpoint)
        return response
    
    def get_notes(self, module_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve cached notes for a module.
        
        Args:
            module_id: The module ID to retrieve notes for
            
        Returns:
            Dictionary containing notes data, or None if not cached
            
        Raises:
            Exception: If API call fails
        """
        endpoint = f"/api/content/notes/{module_id}"
        try:
            response = self.client.get(endpoint)
            return response
        except Exception as e:
            # 404 means not cached, return None
            if "404" in str(e):
                return None
            raise
    
    def get_cheatsheet(self, module_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve cached cheat sheet for a module.
        
        Args:
            module_id: The module ID to retrieve cheat sheet for
            
        Returns:
            Dictionary containing cheat sheet data, or None if not cached
            
        Raises:
            Exception: If API call fails
        """
        endpoint = f"/api/content/cheatsheet/{module_id}"
        try:
            response = self.client.get(endpoint)
            return response
        except Exception as e:
            # 404 means not cached, return None
            if "404" in str(e):
                return None
            raise


# Global content service instance
content_service = ContentService()
