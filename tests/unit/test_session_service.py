"""
Unit tests for Session Service.

Tests session initialization, loading, updating, and persistence.
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime

from app.services.session_service import SessionService
from app.models import SessionData


@pytest.fixture
def mock_cache_service():
    """Create a mock cache service for testing."""
    return Mock()


@pytest.fixture
def session_service(mock_cache_service):
    """Create session service with mocked cache."""
    return SessionService(cache_service=mock_cache_service)


@pytest.fixture
def sample_session_data():
    """Sample session data for testing."""
    return {
        "session_id": "session_test123",
        "created_at": "2024-01-07T10:00:00",
        "last_accessed": "2024-01-07T15:30:00",
        "current_input_id": "input_abc",
        "roadmap_generated": True,
        "current_module_id": "mod_123",
        "modules_completed": ["mod_1", "mod_2"]
    }


class TestSessionInitialization:
    """Test session initialization."""
    
    def test_initialize_session(self, session_service):
        """Test creating a new session."""
        session = session_service.initialize_session()
        
        assert session.session_id.startswith("session_")
        assert session.roadmap_generated == False
        assert session.modules_completed == []
        assert session.current_input_id is None
        assert session.current_module_id is None
        assert isinstance(session.created_at, datetime)
        assert isinstance(session.last_accessed, datetime)
    
    def test_initialize_session_unique_ids(self, session_service):
        """Test that each session gets a unique ID."""
        session1 = session_service.initialize_session()
        session2 = session_service.initialize_session()
        
        assert session1.session_id != session2.session_id


class TestSessionLoading:
    """Test session loading from cache."""
    
    def test_load_existing_session(self, session_service, mock_cache_service, sample_session_data):
        """Test loading an existing session."""
        mock_cache_service.load_session.return_value = sample_session_data
        
        session = session_service.load_session()
        
        assert session is not None
        assert session.session_id == "session_test123"
        assert session.current_input_id == "input_abc"
        assert session.roadmap_generated == True
        assert session.current_module_id == "mod_123"
        assert len(session.modules_completed) == 2
        mock_cache_service.load_session.assert_called_once()
    
    def test_load_nonexistent_session(self, session_service, mock_cache_service):
        """Test loading when no session exists."""
        mock_cache_service.load_session.return_value = None
        
        session = session_service.load_session()
        
        assert session is None
        mock_cache_service.load_session.assert_called_once()
    
    def test_load_invalid_session_data(self, session_service, mock_cache_service):
        """Test loading with invalid session data."""
        mock_cache_service.load_session.return_value = {"invalid": "data"}
        
        session = session_service.load_session()
        
        assert session is None  # Should return None on parse error


class TestSessionUpdates:
    """Test session state updates."""
    
    def test_update_input_id(self, session_service):
        """Test updating current input ID."""
        session = session_service.initialize_session()
        original_accessed = session.last_accessed
        
        updated = session_service.update_session(session, current_input_id="input_new")
        
        assert updated.current_input_id == "input_new"
        assert updated.last_accessed > original_accessed
    
    def test_update_roadmap_status(self, session_service):
        """Test updating roadmap generation status."""
        session = session_service.initialize_session()
        
        updated = session_service.update_session(session, roadmap_generated=True)
        
        assert updated.roadmap_generated == True
    
    def test_update_current_module(self, session_service):
        """Test updating current module."""
        session = session_service.initialize_session()
        
        updated = session_service.update_session(session, current_module_id="mod_456")
        
        assert updated.current_module_id == "mod_456"
    
    def test_add_completed_module(self, session_service):
        """Test adding a completed module."""
        session = session_service.initialize_session()
        
        updated = session_service.update_session(session, add_completed_module="mod_789")
        
        assert "mod_789" in updated.modules_completed
        assert len(updated.modules_completed) == 1
    
    def test_add_duplicate_completed_module(self, session_service):
        """Test that duplicate modules are not added."""
        session = session_service.initialize_session()
        
        # Add module twice
        updated1 = session_service.update_session(session, add_completed_module="mod_123")
        updated2 = session_service.update_session(updated1, add_completed_module="mod_123")
        
        assert updated2.modules_completed.count("mod_123") == 1
    
    def test_update_multiple_fields(self, session_service):
        """Test updating multiple fields at once."""
        session = session_service.initialize_session()
        
        updated = session_service.update_session(
            session,
            current_input_id="input_multi",
            roadmap_generated=True,
            current_module_id="mod_multi",
            add_completed_module="mod_complete"
        )
        
        assert updated.current_input_id == "input_multi"
        assert updated.roadmap_generated == True
        assert updated.current_module_id == "mod_multi"
        assert "mod_complete" in updated.modules_completed
    
    def test_update_with_none_values(self, session_service):
        """Test that None values don't update fields."""
        session = session_service.initialize_session()
        session.current_input_id = "input_original"
        
        updated = session_service.update_session(
            session,
            current_input_id=None,  # Should not update
            roadmap_generated=True
        )
        
        assert updated.current_input_id == "input_original"  # Unchanged
        assert updated.roadmap_generated == True  # Changed


class TestSessionPersistence:
    """Test session persistence."""
    
    def test_persist_session(self, session_service, mock_cache_service):
        """Test persisting a session."""
        session = session_service.initialize_session()
        
        session_service.persist_session(session)
        
        mock_cache_service.save_session.assert_called_once()
        saved_data = mock_cache_service.save_session.call_args[0][0]
        assert saved_data["session_id"] == session.session_id
    
    def test_persist_session_with_data(self, session_service, mock_cache_service):
        """Test persisting a session with data."""
        session = session_service.initialize_session()
        session.current_input_id = "input_test"
        session.roadmap_generated = True
        session.modules_completed = ["mod_1", "mod_2"]
        
        session_service.persist_session(session)
        
        saved_data = mock_cache_service.save_session.call_args[0][0]
        assert saved_data["current_input_id"] == "input_test"
        assert saved_data["roadmap_generated"] == True
        assert len(saved_data["modules_completed"]) == 2


class TestGetOrCreateSession:
    """Test get or create session convenience method."""
    
    def test_get_existing_session(self, session_service, mock_cache_service, sample_session_data):
        """Test getting an existing session."""
        mock_cache_service.load_session.return_value = sample_session_data
        
        session = session_service.get_or_create_session()
        
        assert session.session_id == "session_test123"
        mock_cache_service.load_session.assert_called_once()
        mock_cache_service.save_session.assert_called_once()  # Updates last_accessed
    
    def test_create_new_session(self, session_service, mock_cache_service):
        """Test creating a new session when none exists."""
        mock_cache_service.load_session.return_value = None
        
        session = session_service.get_or_create_session()
        
        assert session.session_id.startswith("session_")
        assert session.roadmap_generated == False
        mock_cache_service.load_session.assert_called_once()
        mock_cache_service.save_session.assert_called_once()
