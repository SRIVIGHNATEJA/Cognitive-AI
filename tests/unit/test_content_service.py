"""
Unit tests for the Content Service.

Tests notes generation, cheat sheet generation, and output sanitization.
"""

import pytest
from unittest.mock import Mock, patch
from app.services.content_service import ContentService
from app.models import Module


class TestOutputSanitization:
    """Test output sanitization for UI safety."""
    
    def test_sanitize_removes_control_characters(self):
        """Test that control characters are removed."""
        service = ContentService()
        
        text_with_control = "Hello\x00World\x1FTest"
        sanitized = service.sanitize_output_for_ui(text_with_control)
        
        assert "\x00" not in sanitized
        assert "\x1F" not in sanitized
        assert "HelloWorldTest" == sanitized
    
    def test_sanitize_preserves_newlines_and_tabs(self):
        """Test that newlines and tabs are preserved."""
        service = ContentService()
        
        text = "Line 1\nLine 2\tTabbed"
        sanitized = service.sanitize_output_for_ui(text)
        
        assert "\n" in sanitized
        assert "\t" in sanitized
    
    def test_sanitize_normalizes_excessive_newlines(self):
        """Test that excessive newlines are normalized."""
        service = ContentService()
        
        text = "Line 1\n\n\n\n\n\nLine 2"
        sanitized = service.sanitize_output_for_ui(text)
        
        # Should reduce to max 3 consecutive newlines
        assert "\n\n\n\n" not in sanitized
        assert "Line 1" in sanitized
        assert "Line 2" in sanitized
    
    def test_sanitize_removes_script_tags(self):
        """Test that script tags are removed for safety."""
        service = ContentService()
        
        text = "Safe content <script>alert('xss')</script> more content"
        sanitized = service.sanitize_output_for_ui(text)
        
        assert "<script>" not in sanitized.lower()
        assert "alert" not in sanitized
        assert "Safe content" in sanitized
        assert "more content" in sanitized
    
    def test_sanitize_removes_style_tags(self):
        """Test that style tags are removed."""
        service = ContentService()
        
        text = "Content <style>body{display:none}</style> more"
        sanitized = service.sanitize_output_for_ui(text)
        
        assert "<style>" not in sanitized.lower()
        assert "display:none" not in sanitized
    
    def test_sanitize_trims_whitespace(self):
        """Test that leading/trailing whitespace is trimmed."""
        service = ContentService()
        
        text = "   Content with spaces   "
        sanitized = service.sanitize_output_for_ui(text)
        
        assert sanitized == "Content with spaces"
    
    def test_sanitize_handles_empty_string(self):
        """Test sanitization of empty string."""
        service = ContentService()
        
        assert service.sanitize_output_for_ui("") == ""
        assert service.sanitize_output_for_ui(None) == ""


class TestNotesGeneration:
    """Test notes generation functionality."""
    
    @patch('app.services.content_service.LLMService')
    def test_generate_notes_success(self, mock_llm_class):
        """Test successful notes generation."""
        # Setup mock LLM service
        mock_llm = Mock()
        mock_llm.generate_notes_llm.return_value = "Detailed notes about Python basics..."
        mock_llm_class.return_value = mock_llm
        
        service = ContentService(llm_service=mock_llm)
        
        # Create test module
        module = Module(
            module_id="mod_test123",
            topic_name="Python Basics",
            estimated_hours=5.0,
            prerequisites=[],
            order=1
        )
        
        # Generate notes
        notes = service.generate_notes(
            module=module,
            input_text="Python is a programming language..."
        )
        
        # Verify results
        assert notes == "Detailed notes about Python basics..."
        assert len(notes) > 0
        
        # Verify LLM was called correctly
        mock_llm.generate_notes_llm.assert_called_once()
        call_args = mock_llm.generate_notes_llm.call_args
        assert call_args[1]["module_info"]["topic_name"] == "Python Basics"
        assert call_args[1]["module_info"]["estimated_hours"] == 5.0
    
    @patch('app.services.content_service.LLMService')
    def test_generate_notes_sanitizes_output(self, mock_llm_class):
        """Test that generated notes are sanitized."""
        # Setup mock LLM service with unsafe content
        mock_llm = Mock()
        mock_llm.generate_notes_llm.return_value = "Notes <script>alert('xss')</script> content"
        mock_llm_class.return_value = mock_llm
        
        service = ContentService(llm_service=mock_llm)
        
        module = Module(
            module_id="mod_test123",
            topic_name="Test",
            estimated_hours=1.0,
            prerequisites=[],
            order=1
        )
        
        notes = service.generate_notes(module, "Test content")
        
        # Verify script tag was removed
        assert "<script>" not in notes.lower()
        assert "alert" not in notes
        assert "Notes" in notes
        assert "content" in notes
    
    def test_generate_notes_invalid_module_raises_error(self):
        """Test that invalid module raises error."""
        service = ContentService()
        
        with pytest.raises(ValueError) as exc_info:
            service.generate_notes(None, "Test content")
        
        assert "invalid module" in str(exc_info.value).lower()
    
    def test_generate_notes_empty_input_raises_error(self):
        """Test that empty input raises error."""
        service = ContentService()
        
        module = Module(
            module_id="mod_test123",
            topic_name="Test",
            estimated_hours=1.0,
            prerequisites=[],
            order=1
        )
        
        with pytest.raises(ValueError) as exc_info:
            service.generate_notes(module, "")
        
        assert "too short or empty" in str(exc_info.value).lower()
    
    @patch('app.services.content_service.LLMService')
    def test_generate_notes_llm_failure_propagates(self, mock_llm_class):
        """Test that LLM failures are propagated."""
        mock_llm = Mock()
        mock_llm.generate_notes_llm.side_effect = RuntimeError("LLM service unavailable")
        mock_llm_class.return_value = mock_llm
        
        service = ContentService(llm_service=mock_llm)
        
        module = Module(
            module_id="mod_test123",
            topic_name="Test",
            estimated_hours=1.0,
            prerequisites=[],
            order=1
        )
        
        with pytest.raises(RuntimeError) as exc_info:
            service.generate_notes(module, "Test content")
        
        assert "LLM service unavailable" in str(exc_info.value)


