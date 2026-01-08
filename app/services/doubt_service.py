"""
Doubt Service for the Cognitive AI Learning Platform.

Handles context-aware question answering with scope detection.
Integrates with LLM service and cache service for module content retrieval.
"""

import logging
from typing import Dict, Any, Optional

from app.services.llm_service import LLMService, LLMServiceError
from app.services.cache_service import CacheService

logger = logging.getLogger(__name__)


class DoubtService:
    """
    Service for answering student questions about modules.
    
    Responsibilities:
    - Answer questions using module content as context
    - Detect if questions are within module scope
    - Provide helpful responses for in-scope questions
    - Politely decline out-of-scope questions
    """
    
    def __init__(
        self,
        llm_service: Optional[LLMService] = None,
        cache_service: Optional[CacheService] = None
    ):
        """
        Initialize the doubt service.
        
        Args:
            llm_service: LLM service instance for question answering
            cache_service: Cache service instance for content retrieval
        """
        self.llm_service = llm_service or LLMService()
        self.cache_service = cache_service or CacheService()
        logger.info("DoubtService initialized")
    
    def answer_doubt(
        self,
        module_id: str,
        module_info: Dict[str, Any],
        question: str
    ) -> Dict[str, Any]:
        """
        Answer a student's question about a module.
        
        Uses module content (notes or input text) as context for answering.
        Determines if the question is within the module scope.
        
        Args:
            module_id: Module identifier
            module_info: Dictionary with module details (topic_name, etc.)
            question: Student's question
            
        Returns:
            Dictionary with 'answer' and 'in_scope' keys
            
        Raises:
            ValueError: If module content not found
            LLMServiceError: If LLM fails to generate answer
        """
        logger.info(f"Answering doubt for module '{module_id}': {question[:50]}...")
        
        # Get module content for context
        module_content = self._get_module_content(module_id)
        
        if not module_content:
            error_msg = (
                f"No content available for module '{module_id}'. "
                "Please generate notes for this module first."
            )
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        logger.debug(f"Using {len(module_content)} characters of module content as context")
        
        # Check question scope and get answer from LLM
        try:
            result = self.check_question_scope(
                module_info=module_info,
                question=question,
                module_content=module_content
            )
            
            logger.info(
                f"Question answered successfully "
                f"(in_scope: {result.get('in_scope', False)})"
            )
            
            return result
            
        except LLMServiceError as e:
            logger.error(f"LLM service error while answering doubt: {str(e)}")
            raise
    
    def check_question_scope(
        self,
        module_info: Dict[str, Any],
        question: str,
        module_content: str
    ) -> Dict[str, Any]:
        """
        Check if a question is within module scope and provide an answer.
        
        Uses the LLM to:
        1. Determine if the question relates to the module topic
        2. Provide a helpful answer if in scope
        3. Politely decline if out of scope
        
        Args:
            module_info: Dictionary with module details (topic_name, etc.)
            question: Student's question
            module_content: Module content for context
            
        Returns:
            Dictionary with 'answer' and 'in_scope' keys
            
        Raises:
            LLMServiceError: If LLM fails to process the question
        """
        logger.debug(f"Checking question scope for: {question[:50]}...")
        
        try:
            # Use LLM to answer question with scope detection
            result = self.llm_service.answer_question_llm(
                module_info=module_info,
                question=question,
                module_content=module_content
            )
            
            in_scope = result.get("in_scope", False)
            answer = result.get("answer", "")
            
            if in_scope:
                logger.info("Question is within module scope")
            else:
                logger.info("Question is outside module scope")
            
            return {
                "answer": answer,
                "in_scope": in_scope
            }
            
        except LLMServiceError as e:
            logger.error(f"Failed to check question scope: {str(e)}")
            raise
    
    def _get_module_content(self, module_id: str) -> Optional[str]:
        """
        Retrieve module content for use as context.
        
        Tries to get cached notes first, falls back to input text if needed.
        
        Args:
            module_id: Module identifier
            
        Returns:
            Module content string, or None if not found
        """
        logger.debug(f"Retrieving content for module '{module_id}'")
        
        # Try to get cached notes first
        notes = self.cache_service.get_cached_content(module_id, 'notes')
        if notes:
            logger.debug(f"Using cached notes ({len(notes)} characters)")
            return notes
        
        # Fall back to input text
        logger.debug("Notes not found, attempting to use input text")
        
        # Get roadmap to find input_id
        roadmap_data = self.cache_service.get_cached_roadmap()
        if not roadmap_data or "input_id" not in roadmap_data:
            logger.warning("No roadmap or input_id found")
            return None
        
        input_id = roadmap_data["input_id"]
        cached_input = self.cache_service.get_cached_data(input_id, 'input')
        
        if cached_input and 'extracted_text' in cached_input:
            input_text = cached_input['extracted_text']
            logger.debug(f"Using input text ({len(input_text)} characters)")
            return input_text
        
        logger.warning(f"No content found for module '{module_id}'")
        return None


# Global doubt service instance
doubt_service = DoubtService()
