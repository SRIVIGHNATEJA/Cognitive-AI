"""
Input service for handling file uploads and text submissions.

Wraps backend input API endpoints.
"""

from typing import Dict, Any, Optional
from services.api_client import api_client


class InputService:
    """Service for input processing operations."""
    
    def upload_file(self, file_data: bytes, filename: str) -> Dict[str, Any]:
        """
        Upload a file to the backend for processing.
        
        Args:
            file_data: File content as bytes
            filename: Original filename
            
        Returns:
            Response from backend with input_id and processing info
            
        Raises:
            requests.RequestException: If upload fails
        """
        files = {
            'file': (filename, file_data)
        }
        
        return api_client.post('/api/input/upload', files=files)
    
    def submit_text(self, content: str, input_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Submit text content to the backend for processing.
        
        Args:
            content: Text content to process
            input_type: Optional hint for input type (syllabus, question_bank, mixed)
            
        Returns:
            Response from backend with input_id and processing info
            
        Raises:
            requests.RequestException: If submission fails
        """
        json_data = {
            'content': content
        }
        
        if input_type:
            json_data['input_type'] = input_type
        
        return api_client.post('/api/input/text', json_data=json_data)
    
    def get_input_status(self, input_id: str) -> Dict[str, Any]:
        """
        Get the status and details of a processed input.
        
        Args:
            input_id: Input identifier
            
        Returns:
            Input data with extracted text and metadata
            
        Raises:
            requests.RequestException: If request fails
        """
        return api_client.get(f'/api/input/status/{input_id}')


# Global input service instance
input_service = InputService()
