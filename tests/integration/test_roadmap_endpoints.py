"""
Integration tests for Roadmap API endpoints.

Tests the complete roadmap generation flow including caching and retrieval.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, Mock
from app.main import app
from app.services.cache_service import CacheService
from app.models import LearningMode

client = TestClient(app)


@pytest.fixture
def cache_service():
    """Provide a cache service instance for tests."""
    return CacheService()


@pytest.fixture
def clear_roadmap_cache(cache_service):
    """Clear roadmap cache before and after each test."""
    cache_service.clear_cache('roadmap')
    yield
    cache_service.clear_cache('roadmap')


@pytest.fixture
def sample_input_data(cache_service):
    """Create sample input data in cache for testing."""
    input_id = "test_input_123"
    input_data = {
        "input_id": input_id,
        "detected_type": "syllabus",
        "extracted_text": "Week 1: Introduction to Python\nWeek 2: Data Structures\nWeek 3: Algorithms",
        "original_filename": "test_syllabus.pdf",
        "processed_at": "2024-01-07T10:00:00"
    }
    cache_service.cache_input(input_id, input_data)
    yield input_id
    # Cleanup
    cache_service.delete_cache(input_id, 'input')


class TestRoadmapGeneration:
    """Test roadmap generation endpoint."""
    
    @patch('app.routers.roadmap.roadmap_service.generate_roadmap')
    def test_generate_roadmap_success(
        self,
        mock_generate,
        sample_input_data,
        clear_roadmap_cache
    ):
        """Test successful roadmap generation."""
        # Mock roadmap generation
        from app.models import Module
        mock_modules = [
            Module(
                module_id="mod_abc123",
                topic_name="Introduction to Python",
                estimated_hours=5.0,
                prerequisites=[],
                order=1
            ),
            Module(
                module_id="mod_def456",
                topic_name="Data Structures",
                estimated_hours=8.0,
                prerequisites=["mod_abc123"],
                order=2
            )
        ]
        mock_generate.return_value = mock_modules
        
        # Make request
        response = client.post(
            "/api/roadmap/generate",
            json={
                "input_id": sample_input_data,
                "mode": "untimed"
            }
        )
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert data["total_modules"] == 2
        assert data["total_estimated_hours"] == 13.0
        assert data["mode"] == "untimed"
        assert data["cached"] is False
        
        # Verify modules
        assert len(data["modules"]) == 2
        assert data["modules"][0]["topic_name"] == "Introduction to Python"
        assert data["modules"][0]["estimated_hours"] == 5.0
        assert data["modules"][1]["topic_name"] == "Data Structures"
        assert data["modules"][1]["estimated_hours"] == 8.0
    
    def test_generate_roadmap_invalid_input_id(self, clear_roadmap_cache):
        """Test roadmap generation with invalid input_id."""
        response = client.post(
            "/api/roadmap/generate",
            json={
                "input_id": "nonexistent_input",
                "mode": "untimed"
            }
        )
        
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()
    
    @patch('app.routers.roadmap.roadmap_service.generate_roadmap')
    def test_generate_roadmap_timed_mode(
        self,
        mock_generate,
        sample_input_data,
        clear_roadmap_cache
    ):
        """Test roadmap generation in timed mode."""
        from app.models import Module
        mock_modules = [
            Module(
                module_id="mod_abc123",
                topic_name="Quick Module",
                estimated_hours=3.0,
                prerequisites=[],
                order=1
            )
        ]
        mock_generate.return_value = mock_modules
        
        response = client.post(
            "/api/roadmap/generate",
            json={
                "input_id": sample_input_data,
                "mode": "timed"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["mode"] == "timed"


class TestRoadmapCaching:
    """Test roadmap caching behavior."""
    
    @patch('app.routers.roadmap.roadmap_service.generate_roadmap')
    def test_roadmap_cached_on_first_generation(
        self,
        mock_generate,
        sample_input_data,
        clear_roadmap_cache,
        cache_service
    ):
        """Test that roadmap is cached after first generation."""
        from app.models import Module
        mock_modules = [
            Module(
                module_id="mod_abc123",
                topic_name="Test Module",
                estimated_hours=5.0,
                prerequisites=[],
                order=1
            )
        ]
        mock_generate.return_value = mock_modules
        
        # Generate roadmap
        response = client.post(
            "/api/roadmap/generate",
            json={
                "input_id": sample_input_data,
                "mode": "untimed"
            }
        )
        
        assert response.status_code == 200
        
        # Verify roadmap is cached
        cached_roadmap = cache_service.get_cached_roadmap()
        assert cached_roadmap is not None
        assert len(cached_roadmap["modules"]) == 1
        assert cached_roadmap["modules"][0]["topic_name"] == "Test Module"
    
    @patch('app.routers.roadmap.roadmap_service.generate_roadmap')
    def test_cached_roadmap_returned_on_second_request(
        self,
        mock_generate,
        sample_input_data,
        clear_roadmap_cache
    ):
        """Test that cached roadmap is returned without regeneration."""
        from app.models import Module
        mock_modules = [
            Module(
                module_id="mod_abc123",
                topic_name="Original Module",
                estimated_hours=5.0,
                prerequisites=[],
                order=1
            )
        ]
        mock_generate.return_value = mock_modules
        
        # First request - generates and caches
        response1 = client.post(
            "/api/roadmap/generate",
            json={
                "input_id": sample_input_data,
                "mode": "untimed"
            }
        )
        assert response1.status_code == 200
        data1 = response1.json()
        assert data1["cached"] is False
        
        # Second request - should return cached version
        response2 = client.post(
            "/api/roadmap/generate",
            json={
                "input_id": sample_input_data,
                "mode": "untimed"
            }
        )
        assert response2.status_code == 200
        data2 = response2.json()
        assert data2["cached"] is True
        
        # Verify LLM was only called once
        assert mock_generate.call_count == 1
        
        # Verify same data returned
        assert data1["modules"] == data2["modules"]


class TestRoadmapRetrieval:
    """Test roadmap retrieval endpoint."""
    
    @patch('app.routers.roadmap.roadmap_service.generate_roadmap')
    def test_get_roadmap_success(
        self,
        mock_generate,
        sample_input_data,
        clear_roadmap_cache
    ):
        """Test successful roadmap retrieval."""
        from app.models import Module
        mock_modules = [
            Module(
                module_id="mod_abc123",
                topic_name="Test Module",
                estimated_hours=5.0,
                prerequisites=[],
                order=1
            )
        ]
        mock_generate.return_value = mock_modules
        
        # First generate a roadmap
        client.post(
            "/api/roadmap/generate",
            json={
                "input_id": sample_input_data,
                "mode": "untimed"
            }
        )
        
        # Then retrieve it
        response = client.get("/api/roadmap")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["cached"] is True
        assert len(data["modules"]) == 1
        assert data["modules"][0]["topic_name"] == "Test Module"
    
    def test_get_roadmap_not_found(self, clear_roadmap_cache):
        """Test roadmap retrieval when no roadmap exists."""
        response = client.get("/api/roadmap")
        
        assert response.status_code == 404
        data = response.json()
        assert "roadmap" in data["detail"].lower()
        assert "found" in data["detail"].lower()


class TestRoadmapReset:
    """Test roadmap reset functionality."""
    
    @patch('app.routers.roadmap.roadmap_service.generate_roadmap')
    def test_reset_roadmap_success(
        self,
        mock_generate,
        sample_input_data,
        clear_roadmap_cache,
        cache_service
    ):
        """Test successful roadmap reset."""
        from app.models import Module
        mock_modules = [
            Module(
                module_id="mod_abc123",
                topic_name="Test Module",
                estimated_hours=5.0,
                prerequisites=[],
                order=1
            )
        ]
        mock_generate.return_value = mock_modules
        
        # Generate a roadmap
        client.post(
            "/api/roadmap/generate",
            json={
                "input_id": sample_input_data,
                "mode": "untimed"
            }
        )
        
        # Verify it's cached
        assert cache_service.get_cached_roadmap() is not None
        
        # Reset the roadmap
        response = client.delete("/api/roadmap")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "cleared" in data["message"].lower()
        
        # Verify cache is cleared
        assert cache_service.get_cached_roadmap() is None
    
    def test_reset_roadmap_when_none_exists(self, clear_roadmap_cache):
        """Test reset when no roadmap exists."""
        response = client.delete("/api/roadmap")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
    
    @patch('app.routers.roadmap.roadmap_service.generate_roadmap')
    def test_regenerate_after_reset(
        self,
        mock_generate,
        sample_input_data,
        clear_roadmap_cache
    ):
        """Test that roadmap can be regenerated after reset."""
        from app.models import Module
        
        # First generation
        mock_modules_1 = [
            Module(
                module_id="mod_abc123",
                topic_name="Original Module",
                estimated_hours=5.0,
                prerequisites=[],
                order=1
            )
        ]
        mock_generate.return_value = mock_modules_1
        
        response1 = client.post(
            "/api/roadmap/generate",
            json={
                "input_id": sample_input_data,
                "mode": "untimed"
            }
        )
        assert response1.status_code == 200
        
        # Reset
        client.delete("/api/roadmap")
        
        # Second generation with different data
        mock_modules_2 = [
            Module(
                module_id="mod_xyz789",
                topic_name="New Module",
                estimated_hours=10.0,
                prerequisites=[],
                order=1
            )
        ]
        mock_generate.return_value = mock_modules_2
        
        response2 = client.post(
            "/api/roadmap/generate",
            json={
                "input_id": sample_input_data,
                "mode": "timed"
            }
        )
        assert response2.status_code == 200
        data2 = response2.json()
        
        # Verify new roadmap was generated
        assert data2["cached"] is False
        assert data2["modules"][0]["topic_name"] == "New Module"
        assert data2["mode"] == "timed"
