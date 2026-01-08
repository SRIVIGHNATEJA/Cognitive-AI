"""
Input service for processing educational materials.

Orchestrates file processing, text extraction, input type detection,
and caching of processed content.
"""

import uuid
from typing import Optional
from datetime import datetime

from fastapi import UploadFile

from app.models import InputData, InputType, InputProcessingResponse
from app.services.file_processor import (
    extract_text_from_file,
    normalize_text,
    validate_file_format,
    validate_file_size,
    FileProcessingError
)
from app.services.cache_service import cache_service
from app.logging_config import get_logger

logger = get_logger(__name__)


class InputService:
    """
    Service for processing and managing educational input materials.
    
    Handles file uploads, text input, type detection, and caching.
    """
    
    def __init__(self):
        """Initialize the input service."""
        self.cache_service = cache_service
    
    def _generate_input_id(self) -> str:
        """
        Generate a unique input ID.
        
        Returns:
            Unique identifier string
        """
        return f"input_{uuid.uuid4().hex[:12]}"
    
    def detect_input_type(self, text: str) -> InputType:
        """
        Detect the type of input content using simple heuristics.
        
        Uses keyword-based detection to classify content as syllabus,
        question bank, or mixed. LLM-based detection will be added in Phase 2.
        
        Args:
            text: Normalized text content to analyze
            
        Returns:
            Detected InputType
        """
        text_lower = text.lower()
        
        # Keywords for syllabus detection
        syllabus_keywords = [
            'syllabus', 'course outline', 'learning objectives',
            'week 1', 'week 2', 'module 1', 'module 2',
            'lecture', 'topics covered', 'course description',
            'prerequisites', 'textbook', 'grading'
        ]
        
        # Keywords for question bank detection
        question_keywords = [
            'question', 'answer', 'multiple choice', 'mcq',
            'true or false', 'fill in the blank', 'short answer',
            'what is', 'which of the following', 'explain',
            'define', 'describe', 'compare'
        ]
        
        # Count keyword matches
        syllabus_score = sum(1 for keyword in syllabus_keywords if keyword in text_lower)
        question_score = sum(1 for keyword in question_keywords if keyword in text_lower)
        
        logger.debug(f"Type detection scores - Syllabus: {syllabus_score}, Questions: {question_score}")
        
        # Determine type based on scores
        if syllabus_score > question_score and syllabus_score >= 2:
            return InputType.SYLLABUS
        elif question_score > syllabus_score and question_score >= 3:
            return InputType.QUESTION_BANK
        elif syllabus_score > 0 and question_score > 0:
            return InputType.MIXED
        else:
            # Default to syllabus if unclear
            return InputType.SYLLABUS
    
    async def process_file_upload(
        self,
        file: UploadFile,
        hint_type: Optional[InputType] = None
    ) -> InputProcessingResponse:
        """
        Process an uploaded file and extract its content.
        
        Args:
            file: Uploaded file object
            hint_type: Optional hint for input type
            
        Returns:
            InputProcessingResponse with processing results
            
        Raises:
            FileProcessingError: If file processing fails
            ValueError: If file validation fails
        """
        logger.info(f"Processing file upload: {file.filename}")
        
        # Validate file format
        if not validate_file_format(file.filename):
            raise ValueError(
                f"Unsupported file format. Please upload PDF, PPT, PPTX, DOC, or DOCX files."
            )
        
        # Read file content
        file_content = await file.read()
        file_size = len(file_content)
        
        # Validate file size
        if not validate_file_size(file_size):
            from app.config import settings
            raise ValueError(
                f"File size ({file_size / (1024*1024):.2f} MB) exceeds maximum "
                f"allowed size ({settings.max_file_size_mb} MB)"
            )
        
        # Extract text from file
        try:
            extracted_text = extract_text_from_file(file.filename, file_content)
        except FileProcessingError as e:
            logger.error(f"File extraction failed: {str(e)}")
            raise
        
        # Detect input type (use hint if provided)
        if hint_type:
            detected_type = hint_type
            logger.info(f"Using provided input type hint: {detected_type}")
        else:
            detected_type = self.detect_input_type(extracted_text)
            logger.info(f"Detected input type: {detected_type}")
        
        # Generate input ID
        input_id = self._generate_input_id()
        
        # Create InputData object
        input_data = InputData(
            input_id=input_id,
            detected_type=detected_type,
            extracted_text=extracted_text,
            original_filename=file.filename,
            processed_at=datetime.now()
        )
        
        # Cache the processed input
        self.cache_service.cache_input(
            input_id,
            input_data.model_dump(mode='json')
        )
        
        logger.info(f"Successfully processed file: {file.filename} -> {input_id}")
        
        # Return response
        return InputProcessingResponse(
            success=True,
            input_id=input_id,
            detected_type=detected_type,
            extracted_text_length=len(extracted_text),
            message="File processed successfully",
            original_filename=file.filename
        )
    
    def process_text_input(
        self,
        content: str,
        hint_type: Optional[InputType] = None
    ) -> InputProcessingResponse:
        """
        Process direct text input.
        
        Args:
            content: Text content to process
            hint_type: Optional hint for input type
            
        Returns:
            InputProcessingResponse with processing results
            
        Raises:
            ValueError: If content is invalid
        """
        logger.info("Processing text input")
        
        # Validate content
        if not content or len(content.strip()) == 0:
            raise ValueError("Text content cannot be empty")
        
        # Normalize text
        normalized_text = normalize_text(content)
        
        # Validate minimum length
        from app.config import settings
        if len(normalized_text) < settings.min_extracted_text_length:
            raise ValueError(
                f"Text content too short ({len(normalized_text)} characters). "
                f"Minimum required: {settings.min_extracted_text_length} characters"
            )
        
        # Detect input type (use hint if provided)
        if hint_type:
            detected_type = hint_type
            logger.info(f"Using provided input type hint: {detected_type}")
        else:
            detected_type = self.detect_input_type(normalized_text)
            logger.info(f"Detected input type: {detected_type}")
        
        # Generate input ID
        input_id = self._generate_input_id()
        
        # Create InputData object
        input_data = InputData(
            input_id=input_id,
            detected_type=detected_type,
            extracted_text=normalized_text,
            original_filename=None,
            processed_at=datetime.now()
        )
        
        # Cache the processed input
        self.cache_service.cache_input(
            input_id,
            input_data.model_dump(mode='json')
        )
        
        logger.info(f"Successfully processed text input -> {input_id}")
        
        # Return response
        return InputProcessingResponse(
            success=True,
            input_id=input_id,
            detected_type=detected_type,
            extracted_text_length=len(normalized_text),
            message="Text input processed successfully",
            original_filename=None
        )
    
    def get_input_status(self, input_id: str) -> Optional[InputData]:
        """
        Get the status and details of a processed input.
        
        Args:
            input_id: Unique identifier for the input
            
        Returns:
            InputData if found, None otherwise
        """
        cached_data = self.cache_service.get_cached_data(input_id, 'input')
        
        if cached_data:
            return InputData(**cached_data)
        
        return None


# Global input service instance
input_service = InputService()
