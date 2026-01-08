"""
Roadmap API Router for the Cognitive AI Learning Platform.

Provides endpoints for generating, retrieving, and resetting learning roadmaps.
"""

import logging
from fastapi import APIRouter, HTTPException, status
from typing import Dict, Any

from app.models import (
    RoadmapGenerateRequest,
    RoadmapResponse,
    SuccessResponse,
    ErrorResponse,
    ErrorType,
    Module,
    LearningMode
)
from app.services.roadmap_service import RoadmapService
from app.services.cache_service import CacheService
from app.services.input_service import InputService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/roadmap", tags=["roadmap"])

# Service instances
roadmap_service = RoadmapService()
cache_service = CacheService()
input_service = InputService()


@router.post("/generate", response_model=RoadmapResponse, status_code=status.HTTP_200_OK)
async def generate_roadmap(request: RoadmapGenerateRequest) -> RoadmapResponse:
    """
    Generate a learning roadmap from processed input.
    
    This endpoint:
    1. Checks if a roadmap already exists in cache (returns cached version)
    2. Validates that the input_id exists
    3. Generates a new roadmap using LLM if not cached
    4. Caches the generated roadmap permanently
    5. Returns the roadmap with module details
    
    Args:
        request: Roadmap generation request with input_id and mode
        
    Returns:
        RoadmapResponse with list of modules and metadata
        
    Raises:
        HTTPException 404: If input_id not found
        HTTPException 503: If LLM service fails
        HTTPException 500: If roadmap generation fails
    """
    try:
        logger.info(f"Roadmap generation requested for input_id: {request.input_id}")
        
        # Check if roadmap already exists in cache
        cached_roadmap = cache_service.get_cached_roadmap()
        if cached_roadmap:
            logger.info("Returning cached roadmap")
            return RoadmapResponse(
                success=True,
                modules=[Module(**m) for m in cached_roadmap["modules"]],
                total_modules=cached_roadmap["total_modules"],
                total_estimated_hours=cached_roadmap["total_estimated_hours"],
                mode=LearningMode(cached_roadmap["mode"]),
                cached=True
            )
        
        # Validate input_id exists
        input_data = input_service.get_input_status(request.input_id)
        if not input_data:
            logger.error(f"Input not found: {request.input_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Input with ID '{request.input_id}' not found. Please upload or process input first."
            )
        
        # Get cached input text
        cached_input = cache_service.get_cached_data(request.input_id, 'input')
        if not cached_input or 'extracted_text' not in cached_input:
            logger.error(f"Input text not found in cache: {request.input_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Input text not found for ID '{request.input_id}'"
            )
        
        input_text = cached_input['extracted_text']
        
        # Generate roadmap using LLM
        logger.info(f"Generating new roadmap in {request.mode} mode")
        modules = roadmap_service.generate_roadmap(
            input_text=input_text,
            mode=request.mode,
            input_id=request.input_id
        )
        
        # Calculate totals
        total_modules = len(modules)
        total_estimated_hours = sum(m.estimated_hours for m in modules)
        
        # Cache the roadmap
        roadmap_data = {
            "modules": [m.model_dump() for m in modules],
            "total_modules": total_modules,
            "total_estimated_hours": total_estimated_hours,
            "mode": request.mode.value,
            "input_id": request.input_id
        }
        cache_service.cache_roadmap(roadmap_data)
        
        logger.info(f"Roadmap generated successfully: {total_modules} modules, {total_estimated_hours} hours")
        
        return RoadmapResponse(
            success=True,
            modules=modules,
            total_modules=total_modules,
            total_estimated_hours=total_estimated_hours,
            mode=request.mode,
            cached=False
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except ValueError as e:
        # Validation or generation errors
        logger.error(f"Roadmap generation validation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Roadmap generation failed: {str(e)}"
        )
    except RuntimeError as e:
        # LLM service errors
        logger.error(f"LLM service error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"LLM service unavailable: {str(e)}. Please ensure Ollama is running."
        )
    except Exception as e:
        # Unexpected errors
        logger.error(f"Unexpected error generating roadmap: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while generating the roadmap"
        )


@router.get("", response_model=RoadmapResponse, status_code=status.HTTP_200_OK)
async def get_roadmap() -> RoadmapResponse:
    """
    Retrieve the cached roadmap for the current session.
    
    Returns:
        RoadmapResponse with cached roadmap data
        
    Raises:
        HTTPException 404: If no roadmap exists in cache
    """
    try:
        logger.info("Roadmap retrieval requested")
        
        # Get cached roadmap
        cached_roadmap = cache_service.get_cached_roadmap()
        if not cached_roadmap:
            logger.info("No roadmap found in cache")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No roadmap found. Please generate a roadmap first."
            )
        
        logger.info("Returning cached roadmap")
        return RoadmapResponse(
            success=True,
            modules=[Module(**m) for m in cached_roadmap["modules"]],
            total_modules=cached_roadmap["total_modules"],
            total_estimated_hours=cached_roadmap["total_estimated_hours"],
            mode=LearningMode(cached_roadmap["mode"]),
            cached=True
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving roadmap: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while retrieving the roadmap"
        )


@router.delete("", response_model=SuccessResponse, status_code=status.HTTP_200_OK)
async def reset_roadmap() -> SuccessResponse:
    """
    Reset (delete) the cached roadmap.
    
    This allows regenerating a new roadmap from the same or different input.
    
    Returns:
        SuccessResponse confirming the reset
    """
    try:
        logger.info("Roadmap reset requested")
        
        # Clear roadmap cache
        deleted_count = cache_service.clear_cache('roadmap')
        
        if deleted_count > 0:
            logger.info(f"Roadmap cache cleared: {deleted_count} files deleted")
            return SuccessResponse(
                success=True,
                message=f"Roadmap cache cleared successfully. {deleted_count} file(s) deleted."
            )
        else:
            logger.info("No roadmap found to clear")
            return SuccessResponse(
                success=True,
                message="No roadmap found in cache."
            )
        
    except Exception as e:
        logger.error(f"Error resetting roadmap: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while resetting the roadmap"
        )
