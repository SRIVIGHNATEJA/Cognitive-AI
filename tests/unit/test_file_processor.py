"""
Unit tests for file processing utilities.
Tests file extraction, validation, and normalization functions.
"""

import pytest
from app.services.file_processor import (
    normalize_text,
    validate_file_format,
    validate_file_size,
    FileProcessingError
)
from app.config import settings


class TestFileFormatValidation:
    """Tests for file format validation."""
    
    def test_validate_supported_pdf_format(self):
        """Test that PDF format is accepted."""
        assert validate_file_format("document.pdf") is True
        assert validate_file_format("DOCUMENT.PDF") is True
    
    def test_validate_supported_pptx_format(self):
        """Test that PPTX format is accepted."""
        assert validate_file_format("presentation.pptx") is True
        assert validate_file_format("presentation.ppt") is True
    
    def test_validate_supported_docx_format(self):
        """Test that DOCX format is accepted."""
        assert validate_file_format("document.docx") is True
        assert validate_file_format("document.doc") is True
    
    def test_validate_unsupported_format(self):
        """Test that unsupported formats are rejected."""
        assert validate_file_format("document.txt") is False
        assert validate_file_format("image.jpg") is False
        assert validate_file_format("data.csv") is False
    
    def test_validate_no_extension(self):
        """Test that files without extension are rejected."""
        assert validate_file_format("document") is False
    
    def test_validate_empty_filename(self):
        """Test that empty filename is rejected."""
        assert validate_file_format("") is False
        assert validate_file_format(None) is False


class TestFileSizeValidation:
    """Tests for file size validation edge cases."""
    
    def test_file_at_size_limit_boundary(self):
        """Test files at the exact size limit boundary."""
        max_size_bytes = settings.max_file_size_mb * 1024 * 1024
        
        # Exactly at limit should be valid
        assert validate_file_size(max_size_bytes) is True
        
        # Just under limit should be valid
        assert validate_file_size(max_size_bytes - 1) is True
    
    def test_file_exceeding_size_limit(self):
        """Test files exceeding the size limit."""
        max_size_bytes = settings.max_file_size_mb * 1024 * 1024
        
        # Just over limit should be invalid
        assert validate_file_size(max_size_bytes + 1) is False
        
        # Significantly over limit should be invalid
        assert validate_file_size(max_size_bytes * 2) is False
    
    def test_small_file_sizes(self):
        """Test that small files are always valid."""
        assert validate_file_size(0) is True
        assert validate_file_size(1024) is True  # 1 KB
        assert validate_file_size(1024 * 1024) is True  # 1 MB
    
    def test_various_file_sizes(self):
        """Test various file sizes around common boundaries."""
        # 5 MB (should be valid with default 10 MB limit)
        assert validate_file_size(5 * 1024 * 1024) is True
        
        # 9.9 MB (should be valid)
        assert validate_file_size(int(9.9 * 1024 * 1024)) is True
        
        # 10.1 MB (should be invalid with default 10 MB limit)
        assert validate_file_size(int(10.1 * 1024 * 1024)) is False


class TestTextNormalization:
    """Tests for text normalization."""
    
    def test_normalize_empty_text(self):
        """Test normalization of empty text."""
        assert normalize_text("") == ""
        assert normalize_text(None) == ""
    
    def test_normalize_excessive_whitespace(self):
        """Test removal of excessive whitespace."""
        text = "This  has   multiple    spaces"
        normalized = normalize_text(text)
        assert "  " not in normalized
        assert normalized == "This has multiple spaces"
    
    def test_normalize_multiple_newlines(self):
        """Test normalization of multiple newlines."""
        text = "Line 1\n\n\n\nLine 2"
        normalized = normalize_text(text)
        assert "\n\n\n" not in normalized
        assert normalized == "Line 1\n\nLine 2"
    
    def test_normalize_leading_trailing_whitespace(self):
        """Test removal of leading and trailing whitespace."""
        text = "  \n  Content here  \n  "
        normalized = normalize_text(text)
        assert normalized == "Content here"
    
    def test_normalize_preserves_content(self):
        """Test that normalization preserves actual content."""
        text = "Important content with proper spacing."
        normalized = normalize_text(text)
        assert "Important" in normalized
        assert "content" in normalized
        assert "proper spacing" in normalized
    
    def test_normalize_complex_text(self):
        """Test normalization of complex text with mixed issues."""
        text = """
        
        Paragraph 1 with   extra spaces.
        
        
        Paragraph 2 with more   content.
        
        """
        normalized = normalize_text(text)
        assert normalized.startswith("Paragraph 1")
        assert "extra spaces" in normalized
        assert "Paragraph 2" in normalized
        # Should have double newline between paragraphs
        assert "\n\n" in normalized
        # Should not have triple newlines
        assert "\n\n\n" not in normalized
