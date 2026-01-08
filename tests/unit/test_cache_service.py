"""
Unit tests for cache service.
Tests cache write/read operations, directory creation, and error handling.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime

from app.services.cache_service import CacheService


@pytest.fixture
def temp_cache_dir():
    """Create a temporary cache directory for testing."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    # Cleanup after test
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def cache_service(temp_cache_dir):
    """Create a cache service instance with temporary directory."""
    return CacheService(cache_dir=temp_cache_dir)


class TestCacheDirectoryCreation:
    """Tests for cache directory structure creation."""
    
    def test_cache_directory_creation(self, temp_cache_dir):
        """Test that cache directory structure is created."""
        service = CacheService(cache_dir=temp_cache_dir)
        
        cache_path = Path(temp_cache_dir)
        assert cache_path.exists()
        assert cache_path.is_dir()
    
    def test_subdirectories_created(self, temp_cache_dir):
        """Test that all required subdirectories are created."""
        service = CacheService(cache_dir=temp_cache_dir)
        
        cache_path = Path(temp_cache_dir)
        expected_subdirs = ['input', 'roadmap', 'content', 'quizzes', 'analytics']
        
        for subdir in expected_subdirs:
            subdir_path = cache_path / subdir
            assert subdir_path.exists()
            assert subdir_path.is_dir()


class TestCacheWriteAndRead:
    """Tests for cache write and read operations."""
    
    def test_cache_input_data(self, cache_service):
        """Test caching input data."""
        input_id = "test_input_123"
        test_data = {
            "input_id": input_id,
            "content": "Test content",
            "type": "syllabus"
        }
        
        # Cache the data
        cache_service.cache_input(input_id, test_data)
        
        # Verify it was cached
        assert cache_service.cache_exists(input_id, 'input')
    
    def test_retrieve_cached_data(self, cache_service):
        """Test retrieving cached data."""
        input_id = "test_input_456"
        test_data = {
            "input_id": input_id,
            "content": "Test content for retrieval",
            "type": "question_bank"
        }
        
        # Cache the data
        cache_service.cache_input(input_id, test_data)
        
        # Retrieve it
        retrieved_data = cache_service.get_cached_data(input_id, 'input')
        
        assert retrieved_data is not None
        assert retrieved_data["input_id"] == input_id
        assert retrieved_data["content"] == test_data["content"]
        assert retrieved_data["type"] == test_data["type"]
    
    def test_cache_with_datetime(self, cache_service):
        """Test caching data with datetime objects."""
        input_id = "test_input_datetime"
        test_data = {
            "input_id": input_id,
            "timestamp": datetime.now(),
            "content": "Test with datetime"
        }
        
        # Cache the data
        cache_service.cache_input(input_id, test_data)
        
        # Retrieve it
        retrieved_data = cache_service.get_cached_data(input_id, 'input')
        
        assert retrieved_data is not None
        assert retrieved_data["input_id"] == input_id
        # Datetime should be serialized as ISO string
        assert isinstance(retrieved_data["timestamp"], str)
    
    def test_cache_complex_nested_data(self, cache_service):
        """Test caching complex nested data structures."""
        input_id = "test_input_complex"
        test_data = {
            "input_id": input_id,
            "metadata": {
                "author": "Test Author",
                "tags": ["python", "learning", "ai"]
            },
            "modules": [
                {"id": 1, "name": "Module 1"},
                {"id": 2, "name": "Module 2"}
            ]
        }
        
        # Cache the data
        cache_service.cache_input(input_id, test_data)
        
        # Retrieve it
        retrieved_data = cache_service.get_cached_data(input_id, 'input')
        
        assert retrieved_data is not None
        assert retrieved_data["metadata"]["author"] == "Test Author"
        assert len(retrieved_data["metadata"]["tags"]) == 3
        assert len(retrieved_data["modules"]) == 2


class TestCacheMissingFiles:
    """Tests for handling missing cache files."""
    
    def test_get_nonexistent_cache(self, cache_service):
        """Test retrieving non-existent cached data."""
        result = cache_service.get_cached_data("nonexistent_id", 'input')
        assert result is None
    
    def test_cache_exists_for_nonexistent(self, cache_service):
        """Test cache_exists for non-existent data."""
        assert cache_service.cache_exists("nonexistent_id", 'input') is False
    
    def test_delete_nonexistent_cache(self, cache_service):
        """Test deleting non-existent cache."""
        result = cache_service.delete_cache("nonexistent_id", 'input')
        assert result is False


class TestCacheDeletion:
    """Tests for cache deletion operations."""
    
    def test_delete_cached_data(self, cache_service):
        """Test deleting cached data."""
        input_id = "test_input_delete"
        test_data = {"input_id": input_id, "content": "To be deleted"}
        
        # Cache the data
        cache_service.cache_input(input_id, test_data)
        assert cache_service.cache_exists(input_id, 'input')
        
        # Delete it
        result = cache_service.delete_cache(input_id, 'input')
        assert result is True
        assert cache_service.cache_exists(input_id, 'input') is False
    
    def test_clear_cache_type(self, cache_service):
        """Test clearing all cache of a specific type."""
        # Cache multiple items
        for i in range(3):
            input_id = f"test_input_{i}"
            cache_service.cache_input(input_id, {"id": input_id})
        
        # Clear all input cache
        count = cache_service.clear_cache_type('input')
        assert count == 3
        
        # Verify all are deleted
        for i in range(3):
            assert cache_service.cache_exists(f"test_input_{i}", 'input') is False


class TestSessionManagement:
    """Tests for session data management."""
    
    def test_save_and_load_session(self, cache_service):
        """Test saving and loading session data."""
        session_data = {
            "session_id": "test_session_123",
            "created_at": datetime.now(),
            "user_data": {"name": "Test User"}
        }
        
        # Save session
        cache_service.save_session(session_data)
        
        # Load session
        loaded_session = cache_service.load_session()
        
        assert loaded_session is not None
        assert loaded_session["session_id"] == "test_session_123"
        assert loaded_session["user_data"]["name"] == "Test User"
    
    def test_load_nonexistent_session(self, cache_service):
        """Test loading session when none exists."""
        result = cache_service.load_session()
        assert result is None


class TestCacheStats:
    """Tests for cache statistics."""
    
    def test_get_cache_stats_empty(self, cache_service):
        """Test getting stats for empty cache."""
        stats = cache_service.get_cache_stats()
        
        assert stats['input'] == 0
        assert stats['roadmap'] == 0
        assert stats['content'] == 0
        assert stats['quizzes'] == 0
        assert stats['analytics'] == 0
        assert stats['session'] == 0
    
    def test_get_cache_stats_with_data(self, cache_service):
        """Test getting stats with cached data."""
        # Cache some input data
        cache_service.cache_input("input1", {"data": "test1"})
        cache_service.cache_input("input2", {"data": "test2"})
        
        # Save session
        cache_service.save_session({"session_id": "test"})
        
        stats = cache_service.get_cache_stats()
        
        assert stats['input'] == 2
        assert stats['session'] == 1
