"""
Unit tests for Phase 2 LLM quiz methods.

Tests the new split methods:
- generate_quiz_questions_llm() - Questions without answers
- generate_quiz_answers_llm() - Answers and explanations
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from app.services.llm_service import LLMService, LLMServiceError


@pytest.fixture
def llm_service():
    """Create an LLMService instance for testing."""
    return LLMService()


@pytest.fixture
def module_info():
    """Sample module info for testing."""
    return {
        "module_id": "mod_123",
        "topic_name": "Introduction to Python",
        "estimated_hours": 5.0
    }


@pytest.fixture
def sample_content():
    """Sample educational content for testing."""
    return """
    Python is a high-level programming language.
    It supports multiple programming paradigms.
    Python uses dynamic typing and garbage collection.
    """


@pytest.fixture
def sample_questions():
    """Sample questions without answers for testing."""
    return [
        {
            "question_number": 1,
            "question_text": "What is Python?",
            "options": ["A language", "A snake", "A framework", "A database"]
        },
        {
            "question_number": 2,
            "question_text": "What typing does Python use?",
            "options": ["Static", "Dynamic", "Strong", "Weak"]
        },
        {
            "question_number": 3,
            "question_text": "What is garbage collection?",
            "options": ["Memory management", "Code cleanup", "Bug fixing", "Testing"]
        },
        {
            "question_number": 4,
            "question_text": "Is Python high-level?",
            "options": ["Yes", "No", "Sometimes", "Depends"]
        },
        {
            "question_number": 5,
            "question_text": "What paradigms does Python support?",
            "options": ["Multiple", "Single", "None", "Two"]
        }
    ]


class TestGenerateQuizQuestionsLLM:
    """Test generate_quiz_questions_llm() method."""
    
    @patch.object(LLMService, '_check_ollama_availability')
    @patch.object(LLMService, '_call_ollama')
    def test_generate_questions_success(self, mock_call, mock_check, llm_service, module_info, sample_content):
        """Test successful generation of quiz questions without answers."""
        mock_check.return_value = True
        mock_call.return_value = {
            "response": """{
                "questions": [
                    {
                        "question_number": 1,
                        "question_text": "What is Python?",
                        "options": ["A", "B", "C", "D"]
                    },
                    {
                        "question_number": 2,
                        "question_text": "Question 2?",
                        "options": ["A", "B", "C", "D"]
                    },
                    {
                        "question_number": 3,
                        "question_text": "Question 3?",
                        "options": ["A", "B", "C", "D"]
                    },
                    {
                        "question_number": 4,
                        "question_text": "Question 4?",
                        "options": ["A", "B", "C", "D"]
                    },
                    {
                        "question_number": 5,
                        "question_text": "Question 5?",
                        "options": ["A", "B", "C", "D"]
                    }
                ]
            }"""
        }
        
        questions = llm_service.generate_quiz_questions_llm(module_info, sample_content)
        
        assert len(questions) == 5
        assert all("question_number" in q for q in questions)
        assert all("question_text" in q for q in questions)
        assert all("options" in q for q in questions)
        # Ensure no answers or explanations
        assert all("correct_answer" not in q for q in questions)
        assert all("explanation" not in q for q in questions)
    
    @patch.object(LLMService, '_check_ollama_availability')
    @patch.object(LLMService, '_call_ollama')
    def test_generate_questions_with_answers_fails_validation(
        self, mock_call, mock_check, llm_service, module_info, sample_content
    ):
        """Test that questions with correct_answer field fail validation."""
        mock_check.return_value = True
        mock_call.return_value = {
            "response": """{
                "questions": [
                    {
                        "question_number": 1,
                        "question_text": "What is Python?",
                        "options": ["A", "B", "C", "D"],
                        "correct_answer": "A"
                    }
                ]
            }"""
        }
        
        with pytest.raises(LLMServiceError, match="Failed to generate valid quiz questions"):
            llm_service.generate_quiz_questions_llm(module_info, sample_content, max_retries=0)
    
    @patch.object(LLMService, '_check_ollama_availability')
    def test_generate_questions_ollama_unavailable(self, mock_check, llm_service, module_info, sample_content):
        """Test error when Ollama is unavailable."""
        mock_check.return_value = False
        
        with pytest.raises(LLMServiceError, match="Ollama service is not available"):
            llm_service.generate_quiz_questions_llm(module_info, sample_content)


class TestGenerateQuizAnswersLLM:
    """Test generate_quiz_answers_llm() method."""
    
    @patch.object(LLMService, '_check_ollama_availability')
    @patch.object(LLMService, '_call_ollama')
    def test_generate_answers_success(
        self, mock_call, mock_check, llm_service, module_info, sample_content, sample_questions
    ):
        """Test successful generation of quiz answers."""
        mock_check.return_value = True
        mock_call.return_value = {
            "response": """{
                "answers": [
                    {
                        "question_number": 1,
                        "correct_answer": "A language",
                        "explanation": "Python is a programming language"
                    },
                    {
                        "question_number": 2,
                        "correct_answer": "Dynamic",
                        "explanation": "Python uses dynamic typing"
                    },
                    {
                        "question_number": 3,
                        "correct_answer": "Memory management",
                        "explanation": "Garbage collection manages memory"
                    },
                    {
                        "question_number": 4,
                        "correct_answer": "Yes",
                        "explanation": "Python is high-level"
                    },
                    {
                        "question_number": 5,
                        "correct_answer": "Multiple",
                        "explanation": "Python supports multiple paradigms"
                    }
                ]
            }"""
        }
        
        answers = llm_service.generate_quiz_answers_llm(module_info, sample_questions, sample_content)
        
        assert len(answers) == 5
        assert all("question_number" in a for a in answers)
        assert all("correct_answer" in a for a in answers)
        assert all("explanation" in a for a in answers)
    
    @patch.object(LLMService, '_check_ollama_availability')
    @patch.object(LLMService, '_call_ollama')
    def test_generate_answers_with_label_normalization(
        self, mock_call, mock_check, llm_service, module_info, sample_content, sample_questions
    ):
        """Test that answer labels (A, B, C, D) are normalized to option text."""
        mock_check.return_value = True
        mock_call.return_value = {
            "response": """{
                "answers": [
                    {
                        "question_number": 1,
                        "correct_answer": "A",
                        "explanation": "Python is a programming language"
                    },
                    {
                        "question_number": 2,
                        "correct_answer": "B",
                        "explanation": "Python uses dynamic typing"
                    },
                    {
                        "question_number": 3,
                        "correct_answer": "A",
                        "explanation": "Garbage collection manages memory"
                    },
                    {
                        "question_number": 4,
                        "correct_answer": "A",
                        "explanation": "Python is high-level"
                    },
                    {
                        "question_number": 5,
                        "correct_answer": "A",
                        "explanation": "Python supports multiple paradigms"
                    }
                ]
            }"""
        }
        
        answers = llm_service.generate_quiz_answers_llm(module_info, sample_questions, sample_content)
        
        # Check that labels were normalized to actual option text
        assert answers[0]["correct_answer"] == "A language"  # A → first option
        assert answers[1]["correct_answer"] == "Dynamic"     # B → second option
    
    @patch.object(LLMService, '_check_ollama_availability')
    @patch.object(LLMService, '_call_ollama')
    def test_generate_answers_wrong_count_fails(
        self, mock_call, mock_check, llm_service, module_info, sample_content, sample_questions
    ):
        """Test that wrong number of answers fails validation."""
        mock_check.return_value = True
        mock_call.return_value = {
            "response": """{
                "answers": [
                    {
                        "question_number": 1,
                        "correct_answer": "A",
                        "explanation": "Explanation"
                    }
                ]
            }"""
        }
        
        with pytest.raises(LLMServiceError, match="Failed to generate valid quiz answers"):
            llm_service.generate_quiz_answers_llm(module_info, sample_questions, sample_content, max_retries=0)
    
    @patch.object(LLMService, '_check_ollama_availability')
    def test_generate_answers_ollama_unavailable(
        self, mock_check, llm_service, module_info, sample_content, sample_questions
    ):
        """Test error when Ollama is unavailable."""
        mock_check.return_value = False
        
        with pytest.raises(LLMServiceError, match="Ollama service is not available"):
            llm_service.generate_quiz_answers_llm(module_info, sample_questions, sample_content)


class TestValidateQuizQuestionsStructure:
    """Test _validate_quiz_questions_structure() method."""
    
    def test_valid_questions_structure(self, llm_service):
        """Test validation of valid questions structure."""
        quiz_data = {
            "questions": [
                {
                    "question_number": i,
                    "question_text": f"Question {i}?",
                    "options": ["A", "B", "C", "D"]
                }
                for i in range(1, 6)
            ]
        }
        
        is_valid, error_msg = llm_service._validate_quiz_questions_structure(quiz_data)
        
        assert is_valid is True
        assert error_msg == ""
    
    def test_questions_with_correct_answer_fails(self, llm_service):
        """Test that questions with correct_answer field fail validation."""
        quiz_data = {
            "questions": [
                {
                    "question_number": i,
                    "question_text": f"Question {i}?",
                    "options": ["A", "B", "C", "D"],
                    "correct_answer": "A"  # Should not be present
                }
                for i in range(1, 6)
            ]
        }
        
        is_valid, error_msg = llm_service._validate_quiz_questions_structure(quiz_data)
        
        assert is_valid is False
        assert "should not have 'correct_answer' field" in error_msg
    
    def test_questions_with_explanation_fails(self, llm_service):
        """Test that questions with explanation field fail validation."""
        quiz_data = {
            "questions": [
                {
                    "question_number": i,
                    "question_text": f"Question {i}?",
                    "options": ["A", "B", "C", "D"],
                    "explanation": "Explanation"  # Should not be present
                }
                for i in range(1, 6)
            ]
        }
        
        is_valid, error_msg = llm_service._validate_quiz_questions_structure(quiz_data)
        
        assert is_valid is False
        assert "should not have 'explanation' field" in error_msg


class TestValidateQuizAnswersStructure:
    """Test _validate_quiz_answers_structure() method."""
    
    def test_valid_answers_structure(self, llm_service, sample_questions):
        """Test validation of valid answers structure."""
        answers_data = {
            "answers": [
                {
                    "question_number": i,
                    "correct_answer": sample_questions[i-1]["options"][0],
                    "explanation": f"Explanation {i}"
                }
                for i in range(1, 6)
            ]
        }
        
        is_valid, error_msg = llm_service._validate_quiz_answers_structure(answers_data, sample_questions)
        
        assert is_valid is True
        assert error_msg == ""
    
    def test_answers_with_invalid_correct_answer_fails(self, llm_service, sample_questions):
        """Test that invalid correct_answer fails validation."""
        answers_data = {
            "answers": [
                {
                    "question_number": i,
                    "correct_answer": "Invalid option",
                    "explanation": "Explanation"
                }
                for i in range(1, 6)
            ]
        }
        
        is_valid, error_msg = llm_service._validate_quiz_answers_structure(answers_data, sample_questions)
        
        assert is_valid is False
        assert "validation failed" in error_msg
    
    def test_answers_wrong_count_fails(self, llm_service, sample_questions):
        """Test that wrong number of answers fails validation."""
        answers_data = {
            "answers": [
                {
                    "question_number": 1,
                    "correct_answer": "A",
                    "explanation": "Explanation"
                }
            ]
        }
        
        is_valid, error_msg = llm_service._validate_quiz_answers_structure(answers_data, sample_questions)
        
        assert is_valid is False
        assert "Expected exactly 5 answers" in error_msg


class TestBackwardCompatibility:
    """Test that legacy generate_quiz_llm() still works."""
    
    @patch.object(LLMService, '_check_ollama_availability')
    @patch.object(LLMService, '_call_ollama')
    def test_legacy_method_still_works(self, mock_call, mock_check, llm_service, module_info, sample_content):
        """Test that the legacy generate_quiz_llm() method still works."""
        mock_check.return_value = True
        mock_call.return_value = {
            "response": """{
                "questions": [
                    {
                        "question_number": 1,
                        "question_text": "What is Python?",
                        "options": ["A", "B", "C", "D"],
                        "correct_answer": "A",
                        "explanation": "Python is a language"
                    },
                    {
                        "question_number": 2,
                        "question_text": "Question 2?",
                        "options": ["A", "B", "C", "D"],
                        "correct_answer": "A",
                        "explanation": "Explanation 2"
                    },
                    {
                        "question_number": 3,
                        "question_text": "Question 3?",
                        "options": ["A", "B", "C", "D"],
                        "correct_answer": "A",
                        "explanation": "Explanation 3"
                    },
                    {
                        "question_number": 4,
                        "question_text": "Question 4?",
                        "options": ["A", "B", "C", "D"],
                        "correct_answer": "A",
                        "explanation": "Explanation 4"
                    },
                    {
                        "question_number": 5,
                        "question_text": "Question 5?",
                        "options": ["A", "B", "C", "D"],
                        "correct_answer": "A",
                        "explanation": "Explanation 5"
                    }
                ]
            }"""
        }
        
        questions = llm_service.generate_quiz_llm(module_info, sample_content)
        
        assert len(questions) == 5
        # Legacy method returns questions WITH answers and explanations
        assert all("correct_answer" in q for q in questions)
        assert all("explanation" in q for q in questions)
