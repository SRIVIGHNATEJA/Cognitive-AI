"""
Content API Router for the Cognitive AI Learning Platform.

Provides endpoints for generating and retrieving notes and cheat sheets for modules.
"""

import logging
from fastapi import APIRouter, HTTPException, status

from app.models import (
    NotesResponse,
    CheatSheetResponse,
    ErrorType,
    Module
)
from app.services.content_service import ContentService
from app.services.cache_service import CacheService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/content", tags=["content"])

# Service instances
content_service = ContentService()
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


def _get_input_text() -> str:
    """
    Helper function to get input text from cache.
    
    Returns:
        Input text
        
    Raises:
        HTTPException 404: If input not found
    """
    # Get roadmap to find input_id
    roadmap_data = cache_service.get_cached_roadmap()
    if not roadmap_data or "input_id" not in roadmap_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Input data not found. Please upload input first."
        )
    
    input_id = roadmap_data["input_id"]
    
    # Get cached input
    cached_input = cache_service.get_cached_data(input_id, 'input')
    if not cached_input or 'extracted_text' not in cached_input:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Input text not found for ID '{input_id}'"
        )
    
    return cached_input['extracted_text']


@router.post("/notes/{module_id}", response_model=NotesResponse, status_code=status.HTTP_200_OK)
async def generate_notes(module_id: str) -> NotesResponse:
    """
    Generate detailed notes for a module.
    
    This endpoint:
    1. Checks if notes already exist in cache (returns cached version)
    2. Validates that the module exists in the roadmap
    3. Generates new notes using LLM if not cached
    4. Caches the generated notes permanently
    5. Returns the notes
    
    Args:
        module_id: Module identifier
        
    Returns:
        NotesResponse with generated notes
        
    Raises:
        HTTPException 404: If module or input not found
        HTTPException 503: If LLM service fails
        HTTPException 500: If notes generation fails
    """
    try:
        logger.info(f"Notes generation requested for module: {module_id}")
        
        # Check if notes already exist in cache
        cached_notes = cache_service.get_cached_content(module_id, 'notes')
        if cached_notes:
            logger.info(f"Returning cached notes for module {module_id}")
            return NotesResponse(
                success=True,
                module_id=module_id,
                notes=cached_notes,
                cached=True
            )
        
        # Get module details from roadmap
        module = _get_module_from_roadmap(module_id)
        
        # Get input text
        input_text = _get_input_text()
        
        # Generate notes using content service
        logger.info(f"Generating new notes for module {module_id}")
        notes = content_service.generate_notes(
            module=module,
            input_text=input_text
        )
        
        # Cache the notes
        cache_service.cache_content(module_id, 'notes', notes)
        
        logger.info(f"Notes generated successfully for module {module_id}")
        
        return NotesResponse(
            success=True,
            module_id=module_id,
            notes=notes,
            cached=False
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except ValueError as e:
        # Validation errors
        logger.error(f"Notes generation validation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Notes generation failed: {str(e)}"
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
        logger.error(f"Unexpected error generating notes: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while generating notes"
        )


@router.post("/cheatsheet/{module_id}", response_model=CheatSheetResponse, status_code=status.HTTP_200_OK)
async def generate_cheatsheet(module_id: str) -> CheatSheetResponse:
    """
    Generate a concise cheat sheet for a module.
    
    This endpoint:
    1. Checks if cheat sheet already exists in cache (returns cached version)
    2. Validates that the module exists in the roadmap
    3. Generates new cheat sheet using LLM if not cached
    4. Caches the generated cheat sheet permanently
    5. Returns the cheat sheet
    
    Args:
        module_id: Module identifier
        
    Returns:
        CheatSheetResponse with generated cheat sheet
        
    Raises:
        HTTPException 404: If module or input not found
        HTTPException 503: If LLM service fails
        HTTPException 500: If cheat sheet generation fails
    """
    try:
        logger.info(f"Cheat sheet generation requested for module: {module_id}")
        
        # Check if cheat sheet already exists in cache
        cached_cheatsheet = cache_service.get_cached_content(module_id, 'cheatsheet')
        if cached_cheatsheet:
            logger.info(f"Returning cached cheat sheet for module {module_id}")
            return CheatSheetResponse(
                success=True,
                module_id=module_id,
                cheat_sheet=cached_cheatsheet,
                cached=True
            )
        
        # Get module details from roadmap
        module = _get_module_from_roadmap(module_id)
        
        # Get input text
        input_text = _get_input_text()
        
        # Generate cheat sheet using content service
        logger.info(f"Generating new cheat sheet for module {module_id}")
        cheat_sheet = content_service.generate_cheat_sheet(
            module=module,
            input_text=input_text
        )
        
        # Cache the cheat sheet
        cache_service.cache_content(module_id, 'cheatsheet', cheat_sheet)
        
        logger.info(f"Cheat sheet generated successfully for module {module_id}")
        
        return CheatSheetResponse(
            success=True,
            module_id=module_id,
            cheat_sheet=cheat_sheet,
            cached=False
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except ValueError as e:
        # Validation errors
        logger.error(f"Cheat sheet generation validation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Cheat sheet generation failed: {str(e)}"
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
        logger.error(f"Unexpected error generating cheat sheet: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while generating the cheat sheet"
        )


@router.get("/notes/{module_id}", response_model=NotesResponse, status_code=status.HTTP_200_OK)
async def get_notes(module_id: str) -> NotesResponse:
    """
    Retrieve cached notes for a module.
    
    Args:
        module_id: Module identifier
        
    Returns:
        NotesResponse with cached notes
        
    Raises:
        HTTPException 404: If notes not found
    """
    try:
        logger.info(f"Notes retrieval requested for module: {module_id}")
        
        # Get cached notes
        cached_notes = cache_service.get_cached_content(module_id, 'notes')
        if not cached_notes:
            logger.info(f"No cached notes found for module {module_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No notes found for module '{module_id}'. Please generate notes first."
            )
        
        logger.info(f"Returning cached notes for module {module_id}")
        return NotesResponse(
            success=True,
            module_id=module_id,
            notes=cached_notes,
            cached=True
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving notes: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while retrieving notes"
        )


@router.get("/cheatsheet/{module_id}", response_model=CheatSheetResponse, status_code=status.HTTP_200_OK)
async def get_cheatsheet(module_id: str) -> CheatSheetResponse:
    """
    Retrieve cached cheat sheet for a module.
    
    Args:
        module_id: Module identifier
        
    Returns:
        CheatSheetResponse with cached cheat sheet
        
    Raises:
        HTTPException 404: If cheat sheet not found
    """
    try:
        logger.info(f"Cheat sheet retrieval requested for module: {module_id}")
        
        # Get cached cheat sheet
        cached_cheatsheet = cache_service.get_cached_content(module_id, 'cheatsheet')
        if not cached_cheatsheet:
            logger.info(f"No cached cheat sheet found for module {module_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No cheat sheet found for module '{module_id}'. Please generate a cheat sheet first."
            )
        
        logger.info(f"Returning cached cheat sheet for module {module_id}")
        return CheatSheetResponse(
            success=True,
            module_id=module_id,
            cheat_sheet=cached_cheatsheet,
            cached=True
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving cheat sheet: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while retrieving the cheat sheet"
        )
