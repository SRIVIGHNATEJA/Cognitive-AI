"""
Unit tests for Analytics Service.

Tests completion calculation, progress tracking, and weak area identification.
"""

import pytest
from unittest.mock import Mock, patch
from app.services.analytics_service import AnalyticsService
from app.models import ModuleProgress


@pytest.fixture
def mock_cache_service():
    """Create a mock cache service for testing."""
    return Mock()


@pytest.fixture
def analytics_service(mock_cache_service):
    """Create analytics service with mocked cache."""
    return AnalyticsService(cache_service=mock_cache_service)


@pytest.fixture
def sample_roadmap():
    """Sample roadmap data for testing."""
    return {
        "modules": [
            {
                "module_id": "mod_1",
                "topic_name": "Python Basics",
                "estimated_hours": 5.0,
                "prerequisites": [],
                "order": 1
            },
            {
                "module_id": "mod_2",
                "topic_name": "Data Structures",
                "estimated_hours": 8.0,
                "prerequisites": ["mod_1"],
                "order": 2
            },
            {
                "module_id": "mod_3",
                "topic_name": "Algorithms",
                "estimated_hours": 10.0,
                "prerequisites": ["mod_2"],
                "order": 3
            }
        ],
        "total_modules": 3,
        "total_estimated_hours": 23.0
    }


class TestModuleCompletionCalculation:
    """Test module completion percentage calculation."""
    
    def test_completion_with_notes_and_quiz(self, analytics_service, mock_cache_service):
        """Test completion when both notes and quiz exist."""
        # Mock: notes exist, quiz taken
        mock_cache_service.get_cached_content.return_value = "Sample notes content"
        mock_cache_service.get_quiz_metrics.return_value = {
            "total_quizzes": 2,
            "average_accuracy": 80.0
        }
        
        completion = analytics_service.calculate_module_completion("mod_1")
        
        assert completion == 100.0
        mock_cache_service.get_cached_content.assert_called_once_with("mod_1", 'notes')
        mock_cache_service.get_quiz_metrics.assert_called_once_with("mod_1")
    
    def test_completion_with_notes_only(self, analytics_service, mock_cache_service):
        """Test completion when only notes exist."""
        # Mock: notes exist, no quiz
        mock_cache_service.get_cached_content.return_value = "Sample notes content"
        mock_cache_service.get_quiz_metrics.return_value = None
        
        completion = analytics_service.calculate_module_completion("mod_1")
        
        assert completion == 50.0
    
    def test_completion_with_quiz_only(self, analytics_service, mock_cache_service):
        """Test completion when only quiz exists."""
        # Mock: no notes, quiz taken
        mock_cache_service.get_cached_content.return_value = None
        mock_cache_service.get_quiz_metrics.return_value = {
            "total_quizzes": 1,
            "average_accuracy": 75.0
        }
        
        completion = analytics_service.calculate_module_completion("mod_1")
        
        assert completion == 50.0
    
    def test_completion_with_nothing(self, analytics_service, mock_cache_service):
        """Test completion when nothing exists."""
        # Mock: no notes, no quiz
        mock_cache_service.get_cached_content.return_value = None
        mock_cache_service.get_quiz_metrics.return_value = None
        
        completion = analytics_service.calculate_module_completion("mod_1")
        
        assert completion == 0.0
    
    def test_completion_with_zero_quizzes(self, analytics_service, mock_cache_service):
        """Test completion when metrics exist but no quizzes taken."""
        # Mock: notes exist, metrics exist but total_quizzes = 0
        mock_cache_service.get_cached_content.return_value = "Sample notes"
        mock_cache_service.get_quiz_metrics.return_value = {
            "total_quizzes": 0,
            "average_accuracy": 0.0
        }
        
        completion = analytics_service.calculate_module_completion("mod_1")
        
        assert completion == 50.0  # Only notes count


