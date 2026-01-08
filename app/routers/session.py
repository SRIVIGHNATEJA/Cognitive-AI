"""
Session API Router for the Cognitive AI Learning Platform.

Provides endpoints for retrieving session state and resetting sessions.
"""

import logging
from fastapi import APIRouter, HTTPException, status
from typing import Dict, Any

from app.models import SessionData, SuccessResponse
from app.services.session_service import SessionService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/session", tags=["session"])

# Service instance
session_service = SessionService()


@router.get("", response_model=SessionData)
async def get_session() -> SessionData:
    """
    Get current session state.
    
    Returns the current session data including:
    - Session ID and timestamps
    - Current input and module information
    - Roadmap generation status
    - List of completed modules
    
    If no session exists, creates a new one automatically.
    
    Returns:
        SessionData with current session state
        
    Raises:
        HTTPException 500: If session retrieval fails
    """
    try:
        logger.info("Retrieving session state")
        
        # Get or create session
        session = session_service.get_or_create_session()
        
        logger.info(f"Session retrieved: {session.session_id}")
        
        return session
        
    except Exception as e:
        logger.error(f"Failed to retrieve session: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve session: {str(e)}"
        )


@router.post("/reset", response_model=SuccessResponse)
async def reset_session() -> SuccessResponse:
    """
    Reset the current session.
    
    Creates a new session with default values, replacing the existing one.
    This effectively clears all progress and starts fresh.
    
    Use cases:
    - Starting over with new content
    - Clearing all cached data
    - Testing/development purposes
    
    Returns:
        SuccessResponse confirming session reset
        
    Raises:
        HTTPException 500: If session reset fails
    """
    try:
        logger.info("Resetting session")
        
        # Initialize new session
        new_session = session_service.initialize_session()
        
        # Persist the new session (replaces old one)
        session_service.persist_session(new_session)
        
        logger.info(f"Session reset complete: {new_session.session_id}")
        
        return SuccessResponse(
            success=True,
            message=f"Session reset successfully. New session ID: {new_session.session_id}"
        )
        
    except Exception as e:
        logger.error(f"Failed to reset session: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reset session: {str(e)}"
        )
