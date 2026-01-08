"""
Frontend Configuration for Cognitive AI Learning Platform.

Loads configuration from environment variables with sensible defaults.
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class FrontendConfig:
    """Frontend configuration settings."""
    
    # Backend API Configuration
    BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
    API_TIMEOUT = int(os.getenv("API_TIMEOUT", "180"))  # 3 minutes for LLM calls
    
    # UI Configuration
    PAGE_TITLE = os.getenv("PAGE_TITLE", "Cognitive AI Learning Platform")
    PAGE_ICON = os.getenv("PAGE_ICON", "🧠")
    LAYOUT = "wide"
    
    # File Upload Configuration
    MAX_FILE_SIZE_MB = 10
    SUPPORTED_FORMATS = ["pdf", "ppt", "pptx", "doc", "docx"]
    
    # Quiz Configuration
    DEFAULT_QUIZ_TIME_LIMIT = 600  # 10 minutes in seconds
    
    # Pagination
    MODULES_PER_PAGE = 10
    QUESTIONS_PER_PAGE = 1  # One question at a time
    
    # Analytics
    WEAK_AREA_THRESHOLD = 60.0  # Percentage
    
    @classmethod
    def get_backend_url(cls) -> str:
        """Get the backend URL."""
        return cls.BACKEND_URL
    
    @classmethod
    def get_api_timeout(cls) -> int:
        """Get the API timeout in seconds."""
        return cls.API_TIMEOUT
    
    @classmethod
    def validate_file_format(cls, filename: str) -> bool:
        """
        Validate if file format is supported.
        
        Args:
            filename: Name of the file
            
        Returns:
            True if format is supported, False otherwise
        """
        if not filename:
            return False
        
        file_ext = filename.split('.')[-1].lower()
        return file_ext in cls.SUPPORTED_FORMATS
    
    @classmethod
    def validate_file_size(cls, file_size_bytes: int) -> bool:
        """
        Validate if file size is within limits.
        
        Args:
            file_size_bytes: File size in bytes
            
        Returns:
            True if size is within limits, False otherwise
        """
        file_size_mb = file_size_bytes / (1024 * 1024)
        return file_size_mb <= cls.MAX_FILE_SIZE_MB
    
    @classmethod
    def get_file_size_mb(cls, file_size_bytes: int) -> float:
        """
        Convert file size from bytes to MB.
        
        Args:
            file_size_bytes: File size in bytes
            
        Returns:
            File size in MB
        """
        return file_size_bytes / (1024 * 1024)


# Global config instance
config = FrontendConfig()
