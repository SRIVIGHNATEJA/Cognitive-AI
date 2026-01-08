"""
Logging configuration for the Cognitive AI Learning Platform.
Sets up structured logging with appropriate levels and formats.
"""

import logging
import sys
from app.config import settings


def setup_logging() -> None:
    """
    Configure application-wide logging.
    
    Sets up console logging with the format and level specified in settings.
    All loggers will inherit this configuration.
    """
    # Get log level from settings
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)
    
    # Configure root logger
    logging.basicConfig(
        level=log_level,
        format=settings.log_format,
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Set specific log levels for third-party libraries to reduce noise
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    
    logger = logging.getLogger(__name__)
    logger.info(f"Logging configured with level: {settings.log_level}")


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for a specific module.
    
    Args:
        name: Name of the module (typically __name__)
        
    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)
