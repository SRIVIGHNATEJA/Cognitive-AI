"""
Property-based tests for Roadmap Service.

Tests universal properties that should hold across all valid inputs.
"""

import pytest
from hypothesis import given, strategies as st, settings
from app.services.roadmap_service import RoadmapService
from app.services.cache_service import CacheService
from app.models import Module, LearningMode
import tempfile
import shutil


class TestModuleIDStability:
    """
    Property tests for module ID stability.
    
    Feature: cognitive-learning-platform, Property 7: Module ID Stability
    Validates: Requirements 2.2
    """
    
    @given(
        topic_name=st.text(min_size=1, max_size=200),
        order=st.integers(min_value=1, max_value=100)
    )
    def test_module_id_stability_property(self, topic_name, order):
        """
        Property 7: Module ID Stability
        
        For any module generated from the same topic name and order,
        the assigned module_id should remain identical across multiple
        generation attempts.
        
        **Validates: Requirements 2.2**
        """
        service = RoadmapService()
        
        # Generate module ID multiple times with same inputs
        id1 = service.generate_stable_module_id(topic_name, order)
        id2 = service.generate_stable_module_id(topic_name, order)
        id3 = service.generate_stable_module_id(topic_name, order)
        
        # All IDs should be identical
        assert id1 == id2 == id3
        
        # ID should have correct format
        assert id1.startswith("mod_")
        assert len(id1) == 16  # "mod_" + 12 hex characters
        
        # ID should be a valid string
        assert isinstance(id1, str)
        assert id1.isascii()


class TestCachePersistenceAndRetrieval:
    """
    Property tests for cache persistence and retrieval.
    
    Feature: cognitive-learning-platform, Property 8: Cache Persistence and Retrieval
    Validates: Requirements 2.6, 2.7, 3.4, 3.5, 8.5, 10.1, 10.2
    """
    
    @given(
        modules=st.lists(
            st.builds(
                Module,
                module_id=st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'), whitelist_characters='_-')),
                topic_name=st.text(min_size=1, max_size=200),
                estimated_hours=st.floats(min_value=0.1, max_value=100.0),
                prerequisites=st.lists(st.text(min_size=1, max_size=50), max_size=3),
                order=st.integers(min_value=1, max_value=100)
            ),
            min_size=1,
            max_size=10
        ),
        mode=st.sampled_from([LearningMode.TIMED, LearningMode.UNTIMED])
    )
    @settings(max_examples=100)
    def test_cache_persistence_and_retrieval_property(self, modules, mode):
        """
        Property 8: Cache Persistence and Retrieval
        
        For any generated content (roadmap, notes, cheat sheet), once cached,
        subsequent requests should return the identical cached content without
        regeneration.
        
        **Validates: Requirements 2.6, 2.7, 3.4, 3.5, 8.5, 10.1, 10.2**
        """
        # Create temporary cache directory for this test
        temp_dir = tempfile.mkdtemp()
        
        try:
            cache_service = CacheService(cache_dir=temp_dir)
            
            # Calculate totals
            total_modules = len(modules)
            total_estimated_hours = sum(m.estimated_hours for m in modules)
            
            # Create roadmap data
            roadmap_data = {
                "modules": [m.model_dump() for m in modules],
                "total_modules": total_modules,
                "total_estimated_hours": total_estimated_hours,
                "mode": mode.value,
                "input_id": "test_input"
            }
            
            # Cache the roadmap
            cache_service.cache_roadmap(roadmap_data)
            
            # Retrieve the cached roadmap
            retrieved_data = cache_service.get_cached_roadmap()
            
            # Verify retrieved data matches original
            assert retrieved_data is not None
            assert retrieved_data["total_modules"] == total_modules
            assert retrieved_data["total_estimated_hours"] == total_estimated_hours
            assert retrieved_data["mode"] == mode.value
            assert len(retrieved_data["modules"]) == len(modules)
            
            # Verify each module is preserved
            for original, retrieved in zip(modules, retrieved_data["modules"]):
                assert retrieved["module_id"] == original.module_id
                assert retrieved["topic_name"] == original.topic_name
                assert retrieved["estimated_hours"] == original.estimated_hours
                assert retrieved["order"] == original.order
            
            # Retrieve again - should get same data
            retrieved_again = cache_service.get_cached_roadmap()
            assert retrieved_again == retrieved_data
            
        finally:
            # Cleanup temporary directory
            shutil.rmtree(temp_dir, ignore_errors=True)