class TestCheatSheetGeneration:
    """Test cheat sheet generation functionality."""
    
    @patch('app.services.content_service.LLMService')
    def test_generate_cheat_sheet_success(self, mock_llm_class):
        """Test successful cheat sheet generation."""
        # Setup mock LLM service
        mock_llm = Mock()
        mock_llm.generate_cheatsheet_llm.return_value = "Quick reference: variables, loops, functions"
        mock_llm_class.return_value = mock_llm
        
        service = ContentService(llm_service=mock_llm)
        
        # Create test module
        module = Module(
            module_id="mod_test123",
            topic_name="Python Basics",
            estimated_hours=5.0,
            prerequisites=[],
            order=1
        )
        
        # Generate cheat sheet
        cheat_sheet = service.generate_cheat_sheet(
            module=module,
            input_text="Python is a programming language..."
        )
        
        # Verify results
        assert cheat_sheet == "Quick reference: variables, loops, functions"
        assert len(cheat_sheet) > 0
        
        # Verify LLM was called correctly
        mock_llm.generate_cheatsheet_llm.assert_called_once()
        call_args = mock_llm.generate_cheatsheet_llm.call_args
        assert call_args[1]["module_info"]["topic_name"] == "Python Basics"
    
    @patch('app.services.content_service.LLMService')
    def test_generate_cheat_sheet_sanitizes_output(self, mock_llm_class):
        """Test that generated cheat sheet is sanitized."""
        # Setup mock LLM service with unsafe content
        mock_llm = Mock()
        mock_llm.generate_cheatsheet_llm.return_value = "Cheat sheet <style>body{}</style> content"
        mock_llm_class.return_value = mock_llm
        
        service = ContentService(llm_service=mock_llm)
        
        module = Module(
            module_id="mod_test123",
            topic_name="Test",
            estimated_hours=1.0,
            prerequisites=[],
            order=1
        )
        
        cheat_sheet = service.generate_cheat_sheet(module, "Test content")
        
        # Verify style tag was removed
        assert "<style>" not in cheat_sheet.lower()
        assert "Cheat sheet" in cheat_sheet
        assert "content" in cheat_sheet
    
    def test_generate_cheat_sheet_invalid_module_raises_error(self):
        """Test that invalid module raises error."""
        service = ContentService()
        
        with pytest.raises(ValueError) as exc_info:
            service.generate_cheat_sheet(None, "Test content")
        
        assert "invalid module" in str(exc_info.value).lower()
    
    def test_generate_cheat_sheet_empty_input_raises_error(self):
        """Test that empty input raises error."""
        service = ContentService()
        
        module = Module(
            module_id="mod_test123",
            topic_name="Test",
            estimated_hours=1.0,
            prerequisites=[],
            order=1
        )
        
        with pytest.raises(ValueError) as exc_info:
            service.generate_cheat_sheet(module, "")
        
        assert "too short or empty" in str(exc_info.value).lower()
    
    @patch('app.services.content_service.LLMService')
    def test_generate_cheat_sheet_llm_failure_propagates(self, mock_llm_class):
        """Test that LLM failures are propagated."""
        mock_llm = Mock()
        mock_llm.generate_cheatsheet_llm.side_effect = RuntimeError("LLM service unavailable")
        mock_llm_class.return_value = mock_llm
        
        service = ContentService(llm_service=mock_llm)
        
        module = Module(
            module_id="mod_test123",
            topic_name="Test",
            estimated_hours=1.0,
            prerequisites=[],
            order=1
        )
        
        with pytest.raises(RuntimeError) as exc_info:
            service.generate_cheat_sheet(module, "Test content")
        
        assert "LLM service unavailable" in str(exc_info.value)
