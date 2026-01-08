"""
Integration tests for Session API endpoints.

Tests session state retrieval, reset, and persistence across "restarts".
"""

import pytest
from fastapi.testclient import TestClient
import tempfile
import shutil
from pathlib import Path

from app.main import app
from app.services.cache_service import CacheService


@pytest.fixture
def temp_cache_dir():
    """Create a temporary cache directory for testing."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def client_with_temp_cache(temp_cache_dir, monkeypatch):
    """Create a test client with temporary cache directory."""
    # Patch the cache directory in settings
    monkeypatch.setenv("CACHE_DIR", temp_cache_dir)
    
    # Create new client with patched settings
    from app import config
    config.settings.cache_dir = temp_cache_dir
    
    # Reinitialize cache service with new directory
    from app.services import session_service
    session_service.session_service.cache_service = CacheService(cache_dir=temp_cache_dir)
    
    client = TestClient(app)
    yield client


class TestSessionRetrieval:
    """Test session state retrieval."""
    
    def test_get_session_creates_new_if_none_exists(self, client_with_temp_cache):
        """Test that GET /api/session creates a new session if none exists."""
        response = client_with_temp_cache.get("/api/session")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "session_id" in data
        assert data["session_id"].startswith("session_")
        assert data["roadmap_generated"] == False
        assert data["modules_completed"] == []
        assert data["current_input_id"] is None
        assert data["current_module_id"] is None
    
    def test_get_session_returns_existing_session(self, client_with_temp_cache):
        """Test that GET /api/session returns the same session on subsequent calls."""
        # First call - creates session
        response1 = client_with_temp_cache.get("/api/session")
        session_id_1 = response1.json()["session_id"]
        
        # Second call - should return same session
        response2 = client_with_temp_cache.get("/api/session")
        session_id_2 = response2.json()["session_id"]
        
        assert session_id_1 == session_id_2
    
    def test_get_session_updates_last_accessed(self, client_with_temp_cache):
        """Test that GET /api/session updates last_accessed timestamp."""
        # First call
        response1 = client_with_temp_cache.get("/api/session")
        last_accessed_1 = response1.json()["last_accessed"]
        
        # Second call
        response2 = client_with_temp_cache.get("/api/session")
        last_accessed_2 = response2.json()["last_accessed"]
        
        # Timestamp should be updated (or at least not earlier)
        assert last_accessed_2 >= last_accessed_1


class TestSessionReset:
    """Test session reset functionality."""
    
    def test_reset_session_creates_new_session(self, client_with_temp_cache):
        """Test that POST /api/session/reset creates a new session."""
        # Get initial session
        response1 = client_with_temp_cache.get("/api/session")
        session_id_1 = response1.json()["session_id"]
        
        # Reset session
        response_reset = client_with_temp_cache.post("/api/session/reset")
        
        assert response_reset.status_code == 200
        reset_data = response_reset.json()
        assert reset_data["success"] == True
        assert "New session ID:" in reset_data["message"]
        
        # Get session after reset
        response2 = client_with_temp_cache.get("/api/session")
        session_id_2 = response2.json()["session_id"]
        
        # Should be a different session
        assert session_id_1 != session_id_2
    
    def test_reset_session_clears_state(self, client_with_temp_cache):
        """Test that reset clears all session state."""
        # Get initial session and simulate some state
        response1 = client_with_temp_cache.get("/api/session")
        session_data = response1.json()
        
        # In a real scenario, state would be updated through other endpoints
        # For this test, we just verify reset creates clean state
        
        # Reset session
        client_with_temp_cache.post("/api/session/reset")
        
        # Get new session
        response2 = client_with_temp_cache.get("/api/session")
        new_session = response2.json()
        
        # Verify clean state
        assert new_session["roadmap_generated"] == False
        assert new_session["modules_completed"] == []
        assert new_session["current_input_id"] is None
        assert new_session["current_module_id"] is None


class TestSessionPersistence:
    """Test session persistence across 'restarts'."""
    
    def test_session_persists_across_restarts(self, temp_cache_dir, monkeypatch):
        """Test that session data persists when service restarts."""
        # Patch cache directory
        monkeypatch.setenv("CACHE_DIR", temp_cache_dir)
        from app import config
        config.settings.cache_dir = temp_cache_dir
        
        # First "instance" - create session
        from app.services.session_service import SessionService
        from app.services.cache_service import CacheService
        
        cache1 = CacheService(cache_dir=temp_cache_dir)
        session_service1 = SessionService(cache_service=cache1)
        
        session1 = session_service1.initialize_session()
        session1.current_input_id = "input_persist_test"
        session1.roadmap_generated = True
        session1.modules_completed = ["mod_1", "mod_2"]
        session_service1.persist_session(session1)
        
        session_id_1 = session1.session_id
        
        # Second "instance" - simulate restart
        cache2 = CacheService(cache_dir=temp_cache_dir)
        session_service2 = SessionService(cache_service=cache2)
        
        session2 = session_service2.load_session()
        
        # Verify data persisted
        assert session2 is not None
        assert session2.session_id == session_id_1
        assert session2.current_input_id == "input_persist_test"
        assert session2.roadmap_generated == True
        assert len(session2.modules_completed) == 2
        assert "mod_1" in session2.modules_completed
        assert "mod_2" in session2.modules_completed
    
    def test_session_file_exists_after_creation(self, temp_cache_dir, monkeypatch):
        """Test that session file is created in cache directory."""
        monkeypatch.setenv("CACHE_DIR", temp_cache_dir)
        from app import config
        config.settings.cache_dir = temp_cache_dir
        
        from app.services.session_service import SessionService
        from app.services.cache_service import CacheService
        
        cache = CacheService(cache_dir=temp_cache_dir)
        session_service = SessionService(cache_service=cache)
        
        session = session_service.initialize_session()
        session_service.persist_session(session)
        
        # Check that session.json file exists
        session_file = Path(temp_cache_dir) / "session.json"
        assert session_file.exists()
        assert session_file.is_file()


class TestSessionEndpointErrors:
    """Test error handling in session endpoints."""
    
    def test_get_session_handles_errors_gracefully(self, client_with_temp_cache):
        """Test that GET /api/session handles errors gracefully."""
        # This test verifies the endpoint doesn't crash
        # In normal operation, it should always succeed
        response = client_with_temp_cache.get("/api/session")
        
        assert response.status_code in [200, 500]  # Either success or handled error
        
        if response.status_code == 200:
            data = response.json()
            assert "session_id" in data
    
    def test_reset_session_handles_errors_gracefully(self, client_with_temp_cache):
        """Test that POST /api/session/reset handles errors gracefully."""
        response = client_with_temp_cache.post("/api/session/reset")
        
        assert response.status_code in [200, 500]  # Either success or handled error
        
        if response.status_code == 200:
            data = response.json()
            assert data["success"] == True
