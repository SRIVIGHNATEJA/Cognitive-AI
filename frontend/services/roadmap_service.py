"""
Roadmap service for generating and managing learning roadmaps.

Wraps backend roadmap API endpoints.
"""

from typing import Dict, Any
from services.api_client import api_client


class RoadmapService:
    """Service for roadmap operations."""
    
    def generate_roadmap(self, input_id: str, mode: str = "untimed") -> Dict[str, Any]:
        """
        Generate a learning roadmap from processed input.
        
        Args:
            input_id: Input identifier to generate roadmap from
            mode: Learning mode - "timed" or "untimed"
            
        Returns:
            Response from backend with modules and roadmap info
            
        Raises:
            requests.RequestException: If generation fails
        """
        json_data = {
            'input_id': input_id,
            'mode': mode
        }
        
        return api_client.post('/api/roadmap/generate', json_data=json_data)
    
    def get_roadmap(self) -> Dict[str, Any]:
        """
        Get the current cached roadmap.
        
        Returns:
            Roadmap data with modules
            
        Raises:
            requests.RequestException: If request fails
        """
        return api_client.get('/api/roadmap')
    
    def delete_roadmap(self) -> Dict[str, Any]:
        """
        Delete the current roadmap.
        
        Returns:
            Success response
            
        Raises:
            requests.RequestException: If deletion fails
        """
        return api_client.delete('/api/roadmap')


# Global roadmap service instance
roadmap_service = RoadmapService()
