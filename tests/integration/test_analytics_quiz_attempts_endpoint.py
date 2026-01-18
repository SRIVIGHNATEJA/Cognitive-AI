"""
Integration tests for quiz attempt analytics endpoint.

Tests the /api/analytics/quiz/{quiz_id}/attempts endpoint.
"""

import pytest
from fastapi.testclient import TestClient
from pathlib import Path
import json

from app.main import app
from app.services.cache_service import CacheService


@pytest.fixture
def test_cache_dir(tmp_path):
    """Create a temporary cache directory for testing."""
    cache_dir = tmp_path / "cache"
    quizzes_dir = cache_dir / "quizzes"
    quizzes_dir.mkdir(parents=True)
    return cache_dir


@pytest.fixture
def client_with_cache(test_cache_dir, monkeypatch):
    """Create test client with custom cache directory."""
    # Patch the cache service to use test directory
    monkeypatch.setenv("CACHE_DIR", str(test_cache_dir))
    
    # Create new cache service instance
    cache_service = CacheService(cache_dir=str(test_cache_dir))
    
    # Patch the global cache service in analytics router
    from app.routers import analytics
    monkeypatch.setattr(analytics, "cache_service", cache_service)
    
    # Patch the analytics service to use the test cache service
    from app.services.analytics_service import AnalyticsService
    analytics_service = AnalyticsService(cache_service=cache_service)
    monkeypatch.setattr(analytics, "analytics_service", analytics_service)
    
    return TestClient(app)


