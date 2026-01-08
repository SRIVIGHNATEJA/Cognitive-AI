"""
Unit tests for Quiz Service.

Tests quiz generation, evaluation, metrics tracking, and Q&A pruning.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from app.services.quiz_service import QuizService
from app.services.cache_service import CacheService
from app.models import (
    Quiz,
    QuizQuestion,
    QuizResult,
    QuizMetrics,
    LearningMode,
    Module
)
import tempfile
import shutil


@pytest.fixture
def temp_cache_dir():
    """Create a temporary cache directory for testing."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def cache_service(temp_cache_dir):
    """Provide a cache service with temporary directory."""
    return CacheService(cache_dir=temp_cache_dir)


@pytest.fixture
def quiz_service(cache_service):
    """Provide a quiz service instance for testing."""
    return QuizService(cache_service=cache_service)


@pytest.fixture
def sample_module():
    """Provide a sample module for testing."""
    return Module(
        module_id="mod_test123",
        topic_name="Python Basics",
        estimated_hours=5.0,
        prerequisites=[],
        order=1
    )


@pytest.fixture
def sample_quiz_questions():
    """Provide sample quiz questions for testing."""
    questions = []
    for i in range(1, 11):
        question = QuizQuestion(
            question_number=i,
            question_text=f"What is the answer to question {i}?",
            options=[f"Option A{i}", f"Option B{i}", f"Option C{i}", f"Option D{i}"],
            correct_answer=f"Option B{i}",
            explanation=f"Explanation for question {i}"
        )
        questions.append(question)
    return questions


class TestQuizIDGeneration:
    """Test quiz ID generation with deterministic hashing."""
    
    def test_generate_stable_quiz_id(self, quiz_service):
        """Test that quiz ID generation is deterministic."""
        module_id = "mod_test123"
        created_at = datetime(2024, 1, 7, 10, 30, 0, 123456)
        
        # Generate ID multiple times with same inputs
        id1 = quiz_service.generate_stable_quiz_id(module_id, created_at)
        id2 = quiz_service.generate_stable_quiz_id(module_id, created_at)
        id3 = quiz_service.generate_stable_quiz_id(module_id, created_at)
        
        # All IDs should be identical
        assert id1 == id2 == id3
        
        # ID should have correct format
        assert id1.startswith("quiz_")
        assert len(id1) == 17  # "quiz_" + 12 hex characters
    
    def test_different_timestamps_produce_different_ids(self, quiz_service):
        """Test that different timestamps produce different quiz IDs."""
        module_id = "mod_test123"
        
        dt1 = datetime(2024, 1, 7, 10, 30, 0, 123456)
        dt2 = datetime(2024, 1, 7, 10, 30, 0, 123457)  # 1 microsecond difference
        
        id1 = quiz_service.generate_stable_quiz_id(module_id, dt1)
        id2 = quiz_service.generate_stable_quiz_id(module_id, dt2)
        
        # IDs should be different
        assert id1 != id2
    
    def test_different_modules_produce_different_ids(self, quiz_service):
        """Test that different modules produce different quiz IDs."""
        created_at = datetime(2024, 1, 7, 10, 30, 0, 123456)
        
        id1 = quiz_service.generate_stable_quiz_id("mod_test123", created_at)
        id2 = quiz_service.generate_stable_quiz_id("mod_test456", created_at)
        
        # IDs should be different
        assert id1 != id2


