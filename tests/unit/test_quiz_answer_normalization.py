"""
Unit tests for quiz answer normalization.

Tests the normalization logic that handles various LLM output formats
for correct_answer field in quiz questions.
"""

import pytest
from app.services.llm_service import LLMService


@pytest.fixture
def llm_service():
    """Provide an LLM service instance for testing."""
    return LLMService()


@pytest.fixture
def sample_options():
    """Provide sample quiz options."""
    return [
        "Python is a compiled language",
        "Python is an interpreted language",
        "Python is a markup language",
        "Python is a database language"
    ]


class TestAnswerNormalization:
    """Test correct_answer normalization for various LLM output formats."""
    
    def test_exact_match_no_normalization(self, llm_service, sample_options):
        """Test that exact matches pass through without normalization."""
        correct_answer = "Python is an interpreted language"
        result = llm_service._normalize_correct_answer(correct_answer, sample_options)
        assert result == correct_answer
    
    def test_single_letter_label_uppercase(self, llm_service, sample_options):
        """Test normalization of single letter labels (A-D)."""
        # B should map to index 1 (second option)
        result = llm_service._normalize_correct_answer("B", sample_options)
        assert result == sample_options[1]
    
    def test_single_letter_label_lowercase(self, llm_service, sample_options):
        """Test normalization of lowercase single letter labels."""
        # b should map to index 1 (second option)
        result = llm_service._normalize_correct_answer("b", sample_options)
        assert result == sample_options[1]
    
    def test_label_with_period(self, llm_service, sample_options):
        """Test normalization of labels with period (A., B., etc.)."""
        result = llm_service._normalize_correct_answer("B.", sample_options)
        assert result == sample_options[1]
    
    def test_label_with_parenthesis(self, llm_service, sample_options):
        """Test normalization of labels with parenthesis (A), B), etc.)."""
        result = llm_service._normalize_correct_answer("B)", sample_options)
        assert result == sample_options[1]
    
    def test_label_with_colon(self, llm_service, sample_options):
        """Test normalization of labels with colon (A:, B:, etc.)."""
        result = llm_service._normalize_correct_answer("B:", sample_options)
        assert result == sample_options[1]
    
    def test_option_prefix(self, llm_service, sample_options):
        """Test normalization of 'Option X' format."""
        result = llm_service._normalize_correct_answer("Option B", sample_options)
        assert result == sample_options[1]
    
    def test_option_prefix_with_period(self, llm_service, sample_options):
        """Test normalization of 'Option X.' format."""
        result = llm_service._normalize_correct_answer("Option B.", sample_options)
        assert result == sample_options[1]
    
    def test_label_with_text(self, llm_service, sample_options):
        """Test normalization of labels followed by text (B. Some text)."""
        result = llm_service._normalize_correct_answer("B. Python is interpreted", sample_options)
        assert result == sample_options[1]
    
    def test_whitespace_handling(self, llm_service, sample_options):
        """Test that leading/trailing whitespace is handled."""
        result = llm_service._normalize_correct_answer("  B  ", sample_options)
        assert result == sample_options[1]
    
    def test_case_insensitive_full_match(self, llm_service, sample_options):
        """Test case-insensitive matching of full option text."""
        result = llm_service._normalize_correct_answer(
            "PYTHON IS AN INTERPRETED LANGUAGE",
            sample_options
        )
        assert result == sample_options[1]
    
    def test_all_labels_map_correctly(self, llm_service, sample_options):
        """Test that all labels A-D map to correct indices."""
        assert llm_service._normalize_correct_answer("A", sample_options) == sample_options[0]
        assert llm_service._normalize_correct_answer("B", sample_options) == sample_options[1]
        assert llm_service._normalize_correct_answer("C", sample_options) == sample_options[2]
        assert llm_service._normalize_correct_answer("D", sample_options) == sample_options[3]
    
    def test_invalid_label_raises_error(self, llm_service, sample_options):
        """Test that invalid labels raise ValueError."""
        with pytest.raises(ValueError, match="Could not normalize"):
            llm_service._normalize_correct_answer("E", sample_options)
    
    def test_invalid_text_raises_error(self, llm_service, sample_options):
        """Test that completely unrelated text raises ValueError."""
        with pytest.raises(ValueError, match="Could not normalize"):
            llm_service._normalize_correct_answer("This is not an option", sample_options)
    
    def test_empty_string_raises_error(self, llm_service, sample_options):
        """Test that empty string raises ValueError."""
        with pytest.raises(ValueError, match="Could not normalize"):
            llm_service._normalize_correct_answer("", sample_options)


