"""
Unit tests for quiz attempt analytics functionality.

Tests the new get_quiz_attempt_history and calculate_improvement_rate methods
in AnalyticsService.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import json

from app.services.analytics_service import AnalyticsService
from app.services.cache_service import CacheService


class TestQuizAttemptHistory:
    """Tests for get_quiz_attempt_history method."""
    
    def test_get_quiz_attempt_history_single_attempt(self, tmp_path):
        """Test getting attempt history with single attempt."""
        # Setup cache directory
        cache_dir = tmp_path / "cache"
        quizzes_dir = cache_dir / "quizzes"
        quizzes_dir.mkdir(parents=True)
        
        # Create evaluation file
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
        
        # Create service with custom cache dir
        cache_service = CacheService(cache_dir=str(cache_dir))
        analytics_service = AnalyticsService(cache_service=cache_service)
        
        # Get attempt history
        attempts = analytics_service.get_quiz_attempt_history("quiz_abc")
        
        # Verify
        assert len(attempts) == 1
        assert attempts[0]["attempt_number"] == 1
        assert attempts[0]["score"] == 3
        assert attempts[0]["accuracy"] == 60.0
        assert attempts[0]["time_taken_seconds"] == 20
        assert attempts[0]["evaluated_at"] == "2026-01-19T10:00:00"
    
    def test_get_quiz_attempt_history_multiple_attempts(self, tmp_path):
        """Test getting attempt history with multiple attempts."""
        # Setup cache directory
        cache_dir = tmp_path / "cache"
        quizzes_dir = cache_dir / "quizzes"
        quizzes_dir.mkdir(parents=True)
        
        # Create evaluation files (out of order to test sorting)
        evaluations = [
            {
                "evaluation_id": "eval_2",
                "quiz_id": "quiz_abc",
                "module_id": "mod_xyz",
                "attempt_number": 2,
                "score": 4,
                "accuracy": 80.0,
                "time_taken_seconds": 15,
                "evaluated_at": "2026-01-19T11:00:00"
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
                "evaluation_id": "eval_3",
                "quiz_id": "quiz_abc",
                "module_id": "mod_xyz",
                "attempt_number": 3,
                "score": 5,
                "accuracy": 100.0,
                "time_taken_seconds": 12,
                "evaluated_at": "2026-01-19T12:00:00"
            }
        ]
        
        for eval_data in evaluations:
            eval_file = quizzes_dir / f"evaluation_{eval_data['evaluation_id']}.json"
            eval_file.write_text(json.dumps(eval_data))
        
        # Create service
        cache_service = CacheService(cache_dir=str(cache_dir))
        analytics_service = AnalyticsService(cache_service=cache_service)
        
        # Get attempt history
        attempts = analytics_service.get_quiz_attempt_history("quiz_abc")
        
        # Verify sorted by attempt_number
        assert len(attempts) == 3
        assert attempts[0]["attempt_number"] == 1
        assert attempts[0]["score"] == 2
        assert attempts[1]["attempt_number"] == 2
        assert attempts[1]["score"] == 4
        assert attempts[2]["attempt_number"] == 3
        assert attempts[2]["score"] == 5
    
    def test_get_quiz_attempt_history_no_attempts(self, tmp_path):
        """Test getting attempt history when no attempts exist."""
        # Setup empty cache directory
        cache_dir = tmp_path / "cache"
        quizzes_dir = cache_dir / "quizzes"
        quizzes_dir.mkdir(parents=True)
        
        # Create service
        cache_service = CacheService(cache_dir=str(cache_dir))
        analytics_service = AnalyticsService(cache_service=cache_service)
        
        # Get attempt history
        attempts = analytics_service.get_quiz_attempt_history("quiz_nonexistent")
        
        # Verify empty list
        assert len(attempts) == 0
    
    def test_get_quiz_attempt_history_filters_by_quiz_id(self, tmp_path):
        """Test that only matching quiz_id attempts are returned."""
        # Setup cache directory
        cache_dir = tmp_path / "cache"
        quizzes_dir = cache_dir / "quizzes"
        quizzes_dir.mkdir(parents=True)
        
        # Create evaluation files for different quizzes
        evaluations = [
            {
                "evaluation_id": "eval_1",
                "quiz_id": "quiz_abc",
                "module_id": "mod_xyz",
                "attempt_number": 1,
                "score": 3,
                "accuracy": 60.0,
                "time_taken_seconds": 20,
                "evaluated_at": "2026-01-19T10:00:00"
            },
            {
                "evaluation_id": "eval_2",
                "quiz_id": "quiz_def",
                "module_id": "mod_xyz",
                "attempt_number": 1,
                "score": 4,
                "accuracy": 80.0,
                "time_taken_seconds": 15,
                "evaluated_at": "2026-01-19T11:00:00"
            }
        ]
        
        for eval_data in evaluations:
            eval_file = quizzes_dir / f"evaluation_{eval_data['evaluation_id']}.json"
            eval_file.write_text(json.dumps(eval_data))
        
        # Create service
        cache_service = CacheService(cache_dir=str(cache_dir))
        analytics_service = AnalyticsService(cache_service=cache_service)
        
        # Get attempt history for quiz_abc
        attempts = analytics_service.get_quiz_attempt_history("quiz_abc")
        
        # Verify only quiz_abc attempt returned
        assert len(attempts) == 1
        assert attempts[0]["score"] == 3
    
    def test_get_quiz_attempt_history_handles_missing_attempt_number(self, tmp_path):
        """Test backward compatibility with old evaluations without attempt_number."""
        # Setup cache directory
        cache_dir = tmp_path / "cache"
        quizzes_dir = cache_dir / "quizzes"
        quizzes_dir.mkdir(parents=True)
        
        # Create evaluation file without attempt_number
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
        
        # Create service
        cache_service = CacheService(cache_dir=str(cache_dir))
        analytics_service = AnalyticsService(cache_service=cache_service)
        
        # Get attempt history
        attempts = analytics_service.get_quiz_attempt_history("quiz_abc")
        
        # Verify defaults to attempt 1
        assert len(attempts) == 1
        assert attempts[0]["attempt_number"] == 1


class TestImprovementRate:
    """Tests for calculate_improvement_rate method."""
    
    def test_calculate_improvement_rate_positive(self):
        """Test calculating positive improvement rate."""
        analytics_service = AnalyticsService()
        
        attempts = [
            {"attempt_number": 1, "accuracy": 40.0},
            {"attempt_number": 2, "accuracy": 60.0}
        ]
        
        improvement_rate = analytics_service.calculate_improvement_rate(attempts)
        
        # (60 - 40) / 40 * 100 = 50%
        assert improvement_rate == 50.0
    
    def test_calculate_improvement_rate_negative(self):
        """Test calculating negative improvement rate (regression)."""
        analytics_service = AnalyticsService()
        
        attempts = [
            {"attempt_number": 1, "accuracy": 80.0},
            {"attempt_number": 2, "accuracy": 60.0}
        ]
        
        improvement_rate = analytics_service.calculate_improvement_rate(attempts)
        
        # (60 - 80) / 80 * 100 = -25%
        assert improvement_rate == -25.0
    
    def test_calculate_improvement_rate_zero(self):
        """Test calculating zero improvement rate (no change)."""
        analytics_service = AnalyticsService()
        
        attempts = [
            {"attempt_number": 1, "accuracy": 60.0},
            {"attempt_number": 2, "accuracy": 60.0}
        ]
        
        improvement_rate = analytics_service.calculate_improvement_rate(attempts)
        
        assert improvement_rate == 0.0
    
    def test_calculate_improvement_rate_single_attempt(self):
        """Test that single attempt returns None."""
        analytics_service = AnalyticsService()
        
        attempts = [
            {"attempt_number": 1, "accuracy": 60.0}
        ]
        
        improvement_rate = analytics_service.calculate_improvement_rate(attempts)
        
        assert improvement_rate is None
    
    def test_calculate_improvement_rate_zero_first_accuracy(self):
        """Test that zero first accuracy returns None (avoid division by zero)."""
        analytics_service = AnalyticsService()
        
        attempts = [
            {"attempt_number": 1, "accuracy": 0.0},
            {"attempt_number": 2, "accuracy": 60.0}
        ]
        
        improvement_rate = analytics_service.calculate_improvement_rate(attempts)
        
        assert improvement_rate is None
    
    def test_calculate_improvement_rate_multiple_attempts(self):
        """Test that improvement rate uses first and latest attempts."""
        analytics_service = AnalyticsService()
        
        attempts = [
            {"attempt_number": 1, "accuracy": 40.0},
            {"attempt_number": 2, "accuracy": 50.0},
            {"attempt_number": 3, "accuracy": 80.0}
        ]
        
        improvement_rate = analytics_service.calculate_improvement_rate(attempts)
        
        # (80 - 40) / 40 * 100 = 100%
        assert improvement_rate == 100.0
    
    def test_calculate_improvement_rate_large_improvement(self):
        """Test calculating large improvement rate."""
        analytics_service = AnalyticsService()
        
        attempts = [
            {"attempt_number": 1, "accuracy": 20.0},
            {"attempt_number": 2, "accuracy": 100.0}
        ]
        
        improvement_rate = analytics_service.calculate_improvement_rate(attempts)
        
        # (100 - 20) / 20 * 100 = 400%
        assert improvement_rate == 400.0