class TestQuizGeneration:
    """Test quiz generation functionality."""
    
    @patch('app.services.quiz_service.LLMService')
    def test_generate_quiz_untimed(self, mock_llm_class, quiz_service, sample_module):
        """Test generating an untimed quiz."""
        # Mock LLM service
        mock_llm = Mock()
        mock_llm.generate_quiz_llm.return_value = [
            {
                "question_number": i,
                "question_text": f"Question {i}?",
                "options": ["A", "B", "C", "D"],
                "correct_answer": "B",
                "explanation": f"Explanation {i}"
            }
            for i in range(1, 11)
        ]
        quiz_service.llm_service = mock_llm
        
        # Generate quiz
        quiz = quiz_service.generate_quiz(
            module=sample_module,
            content="Test content",
            mode=LearningMode.UNTIMED
        )
        
        # Verify quiz structure
        assert quiz.module_id == sample_module.module_id
        assert quiz.mode == LearningMode.UNTIMED
        assert quiz.time_limit_seconds is None
        assert len(quiz.questions) == 10
        assert quiz.quiz_id.startswith("quiz_")
    
    @patch('app.services.quiz_service.LLMService')
    def test_generate_quiz_timed(self, mock_llm_class, quiz_service, sample_module):
        """Test generating a timed quiz."""
        # Mock LLM service
        mock_llm = Mock()
        mock_llm.generate_quiz_llm.return_value = [
            {
                "question_number": i,
                "question_text": f"Question {i}?",
                "options": ["A", "B", "C", "D"],
                "correct_answer": "B",
                "explanation": f"Explanation {i}"
            }
            for i in range(1, 11)
        ]
        quiz_service.llm_service = mock_llm
        
        # Generate timed quiz
        quiz = quiz_service.generate_quiz(
            module=sample_module,
            content="Test content",
            mode=LearningMode.TIMED,
            time_limit_seconds=600
        )
        
        # Verify quiz structure
        assert quiz.mode == LearningMode.TIMED
        assert quiz.time_limit_seconds == 600
        assert len(quiz.questions) == 10
    
    def test_generate_quiz_timed_without_time_limit_raises_error(self, quiz_service, sample_module):
        """Test that timed quiz without time limit raises error."""
        with pytest.raises(ValueError, match="time_limit_seconds is required"):
            quiz_service.generate_quiz(
                module=sample_module,
                content="Test content",
                mode=LearningMode.TIMED,
                time_limit_seconds=None
            )
    
    @patch('app.services.quiz_service.LLMService')
    def test_generate_quiz_invalid_question_count_raises_error(
        self,
        mock_llm_class,
        quiz_service,
        sample_module
    ):
        """Test that invalid question count raises error."""
        # Mock LLM service to return wrong number of questions
        mock_llm = Mock()
        mock_llm.generate_quiz_llm.return_value = [
            {
                "question_number": 1,
                "question_text": "Question 1?",
                "options": ["A", "B", "C", "D"],
                "correct_answer": "B",
                "explanation": "Explanation"
            }
        ]  # Only 1 question instead of 10
        quiz_service.llm_service = mock_llm
        
        with pytest.raises(ValueError, match="invalid number of questions"):
            quiz_service.generate_quiz(
                module=sample_module,
                content="Test content",
                mode=LearningMode.UNTIMED
            )


