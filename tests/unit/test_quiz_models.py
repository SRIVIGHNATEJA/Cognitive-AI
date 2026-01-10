"""
Unit tests for Quiz-related Pydantic models.

Tests the new quiz evaluation models introduced in Phase 1:
- QuizQuestion (with optional correct_answer/explanation)
- QuizSubmission
- QuestionResult
- QuizEvaluation
"""

import pytest
from datetime import datetime
from app.models import (
    QuizQuestion,
    Quiz,
    QuizSubmission,
    QuestionResult,
    QuizEvaluation,
    LearningMode
)


class TestQuizQuestion:
    """Test QuizQuestion model with backward compatibility."""
    
    def test_quiz_question_without_answers(self):
        """Test creating QuizQuestion without correct_answer and explanation (new format)."""
        question = QuizQuestion(
            question_number=1,
            question_text="What is Python?",
            options=["A language", "A snake", "A framework", "A database"]
        )
        
        assert question.question_number == 1
        assert question.question_text == "What is Python?"
        assert len(question.options) == 4
        assert question.correct_answer is None
        assert question.explanation is None
    
    def test_quiz_question_with_answers(self):
        """Test creating QuizQuestion with correct_answer and explanation (old format)."""
        question = QuizQuestion(
            question_number=1,
            question_text="What is Python?",
            options=["A language", "A snake", "A framework", "A database"],
            correct_answer="A language",
            explanation="Python is a programming language"
        )
        
        assert question.question_number == 1
        assert question.correct_answer == "A language"
        assert question.explanation == "Python is a programming language"
    
    def test_quiz_question_validation(self):
        """Test QuizQuestion validation rules."""
        # Must have exactly 4 options
        with pytest.raises(ValueError):
            QuizQuestion(
                question_number=1,
                question_text="What is Python?",
                options=["A", "B"]  # Only 2 options
            )
        
        # Question number must be 1-5
        with pytest.raises(ValueError):
            QuizQuestion(
                question_number=10,
                question_text="What is Python?",
                options=["A", "B", "C", "D"]
            )


class TestQuizSubmission:
    """Test QuizSubmission model."""
    
    def test_quiz_submission_creation(self):
        """Test creating a valid QuizSubmission."""
        submission = QuizSubmission(
            submission_id="sub_123",
            quiz_id="quiz_456",
            module_id="mod_789",
            user_answers={1: "A", 2: "B", 3: "C", 4: "D", 5: "A"},
            time_taken_seconds=300
        )
        
        assert submission.submission_id == "sub_123"
        assert submission.quiz_id == "quiz_456"
        assert submission.module_id == "mod_789"
        assert len(submission.user_answers) == 5
        assert submission.time_taken_seconds == 300
        assert isinstance(submission.submitted_at, datetime)
    
    def test_quiz_submission_validation(self):
        """Test QuizSubmission validation rules."""
        # time_taken_seconds must be >= 0
        with pytest.raises(ValueError):
            QuizSubmission(
                submission_id="sub_123",
                quiz_id="quiz_456",
                module_id="mod_789",
                user_answers={1: "A"},
                time_taken_seconds=-10
            )


class TestQuestionResult:
    """Test QuestionResult model."""
    
    def test_question_result_correct(self):
        """Test QuestionResult for a correct answer."""
        result = QuestionResult(
            question_number=1,
            question_text="What is 2+2?",
            options=["3", "4", "5", "6"],
            user_answer="4",
            correct_answer="4",
            is_correct=True,
            explanation="2+2 equals 4"
        )
        
        assert result.question_number == 1
        assert result.user_answer == "4"
        assert result.correct_answer == "4"
        assert result.is_correct is True
    
    def test_question_result_incorrect(self):
        """Test QuestionResult for an incorrect answer."""
        result = QuestionResult(
            question_number=1,
            question_text="What is 2+2?",
            options=["3", "4", "5", "6"],
            user_answer="5",
            correct_answer="4",
            is_correct=False,
            explanation="2+2 equals 4"
        )
        
        assert result.user_answer == "5"
        assert result.correct_answer == "4"
        assert result.is_correct is False


class TestQuizEvaluation:
    """Test QuizEvaluation model."""
    
    def test_quiz_evaluation_creation(self):
        """Test creating a valid QuizEvaluation."""
        question_results = [
            QuestionResult(
                question_number=i,
                question_text=f"Question {i}",
                options=["A", "B", "C", "D"],
                user_answer="A",
                correct_answer="A",
                is_correct=True,
                explanation="Explanation"
            )
            for i in range(1, 6)
        ]
        
        evaluation = QuizEvaluation(
            evaluation_id="eval_123",
            quiz_id="quiz_456",
            module_id="mod_789",
            score=4,
            accuracy=80.0,
            correct_answers_count=4,
            incorrect_answers_count=1,
            question_results=question_results,
            time_taken_seconds=300,
            time_limit_exceeded=False
        )
        
        assert evaluation.evaluation_id == "eval_123"
        assert evaluation.quiz_id == "quiz_456"
        assert evaluation.score == 4
        assert evaluation.accuracy == 80.0
        assert evaluation.correct_answers_count == 4
        assert evaluation.incorrect_answers_count == 1
        assert len(evaluation.question_results) == 5
        assert evaluation.time_taken_seconds == 300
        assert evaluation.time_limit_exceeded is False
        assert isinstance(evaluation.evaluated_at, datetime)
    
    def test_quiz_evaluation_validation(self):
        """Test QuizEvaluation validation rules."""
        # Score must be 0-5
        with pytest.raises(ValueError):
            QuizEvaluation(
                evaluation_id="eval_123",
                quiz_id="quiz_456",
                module_id="mod_789",
                score=10,  # Invalid
                accuracy=80.0,
                correct_answers_count=4,
                incorrect_answers_count=1,
                question_results=[],
                time_taken_seconds=300
            )
        
        # Accuracy must be 0-100
        with pytest.raises(ValueError):
            QuizEvaluation(
                evaluation_id="eval_123",
                quiz_id="quiz_456",
                module_id="mod_789",
                score=4,
                accuracy=150.0,  # Invalid
                correct_answers_count=4,
                incorrect_answers_count=1,
                question_results=[],
                time_taken_seconds=300
            )


class TestQuizBackwardCompatibility:
    """Test backward compatibility between old and new quiz formats."""
    
    def test_quiz_with_old_format_questions(self):
        """Test Quiz with old-format questions (with correct_answer)."""
        questions = [
            QuizQuestion(
                question_number=i,
                question_text=f"Question {i}",
                options=["A", "B", "C", "D"],
                correct_answer="A",
                explanation="Explanation"
            )
            for i in range(1, 6)
        ]
        
        quiz = Quiz(
            quiz_id="quiz_123",
            module_id="mod_456",
            questions=questions,
            mode=LearningMode.UNTIMED
        )
        
        assert len(quiz.questions) == 5
        assert all(q.correct_answer == "A" for q in quiz.questions)
        assert all(q.explanation == "Explanation" for q in quiz.questions)
    
    def test_quiz_with_new_format_questions(self):
        """Test Quiz with new-format questions (without correct_answer)."""
        questions = [
            QuizQuestion(
                question_number=i,
                question_text=f"Question {i}",
                options=["A", "B", "C", "D"]
            )
            for i in range(1, 6)
        ]
        
        quiz = Quiz(
            quiz_id="quiz_123",
            module_id="mod_456",
            questions=questions,
            mode=LearningMode.UNTIMED
        )
        
        assert len(quiz.questions) == 5
        assert all(q.correct_answer is None for q in quiz.questions)
        assert all(q.explanation is None for q in quiz.questions)
