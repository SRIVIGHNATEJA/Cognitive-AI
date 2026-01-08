"""
Session Service for the Cognitive AI Learning Platform.

Handles session state management, persistence, and tracking of user progress.
Integrates with cache service for session data storage.
"""

import logging
import uuid
from typing import Optional
from datetime import datetime

from app.models import SessionData
from app.services.cache_service import CacheService

logger = logging.getLogger(__name__)


class SessionService:
    """
    Service for managing user session state and progress tracking.
    
    Responsibilities:
    - Initialize new sessions
    - Load existing sessions
    - Update session state
    - Persist session data
    - Track user progress across modules
    """
    
    def __init__(self, cache_service: Optional[CacheService] = None):
        """
        Initialize the session service.
        
        Args:
            cache_service: Cache service instance for session persistence
        """
        self.cache_service = cache_service or CacheService()
        logger.info("SessionService initialized")
    
    def initialize_session(self) -> SessionData:
        """
        Initialize a new session with default values.
        
        Creates a new session with a unique ID and default state.
        Does not persist the session automatically.
        
        Returns:
            New SessionData object
        """
        session_id = self._generate_session_id()
        
        session = SessionData(
            session_id=session_id,
            created_at=datetime.now(),
            last_accessed=datetime.now(),
            current_input_id=None,
            roadmap_generated=False,
            current_module_id=None,
            modules_completed=[]
        )
        
        logger.info(f"Initialized new session: {session_id}")
        return session
    
    def load_session(self) -> Optional[SessionData]:
        """
        Load existing session from cache.
        
        Returns:
            SessionData if session exists, None otherwise
        """
        logger.debug("Loading session from cache")
        
        session_data = self.cache_service.load_session()
        
        if not session_data:
            logger.info("No existing session found")
            return None
        
        try:
            # Convert to SessionData model
            session = SessionData(**session_data)
            
            logger.info(f"Loaded session: {session.session_id}")
            return session
            
        except Exception as e:
            logger.error(f"Failed to parse session data: {str(e)}")
            return None
    
    def update_session(
        self,
        session: SessionData,
        current_input_id: Optional[str] = None,
        roadmap_generated: Optional[bool] = None,
        current_module_id: Optional[str] = None,
        add_completed_module: Optional[str] = None
    ) -> SessionData:
        """
        Update session state with new values.
        
        Updates the last_accessed timestamp automatically.
        Does not persist the session automatically.
        
        Args:
            session: Current session data
            current_input_id: New input ID (if provided)
            roadmap_generated: New roadmap status (if provided)
            current_module_id: New current module (if provided)
            add_completed_module: Module ID to add to completed list (if provided)
            
        Returns:
            Updated SessionData object
        """
        logger.debug(f"Updating session: {session.session_id}")
        
        # Update last accessed
        session.last_accessed = datetime.now()
        
        # Update fields if provided
        if current_input_id is not None:
            session.current_input_id = current_input_id
            logger.debug(f"Updated current_input_id: {current_input_id}")
        
        if roadmap_generated is not None:
            session.roadmap_generated = roadmap_generated
            logger.debug(f"Updated roadmap_generated: {roadmap_generated}")
        
        if current_module_id is not None:
            session.current_module_id = current_module_id
            logger.debug(f"Updated current_module_id: {current_module_id}")
        
        if add_completed_module is not None:
            if add_completed_module not in session.modules_completed:
                session.modules_completed.append(add_completed_module)
                logger.debug(f"Added completed module: {add_completed_module}")
        
        logger.info(f"Session updated: {session.session_id}")
        return session
    
    def persist_session(self, session: SessionData) -> None:
        """
        Persist session data to cache.
        
        Saves the session state to persistent storage.
        
        Args:
            session: Session data to persist
            
        Raises:
            Exception: If persistence fails
        """
        logger.debug(f"Persisting session: {session.session_id}")
        
        try:
            # Convert to dict for caching
            session_dict = session.model_dump(mode='json')
            
            # Save to cache
            self.cache_service.save_session(session_dict)
            
            logger.info(f"Session persisted: {session.session_id}")
            
        except Exception as e:
            logger.error(f"Failed to persist session: {str(e)}")
            raise
    
    def get_or_create_session(self) -> SessionData:
        """
        Get existing session or create a new one.
        
        Convenience method that loads existing session or initializes
        a new one if none exists. Automatically persists new sessions.
        
        Returns:
            SessionData object (existing or new)
        """
        logger.debug("Getting or creating session")
        
        # Try to load existing session
        session = self.load_session()
        
        if session:
            # Update last accessed and persist
            session.last_accessed = datetime.now()
            self.persist_session(session)
            logger.info(f"Using existing session: {session.session_id}")
            return session
        
        # Create new session
        session = self.initialize_session()
        self.persist_session(session)
        logger.info(f"Created new session: {session.session_id}")
        
        return session
    
    def _generate_session_id(self) -> str:
        """
        Generate a unique session identifier.
        
        Returns:
            Unique session ID string
        """
        return f"session_{uuid.uuid4().hex}"


# Global session service instance
session_service = SessionService()