class TestQuizEvaluation:
    """Test quiz evaluation functionality."""
    
    def test_evaluate_quiz_all_correct(self, quiz_service, sample_quiz_questions):
        """Test evaluating a quiz with all correct answers."""
        # Create quiz
        quiz = Quiz(
            quiz_id="quiz_test123",
            module_id="mod_test123",
            questions=sample_quiz_questions,
            mode=LearningMode.UNTIMED,
            time_limit_seconds=None,
            created_at=datetime.now()
        )
        
        # All correct answers
        answers = {i: f"Option B{i}" for i in range(1, 11)}
        
        # Evaluate
        result = quiz_service.evaluate_quiz(quiz, answers, time_taken_seconds=300)
        
        # Verify results
        assert result.score == 10
        assert result.accuracy == 100.0
        assert result.correct_answers == 10
        assert result.incorrect_answers == 0
        assert result.time_taken_seconds == 300
        assert result.time_limit_exceeded is False
    
    def test_evaluate_quiz_partial_correct(self, quiz_service, sample_quiz_questions):
        """Test evaluating a quiz with some correct answers."""
        # Create quiz
        quiz = Quiz(
            quiz_id="quiz_test123",
            module_id="mod_test123",
            questions=sample_quiz_questions,
            mode=LearningMode.UNTIMED,
            time_limit_seconds=None,
            created_at=datetime.now()
        )
        
        # 7 correct, 3 incorrect
        answers = {}
        for i in range(1, 11):
            if i <= 7:
                answers[i] = f"Option B{i}"  # Correct
            else:
                answers[i] = f"Option A{i}"  # Incorrect
        
        # Evaluate
        result = quiz_service.evaluate_quiz(quiz, answers, time_taken_seconds=450)
        
        # Verify results
        assert result.score == 7
        assert result.accuracy == 70.0
        assert result.correct_answers == 7
        assert result.incorrect_answers == 3
    
    def test_evaluate_quiz_time_limit_not_exceeded(self, quiz_service, sample_quiz_questions):
        """Test that time limit not exceeded is recorded correctly."""
        # Create timed quiz
        quiz = Quiz(
            quiz_id="quiz_test123",
            module_id="mod_test123",
            questions=sample_quiz_questions,
            mode=LearningMode.TIMED,
            time_limit_seconds=600,
            created_at=datetime.now()
        )
        
        answers = {i: f"Option B{i}" for i in range(1, 11)}
        
        # Evaluate with time under limit
        result = quiz_service.evaluate_quiz(quiz, answers, time_taken_seconds=500)
        
        # Verify time limit not exceeded
        assert result.time_limit_exceeded is False
        assert result.score == 10  # Score not affected by time
    
    def test_evaluate_quiz_time_limit_exceeded(self, quiz_service, sample_quiz_questions):
        """Test that time limit exceeded is recorded correctly."""
        # Create timed quiz
        quiz = Quiz(
            quiz_id="quiz_test123",
            module_id="mod_test123",
            questions=sample_quiz_questions,
            mode=LearningMode.TIMED,
            time_limit_seconds=600,
            created_at=datetime.now()
        )
        
        answers = {i: f"Option B{i}" for i in range(1, 11)}
        
        # Evaluate with time over limit
        result = quiz_service.evaluate_quiz(quiz, answers, time_taken_seconds=700)
        
        # Verify time limit exceeded but score still calculated
        assert result.time_limit_exceeded is True
        assert result.score == 10  # Score not affected by time (backend accepts all)
    
    def test_evaluate_quiz_empty_answers_raises_error(self, quiz_service, sample_quiz_questions):
        """Test that empty answers raise error."""
        quiz = Quiz(
            quiz_id="quiz_test123",
            module_id="mod_test123",
            questions=sample_quiz_questions,
            mode=LearningMode.UNTIMED,
            time_limit_seconds=None,
            created_at=datetime.now()
        )
        
        with pytest.raises(ValueError, match="No answers provided"):
            quiz_service.evaluate_quiz(quiz, {}, time_taken_seconds=300)


class TestQuizMetrics:
    """Test quiz metrics tracking."""
    
    def test_update_quiz_metrics_first_quiz(self, quiz_service, cache_service):
        """Test updating metrics for the first quiz."""
        module_id = "mod_test123"
        
        result = QuizResult(
            quiz_id="quiz_001",
            module_id=module_id,
            score=8,
            accuracy=80.0,
            time_taken_seconds=400,
            time_limit_exceeded=False,
            correct_answers=8,
            incorrect_answers=2,
            submitted_at=datetime.now()
        )
        
        # Update metrics
        quiz_service._update_quiz_metrics(module_id, result)
        
        # Retrieve metrics
        metrics = cache_service.get_quiz_metrics(module_id)
        
        # Verify metrics
        assert metrics is not None
        assert metrics["total_quizzes"] == 1
        assert metrics["average_score"] == 8.0
        assert metrics["best_score"] == 8
        assert metrics["worst_score"] == 8
        assert metrics["average_accuracy"] == 80.0
    
    def test_update_quiz_metrics_multiple_quizzes(self, quiz_service, cache_service):
        """Test updating metrics for multiple quizzes."""
        module_id = "mod_test123"
        
        # First quiz
        result1 = QuizResult(
            quiz_id="quiz_001",
            module_id=module_id,
            score=8,
            accuracy=80.0,
            time_taken_seconds=400,
            time_limit_exceeded=False,
            correct_answers=8,
            incorrect_answers=2,
            submitted_at=datetime.now()
        )
        quiz_service._update_quiz_metrics(module_id, result1)
        
        # Second quiz
        result2 = QuizResult(
            quiz_id="quiz_002",
            module_id=module_id,
            score=6,
            accuracy=60.0,
            time_taken_seconds=500,
            time_limit_exceeded=False,
            correct_answers=6,
            incorrect_answers=4,
            submitted_at=datetime.now()
        )
        quiz_service._update_quiz_metrics(module_id, result2)
        
        # Retrieve metrics
        metrics = cache_service.get_quiz_metrics(module_id)
        
        # Verify aggregated metrics
        assert metrics["total_quizzes"] == 2
        assert metrics["average_score"] == 7.0  # (8 + 6) / 2
        assert metrics["best_score"] == 8
        assert metrics["worst_score"] == 6
        assert metrics["average_accuracy"] == 70.0  # (80 + 60) / 2


