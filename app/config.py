"""
Configuration module for the Cognitive AI Learning Platform.
Manages application settings using Pydantic Settings.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    """
    Application settings with environment variable support.
    
    All settings can be overridden via environment variables.
    Example: APP_NAME="My App" python main.py
    """
    
    # Application Settings
    app_name: str = "Cognitive AI Learning Platform"
    app_version: str = "1.0.0"
    debug: bool = False
    
    # Server Settings
    host: str = "0.0.0.0"
    port: int = 8000
    
    # LLM Settings
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:1.5b"
    llm_temperature: float = 0.1
    llm_timeout: int = 120  # seconds
    llm_num_predict: int = 8192  # Maximum output tokens (ensures complete JSON generation)
    
    # File Upload Settings
    max_file_size_mb: int = 10
    supported_file_formats: list[str] = [".pdf", ".ppt", ".pptx", ".doc", ".docx"]
    min_extracted_text_length: int = 20
    
    # Cache Settings
    cache_dir: str = "cache"
    
    # Quiz Settings
    quiz_questions_count: int = 5  # Optimized for small models (qwen2.5:1.5b)
    quiz_options_count: int = 4
    quiz_explanation_max_length: int = 200
    quiz_history_retention: int = 2  # Keep last 2 quizzes Q&A
    
    # Analytics Settings
    weak_area_threshold: float = 60.0  # Percentage
    
    # Logging Settings
    log_level: str = "INFO"
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        env_prefix="APP_"
    )


# Global settings instance
settings = Settings()
