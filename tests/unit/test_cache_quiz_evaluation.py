"""
Unit tests for cache service quiz evaluation methods.

Tests the new cache methods introduced in Phase 1:
- cache_quiz_submission / get_quiz_submission
- cache_quiz_evaluation / get_quiz_evaluation
- get_quiz_evaluation_by_quiz_id
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
    shutil.rmtree(temp_dir)


@pytest.fixture
def cache_service(temp_cache_dir):
    """Create a CacheService instance with temporary directory."""
    return CacheService(cache_dir=temp_cache_dir)


class TestQuizSubmissionCache:
    """Test quiz submission caching methods."""
    
    def test_cache_and_retrieve_submission(self, cache_service):
        """Test caching and retrieving a quiz submission."""
        submission_data = {
            "submission_id": "sub_123",
            "quiz_id": "quiz_456",
            "module_id": "mod_789",
            "user_answers": {1: "A", 2: "B", 3: "C", 4: "D", 5: "A"},
            "time_taken_seconds": 300,
            "submitted_at": datetime.now().isoformat()
        }
        
        # Cache submission
        cache_service.cache_quiz_submission(submission_data)
        
        # Retrieve submission
        retrieved = cache_service.get_quiz_submission("sub_123")
        
        assert retrieved is not None
        assert retrieved["submission_id"] == "sub_123"
        assert retrieved["quiz_id"] == "quiz_456"
        assert retrieved["module_id"] == "mod_789"
        assert len(retrieved["user_answers"]) == 5
        assert retrieved["time_taken_seconds"] == 300
    
    def test_get_nonexistent_submission(self, cache_service):
        """Test retrieving a submission that doesn't exist."""
        retrieved = cache_service.get_quiz_submission("nonexistent")
        assert retrieved is None
    
    def test_cache_submission_without_required_fields(self, cache_service):
        """Test caching submission without required fields raises error."""
        with pytest.raises(ValueError):
            cache_service.cache_quiz_submission({"quiz_id": "quiz_123"})  # Missing submission_id


class TestQuizEvaluationCache:
    """Test quiz evaluation caching methods."""
    
    def test_cache_and_retrieve_evaluation(self, cache_service):
        """Test caching and retrieving a quiz evaluation."""
        evaluation_data = {
            "evaluation_id": "eval_123",
            "quiz_id": "quiz_456",
            "module_id": "mod_789",
            "score": 4,
            "accuracy": 80.0,
            "correct_answers_count": 4,
            "incorrect_answers_count": 1,
            "question_results": [],
            "time_taken_seconds": 300,
            "time_limit_exceeded": False,
            "evaluated_at": datetime.now().isoformat()
        }
        
        # Cache evaluation
        cache_service.cache_quiz_evaluation(evaluation_data)
        
        # Retrieve evaluation
        retrieved = cache_service.get_quiz_evaluation("eval_123")
        
        assert retrieved is not None
        assert retrieved["evaluation_id"] == "eval_123"
        assert retrieved["quiz_id"] == "quiz_456"
        assert retrieved["score"] == 4
        assert retrieved["accuracy"] == 80.0
    
    def test_get_nonexistent_evaluation(self, cache_service):
        """Test retrieving an evaluation that doesn't exist."""
        retrieved = cache_service.get_quiz_evaluation("nonexistent")
        assert retrieved is None
    
    def test_cache_evaluation_without_required_fields(self, cache_service):
        """Test caching evaluation without required fields raises error."""
        with pytest.raises(ValueError):
            cache_service.cache_quiz_evaluation({"quiz_id": "quiz_123"})  # Missing evaluation_id
    
    def test_get_evaluation_by_quiz_id(self, cache_service):
        """Test retrieving evaluation by quiz_id."""
        evaluation_data = {
            "evaluation_id": "eval_123",
            "quiz_id": "quiz_456",
            "module_id": "mod_789",
            "score": 4,
            "accuracy": 80.0,
            "correct_answers_count": 4,
            "incorrect_answers_count": 1,
            "question_results": [],
            "time_taken_seconds": 300,
            "time_limit_exceeded": False,
            "evaluated_at": datetime.now().isoformat()
        }
        
        # Cache evaluation
        cache_service.cache_quiz_evaluation(evaluation_data)
        
        # Retrieve by quiz_id
        retrieved = cache_service.get_quiz_evaluation_by_quiz_id("quiz_456")
        
        assert retrieved is not None
        assert retrieved["quiz_id"] == "quiz_456"
        assert retrieved["evaluation_id"] == "eval_123"
    
    def test_get_evaluation_by_quiz_id_nonexistent(self, cache_service):
        """Test retrieving evaluation by quiz_id that doesn't exist."""
        retrieved = cache_service.get_quiz_evaluation_by_quiz_id("nonexistent")
        assert retrieved is None
    
    def test_get_evaluation_by_quiz_id_multiple_evaluations(self, cache_service):
        """Test retrieving evaluation when multiple evaluations exist."""
        # Cache multiple evaluations
        for i in range(3):
            evaluation_data = {
                "evaluation_id": f"eval_{i}",
                "quiz_id": f"quiz_{i}",
                "module_id": "mod_789",
                "score": 4,
                "accuracy": 80.0,
                "correct_answers_count": 4,
                "incorrect_answers_count": 1,
                "question_results": [],
                "time_taken_seconds": 300,
                "time_limit_exceeded": False,
                "evaluated_at": datetime.now().isoformat()
            }
            cache_service.cache_quiz_evaluation(evaluation_data)
        
        # Retrieve specific quiz evaluation
        retrieved = cache_service.get_quiz_evaluation_by_quiz_id("quiz_1")
        
        assert retrieved is not None
        assert retrieved["quiz_id"] == "quiz_1"
        assert retrieved["evaluation_id"] == "eval_1"


class TestQuizEvaluationWorkflow:
    """Test complete workflow: submission → evaluation."""
    
    def test_submission_then_evaluation_workflow(self, cache_service):
        """Test the complete workflow of submission followed by evaluation."""
        # Step 1: Cache submission
        submission_data = {
            "submission_id": "sub_123",
            "quiz_id": "quiz_456",
            "module_id": "mod_789",
            "user_answers": {1: "A", 2: "B", 3: "C", 4: "D", 5: "A"},
            "time_taken_seconds": 300,
            "submitted_at": datetime.now().isoformat()
        }
        cache_service.cache_quiz_submission(submission_data)
        
        # Step 2: Cache evaluation
        evaluation_data = {
            "evaluation_id": "eval_123",
            "quiz_id": "quiz_456",
            "module_id": "mod_789",
            "score": 4,
            "accuracy": 80.0,
            "correct_answers_count": 4,
            "incorrect_answers_count": 1,
            "question_results": [],
            "time_taken_seconds": 300,
            "time_limit_exceeded": False,
            "evaluated_at": datetime.now().isoformat()
        }
        cache_service.cache_quiz_evaluation(evaluation_data)
        
        # Step 3: Verify both are retrievable
        submission = cache_service.get_quiz_submission("sub_123")
        evaluation = cache_service.get_quiz_evaluation_by_quiz_id("quiz_456")
        
        assert submission is not None
        assert evaluation is not None
        assert submission["quiz_id"] == evaluation["quiz_id"]
        assert submission["time_taken_seconds"] == evaluation["time_taken_seconds"]