class TestOverallProgressCalculation:
    """Test overall progress calculation across modules."""
    
    def test_overall_progress_all_complete(self, analytics_service, mock_cache_service, sample_roadmap):
        """Test overall progress when all modules are complete."""
        mock_cache_service.get_cached_roadmap.return_value = sample_roadmap
        
        # Mock all modules as 100% complete
        mock_cache_service.get_cached_content.return_value = "Notes"
        mock_cache_service.get_quiz_metrics.return_value = {"total_quizzes": 1}
        
        progress = analytics_service.calculate_overall_progress()
        
        assert progress == 100.0
    
    def test_overall_progress_partial_complete(self, analytics_service, mock_cache_service, sample_roadmap):
        """Test overall progress with partial completion."""
        mock_cache_service.get_cached_roadmap.return_value = sample_roadmap
        
        # Mock different completion levels
        def mock_content(module_id, content_type):
            return "Notes" if module_id in ["mod_1", "mod_2"] else None
        
        def mock_metrics(module_id):
            if module_id == "mod_1":
                return {"total_quizzes": 1}
            return None
        
        mock_cache_service.get_cached_content.side_effect = mock_content
        mock_cache_service.get_quiz_metrics.side_effect = mock_metrics
        
        progress = analytics_service.calculate_overall_progress()
        
        # mod_1: 100% (notes + quiz), mod_2: 50% (notes only), mod_3: 0%
        # Average: (100 + 50 + 0) / 3 = 50.0
        assert progress == 50.0
    
    def test_overall_progress_no_roadmap(self, analytics_service, mock_cache_service):
        """Test overall progress when no roadmap exists."""
        mock_cache_service.get_cached_roadmap.return_value = None
        
        progress = analytics_service.calculate_overall_progress()
        
        assert progress == 0.0
    
    def test_overall_progress_empty_modules(self, analytics_service, mock_cache_service):
        """Test overall progress with empty modules list."""
        mock_cache_service.get_cached_roadmap.return_value = {"modules": []}
        
        progress = analytics_service.calculate_overall_progress()
        
        assert progress == 0.0


class TestWeakAreaIdentification:
    """Test weak area identification logic."""
    
    def test_identify_weak_areas_default_threshold(self, analytics_service, mock_cache_service, sample_roadmap):
        """Test weak area identification with default 60% threshold."""
        mock_cache_service.get_cached_roadmap.return_value = sample_roadmap
        
        # Mock quiz metrics with different accuracies
        def mock_metrics(module_id):
            metrics_map = {
                "mod_1": {"total_quizzes": 2, "average_accuracy": 75.0},  # Above threshold
                "mod_2": {"total_quizzes": 1, "average_accuracy": 55.0},  # Below threshold
                "mod_3": {"total_quizzes": 3, "average_accuracy": 45.0}   # Below threshold
            }
            return metrics_map.get(module_id)
        
        mock_cache_service.get_quiz_metrics.side_effect = mock_metrics
        
        weak_areas = analytics_service.identify_weak_areas()
        
        assert len(weak_areas) == 2
        assert "mod_2" in weak_areas
        assert "mod_3" in weak_areas
        assert "mod_1" not in weak_areas
    
    def test_identify_weak_areas_custom_threshold(self, analytics_service, mock_cache_service, sample_roadmap):
        """Test weak area identification with custom threshold."""
        mock_cache_service.get_cached_roadmap.return_value = sample_roadmap
        
        def mock_metrics(module_id):
            metrics_map = {
                "mod_1": {"total_quizzes": 2, "average_accuracy": 85.0},
                "mod_2": {"total_quizzes": 1, "average_accuracy": 75.0},
                "mod_3": {"total_quizzes": 3, "average_accuracy": 65.0}
            }
            return metrics_map.get(module_id)
        
        mock_cache_service.get_quiz_metrics.side_effect = mock_metrics
        
        # Use 80% threshold
        weak_areas = analytics_service.identify_weak_areas(threshold=80.0)
        
        assert len(weak_areas) == 2
        assert "mod_2" in weak_areas
        assert "mod_3" in weak_areas
    
    def test_identify_weak_areas_no_quizzes(self, analytics_service, mock_cache_service, sample_roadmap):
        """Test weak area identification when no quizzes taken."""
        mock_cache_service.get_cached_roadmap.return_value = sample_roadmap
        mock_cache_service.get_quiz_metrics.return_value = None
        
        weak_areas = analytics_service.identify_weak_areas()
        
        assert len(weak_areas) == 0
    
    def test_identify_weak_areas_no_roadmap(self, analytics_service, mock_cache_service):
        """Test weak area identification when no roadmap exists."""
        mock_cache_service.get_cached_roadmap.return_value = None
        
        weak_areas = analytics_service.identify_weak_areas()
        
        assert len(weak_areas) == 0


