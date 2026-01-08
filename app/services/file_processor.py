"""
File processing utilities for extracting text from various file formats.

Supports PDF, PPT/PPTX, and DOC/DOCX file formats with text extraction
and normalization capabilities.
"""

import re
import logging
from typing import Optional
from io import BytesIO

from pypdf import PdfReader
from pptx import Presentation
from docx import Document

from app.config import settings
from app.logging_config import get_logger

logger = get_logger(__name__)


class FileProcessingError(Exception):
    """Exception raised when file processing fails."""
    pass


def extract_from_pdf(file_bytes: bytes) -> str:
    """
    Extract text content from a PDF file.
    
    Args:
        file_bytes: PDF file content as bytes
        
    Returns:
        Extracted text content
        
    Raises:
        FileProcessingError: If PDF extraction fails
    """
    try:
        pdf_file = BytesIO(file_bytes)
        reader = PdfReader(pdf_file)
        
        text_content = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                text_content.append(text)
        
        extracted_text = "\n".join(text_content)
        logger.info(f"Extracted {len(extracted_text)} characters from PDF ({len(reader.pages)} pages)")
        
        return extracted_text
        
    except Exception as e:
        logger.error(f"Failed to extract text from PDF: {str(e)}")
        raise FileProcessingError(f"PDF extraction failed: {str(e)}")


def extract_from_pptx(file_bytes: bytes) -> str:
    """
    Extract text content from a PowerPoint file (PPT/PPTX).
    
    Args:
        file_bytes: PowerPoint file content as bytes
        
    Returns:
        Extracted text content
        
    Raises:
        FileProcessingError: If PowerPoint extraction fails
    """
    try:
        pptx_file = BytesIO(file_bytes)
        presentation = Presentation(pptx_file)
        
        text_content = []
        for slide in presentation.slides:
            for shape in slide.shapes:
                if hasattr(shape, "text") and shape.text:
                    text_content.append(shape.text)
        
        extracted_text = "\n".join(text_content)
        logger.info(f"Extracted {len(extracted_text)} characters from PPTX ({len(presentation.slides)} slides)")
        
        return extracted_text
        
    except Exception as e:
        logger.error(f"Failed to extract text from PPTX: {str(e)}")
        raise FileProcessingError(f"PowerPoint extraction failed: {str(e)}")


def extract_from_docx(file_bytes: bytes) -> str:
    """
    Extract text content from a Word document (DOC/DOCX).
    
    Args:
        file_bytes: Word document content as bytes
        
    Returns:
        Extracted text content
        
    Raises:
        FileProcessingError: If Word document extraction fails
    """
    try:
        docx_file = BytesIO(file_bytes)
        document = Document(docx_file)
        
        text_content = []
        for paragraph in document.paragraphs:
            if paragraph.text:
                text_content.append(paragraph.text)
        
        # Also extract text from tables
        for table in document.tables:
            for row in table.rows:
                for cell in row.cells:
                    if cell.text:
                        text_content.append(cell.text)
        
        extracted_text = "\n".join(text_content)
        logger.info(f"Extracted {len(extracted_text)} characters from DOCX ({len(document.paragraphs)} paragraphs)")
        
        return extracted_text
        
    except Exception as e:
        logger.error(f"Failed to extract text from DOCX: {str(e)}")
        raise FileProcessingError(f"Word document extraction failed: {str(e)}")


def normalize_text(text: str) -> str:
    """
    Clean and normalize extracted text content.
    
    Performs the following operations:
    - Removes excessive whitespace
    - Normalizes line breaks
    - Removes special characters that may interfere with processing
    - Strips leading/trailing whitespace
    
    Args:
        text: Raw extracted text
        
    Returns:
        Normalized text content
    """
    if not text:
        return ""
    
    # Replace multiple spaces with single space
    text = re.sub(r' +', ' ', text)
    
    # Replace multiple newlines with double newline (paragraph separation)
    text = re.sub(r'\n\s*\n+', '\n\n', text)
    
    # Remove leading/trailing whitespace from each line
    lines = [line.strip() for line in text.split('\n')]
    text = '\n'.join(lines)
    
    # Remove any remaining excessive whitespace
    text = text.strip()
    
    logger.debug(f"Normalized text to {len(text)} characters")
    
    return text


def validate_file_format(filename: str) -> bool:
    """
    Validate that the file format is supported.
    
    Args:
        filename: Name of the file to validate
        
    Returns:
        True if format is supported, False otherwise
    """
    if not filename:
        return False
    
    # Get file extension (case-insensitive)
    file_ext = None
    if '.' in filename:
        file_ext = '.' + filename.rsplit('.', 1)[1].lower()
    
    is_valid = file_ext in settings.supported_file_formats
    
    if not is_valid:
        logger.warning(f"Unsupported file format: {file_ext} (file: {filename})")
    
    return is_valid


def validate_file_size(file_size: int) -> bool:
    """
    Validate that the file size is within acceptable limits.
    
    Args:
        file_size: Size of the file in bytes
        
    Returns:
        True if size is acceptable, False otherwise
    """
    max_size_bytes = settings.max_file_size_mb * 1024 * 1024
    is_valid = file_size <= max_size_bytes
    
    if not is_valid:
        logger.warning(
            f"File size {file_size} bytes exceeds maximum {max_size_bytes} bytes "
            f"({settings.max_file_size_mb} MB)"
        )
    
    return is_valid


def extract_text_from_file(filename: str, file_bytes: bytes) -> str:
    """
    Extract text from a file based on its format.
    
    Automatically detects the file format and uses the appropriate
    extraction method.
    
    Args:
        filename: Name of the file (used to determine format)
        file_bytes: File content as bytes
        
    Returns:
        Extracted and normalized text content
        
    Raises:
        FileProcessingError: If extraction fails or format is unsupported
    """
    if not validate_file_format(filename):
        raise FileProcessingError(
            f"Unsupported file format. Supported formats: {', '.join(settings.supported_file_formats)}"
        )
    
    # Get file extension
    file_ext = '.' + filename.rsplit('.', 1)[1].lower()
    
    # Extract based on format
    if file_ext == '.pdf':
        raw_text = extract_from_pdf(file_bytes)
    elif file_ext in ['.ppt', '.pptx']:
        raw_text = extract_from_pptx(file_bytes)
    elif file_ext in ['.doc', '.docx']:
        raw_text = extract_from_docx(file_bytes)
    else:
        raise FileProcessingError(f"Unsupported file format: {file_ext}")
    
    # Normalize the extracted text
    normalized_text = normalize_text(raw_text)
    
    # Validate minimum text length
    if len(normalized_text) < settings.min_extracted_text_length:
        raise FileProcessingError(
            f"Extracted text too short ({len(normalized_text)} characters). "
            f"Minimum required: {settings.min_extracted_text_length} characters"
        )
    
    return normalized_text
