"""
Integration tests for Quiz API endpoints.

Tests the complete quiz flow including generation, submission, history, and metrics.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, Mock
from datetime import datetime
from app.main import app
from app.services.cache_service import CacheService
from app.models import Quiz, QuizQuestion, LearningMode

client = TestClient(app)


@pytest.fixture
def cache_service():
    """Provide a cache service instance for tests."""
    return CacheService()


@pytest.fixture
def clear_quiz_cache(cache_service):
    """Clear quiz cache before and after each test."""
    cache_service.clear_cache('quizzes')
    yield
    cache_service.clear_cache('quizzes')


@pytest.fixture
def setup_roadmap_and_content(cache_service):
    """Set up roadmap, input, and content data for testing."""
    # Create input data
    input_id = "test_input_quiz"
    input_data = {
        "input_id": input_id,
        "detected_type": "syllabus",
        "extracted_text": "Python programming: variables, loops, functions, data structures",
        "processed_at": "2024-01-07T10:00:00"
    }
    cache_service.cache_input(input_id, input_data)
    
    # Create roadmap data
    module_id = "mod_quiz_test"
    roadmap_data = {
        "modules": [
            {
                "module_id": module_id,
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
    
    # Create content (notes)
    notes = "Python basics: variables store data, loops repeat code, functions organize logic"
    cache_service.cache_content(module_id, 'notes', notes)
    
    yield module_id
    
    # Cleanup
    cache_service.delete_cache(input_id, 'input')
    cache_service.clear_cache('roadmap')
    cache_service.clear_cache('content')


@pytest.fixture
def sample_quiz_questions():
    """Provide sample quiz questions for testing."""
    return [
        {
            "question_number": i,
            "question_text": f"Question {i}?",
            "options": ["A", "B", "C", "D"],
            "correct_answer": "A",
            "explanation": f"Explanation {i}"
        }
        for i in range(1, 11)
    ]


class TestQuizGeneration:
    """Test quiz generation endpoint."""
    
    @patch('app.routers.quiz.quiz_service.generate_quiz')
    def test_generate_untimed_quiz_success(
        self,
        mock_generate_quiz,
        setup_roadmap_and_content,
        clear_quiz_cache,
        sample_quiz_questions
    ):
        """Test successful untimed quiz generation."""
        module_id = setup_roadmap_and_content
        
        # Mock quiz generation
        questions = [QuizQuestion(**q) for q in sample_quiz_questions]
        mock_quiz = Quiz(
            quiz_id="quiz_test_123",
            module_id=module_id,
            questions=questions,
            mode=LearningMode.UNTIMED,
            time_limit_seconds=None,
            created_at=datetime.now()
        )
        mock_generate_quiz.return_value = mock_quiz
        
        # Make request
        response = client.post(
            f"/api/quiz/generate/{module_id}",
            json={"mode": "untimed"}
        )
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert data["module_id"] == module_id
        assert data["mode"] == "untimed"
        assert data["time_limit_seconds"] is None
        assert len(data["questions"]) == 10
        
        # Verify quiz generation was called
        mock_generate_quiz.assert_called_once()
    
    @patch('app.routers.quiz.quiz_service.generate_quiz')
    def test_generate_timed_quiz_success(
        self,
        mock_generate_quiz,
        setup_roadmap_and_content,
        clear_quiz_cache,
        sample_quiz_questions
    ):
        """Test successful timed quiz generation."""
        module_id = setup_roadmap_and_content
        
        # Mock quiz generation
        questions = [QuizQuestion(**q) for q in sample_quiz_questions]
        mock_quiz = Quiz(
            quiz_id="quiz_test_456",
            module_id=module_id,
            questions=questions,
            mode=LearningMode.TIMED,
            time_limit_seconds=600,
            created_at=datetime.now()
        )
        mock_generate_quiz.return_value = mock_quiz
        
        # Make request
        response = client.post(
            f"/api/quiz/generate/{module_id}",
            json={"mode": "timed", "time_limit_seconds": 600}
        )
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert data["mode"] == "timed"
        assert data["time_limit_seconds"] == 600
    
    def test_generate_timed_quiz_without_time_limit(
        self,
        setup_roadmap_and_content,
        clear_quiz_cache
    ):
        """Test timed quiz generation fails without time limit."""
        module_id = setup_roadmap_and_content
        
        response = client.post(
            f"/api/quiz/generate/{module_id}",
            json={"mode": "timed"}
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "time_limit_seconds" in data["detail"].lower()
    
    def test_generate_quiz_invalid_module_id(self, clear_quiz_cache):
        """Test quiz generation with invalid module ID."""
        response = client.post(
            "/api/quiz/generate/nonexistent_module",
            json={"mode": "untimed"}
        )
        
        assert response.status_code == 404
        data = response.json()
        assert "roadmap" in data["detail"].lower() or "not found" in data["detail"].lower()
    
    def test_generate_quiz_no_roadmap(self, clear_quiz_cache, cache_service):
        """Test quiz generation when no roadmap exists."""
        cache_service.clear_cache('roadmap')
        
        response = client.post(
            "/api/quiz/generate/mod_test",
            json={"mode": "untimed"}
        )
        
        assert response.status_code == 404
        data = response.json()
        assert "roadmap" in data["detail"].lower()


class TestQuizSubmission:
    """Test quiz submission endpoint."""
    
    @patch('app.routers.quiz.quiz_service.generate_quiz')
    @patch('app.routers.quiz.quiz_service.evaluate_quiz')
    @patch('app.routers.quiz.quiz_service.store_quiz_data')
    def test_submit_quiz_success(
        self,
        mock_store_quiz_data,
        mock_evaluate_quiz,
        mock_generate_quiz,
        setup_roadmap_and_content,
        clear_quiz_cache,
        sample_quiz_questions,
        cache_service
    ):
        """Test successful quiz submission."""
        module_id = setup_roadmap_and_content
        
        # Generate a quiz first
        questions = [QuizQuestion(**q) for q in sample_quiz_questions]
        quiz = Quiz(
            quiz_id="quiz_submit_test",
            module_id=module_id,
            questions=questions,
            mode=LearningMode.UNTIMED,
            time_limit_seconds=None,
            created_at=datetime.now()
        )
        mock_generate_quiz.return_value = quiz
        
        # Generate quiz via API
        gen_response = client.post(
            f"/api/quiz/generate/{module_id}",
            json={"mode": "untimed"}
        )
        assert gen_response.status_code == 200
        quiz_id = gen_response.json()["quiz_id"]
        
        # Mock evaluation result
        from app.models import QuizResult
        mock_result = QuizResult(
            quiz_id=quiz_id,
            module_id=module_id,
            score=8,
            accuracy=80.0,
            time_taken_seconds=300,
            time_limit_exceeded=False,
            correct_answers=8,
            incorrect_answers=2,
            submitted_at=datetime.now()
        )
        mock_evaluate_quiz.return_value = mock_result
        
        # Submit quiz
        answers = {i: "A" for i in range(1, 11)}
        response = client.post(
            f"/api/quiz/submit/{module_id}",
            json={
                "quiz_id": quiz_id,
                "answers": answers,
                "time_taken_seconds": 300
            }
        )
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert data["quiz_id"] == quiz_id
        assert data["score"] == 8
        assert data["accuracy"] == 80.0
        assert data["time_taken_seconds"] == 300
        assert data["time_limit_exceeded"] is False
        assert len(data["detailed_results"]) == 10
        
        # Verify evaluation and storage were called
        mock_evaluate_quiz.assert_called_once()
        mock_store_quiz_data.assert_called_once()
    
    @patch('app.routers.quiz.quiz_service.generate_quiz')
    @patch('app.routers.quiz.quiz_service.evaluate_quiz')
    @patch('app.routers.quiz.quiz_service.store_quiz_data')
    def test_submit_quiz_time_limit_exceeded(
        self,
        mock_store_quiz_data,
        mock_evaluate_quiz,
        mock_generate_quiz,
        setup_roadmap_and_content,
        clear_quiz_cache,
        sample_quiz_questions
    ):
        """Test quiz submission with time limit exceeded."""
        module_id = setup_roadmap_and_content
        
        # Generate a timed quiz
        questions = [QuizQuestion(**q) for q in sample_quiz_questions]
        quiz = Quiz(
            quiz_id="quiz_timed_test",
            module_id=module_id,
            questions=questions,
            mode=LearningMode.TIMED,
            time_limit_seconds=600,
            created_at=datetime.now()
        )
        mock_generate_quiz.return_value = quiz
        
        gen_response = client.post(
            f"/api/quiz/generate/{module_id}",
            json={"mode": "timed", "time_limit_seconds": 600}
        )
        assert gen_response.status_code == 200
        quiz_id = gen_response.json()["quiz_id"]
        
        # Mock evaluation with time limit exceeded
        from app.models import QuizResult
        mock_result = QuizResult(
            quiz_id=quiz_id,
            module_id=module_id,
            score=7,
            accuracy=70.0,
            time_taken_seconds=700,  # Exceeded 600s limit
            time_limit_exceeded=True,
            correct_answers=7,
            incorrect_answers=3,
            submitted_at=datetime.now()
        )
        mock_evaluate_quiz.return_value = mock_result
        
        # Submit quiz
        answers = {i: "A" for i in range(1, 11)}
        response = client.post(
            f"/api/quiz/submit/{module_id}",
            json={
                "quiz_id": quiz_id,
                "answers": answers,
                "time_taken_seconds": 700
            }
        )
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        
        assert data["time_limit_exceeded"] is True
        assert data["time_taken_seconds"] == 700
    
    def test_submit_quiz_not_found(
        self,
        setup_roadmap_and_content,
        clear_quiz_cache
    ):
        """Test quiz submission with non-existent quiz ID."""
        module_id = setup_roadmap_and_content
        
        response = client.post(
            f"/api/quiz/submit/{module_id}",
            json={
                "quiz_id": "nonexistent_quiz",
                "answers": {1: "A"},
                "time_taken_seconds": 100
            }
        )
        
        assert response.status_code == 404
        data = response.json()
        assert "quiz" in data["detail"].lower() and "found" in data["detail"].lower()


class TestQuizHistory:
    """Test quiz history endpoint."""
    
    @patch('app.routers.quiz.quiz_service.generate_quiz')
    @patch('app.routers.quiz.quiz_service.evaluate_quiz')
    @patch('app.routers.quiz.quiz_service.store_quiz_data')
    def test_get_quiz_history_success(
        self,
        mock_store_quiz_data,
        mock_evaluate_quiz,
        mock_generate_quiz,
        setup_roadmap_and_content,
        clear_quiz_cache,
        sample_quiz_questions
    ):
        """Test successful quiz history retrieval."""
        module_id = setup_roadmap_and_content
        
        # Generate and submit 2 quizzes
        for i in range(2):
            questions = [QuizQuestion(**q) for q in sample_quiz_questions]
            quiz = Quiz(
                quiz_id=f"quiz_history_{i}",
                module_id=module_id,
                questions=questions,
                mode=LearningMode.UNTIMED,
                time_limit_seconds=None,
                created_at=datetime.now()
            )
            mock_generate_quiz.return_value = quiz
            
            # Generate quiz
            gen_response = client.post(
                f"/api/quiz/generate/{module_id}",
                json={"mode": "untimed"}
            )
            quiz_id = gen_response.json()["quiz_id"]
            
            # Mock evaluation
            from app.models import QuizResult
            mock_result = QuizResult(
                quiz_id=quiz_id,
                module_id=module_id,
                score=8,
                accuracy=80.0,
                time_taken_seconds=300,
                time_limit_exceeded=False,
                correct_answers=8,
                incorrect_answers=2,
                submitted_at=datetime.now()
            )
            mock_evaluate_quiz.return_value = mock_result
            
            # Submit quiz
            client.post(
                f"/api/quiz/submit/{module_id}",
                json={
                    "quiz_id": quiz_id,
                    "answers": {j: "A" for j in range(1, 11)},
                    "time_taken_seconds": 300
                }
            )
        
        # Get quiz history
        response = client.get(f"/api/quiz/history/{module_id}")
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert data["module_id"] == module_id
        assert data["quiz_count"] == 2
        assert len(data["quizzes"]) == 2
    
    def test_get_quiz_history_not_found(
        self,
        setup_roadmap_and_content,
        clear_quiz_cache
    ):
        """Test quiz history retrieval when no quizzes exist."""
        module_id = setup_roadmap_and_content
        
        response = client.get(f"/api/quiz/history/{module_id}")
        
        assert response.status_code == 404
        data = response.json()
        assert "quiz" in data["detail"].lower() and "found" in data["detail"].lower()
    
    def test_get_quiz_history_invalid_module(self, clear_quiz_cache):
        """Test quiz history retrieval with invalid module ID."""
        response = client.get("/api/quiz/history/nonexistent_module")
        
        assert response.status_code == 404
        data = response.json()
        assert "roadmap" in data["detail"].lower() or "found" in data["detail"].lower()


class TestQuizMetrics:
    """Test quiz metrics endpoint."""
    
    @patch('app.routers.quiz.quiz_service.generate_quiz')
    @patch('app.routers.quiz.quiz_service.evaluate_quiz')
    @patch('app.routers.quiz.quiz_service.store_quiz_data')
    def test_get_quiz_metrics_success(
        self,
        mock_store_quiz_data,
        mock_evaluate_quiz,
        mock_generate_quiz,
        setup_roadmap_and_content,
        clear_quiz_cache,
        sample_quiz_questions,
        cache_service
    ):
        """Test successful quiz metrics retrieval."""
        module_id = setup_roadmap_and_content
        
        # Generate and submit a quiz
        questions = [QuizQuestion(**q) for q in sample_quiz_questions]
        quiz = Quiz(
            quiz_id="quiz_metrics_test",
            module_id=module_id,
            questions=questions,
            mode=LearningMode.UNTIMED,
            time_limit_seconds=None,
            created_at=datetime.now()
        )
        mock_generate_quiz.return_value = quiz
        
        gen_response = client.post(
            f"/api/quiz/generate/{module_id}",
            json={"mode": "untimed"}
        )
        quiz_id = gen_response.json()["quiz_id"]
        
        # Mock evaluation
        from app.models import QuizResult
        mock_result = QuizResult(
            quiz_id=quiz_id,
            module_id=module_id,
            score=9,
            accuracy=90.0,
            time_taken_seconds=250,
            time_limit_exceeded=False,
            correct_answers=9,
            incorrect_answers=1,
            submitted_at=datetime.now()
        )
        mock_evaluate_quiz.return_value = mock_result
        
        # Submit quiz
        client.post(
            f"/api/quiz/submit/{module_id}",
            json={
                "quiz_id": quiz_id,
                "answers": {i: "A" for i in range(1, 11)},
                "time_taken_seconds": 250
            }
        )
        
        # Manually cache metrics for testing
        metrics = {
            "module_id": module_id,
            "total_quizzes": 1,
            "average_score": 9.0,
            "best_score": 9,
            "worst_score": 9,
            "average_accuracy": 90.0
        }
        cache_service.cache_quiz_metrics(module_id, metrics)
        
        # Get quiz metrics
        response = client.get(f"/api/quiz/metrics/{module_id}")
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert data["module_id"] == module_id
        assert data["total_quizzes"] == 1
        assert data["average_score"] == 9.0
        assert data["best_score"] == 9
        assert data["worst_score"] == 9
        assert data["average_accuracy"] == 90.0
    
    def test_get_quiz_metrics_not_found(
        self,
        setup_roadmap_and_content,
        clear_quiz_cache
    ):
        """Test quiz metrics retrieval when no metrics exist."""
        module_id = setup_roadmap_and_content
        
        response = client.get(f"/api/quiz/metrics/{module_id}")
        
        assert response.status_code == 404
        data = response.json()
        assert "metrics" in data["detail"].lower() and "found" in data["detail"].lower()


class TestQuizPruning:
    """Test quiz Q&A pruning behavior."""
    
    @patch('app.routers.quiz.quiz_service.generate_quiz')
    @patch('app.routers.quiz.quiz_service.evaluate_quiz')
    def test_quiz_pruning_keeps_last_two(
        self,
        mock_evaluate_quiz,
        mock_generate_quiz,
        setup_roadmap_and_content,
        clear_quiz_cache,
        sample_quiz_questions,
        cache_service
    ):
        """Test that only last 2 quizzes are retained after pruning."""
        module_id = setup_roadmap_and_content
        
        # Generate and submit 3 quizzes
        quiz_ids = []
        for i in range(3):
            questions = [QuizQuestion(**q) for q in sample_quiz_questions]
            quiz = Quiz(
                quiz_id=f"quiz_prune_{i}",
                module_id=module_id,
                questions=questions,
                mode=LearningMode.UNTIMED,
                time_limit_seconds=None,
                created_at=datetime.now()
            )
            mock_generate_quiz.return_value = quiz
            
            # Generate quiz
            gen_response = client.post(
                f"/api/quiz/generate/{module_id}",
                json={"mode": "untimed"}
            )
            quiz_id = gen_response.json()["quiz_id"]
            quiz_ids.append(quiz_id)
            
            # Mock evaluation
            from app.models import QuizResult
            mock_result = QuizResult(
                quiz_id=quiz_id,
                module_id=module_id,
                score=8,
                accuracy=80.0,
                time_taken_seconds=300,
                time_limit_exceeded=False,
                correct_answers=8,
                incorrect_answers=2,
                submitted_at=datetime.now()
            )
            mock_evaluate_quiz.return_value = mock_result
            
            # Submit quiz (store_quiz_data is NOT mocked, so pruning will happen)
            client.post(
                f"/api/quiz/submit/{module_id}",
                json={
                    "quiz_id": quiz_id,
                    "answers": {j: "A" for j in range(1, 11)},
                    "time_taken_seconds": 300
                }
            )
        
        # Get quiz history - should only have last 2
        response = client.get(f"/api/quiz/history/{module_id}")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify only 2 quizzes retained
        assert data["quiz_count"] == 2
        
        # Verify the last 2 quiz IDs are present
        returned_quiz_ids = [q["quiz_id"] for q in data["quizzes"]]
        assert quiz_ids[1] in returned_quiz_ids
        assert quiz_ids[2] in returned_quiz_ids
        assert quiz_ids[0] not in returned_quiz_ids
