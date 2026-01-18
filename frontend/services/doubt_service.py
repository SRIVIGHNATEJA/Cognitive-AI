"""
Doubt service for frontend - handles doubt/question submission to backend.
"""

import requests
from typing import Dict, Any
import logging

from config import config

logger = logging.getLogger(__name__)


class DoubtService:
    """Service for submitting doubts/questions to the backend."""
    
    def __init__(self):
        """Initialize the doubt service."""
        self.base_url = config.BACKEND_URL
        logger.info(f"DoubtService initialized with base URL: {self.base_url}")
    
    def ask_doubt(self, module_id: str, question: str) -> Dict[str, Any]:
        """
        Submit a doubt/question to the backend.
        
        Args:
            module_id: Module identifier
            question: User's question
            
        Returns:
            Response dictionary with answer and scope information
            
        Raises:
            requests.RequestException: If the request fails
        """
        logger.info(f"Submitting doubt for module '{module_id}'")
        
        url = f"{self.base_url}/api/doubt/ask"
        payload = {
            "module_id": module_id,
            "question": question
        }
        
        try:
            response = requests.post(url, json=payload, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            logger.info(f"Doubt answered successfully (in_scope: {result.get('in_scope', False)})")
            
            return result
            
        except requests.Timeout:
            logger.error("Doubt request timed out")
            raise
        except requests.RequestException as e:
            logger.error(f"Failed to submit doubt: {str(e)}")
            raise


# Global doubt service instance
doubt_service = DoubtService()

