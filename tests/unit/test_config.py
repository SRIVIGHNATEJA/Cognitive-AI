"""
Unit tests for configuration module.
Tests environment variable loading and default configuration values.
"""

import pytest
from app.config import Settings


def test_default_configuration_values():
    """Test that default configuration values are set correctly."""
    settings = Settings()
    
    assert settings.app_name == "Cognitive AI Learning Platform"
    assert settings.app_version == "1.0.0"
    assert settings.debug is False
    assert settings.host == "0.0.0.0"
    assert settings.port == 8000


def test_llm_configuration():
    """Test LLM-related configuration defaults."""
    settings = Settings()
    
    assert settings.ollama_base_url == "http://localhost:11434"
    assert settings.ollama_model == "qwen2.5:1.5b"
    assert settings.llm_temperature == 0.1
    assert settings.llm_timeout == 120


def test_file_upload_configuration():
    """Test file upload configuration defaults."""
    settings = Settings()
    
    assert settings.max_file_size_mb == 10
    assert ".pdf" in settings.supported_file_formats
    assert ".pptx" in settings.supported_file_formats
    assert ".docx" in settings.supported_file_formats
    assert settings.min_extracted_text_length == 100


def test_quiz_configuration():
    """Test quiz-related configuration defaults."""
    settings = Settings()
    
    assert settings.quiz_questions_count == 5
    assert settings.quiz_options_count == 4
    assert settings.quiz_explanation_max_length == 200
    assert settings.quiz_history_retention == 2


def test_cache_configuration():
    """Test cache configuration defaults."""
    settings = Settings()
    
    assert settings.cache_dir == "cache"


def test_analytics_configuration():
    """Test analytics configuration defaults."""
    settings = Settings()
    
    assert settings.weak_area_threshold == 60.0


def test_logging_configuration():
    """Test logging configuration defaults."""
    settings = Settings()
    
    assert settings.log_level == "INFO"
    assert "%(asctime)s" in settings.log_format
    assert "%(levelname)s" in settings.log_format
