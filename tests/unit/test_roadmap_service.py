"""
Unit tests for the Roadmap Service.

Tests roadmap generation, module ID stability, and prerequisite validation.
"""

import pytest
from unittest.mock import Mock, patch
from app.services.roadmap_service import RoadmapService
from app.models import Module, LearningMode


class TestModuleIDGeneration:
    """Test stable module ID generation."""
    
    def test_generate_stable_module_id_consistency(self):
        """Test that same inputs produce same module ID."""
        service = RoadmapService()
        
        # Generate ID twice with same inputs
        id1 = service.generate_stable_module_id("Python Basics", 1)
        id2 = service.generate_stable_module_id("Python Basics", 1)
        
        assert id1 == id2
        assert id1.startswith("mod_")
        assert len(id1) == 16  # "mod_" + 12 hex characters
    
    def test_generate_stable_module_id_different_topics(self):
        """Test that different topics produce different IDs."""
        service = RoadmapService()
        
        id1 = service.generate_stable_module_id("Python Basics", 1)
        id2 = service.generate_stable_module_id("Advanced Python", 1)
        
        assert id1 != id2
    
    def test_generate_stable_module_id_different_orders(self):
        """Test that different orders produce different IDs."""
        service = RoadmapService()
        
        id1 = service.generate_stable_module_id("Python Basics", 1)
        id2 = service.generate_stable_module_id("Python Basics", 2)
        
        assert id1 != id2
    
    def test_generate_stable_module_id_case_insensitive(self):
        """Test that topic name is case-insensitive."""
        service = RoadmapService()
        
        id1 = service.generate_stable_module_id("Python Basics", 1)
        id2 = service.generate_stable_module_id("python basics", 1)
        id3 = service.generate_stable_module_id("PYTHON BASICS", 1)
        
        assert id1 == id2 == id3
    
    def test_generate_stable_module_id_whitespace_normalized(self):
        """Test that whitespace is normalized."""
        service = RoadmapService()
        
        id1 = service.generate_stable_module_id("Python Basics", 1)
        id2 = service.generate_stable_module_id("  Python Basics  ", 1)
        id3 = service.generate_stable_module_id("Python  Basics", 1)
        
        # Leading/trailing whitespace should be normalized
        assert id1 == id2
        # Internal whitespace differences should produce different IDs
        assert id1 != id3


class TestPrerequisiteValidation:
    """Test module prerequisite validation."""
    
    def test_validate_valid_prerequisites(self):
        """Test validation passes for valid prerequisites."""
        service = RoadmapService()
        
        modules = [
            Module(
                module_id="mod_abc123",
                topic_name="Basics",
                estimated_hours=5.0,
                prerequisites=[],
                order=1
            ),
            Module(
                module_id="mod_def456",
                topic_name="Advanced",
                estimated_hours=10.0,
                prerequisites=["mod_abc123"],
                order=2
            )
        ]
        
        assert service.validate_module_prerequisites(modules) is True
    
    def test_validate_no_prerequisites(self):
        """Test validation passes when no prerequisites exist."""
        service = RoadmapService()
        
        modules = [
            Module(
                module_id="mod_abc123",
                topic_name="Basics",
                estimated_hours=5.0,
                prerequisites=[],
                order=1
            )
        ]
        
        assert service.validate_module_prerequisites(modules) is True
    
    def test_validate_invalid_prerequisite_raises_error(self):
        """Test validation fails for invalid prerequisite."""
        service = RoadmapService()
        
        modules = [
            Module(
                module_id="mod_abc123",
                topic_name="Basics",
                estimated_hours=5.0,
                prerequisites=["mod_nonexistent"],  # Invalid prerequisite
                order=1
            )
        ]
        
        with pytest.raises(ValueError) as exc_info:
            service.validate_module_prerequisites(modules)
        
        assert "invalid prerequisite" in str(exc_info.value).lower()
        assert "mod_nonexistent" in str(exc_info.value)
    
    def test_validate_multiple_prerequisites(self):
        """Test validation with multiple prerequisites."""
        service = RoadmapService()
        
        modules = [
            Module(
                module_id="mod_abc123",
                topic_name="Basics 1",
                estimated_hours=5.0,
                prerequisites=[],
                order=1
            ),
            Module(
                module_id="mod_def456",
                topic_name="Basics 2",
                estimated_hours=5.0,
                prerequisites=[],
                order=2
            ),
            Module(
                module_id="mod_ghi789",
                topic_name="Advanced",
                estimated_hours=10.0,
                prerequisites=["mod_abc123", "mod_def456"],
                order=3
            )
        ]
        
        assert service.validate_module_prerequisites(modules) is True


