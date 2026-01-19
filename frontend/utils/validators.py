"""
Input validation utilities.

Provides validation functions for user inputs.
"""

from typing import Tuple
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import config


def validate_file_upload(uploaded_file) -> Tuple[bool, str]:
    """
    Validate uploaded file.
    
    Args:
        uploaded_file: Streamlit UploadedFile object
        
    Returns:
        Tuple of (is_valid, message)
    """
    # Check file exists
    if uploaded_file is None:
        return False, "No file selected"
    
    # Check file format
    file_ext = uploaded_file.name.split('.')[-1].lower()
    
    if not config.validate_file_format(uploaded_file.name):
        allowed = ', '.join(config.SUPPORTED_FORMATS)
        return False, f"Unsupported format. Allowed: {allowed}"
    
    # Check file size
    if not config.validate_file_size(uploaded_file.size):
        file_size_mb = config.get_file_size_mb(uploaded_file.size)
        return False, f"File too large ({file_size_mb:.1f}MB). Maximum: {config.MAX_FILE_SIZE_MB}MB"
    
    return True, "Valid"


def validate_text_input(text: str, min_length: int = 20, max_length: int = 10000) -> Tuple[bool, str]:
    """
    Validate text input.
    
    Args:
        text: Text to validate
        min_length: Minimum length
        max_length: Maximum length
        
    Returns:
        Tuple of (is_valid, message)
    """
    if not text or not text.strip():
        return False, "Text cannot be empty"
    
    text_length = len(text.strip())
    
    if text_length < min_length:
        return False, f"Text too short. Minimum: {min_length} characters"
    
    if text_length > max_length:
        return False, f"Text too long. Maximum: {max_length} characters"
    
    return True, "Valid"


def validate_module_id(module_id: str) -> Tuple[bool, str]:
    """
    Validate module ID format.
    
    Args:
        module_id: Module ID to validate
        
    Returns:
        Tuple of (is_valid, message)
    """
    if not module_id:
        return False, "Module ID cannot be empty"
    
    if not module_id.startswith("mod_"):
        return False, "Invalid module ID format"
    
    return True, "Valid"


def validate_quiz_answers(answers: dict, expected_count: int = 10) -> Tuple[bool, str]:
    """
    Validate quiz answers.
    
    Args:
        answers: Dictionary of question_number -> answer
        expected_count: Expected number of answers
        
    Returns:
        Tuple of (is_valid, message)
    """
    if not answers:
        return False, "No answers provided"
    
    if len(answers) != expected_count:
        return False, f"Expected {expected_count} answers, got {len(answers)}"
    
    # Check all question numbers are present
    for i in range(1, expected_count + 1):
        if i not in answers:
            return False, f"Missing answer for question {i}"
    
    return True, "Valid"