class TestQuizMetricsAggregation:
    """Test quiz metrics aggregation."""
    
    def test_aggregate_quiz_metrics_success(self, analytics_service, mock_cache_service):
        """Test successful quiz metrics aggregation."""
        expected_metrics = {
            "module_id": "mod_1",
            "total_quizzes": 5,
            "average_score": 7.4,
            "best_score": 9,
            "worst_score": 6,
            "average_accuracy": 74.0
        }
        mock_cache_service.get_quiz_metrics.return_value = expected_metrics
        
        metrics = analytics_service.aggregate_quiz_metrics("mod_1")
        
        assert metrics == expected_metrics
        mock_cache_service.get_quiz_metrics.assert_called_once_with("mod_1")
    
    def test_aggregate_quiz_metrics_no_data(self, analytics_service, mock_cache_service):
        """Test quiz metrics aggregation when no data exists."""
        mock_cache_service.get_quiz_metrics.return_value = None
        
        metrics = analytics_service.aggregate_quiz_metrics("mod_1")
        
        assert metrics == {}


class TestModuleProgressRetrieval:
    """Test module progress data retrieval."""
    
    def test_get_module_progress(self, analytics_service, mock_cache_service):
        """Test getting progress for a specific module."""
        # Mock completion and metrics
        mock_cache_service.get_cached_content.return_value = "Notes"
        mock_cache_service.get_quiz_metrics.return_value = {
            "total_quizzes": 3,
            "average_accuracy": 82.5
        }
        
        progress = analytics_service.get_module_progress("mod_1", "Python Basics")
        
        assert isinstance(progress, ModuleProgress)
        assert progress.module_id == "mod_1"
        assert progress.topic_name == "Python Basics"
        assert progress.completion_percentage == 100.0
        assert progress.quizzes_taken == 3
        assert progress.average_accuracy == 82.5
    
    def test_get_all_module_progress(self, analytics_service, mock_cache_service, sample_roadmap):
        """Test getting progress for all modules."""
        mock_cache_service.get_cached_roadmap.return_value = sample_roadmap
        
        # Mock different states for each module
        def mock_content(module_id, content_type):
            return "Notes" if module_id in ["mod_1", "mod_2"] else None
        
        def mock_metrics(module_id):
            metrics_map = {
                "mod_1": {"total_quizzes": 2, "average_accuracy": 80.0},
                "mod_2": {"total_quizzes": 1, "average_accuracy": 70.0},
                "mod_3": None
            }
            return metrics_map.get(module_id)
        
        mock_cache_service.get_cached_content.side_effect = mock_content
        mock_cache_service.get_quiz_metrics.side_effect = mock_metrics
        
        progress_list = analytics_service.get_all_module_progress()
        
        assert len(progress_list) == 3
        assert all(isinstance(p, ModuleProgress) for p in progress_list)
        
        # Verify first module
        assert progress_list[0].module_id == "mod_1"
        assert progress_list[0].completion_percentage == 100.0
        assert progress_list[0].quizzes_taken == 2
    
    def test_get_all_module_progress_no_roadmap(self, analytics_service, mock_cache_service):
        """Test getting all module progress when no roadmap exists."""
        mock_cache_service.get_cached_roadmap.return_value = None
        
        progress_list = analytics_service.get_all_module_progress()
        
        assert progress_list == []