class TestRoadmapGeneration:
    """Test roadmap generation from input content."""
    
    @patch('app.services.roadmap_service.LLMService')
    def test_successful_roadmap_generation(self, mock_llm_class):
        """
        Test successful roadmap generation.
        
        **unit test 6: Roadmap Generation**
        **Validates: Requirements 2.1, 2.3**
        """
        # Setup mock LLM service
        mock_llm = Mock()
        mock_llm.generate_roadmap_llm.return_value = {
            "modules": [
                {
                    "topic_name": "Introduction to Python",
                    "estimated_hours": 5.0,
                    "prerequisites": [],
                    "order": 1
                },
                {
                    "topic_name": "Data Structures",
                    "estimated_hours": 8.0,
                    "prerequisites": [],
                    "order": 2
                }
            ]
        }
        mock_llm_class.return_value = mock_llm
        
        service = RoadmapService(llm_service=mock_llm)
        
        # Generate roadmap
        modules = service.generate_roadmap(
            input_text="Python programming course syllabus...",
            mode=LearningMode.UNTIMED,
            input_id="input_test123"
        )
        
        # Verify results
        assert len(modules) == 2
        assert all(isinstance(m, Module) for m in modules)
        
        # Check first module
        assert modules[0].topic_name == "Introduction to Python"
        assert modules[0].estimated_hours == 5.0
        assert modules[0].order == 1
        assert modules[0].module_id.startswith("mod_")
        
        # Check second module
        assert modules[1].topic_name == "Data Structures"
        assert modules[1].estimated_hours == 8.0
        assert modules[1].order == 2
        assert modules[1].module_id.startswith("mod_")
        
        # Verify module IDs are different
        assert modules[0].module_id != modules[1].module_id
        
        # Verify LLM was called correctly
        mock_llm.generate_roadmap_llm.assert_called_once_with(
            input_text="Python programming course syllabus...",
            mode="untimed"
        )
    
    @patch('app.services.roadmap_service.LLMService')
    def test_roadmap_generation_with_prerequisites(self, mock_llm_class):
        """Test roadmap generation with module prerequisites."""
        # Setup mock LLM service
        mock_llm = Mock()
        
        # First, generate modules to get their IDs
        service = RoadmapService(llm_service=mock_llm)
        mod1_id = service.generate_stable_module_id("Basics", 1)
        
        mock_llm.generate_roadmap_llm.return_value = {
            "modules": [
                {
                    "topic_name": "Basics",
                    "estimated_hours": 5.0,
                    "prerequisites": [],
                    "order": 1
                },
                {
                    "topic_name": "Advanced",
                    "estimated_hours": 10.0,
                    "prerequisites": [mod1_id],
                    "order": 2
                }
            ]
        }
        mock_llm_class.return_value = mock_llm
        
        # Generate roadmap
        modules = service.generate_roadmap(
            input_text="Course content...",
            mode=LearningMode.TIMED,
            input_id="input_test456"
        )
        
        # Verify prerequisites
        assert len(modules) == 2
        assert modules[0].prerequisites == []
        assert modules[1].prerequisites == [mod1_id]
    
    @patch('app.services.roadmap_service.LLMService')
    def test_roadmap_generation_empty_response_raises_error(self, mock_llm_class):
        """Test that empty LLM response raises error."""
        mock_llm = Mock()
        mock_llm.generate_roadmap_llm.return_value = {"modules": []}
        mock_llm_class.return_value = mock_llm
        
        service = RoadmapService(llm_service=mock_llm)
        
        with pytest.raises(ValueError) as exc_info:
            service.generate_roadmap(
                input_text="Test content",
                mode=LearningMode.UNTIMED,
                input_id="input_test789"
            )
        
        assert "empty roadmap" in str(exc_info.value).lower()
    
    @patch('app.services.roadmap_service.LLMService')
    def test_roadmap_generation_missing_modules_field_raises_error(self, mock_llm_class):
        """Test that missing 'modules' field raises error."""
        mock_llm = Mock()
        mock_llm.generate_roadmap_llm.return_value = {}
        mock_llm_class.return_value = mock_llm
        
        service = RoadmapService(llm_service=mock_llm)
        
        with pytest.raises(ValueError) as exc_info:
            service.generate_roadmap(
                input_text="Test content",
                mode=LearningMode.UNTIMED,
                input_id="input_test999"
            )
        
        assert "missing 'modules' field" in str(exc_info.value).lower()
    
    @patch('app.services.roadmap_service.LLMService')
    def test_roadmap_generation_llm_failure_propagates(self, mock_llm_class):
        """Test that LLM failures are propagated."""
        mock_llm = Mock()
        mock_llm.generate_roadmap_llm.side_effect = RuntimeError("LLM service unavailable")
        mock_llm_class.return_value = mock_llm
        
        service = RoadmapService(llm_service=mock_llm)
        
        with pytest.raises(RuntimeError) as exc_info:
            service.generate_roadmap(
                input_text="Test content",
                mode=LearningMode.UNTIMED,
                input_id="input_test000"
            )
        
        assert "LLM service unavailable" in str(exc_info.value)


class TestRoadmapStructureValidation:
    """Test roadmap structure validation."""
    
    @patch('app.services.roadmap_service.LLMService')
    def test_all_modules_have_required_fields(self, mock_llm_class):
        """Test that all generated modules have required fields."""
        mock_llm = Mock()
        mock_llm.generate_roadmap_llm.return_value = {
            "modules": [
                {
                    "topic_name": "Module 1",
                    "estimated_hours": 5.0,
                    "prerequisites": [],
                    "order": 1
                }
            ]
        }
        mock_llm_class.return_value = mock_llm
        
        service = RoadmapService(llm_service=mock_llm)
        modules = service.generate_roadmap(
            input_text="Test",
            mode=LearningMode.UNTIMED,
            input_id="input_test"
        )
        
        module = modules[0]
        assert hasattr(module, 'module_id')
        assert hasattr(module, 'topic_name')
        assert hasattr(module, 'estimated_hours')
        assert hasattr(module, 'prerequisites')
        assert hasattr(module, 'order')
        
        # Verify types
        assert isinstance(module.module_id, str)
        assert isinstance(module.topic_name, str)
        assert isinstance(module.estimated_hours, float)
        assert isinstance(module.prerequisites, list)
        assert isinstance(module.order, int)