class TestQuizValidationWithNormalization:
    """Test that quiz validation applies normalization correctly."""
    
    def test_validation_normalizes_label_answers(self, llm_service):
        """Test that validation normalizes label-based answers."""
        quiz_data = {
            "questions": [
                {
                    "question_number": 1,
                    "question_text": "What is Python?",
                    "options": ["Compiled", "Interpreted", "Markup", "Database"],
                    "correct_answer": "B",  # Should be normalized to "Interpreted"
                    "explanation": "Python is an interpreted language"
                },
                {
                    "question_number": 2,
                    "question_text": "What is JavaScript?",
                    "options": ["Compiled", "Interpreted", "Markup", "Database"],
                    "correct_answer": "B",
                    "explanation": "JavaScript is interpreted"
                },
                {
                    "question_number": 3,
                    "question_text": "What is HTML?",
                    "options": ["Compiled", "Interpreted", "Markup", "Database"],
                    "correct_answer": "C",
                    "explanation": "HTML is a markup language"
                },
                {
                    "question_number": 4,
                    "question_text": "What is SQL?",
                    "options": ["Compiled", "Interpreted", "Markup", "Database"],
                    "correct_answer": "D",
                    "explanation": "SQL is for databases"
                },
                {
                    "question_number": 5,
                    "question_text": "What is C++?",
                    "options": ["Compiled", "Interpreted", "Markup", "Database"],
                    "correct_answer": "A",
                    "explanation": "C++ is compiled"
                }
            ]
        }
        
        is_valid, error_msg = llm_service._validate_quiz_structure(quiz_data)
        
        assert is_valid, f"Validation failed: {error_msg}"
        
        # Check that answers were normalized
        assert quiz_data["questions"][0]["correct_answer"] == "Interpreted"
        assert quiz_data["questions"][1]["correct_answer"] == "Interpreted"
        assert quiz_data["questions"][2]["correct_answer"] == "Markup"
        assert quiz_data["questions"][3]["correct_answer"] == "Database"
        assert quiz_data["questions"][4]["correct_answer"] == "Compiled"
    
    def test_validation_normalizes_option_prefix(self, llm_service):
        """Test that validation normalizes 'Option X' format."""
        quiz_data = {
            "questions": [
                {
                    "question_number": i,
                    "question_text": f"Question {i}?",
                    "options": ["Option A", "Option B", "Option C", "Option D"],
                    "correct_answer": "Option B",
                    "explanation": f"Explanation {i}"
                }
                for i in range(1, 6)
            ]
        }
        
        is_valid, error_msg = llm_service._validate_quiz_structure(quiz_data)
        
        assert is_valid, f"Validation failed: {error_msg}"
        
        # All answers should remain "Option B" (exact match)
        for question in quiz_data["questions"]:
            assert question["correct_answer"] == "Option B"
    
    def test_validation_fails_on_invalid_answer(self, llm_service):
        """Test that validation fails when answer cannot be normalized."""
        quiz_data = {
            "questions": [
                {
                    "question_number": i,
                    "question_text": f"Question {i}?",
                    "options": ["Option A", "Option B", "Option C", "Option D"],
                    "correct_answer": "Invalid Answer",
                    "explanation": f"Explanation {i}"
                }
                for i in range(1, 6)
            ]
        }
        
        is_valid, error_msg = llm_service._validate_quiz_structure(quiz_data)
        
        assert not is_valid
        assert "Could not normalize" in error_msg