class TestCompletedModulesCount:
    """Test counting completed modules."""
    
    def test_count_completed_modules_default_threshold(self, analytics_service, mock_cache_service, sample_roadmap):
        """Test counting completed modules with default 100% threshold."""
        mock_cache_service.get_cached_roadmap.return_value = sample_roadmap
        
        # Mock: mod_1 complete, mod_2 partial, mod_3 not started
        def mock_content(module_id, content_type):
            return "Notes" if module_id in ["mod_1", "mod_2"] else None
        
        def mock_metrics(module_id):
            return {"total_quizzes": 1} if module_id == "mod_1" else None
        
        mock_cache_service.get_cached_content.side_effect = mock_content
        mock_cache_service.get_quiz_metrics.side_effect = mock_metrics
        
        count = analytics_service.count_completed_modules()
        
        assert count == 1  # Only mod_1 is 100% complete
    
    def test_count_completed_modules_custom_threshold(self, analytics_service, mock_cache_service, sample_roadmap):
        """Test counting completed modules with custom threshold."""
        mock_cache_service.get_cached_roadmap.return_value = sample_roadmap
        
        def mock_content(module_id, content_type):
            return "Notes" if module_id in ["mod_1", "mod_2"] else None
        
        def mock_metrics(module_id):
            return {"total_quizzes": 1} if module_id == "mod_1" else None
        
        mock_cache_service.get_cached_content.side_effect = mock_content
        mock_cache_service.get_quiz_metrics.side_effect = mock_metrics
        
        # Use 50% threshold
        count = analytics_service.count_completed_modules(threshold=50.0)
        
        assert count == 2  # mod_1 (100%) and mod_2 (50%)


class TestAverageQuizAccuracy:
    """Test average quiz accuracy calculation."""
    
    def test_calculate_average_quiz_accuracy(self, analytics_service, mock_cache_service, sample_roadmap):
        """Test calculating average quiz accuracy across modules."""
        mock_cache_service.get_cached_roadmap.return_value = sample_roadmap
        
        def mock_metrics(module_id):
            metrics_map = {
                "mod_1": {"total_quizzes": 2, "average_accuracy": 80.0},
                "mod_2": {"total_quizzes": 1, "average_accuracy": 70.0},
                "mod_3": {"total_quizzes": 3, "average_accuracy": 90.0}
            }
            return metrics_map.get(module_id)
        
        mock_cache_service.get_quiz_metrics.side_effect = mock_metrics
        
        avg_accuracy = analytics_service.calculate_average_quiz_accuracy()
        
        # Average: (80 + 70 + 90) / 3 = 80.0
        assert avg_accuracy == 80.0
    
    def test_calculate_average_quiz_accuracy_partial_quizzes(self, analytics_service, mock_cache_service, sample_roadmap):
        """Test average accuracy when only some modules have quizzes."""
        mock_cache_service.get_cached_roadmap.return_value = sample_roadmap
        
        def mock_metrics(module_id):
            metrics_map = {
                "mod_1": {"total_quizzes": 2, "average_accuracy": 80.0},
                "mod_2": None,  # No quizzes
                "mod_3": {"total_quizzes": 1, "average_accuracy": 60.0}
            }
            return metrics_map.get(module_id)
        
        mock_cache_service.get_quiz_metrics.side_effect = mock_metrics
        
        avg_accuracy = analytics_service.calculate_average_quiz_accuracy()
        
        # Average: (80 + 60) / 2 = 70.0 (mod_2 excluded)
        assert avg_accuracy == 70.0
    
    def test_calculate_average_quiz_accuracy_no_quizzes(self, analytics_service, mock_cache_service, sample_roadmap):
        """Test average accuracy when no quizzes taken."""
        mock_cache_service.get_cached_roadmap.return_value = sample_roadmap
        mock_cache_service.get_quiz_metrics.return_value = None
        
        avg_accuracy = analytics_service.calculate_average_quiz_accuracy()
        
        assert avg_accuracy == 0.0
    
    def test_calculate_average_quiz_accuracy_no_roadmap(self, analytics_service, mock_cache_service):
        """Test average accuracy when no roadmap exists."""
        mock_cache_service.get_cached_roadmap.return_value = None
        
        avg_accuracy = analytics_service.calculate_average_quiz_accuracy()
        
        assert avg_accuracy == 0.0
