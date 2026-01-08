"""
Content Service for the Cognitive AI Learning Platform.

Handles generation of detailed notes and concise cheat sheets for modules.
Integrates with LLM service and cache service for content generation and persistence.
"""

import re
import logging
from typing import Optional, Dict, Any

from app.models import Module
from app.services.llm_service import LLMService
from app.services.cache_service import CacheService

logger = logging.getLogger(__name__)


class ContentService:
    """
    Service for generating and managing module content.
    
    Responsibilities:
    - Generate detailed notes for modules
    - Generate concise cheat sheets for modules
    - Sanitize output for UI safety
    - Integrate with cache for persistence
    """
    
    def __init__(
        self,
        llm_service: Optional[LLMService] = None,
        cache_service: Optional[CacheService] = None
    ):
        """
        Initialize the content service.
        
        Args:
            llm_service: LLM service instance for content generation
            cache_service: Cache service instance for persistence
        """
        self.llm_service = llm_service or LLMService()
        self.cache_service = cache_service or CacheService()
        logger.info("ContentService initialized")
    
    def sanitize_output_for_ui(self, text: str) -> str:
        """
        Sanitize generated content to be UI-safe.
        
        Removes or escapes characters that could break UI rendering.
        
        Args:
            text: Raw generated text
            
        Returns:
            Sanitized text safe for UI display
        """
        if not text:
            return ""
        
        # Remove control characters except newlines and tabs
        sanitized = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)
        
        # Normalize excessive newlines (more than 3 consecutive)
        sanitized = re.sub(r'\n{4,}', '\n\n\n', sanitized)
        
        # Remove any potential HTML/script tags for safety
        sanitized = re.sub(r'<script[^>]*>.*?</script>', '', sanitized, flags=re.DOTALL | re.IGNORECASE)
        sanitized = re.sub(r'<style[^>]*>.*?</style>', '', sanitized, flags=re.DOTALL | re.IGNORECASE)
        
        # Trim excessive whitespace
        sanitized = sanitized.strip()
        
        logger.debug(f"Sanitized text: {len(text)} -> {len(sanitized)} characters")
        return sanitized
    
    def generate_notes(
        self,
        module: Module,
        input_text: str
    ) -> str:
        """
        Generate detailed notes for a module.
        
        Args:
            module: Module object with topic details
            input_text: Source educational content
            
        Returns:
            Generated and sanitized notes
            
        Raises:
            ValueError: If module or input_text is invalid
            RuntimeError: If LLM service fails
        """
        if not module or not hasattr(module, 'module_id') or not module.module_id:
            raise ValueError("Invalid module provided")
        
        logger.info(f"Generating notes for module: {module.module_id} ({module.topic_name})")
        
        if not input_text or len(input_text) < 10:
            raise ValueError("Input text is too short or empty")
        
        try:
            # Prepare module info for LLM
            module_info = {
                "topic_name": module.topic_name,
                "estimated_hours": module.estimated_hours,
                "order": module.order
            }
            
            # Generate notes using LLM
            raw_notes = self.llm_service.generate_notes_llm(
                module_info=module_info,
                content=input_text
            )
            
            # Sanitize for UI safety
            sanitized_notes = self.sanitize_output_for_ui(raw_notes)
            
            if not sanitized_notes:
                raise RuntimeError("Generated notes are empty after sanitization")
            
            logger.info(f"Notes generated successfully for {module.module_id}")
            return sanitized_notes
            
        except Exception as e:
            logger.error(f"Failed to generate notes for {module.module_id}: {str(e)}")
            raise
    
    def generate_cheat_sheet(
        self,
        module: Module,
        input_text: str
    ) -> str:
        """
        Generate a concise cheat sheet for a module.
        
        Args:
            module: Module object with topic details
            input_text: Source educational content
            
        Returns:
            Generated and sanitized cheat sheet
            
        Raises:
            ValueError: If module or input_text is invalid
            RuntimeError: If LLM service fails
        """
        if not module or not hasattr(module, 'module_id') or not module.module_id:
            raise ValueError("Invalid module provided")
        
        logger.info(f"Generating cheat sheet for module: {module.module_id} ({module.topic_name})")
        
        if not input_text or len(input_text) < 10:
            raise ValueError("Input text is too short or empty")
        
        try:
            # Prepare module info for LLM
            module_info = {
                "topic_name": module.topic_name,
                "estimated_hours": module.estimated_hours,
                "order": module.order
            }
            
            # Generate cheat sheet using LLM
            raw_cheat_sheet = self.llm_service.generate_cheatsheet_llm(
                module_info=module_info,
                content=input_text
            )
            
            # Sanitize for UI safety
            sanitized_cheat_sheet = self.sanitize_output_for_ui(raw_cheat_sheet)
            
            if not sanitized_cheat_sheet:
                raise RuntimeError("Generated cheat sheet is empty after sanitization")
            
            logger.info(f"Cheat sheet generated successfully for {module.module_id}")
            return sanitized_cheat_sheet
            
        except Exception as e:
            logger.error(f"Failed to generate cheat sheet for {module.module_id}: {str(e)}")
            raise
