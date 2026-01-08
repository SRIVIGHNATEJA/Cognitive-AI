"""
Unit tests for input service.
Tests input processing, type detection, and validation.
"""

import pytest
from io import BytesIO
from fastapi import UploadFile

from app.services.input_service import InputService
from app.models import InputType
from app.services.file_processor import FileProcessingError


@pytest.fixture
def input_service():
    """Create an input service instance for testing."""
    return InputService()


class TestInputTypeDetection:
    """Tests for input type detection."""
    
    def test_detect_syllabus_type(self, input_service):
        """Test detection of syllabus content."""
        syllabus_text = """
        Course Syllabus: Introduction to Python Programming
        
        Week 1: Python Basics
        Week 2: Data Structures
        Week 3: Functions and Modules
        
        Learning Objectives:
        - Understand Python syntax
        - Master data structures
        
        Prerequisites: None
        Textbook: Python Programming by Example
        """
        
        detected_type = input_service.detect_input_type(syllabus_text)
        assert detected_type == InputType.SYLLABUS
    
    def test_detect_question_bank_type(self, input_service):
        """Test detection of question bank content."""
        question_text = """
        Question 1: What is Python?
        Answer: Python is a programming language.
        
        Question 2: Which of the following is a data type in Python?
        a) Integer
        b) String
        c) List
        d) All of the above
        Answer: d
        
        Question 3: Explain the difference between lists and tuples.
        Answer: Lists are mutable while tuples are immutable.
        """
        
        detected_type = input_service.detect_input_type(question_text)
        assert detected_type == InputType.QUESTION_BANK
    
    def test_detect_mixed_type(self, input_service):
        """Test detection of mixed content."""
        mixed_text = """
        Course Syllabus: Programming Fundamentals
        Week 1: Introduction to Programming
        Week 2: Variables and Data Types
        
        Learning Objectives:
        - Understand programming concepts
        
        Practice Questions:
        Question: What is a variable?
        Answer: A variable stores data.
        
        Question: Define a string.
        Answer: A string is a sequence of characters.
        """
        
        detected_type = input_service.detect_input_type(mixed_text)
        assert detected_type == InputType.MIXED
    
    def test_detect_default_to_syllabus(self, input_service):
        """Test that unclear content defaults to syllabus."""
        unclear_text = "This is some educational content without clear indicators."
        
        detected_type = input_service.detect_input_type(unclear_text)
        assert detected_type == InputType.SYLLABUS


class TestTextInputProcessing:
    """Tests for text input processing."""
    
    def test_process_valid_text_input(self, input_service):
        """Test processing valid text input."""
        content = "A" * 150  # Long enough to pass minimum length
        
        response = input_service.process_text_input(content)
        
        assert response.success is True
        assert response.input_id.startswith("input_")
        assert response.extracted_text_length >= 100
        assert response.message == "Text input processed successfully"
    
    def test_process_text_with_type_hint(self, input_service):
        """Test processing text with type hint."""
        content = "A" * 150
        
        response = input_service.process_text_input(
            content,
            hint_type=InputType.QUESTION_BANK
        )
        
        assert response.success is True
        assert response.detected_type == InputType.QUESTION_BANK
    
    def test_process_empty_text_raises_error(self, input_service):
        """Test that empty text raises ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            input_service.process_text_input("")
    
    def test_process_whitespace_only_text_raises_error(self, input_service):
        """Test that whitespace-only text raises ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            input_service.process_text_input("   \n   \t   ")
    
    def test_process_too_short_text_raises_error(self, input_service):
        """Test that text below minimum length raises ValueError."""
        short_text = "Too short"
        
        with pytest.raises(ValueError, match="too short"):
            input_service.process_text_input(short_text)
    
    def test_processed_text_is_cached(self, input_service):
        """Test that processed text is cached."""
        content = "A" * 150
        
        response = input_service.process_text_input(content)
        
        # Verify it's cached
        cached_data = input_service.get_input_status(response.input_id)
        assert cached_data is not None
        assert cached_data.input_id == response.input_id


class TestInputIDGeneration:
    """Tests for input ID generation."""
    
    def test_generate_unique_input_ids(self, input_service):
        """Test that generated input IDs are unique."""
        id1 = input_service._generate_input_id()
        id2 = input_service._generate_input_id()
        id3 = input_service._generate_input_id()
        
        assert id1 != id2
        assert id2 != id3
        assert id1 != id3
    
    def test_input_id_format(self, input_service):
        """Test that input IDs follow expected format."""
        input_id = input_service._generate_input_id()
        
        assert input_id.startswith("input_")
        assert len(input_id) > 6  # "input_" + some hex characters


class TestGetInputStatus:
    """Tests for retrieving input status."""
    
    def test_get_existing_input_status(self, input_service):
        """Test retrieving status of existing input."""
        content = "A" * 150
        response = input_service.process_text_input(content)
        
        # Get status
        status = input_service.get_input_status(response.input_id)
        
        assert status is not None
        assert status.input_id == response.input_id
        assert status.extracted_text == content
    
    def test_get_nonexistent_input_status(self, input_service):
        """Test retrieving status of non-existent input."""
        status = input_service.get_input_status("nonexistent_id")
        
        assert status is None
