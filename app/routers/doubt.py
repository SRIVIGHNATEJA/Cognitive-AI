"""
Doubt Resolution API Router for the Cognitive AI Learning Platform.

Provides endpoint for asking questions about modules with context-aware answering.
"""

import logging
from fastapi import APIRouter, HTTPException, status, Body
from typing import Dict, Any

from app.models import (
    DoubtRequest,
    DoubtResponse,
    Module
)
from app.services.doubt_service import DoubtService
from app.services.cache_service import CacheService
from app.services.llm_service import LLMServiceError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/doubt", tags=["doubt"])

# Service instances
doubt_service = DoubtService()
cache_service = CacheService()


def _get_module_from_roadmap(module_id: str) -> Module:
    """
    Helper function to get module details from cached roadmap.
    
    Args:
        module_id: Module identifier
        
    Returns:
        Module object
        
    Raises:
        HTTPException 404: If roadmap or module not found
    """
    # Get cached roadmap
    roadmap_data = cache_service.get_cached_roadmap()
    if not roadmap_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No roadmap found. Please generate a roadmap first."
        )
    
    # Find the module
    modules = roadmap_data.get("modules", [])
    for module_data in modules:
        if module_data.get("module_id") == module_id:
            return Module(**module_data)
    
    # Module not found
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Module '{module_id}' not found in roadmap."
    )


@router.post("/ask", response_model=DoubtResponse)
async def ask_doubt(request: DoubtRequest = Body(...)) -> DoubtResponse:
    """
    Ask a question about a module.
    
    Provides context-aware answers using module content (notes or input text).
    Automatically detects if the question is within the module scope.
    
    For in-scope questions:
    - Provides helpful answers based on module content
    - Uses the module topic and content as context
    
    For out-of-scope questions:
    - Politely explains the question is outside module scope
    - Suggests focusing on the module topic
    
    Args:
        request: DoubtRequest with module_id and question
        
    Returns:
        DoubtResponse with answer and scope information
        
    Raises:
        HTTPException 404: If module not found or no content available
        HTTPException 500: If LLM service fails
    """
    try:
        logger.info(f"Received doubt for module '{request.module_id}': {request.question[:50]}...")
        
        # Validate module exists
        module = _get_module_from_roadmap(request.module_id)
        
        # Prepare module info for doubt service
        module_info = {
            "topic_name": module.topic_name,
            "estimated_hours": module.estimated_hours
        }
        
        # Answer the doubt
        try:
            result = doubt_service.answer_doubt(
                module_id=request.module_id,
                module_info=module_info,
                question=request.question
            )
            
            logger.info(
                f"Doubt answered for module '{request.module_id}' "
                f"(in_scope: {result.get('in_scope', False)})"
            )
            
            return DoubtResponse(
                success=True,
                module_id=request.module_id,
                question=request.question,
                answer=result["answer"],
                in_scope=result["in_scope"]
            )
            
        except ValueError as e:
            # Content not found
            logger.error(f"Content not found for module '{request.module_id}': {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e)
            )
        
        except LLMServiceError as e:
            # LLM service error
            logger.error(f"LLM service error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to answer question: {str(e)}"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error answering doubt: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
        )
