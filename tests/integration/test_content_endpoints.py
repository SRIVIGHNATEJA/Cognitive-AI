"""
Integration tests for Content API endpoints.

Tests the complete content generation flow including caching and retrieval.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, Mock
from app.main import app
from app.services.cache_service import CacheService
from app.models import Module

client = TestClient(app)


@pytest.fixture
def cache_service():
    """Provide a cache service instance for tests."""
    return CacheService()


@pytest.fixture
def clear_content_cache(cache_service):
    """Clear content cache before and after each test."""
    cache_service.clear_cache('content')
    yield
    cache_service.clear_cache('content')


@pytest.fixture
def setup_roadmap_and_input(cache_service):
    """Set up roadmap and input data for testing."""
    # Create input data
    input_id = "test_input_content"
    input_data = {
        "input_id": input_id,
        "detected_type": "syllabus",
        "extracted_text": "Python programming: variables, loops, functions, data structures",
        "processed_at": "2024-01-07T10:00:00"
    }
    cache_service.cache_input(input_id, input_data)
    
    # Create roadmap data
    roadmap_data = {
        "modules": [
            {
                "module_id": "mod_test123",
                "topic_name": "Python Basics",
                "estimated_hours": 5.0,
                "prerequisites": [],
                "order": 1
            }
        ],
        "total_modules": 1,
        "total_estimated_hours": 5.0,
        "mode": "untimed",
        "input_id": input_id
    }
    cache_service.cache_roadmap(roadmap_data)
    
    yield "mod_test123"
    
    # Cleanup
    cache_service.delete_cache(input_id, 'input')
    cache_service.clear_cache('roadmap')


class TestNotesGeneration:
    """Test notes generation endpoint."""
    
    @patch('app.routers.content.content_service.generate_notes')
    def test_generate_notes_success(
        self,
        mock_generate_notes,
        setup_roadmap_and_input,
        clear_content_cache
    ):
        """Test successful notes generation."""
        module_id = setup_roadmap_and_input
        
        # Mock notes generation
        mock_generate_notes.return_value = "Detailed notes about Python basics..."
        
        # Make request
        response = client.post(f"/api/content/notes/{module_id}")
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert data["module_id"] == module_id
        assert data["notes"] == "Detailed notes about Python basics..."
        assert data["cached"] is False
        
        # Verify notes generation was called
        mock_generate_notes.assert_called_once()
    
    @patch('app.routers.content.content_service.generate_notes')
    def test_generate_notes_caches_result(
        self,
        mock_generate_notes,
        setup_roadmap_and_input,
        clear_content_cache,
        cache_service
    ):
        """Test that generated notes are cached."""
        module_id = setup_roadmap_and_input
        
        mock_generate_notes.return_value = "Test notes content"
        
        # Generate notes
        response = client.post(f"/api/content/notes/{module_id}")
        assert response.status_code == 200
        
        # Verify notes are cached
        cached_notes = cache_service.get_cached_content(module_id, 'notes')
        assert cached_notes is not None
        assert cached_notes == "Test notes content"
    
    @patch('app.routers.content.content_service.generate_notes')
    def test_generate_notes_returns_cached_on_second_request(
        self,
        mock_generate_notes,
        setup_roadmap_and_input,
        clear_content_cache
    ):
        """Test that cached notes are returned without regeneration."""
        module_id = setup_roadmap_and_input
        
        mock_generate_notes.return_value = "Original notes"
        
        # First request - generates and caches
        response1 = client.post(f"/api/content/notes/{module_id}")
        assert response1.status_code == 200
        data1 = response1.json()
        assert data1["cached"] is False
        
        # Second request - should return cached version
        response2 = client.post(f"/api/content/notes/{module_id}")
        assert response2.status_code == 200
        data2 = response2.json()
        assert data2["cached"] is True
        
        # Verify generation was only called once
        assert mock_generate_notes.call_count == 1
        
        # Verify same content returned
        assert data1["notes"] == data2["notes"]
    
    def test_generate_notes_invalid_module_id(
        self,
        setup_roadmap_and_input,
        clear_content_cache
    ):
        """Test notes generation with invalid module ID."""
        response = client.post("/api/content/notes/nonexistent_module")
        
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()
    
    def test_generate_notes_no_roadmap(self, clear_content_cache, cache_service):
        """Test notes generation when no roadmap exists."""
        # Clear roadmap
        cache_service.clear_cache('roadmap')
        
        response = client.post("/api/content/notes/mod_test123")
        
        assert response.status_code == 404
        data = response.json()
        assert "roadmap" in data["detail"].lower()


class TestCheatSheetGeneration:
    """Test cheat sheet generation endpoint."""
    
    @patch('app.routers.content.content_service.generate_cheat_sheet')
    def test_generate_cheatsheet_success(
        self,
        mock_generate_cheatsheet,
        setup_roadmap_and_input,
        clear_content_cache
    ):
        """Test successful cheat sheet generation."""
        module_id = setup_roadmap_and_input
        
        # Mock cheat sheet generation
        mock_generate_cheatsheet.return_value = "Quick reference: variables, loops, functions"
        
        # Make request
        response = client.post(f"/api/content/cheatsheet/{module_id}")
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert data["module_id"] == module_id
        assert data["cheat_sheet"] == "Quick reference: variables, loops, functions"
        assert data["cached"] is False
        
        # Verify cheat sheet generation was called
        mock_generate_cheatsheet.assert_called_once()
    
    @patch('app.routers.content.content_service.generate_cheat_sheet')
    def test_generate_cheatsheet_caches_result(
        self,
        mock_generate_cheatsheet,
        setup_roadmap_and_input,
        clear_content_cache,
        cache_service
    ):
        """Test that generated cheat sheet is cached."""
        module_id = setup_roadmap_and_input
        
        mock_generate_cheatsheet.return_value = "Test cheat sheet content"
        
        # Generate cheat sheet
        response = client.post(f"/api/content/cheatsheet/{module_id}")
        assert response.status_code == 200
        
        # Verify cheat sheet is cached
        cached_cheatsheet = cache_service.get_cached_content(module_id, 'cheatsheet')
        assert cached_cheatsheet is not None
        assert cached_cheatsheet == "Test cheat sheet content"
    
    @patch('app.routers.content.content_service.generate_cheat_sheet')
    def test_generate_cheatsheet_returns_cached_on_second_request(
        self,
        mock_generate_cheatsheet,
        setup_roadmap_and_input,
        clear_content_cache
    ):
        """Test that cached cheat sheet is returned without regeneration."""
        module_id = setup_roadmap_and_input
        
        mock_generate_cheatsheet.return_value = "Original cheat sheet"
        
        # First request - generates and caches
        response1 = client.post(f"/api/content/cheatsheet/{module_id}")
        assert response1.status_code == 200
        data1 = response1.json()
        assert data1["cached"] is False
        
        # Second request - should return cached version
        response2 = client.post(f"/api/content/cheatsheet/{module_id}")
        assert response2.status_code == 200
        data2 = response2.json()
        assert data2["cached"] is True
        
        # Verify generation was only called once
        assert mock_generate_cheatsheet.call_count == 1
        
        # Verify same content returned
        assert data1["cheat_sheet"] == data2["cheat_sheet"]


class TestNotesRetrieval:
    """Test notes retrieval endpoint."""
    
    @patch('app.routers.content.content_service.generate_notes')
    def test_get_notes_success(
        self,
        mock_generate_notes,
        setup_roadmap_and_input,
        clear_content_cache
    ):
        """Test successful notes retrieval."""
        module_id = setup_roadmap_and_input
        
        mock_generate_notes.return_value = "Cached notes content"
        
        # First generate notes
        client.post(f"/api/content/notes/{module_id}")
        
        # Then retrieve them
        response = client.get(f"/api/content/notes/{module_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["cached"] is True
        assert data["notes"] == "Cached notes content"
    
    def test_get_notes_not_found(
        self,
        setup_roadmap_and_input,
        clear_content_cache
    ):
        """Test notes retrieval when notes don't exist."""
        module_id = setup_roadmap_and_input
        
        response = client.get(f"/api/content/notes/{module_id}")
        
        assert response.status_code == 404
        data = response.json()
        assert "notes" in data["detail"].lower() and "found" in data["detail"].lower()


class TestCheatSheetRetrieval:
    """Test cheat sheet retrieval endpoint."""
    
    @patch('app.routers.content.content_service.generate_cheat_sheet')
    def test_get_cheatsheet_success(
        self,
        mock_generate_cheatsheet,
        setup_roadmap_and_input,
        clear_content_cache
    ):
        """Test successful cheat sheet retrieval."""
        module_id = setup_roadmap_and_input
        
        mock_generate_cheatsheet.return_value = "Cached cheat sheet content"
        
        # First generate cheat sheet
        client.post(f"/api/content/cheatsheet/{module_id}")
        
        # Then retrieve it
        response = client.get(f"/api/content/cheatsheet/{module_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["cached"] is True
        assert data["cheat_sheet"] == "Cached cheat sheet content"
    
    def test_get_cheatsheet_not_found(
        self,
        setup_roadmap_and_input,
        clear_content_cache
    ):
        """Test cheat sheet retrieval when cheat sheet doesn't exist."""
        module_id = setup_roadmap_and_input
        
        response = client.get(f"/api/content/cheatsheet/{module_id}")
        
        assert response.status_code == 404
        data = response.json()
        assert "cheat sheet" in data["detail"].lower() and "found" in data["detail"].lower()