class TestQuizQAPruning:
    """Test quiz Q&A pruning functionality."""
    
    def test_prune_quiz_qa_keeps_last_two(self, quiz_service, cache_service):
        """Test that pruning keeps only the last 2 quizzes."""
        module_id = "mod_test123"
        
        # Add 5 quizzes
        for i in range(1, 6):
            quiz_data = {
                "quiz_id": f"quiz_00{i}",
                "module_id": module_id,
                "questions": [],
                "created_at": datetime.now().isoformat()
            }
            cache_service.cache_quiz_qa(module_id, quiz_data)
        
        # Verify 5 quizzes exist
        history_before = cache_service.get_quiz_history(module_id)
        assert len(history_before) == 5
        
        # Prune
        quiz_service.prune_old_quiz_qa(module_id)
        
        # Verify only last 2 remain
        history_after = cache_service.get_quiz_history(module_id)
        assert len(history_after) == 2
        assert history_after[0]["quiz_id"] == "quiz_004"
        assert history_after[1]["quiz_id"] == "quiz_005"
    
    def test_prune_quiz_qa_no_pruning_needed(self, quiz_service, cache_service):
        """Test that pruning does nothing when 2 or fewer quizzes exist."""
        module_id = "mod_test123"
        
        # Add only 2 quizzes
        for i in range(1, 3):
            quiz_data = {
                "quiz_id": f"quiz_00{i}",
                "module_id": module_id,
                "questions": [],
                "created_at": datetime.now().isoformat()
            }
            cache_service.cache_quiz_qa(module_id, quiz_data)
        
        # Prune
        quiz_service.prune_old_quiz_qa(module_id)
        
        # Verify both quizzes still exist
        history = cache_service.get_quiz_history(module_id)
        assert len(history) == 2


class TestStoreQuizData:
    """Test storing quiz data with automatic pruning."""
    
    @patch('app.services.quiz_service.LLMService')
    def test_store_quiz_data_triggers_pruning(
        self,
        mock_llm_class,
        quiz_service,
        cache_service,
        sample_quiz_questions
    ):
        """Test that storing quiz data triggers automatic pruning."""
        module_id = "mod_test123"
        
        # Create and store 3 quizzes
        for i in range(1, 4):
            quiz = Quiz(
                quiz_id=f"quiz_00{i}",
                module_id=module_id,
                questions=sample_quiz_questions,
                mode=LearningMode.UNTIMED,
                time_limit_seconds=None,
                created_at=datetime.now()
            )
            
            result = QuizResult(
                quiz_id=quiz.quiz_id,
                module_id=module_id,
                score=8,
                accuracy=80.0,
                time_taken_seconds=400,
                time_limit_exceeded=False,
                correct_answers=8,
                incorrect_answers=2,
                submitted_at=datetime.now()
            )
            
            quiz_service.store_quiz_data(quiz, result)
        
        # Verify only last 2 Q&As remain
        history = cache_service.get_quiz_history(module_id)
        assert len(history) == 2
        
        # Verify all 3 metrics are retained
        metrics = cache_service.get_quiz_metrics(module_id)
        assert metrics["total_quizzes"] == 3
