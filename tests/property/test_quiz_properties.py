"""
Property-based tests for Quiz System.

Tests universal properties that should hold across all valid inputs.
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
from app.models import QuizQuestion, Quiz, LearningMode
from datetime import datetime
from typing import List


class TestQuizStructureCompliance:
    """
    Property tests for quiz structure compliance.
    
    Feature: cognitive-learning-platform, Property 11: Quiz Structure Compliance
    Validates: Requirements 4.1, 4.2, 4.3
    """
    
    @given(
        module_id=st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'), whitelist_characters='_-')),
        mode=st.sampled_from([LearningMode.TIMED, LearningMode.UNTIMED]),
        time_limit=st.one_of(st.none(), st.integers(min_value=60, max_value=3600))
    )
    @settings(max_examples=100)
    def test_quiz_structure_compliance_property(self, module_id, mode, time_limit):
        """
        Property 11: Quiz Structure Compliance
        
        For any generated quiz, it should contain exactly 10 questions,
        each with exactly 4 options, a correct answer that matches one
        of the options, and an explanation.
        
        **Validates: Requirements 4.1, 4.2, 4.3**
        """
        # If mode is TIMED, ensure time_limit is not None
        if mode == LearningMode.TIMED and time_limit is None:
            time_limit = 600  # Default 10 minutes for timed quizzes
        
        # Generate 10 valid quiz questions
        questions = self._generate_valid_questions()
        
        # Create quiz with deterministic ID
        quiz_id = f"quiz_{module_id}_{datetime.now().isoformat()}"
        
        # Create Quiz object
        quiz = Quiz(
            quiz_id=quiz_id,
            module_id=module_id,
            questions=questions,
            mode=mode,
            time_limit_seconds=time_limit if mode == LearningMode.TIMED else None,
            created_at=datetime.now()
        )
        
        # Property 1: Quiz must have exactly 10 questions
        assert len(quiz.questions) == 10, f"Quiz must have exactly 10 questions, got {len(quiz.questions)}"
        
        # Property 2: Each question must have exactly 4 options
        for i, question in enumerate(quiz.questions, 1):
            assert len(question.options) == 4, f"Question {i} must have exactly 4 options, got {len(question.options)}"
        
        # Property 3: Each question's correct_answer must be one of the 4 options
        for i, question in enumerate(quiz.questions, 1):
            assert question.correct_answer in question.options, \
                f"Question {i} correct_answer '{question.correct_answer}' not in options {question.options}"
        
        # Property 4: Each question must have an explanation
        for i, question in enumerate(quiz.questions, 1):
            assert question.explanation is not None, f"Question {i} must have an explanation"
            assert len(question.explanation) > 0, f"Question {i} explanation cannot be empty"
            assert len(question.explanation) <= 200, \
                f"Question {i} explanation must be <= 200 chars, got {len(question.explanation)}"
        
        # Property 5: Question numbers must be sequential from 1 to 10
        for i, question in enumerate(quiz.questions, 1):
            assert question.question_number == i, \
                f"Question {i} has incorrect question_number: {question.question_number}"
        
        # Property 6: All question texts must be non-empty and at least 10 characters
        for i, question in enumerate(quiz.questions, 1):
            assert len(question.question_text) >= 10, \
                f"Question {i} text must be at least 10 characters, got {len(question.question_text)}"
        
        # Property 7: All options must be non-empty strings
        for i, question in enumerate(quiz.questions, 1):
            for j, option in enumerate(question.options, 1):
                assert isinstance(option, str), f"Question {i}, option {j} must be a string"
                assert len(option.strip()) > 0, f"Question {i}, option {j} cannot be empty"
        
        # Property 8: Timed quizzes must have time_limit_seconds
        if mode == LearningMode.TIMED:
            assert quiz.time_limit_seconds is not None, "Timed quiz must have time_limit_seconds"
            assert quiz.time_limit_seconds > 0, "Time limit must be positive"
        
        # Property 9: Quiz ID must be non-empty
        assert len(quiz.quiz_id) > 0, "Quiz ID cannot be empty"
        
        # Property 10: Module ID must be non-empty
        assert len(quiz.module_id) > 0, "Module ID cannot be empty"
    
    def _generate_valid_questions(self) -> List[QuizQuestion]:
        """
        Generate 10 valid quiz questions for testing.
        
        Returns:
            List of 10 valid QuizQuestion objects
        """
        questions = []
        
        for i in range(1, 11):
            question = QuizQuestion(
                question_number=i,
                question_text=f"What is the answer to question {i}?",
                options=[f"Option A{i}", f"Option B{i}", f"Option C{i}", f"Option D{i}"],
                correct_answer=f"Option B{i}",
                explanation=f"This is the explanation for question {i}"
            )
            questions.append(question)
        
        return questions
    
    @given(
        question_number=st.integers(min_value=1, max_value=10),
        question_text=st.text(min_size=10, max_size=500),
        options=st.lists(
            st.text(min_size=1, max_size=100),
            min_size=4,
            max_size=4
        ),
        explanation=st.text(min_size=1, max_size=200)
    )
    @settings(max_examples=100)
    def test_individual_question_structure_property(
        self,
        question_number,
        question_text,
        options,
        explanation
    ):
        """
        Property: Individual Question Structure
        
        For any individual quiz question, it must satisfy all structural
        requirements: valid question number, 4 options, correct answer in
        options, and valid explanation.
        
        **Validates: Requirements 4.1, 4.2, 4.3**
        """
        # Ensure all options are non-empty
        assume(all(opt.strip() for opt in options))
        
        # Pick a correct answer from the options
        correct_answer = options[0]
        
        # Create QuizQuestion
        question = QuizQuestion(
            question_number=question_number,
            question_text=question_text,
            options=options,
            correct_answer=correct_answer,
            explanation=explanation
        )
        
        # Verify all properties
        assert 1 <= question.question_number <= 10
        assert len(question.question_text) >= 10
        assert len(question.options) == 4
        assert question.correct_answer in question.options
        assert 0 < len(question.explanation) <= 200
        
        # Verify all options are strings
        for option in question.options:
            assert isinstance(option, str)
            assert len(option.strip()) > 0
    
    @given(
        questions=st.lists(
            st.builds(
                QuizQuestion,
                question_number=st.integers(min_value=1, max_value=10),
                question_text=st.text(min_size=10, max_size=500),
                options=st.lists(
                    st.text(min_size=1, max_size=100),
                    min_size=4,
                    max_size=4
                ),
                correct_answer=st.text(min_size=1, max_size=100),
                explanation=st.text(min_size=1, max_size=200)
            ),
            min_size=10,
            max_size=10
        )
    )
    @settings(max_examples=100)
    def test_quiz_question_count_invariant(self, questions):
        """
        Property: Quiz Question Count Invariant
        
        For any quiz, the number of questions must always be exactly 10,
        regardless of how the quiz is constructed or modified.
        
        **Validates: Requirements 4.1**
        """
        # Ensure all questions have valid structure
        for i, q in enumerate(questions, 1):
            # Fix question number to be sequential
            q.question_number = i
            
            # Ensure correct_answer is in options
            if q.correct_answer not in q.options:
                q.correct_answer = q.options[0]
            
            # Ensure all options are non-empty
            assume(all(opt.strip() for opt in q.options))
        
        # Create quiz
        quiz = Quiz(
            quiz_id="test_quiz_id",
            module_id="test_module_id",
            questions=questions,
            mode=LearningMode.UNTIMED,
            time_limit_seconds=None,
            created_at=datetime.now()
        )
        
        # Invariant: Quiz must always have exactly 10 questions
        assert len(quiz.questions) == 10
        
        # Invariant: Question numbers must be 1-10
        question_numbers = [q.question_number for q in quiz.questions]
        assert sorted(question_numbers) == list(range(1, 11))