class TestQuizAttemptAnalyticsEndpoint:
    """Tests for /api/analytics/quiz/{quiz_id}/attempts endpoint."""
    
    def test_get_quiz_attempts_single_attempt(self, client_with_cache, test_cache_dir):
        """Test getting quiz attempts with single attempt."""
        # Create evaluation file
        quizzes_dir = test_cache_dir / "quizzes"
        evaluation_data = {
            "evaluation_id": "eval_123",
            "quiz_id": "quiz_abc",
            "module_id": "mod_xyz",
            "attempt_number": 1,
            "score": 3,
            "accuracy": 60.0,
            "time_taken_seconds": 20,
            "evaluated_at": "2026-01-19T10:00:00"
        }
        
        eval_file = quizzes_dir / "evaluation_eval_123.json"
        eval_file.write_text(json.dumps(evaluation_data))
        
        # Make request
        response = client_with_cache.get("/api/analytics/quiz/quiz_abc/attempts")
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert data["quiz_id"] == "quiz_abc"
        assert data["module_id"] == "mod_xyz"
        assert len(data["attempts"]) == 1
        assert data["attempts"][0]["attempt_number"] == 1
        assert data["attempts"][0]["score"] == 3
        assert data["attempts"][0]["accuracy"] == 60.0
        assert data["attempts"][0]["time_taken_seconds"] == 20
        assert data["improvement_rate"] is None  # Only one attempt
    
    def test_get_quiz_attempts_multiple_attempts(self, client_with_cache, test_cache_dir):
        """Test getting quiz attempts with multiple attempts."""
        # Create evaluation files
        quizzes_dir = test_cache_dir / "quizzes"
        evaluations = [
            {
                "evaluation_id": "eval_1",
                "quiz_id": "quiz_abc",
                "module_id": "mod_xyz",
                "attempt_number": 1,
                "score": 2,
                "accuracy": 40.0,
                "time_taken_seconds": 20,
                "evaluated_at": "2026-01-19T10:00:00"
            },
            {
                "evaluation_id": "eval_2",
                "quiz_id": "quiz_abc",
                "module_id": "mod_xyz",
                "attempt_number": 2,
                "score": 4,
                "accuracy": 80.0,
                "time_taken_seconds": 15,
                "evaluated_at": "2026-01-19T11:00:00"
            }
        ]
        
        for eval_data in evaluations:
            eval_file = quizzes_dir / f"evaluation_{eval_data['evaluation_id']}.json"
            eval_file.write_text(json.dumps(eval_data))
        
        # Make request
        response = client_with_cache.get("/api/analytics/quiz/quiz_abc/attempts")
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert len(data["attempts"]) == 2
        assert data["attempts"][0]["attempt_number"] == 1
        assert data["attempts"][0]["score"] == 2
        assert data["attempts"][1]["attempt_number"] == 2
        assert data["attempts"][1]["score"] == 4
        assert data["improvement_rate"] == 100.0  # (80-40)/40*100
    
    def test_get_quiz_attempts_not_found(self, client_with_cache, test_cache_dir):
        """Test getting quiz attempts for non-existent quiz."""
        # Make request for non-existent quiz
        response = client_with_cache.get("/api/analytics/quiz/quiz_nonexistent/attempts")
        
        # Verify 404 response
        assert response.status_code == 404
        data = response.json()
        assert "No attempts found" in data["detail"]
    
    def test_get_quiz_attempts_sorted_by_attempt_number(self, client_with_cache, test_cache_dir):
        """Test that attempts are sorted by attempt_number."""
        # Create evaluation files out of order
        quizzes_dir = test_cache_dir / "quizzes"
        evaluations = [
            {
                "evaluation_id": "eval_3",
                "quiz_id": "quiz_abc",
                "module_id": "mod_xyz",
                "attempt_number": 3,
                "score": 5,
                "accuracy": 100.0,
                "time_taken_seconds": 10,
                "evaluated_at": "2026-01-19T12:00:00"
            },
            {
                "evaluation_id": "eval_1",
                "quiz_id": "quiz_abc",
                "module_id": "mod_xyz",
                "attempt_number": 1,
                "score": 2,
                "accuracy": 40.0,
                "time_taken_seconds": 20,
                "evaluated_at": "2026-01-19T10:00:00"
            },
            {
                "evaluation_id": "eval_2",
                "quiz_id": "quiz_abc",
                "module_id": "mod_xyz",
                "attempt_number": 2,
                "score": 3,
                "accuracy": 60.0,
                "time_taken_seconds": 15,
                "evaluated_at": "2026-01-19T11:00:00"
            }
        ]
        
        for eval_data in evaluations:
            eval_file = quizzes_dir / f"evaluation_{eval_data['evaluation_id']}.json"
            eval_file.write_text(json.dumps(eval_data))
        
        # Make request
        response = client_with_cache.get("/api/analytics/quiz/quiz_abc/attempts")
        
        # Verify sorted order
        assert response.status_code == 200
        data = response.json()
        
        assert len(data["attempts"]) == 3
        assert data["attempts"][0]["attempt_number"] == 1
        assert data["attempts"][1]["attempt_number"] == 2
        assert data["attempts"][2]["attempt_number"] == 3
    
    def test_get_quiz_attempts_improvement_rate_calculation(self, client_with_cache, test_cache_dir):
        """Test improvement rate calculation with various scenarios."""
        # Create evaluation files
        quizzes_dir = test_cache_dir / "quizzes"
        evaluations = [
            {
                "evaluation_id": "eval_1",
                "quiz_id": "quiz_abc",
                "module_id": "mod_xyz",
                "attempt_number": 1,
                "score": 1,
                "accuracy": 20.0,
                "time_taken_seconds": 25,
                "evaluated_at": "2026-01-19T10:00:00"
            },
            {
                "evaluation_id": "eval_2",
                "quiz_id": "quiz_abc",
                "module_id": "mod_xyz",
                "attempt_number": 2,
                "score": 5,
                "accuracy": 100.0,
                "time_taken_seconds": 12,
                "evaluated_at": "2026-01-19T11:00:00"
            }
        ]
        
        for eval_data in evaluations:
            eval_file = quizzes_dir / f"evaluation_{eval_data['evaluation_id']}.json"
            eval_file.write_text(json.dumps(eval_data))
        
        # Make request
        response = client_with_cache.get("/api/analytics/quiz/quiz_abc/attempts")
        
        # Verify improvement rate
        assert response.status_code == 200
        data = response.json()
        
        # (100-20)/20*100 = 400%
        assert data["improvement_rate"] == 400.0
    
    def test_get_quiz_attempts_backward_compatibility(self, client_with_cache, test_cache_dir):
        """Test backward compatibility with old evaluations without attempt_number."""
        # Create evaluation file without attempt_number
        quizzes_dir = test_cache_dir / "quizzes"
        evaluation_data = {
            "evaluation_id": "eval_old",
            "quiz_id": "quiz_abc",
            "module_id": "mod_xyz",
            # No attempt_number field
            "score": 3,
            "accuracy": 60.0,
            "time_taken_seconds": 20,
            "evaluated_at": "2026-01-19T10:00:00"
        }
        
        eval_file = quizzes_dir / "evaluation_eval_old.json"
        eval_file.write_text(json.dumps(evaluation_data))
        
        # Make request
        response = client_with_cache.get("/api/analytics/quiz/quiz_abc/attempts")
        
        # Verify defaults to attempt 1
        assert response.status_code == 200
        data = response.json()
        
        assert len(data["attempts"]) == 1
        assert data["attempts"][0]["attempt_number"] == 1
