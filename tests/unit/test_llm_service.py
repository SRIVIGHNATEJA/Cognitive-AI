"""
Unit tests for LLM service.
Tests Ollama integration, roadmap generation, validation, and error handling.
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
import httpx

from app.services.llm_service import LLMService, LLMServiceError


@pytest.fixture
def llm_service():
    """Create an LLM service instance for testing."""
    return LLMService(
        base_url="http://localhost:11434",
        model="qwen2.5:1.5b",
        timeout=120
    )


@pytest.fixture
def sample_input_text():
    """Sample educational input text."""
    return """
    Course: Introduction to Python Programming
    
    Week 1: Python Basics
    - Variables and data types
    - Control structures
    
    Week 2: Functions and Modules
    - Defining functions
    - Importing modules
    
    Week 3: Data Structures
    - Lists and tuples
    - Dictionaries and sets
    """


@pytest.fixture
def valid_roadmap_response():
    """Valid roadmap JSON response."""
    return {
        "modules": [
            {
                "topic_name": "Python Basics",
                "estimated_hours": 5.0,
                "prerequisites": [],
                "order": 1
            },
            {
                "topic_name": "Functions and Modules",
                "estimated_hours": 6.0,
                "prerequisites": ["Python Basics"],
                "order": 2
            },
            {
                "topic_name": "Data Structures",
                "estimated_hours": 8.0,
                "prerequisites": ["Python Basics"],
                "order": 3
            }
        ]
    }


class TestLLMServiceInitialization:
    """Tests for LLM service initialization."""
    
    def test_service_initialization_with_defaults(self):
        """Test service initializes with default settings."""
        service = LLMService()
        
        assert service.base_url is not None
        assert service.model is not None
        assert service.timeout > 0
    
    def test_service_initialization_with_custom_values(self):
        """Test service initializes with custom values."""
        service = LLMService(
            base_url="http://custom:8080",
            model="custom-model",
            timeout=60
        )
        
        assert service.base_url == "http://custom:8080"
        assert service.model == "custom-model"
        assert service.timeout == 60


class TestOllamaAvailability:
    """Tests for Ollama service availability checking."""
    
    @patch('httpx.Client')
    def test_ollama_available(self, mock_client, llm_service):
        """Test detection when Ollama is available."""
        mock_response = Mock()
        mock_response.status_code = 200
        
        mock_client_instance = MagicMock()
        mock_client_instance.__enter__.return_value.get.return_value = mock_response
        mock_client.return_value = mock_client_instance
        
        is_available = llm_service._check_ollama_availability()
        
        assert is_available is True
    
    @patch('httpx.Client')
    def test_ollama_unavailable(self, mock_client, llm_service):
        """Test detection when Ollama is unavailable."""
        mock_client_instance = MagicMock()
        mock_client_instance.__enter__.return_value.get.side_effect = httpx.ConnectError("Connection failed")
        mock_client.return_value = mock_client_instance
        
        is_available = llm_service._check_ollama_availability()
        
        assert is_available is False


class TestLLMJSONOutput:
    """
    Unit test 24: LLM JSON Output
    Validates: Requirements 8.3
    """
    
    @patch.object(LLMService, '_check_ollama_availability')
    @patch.object(LLMService, '_call_ollama')
    def test_llm_generates_valid_json(
        self,
        mock_call_ollama,
        mock_check_availability,
        llm_service,
        sample_input_text,
        valid_roadmap_response
    ):
        """Test that LLM generates valid JSON output."""
        # Mock Ollama availability
        mock_check_availability.return_value = True
        
        # Mock Ollama response with valid JSON
        mock_call_ollama.return_value = {
            "response": json.dumps(valid_roadmap_response)
        }
        
        # Generate roadmap without strict topic checking for this test
        with patch('app.services.llm_service.validate_roadmap_output') as mock_validate:
            mock_validate.return_value = (True, "")
            
            # Generate roadmap
            result = llm_service.generate_roadmap_llm(sample_input_text)
            
            # Verify result is valid JSON structure
            assert isinstance(result, dict)
            assert "modules" in result
            assert isinstance(result["modules"], list)
            assert len(result["modules"]) > 0
            
            # Verify each module has required fields
            for module in result["modules"]:
                assert "topic_name" in module
                assert "estimated_hours" in module
                assert "order" in module
                assert isinstance(module["topic_name"], str)
                assert isinstance(module["estimated_hours"], (int, float))
                assert isinstance(module["order"], int)


class TestRoadmapGeneration:
    """Tests for roadmap generation with mocked Ollama."""
    
    @patch.object(LLMService, '_check_ollama_availability')
    @patch.object(LLMService, '_call_ollama')
    def test_successful_generation_with_mocked_ollama(
        self,
        mock_call_ollama,
        mock_check_availability,
        llm_service,
        sample_input_text,
        valid_roadmap_response
    ):
        """Test successful roadmap generation with mocked Ollama."""
        mock_check_availability.return_value = True
        mock_call_ollama.return_value = {
            "response": json.dumps(valid_roadmap_response)
        }
        
        # Mock validation to pass for this test
        with patch('app.services.llm_service.validate_roadmap_output') as mock_validate:
            mock_validate.return_value = (True, "")
            
            result = llm_service.generate_roadmap_llm(sample_input_text)
            
            assert result == valid_roadmap_response
            assert len(result["modules"]) == 3
    
    @patch.object(LLMService, '_check_ollama_availability')
    @patch.object(LLMService, '_call_ollama')
    def test_schema_validation_integration(
        self,
        mock_call_ollama,
        mock_check_availability,
        llm_service,
        sample_input_text
    ):
        """Test that schema validation is integrated into generation."""
        mock_check_availability.return_value = True
        
        # Mock invalid response (missing required field)
        invalid_response = {
            "modules": [
                {
                    "topic_name": "Python Basics",
                    # Missing estimated_hours
                    "order": 1
                }
            ]
        }
        
        mock_call_ollama.return_value = {
            "response": json.dumps(invalid_response)
        }
        
        # Should fail validation and raise error after retries
        with pytest.raises(LLMServiceError, match="Failed to generate valid roadmap"):
            llm_service.generate_roadmap_llm(sample_input_text, max_retries=1)
    
    @patch.object(LLMService, '_check_ollama_availability')
    @patch.object(LLMService, '_call_ollama')
    def test_retry_logic_on_validation_failure(
        self,
        mock_call_ollama,
        mock_check_availability,
        llm_service,
        sample_input_text,
        valid_roadmap_response
    ):
        """Test retry logic when validation fails."""
        mock_check_availability.return_value = True
        
        # First call returns invalid, second call returns valid
        invalid_response = {"modules": []}  # Empty modules fails validation
        
        mock_call_ollama.side_effect = [
            {"response": json.dumps(invalid_response)},
            {"response": json.dumps(valid_roadmap_response)}
        ]
        
        # Mock validation: first fails, second succeeds
        with patch('app.services.llm_service.validate_roadmap_output') as mock_validate:
            mock_validate.side_effect = [
                (False, "Empty modules"),
                (True, "")
            ]
            
            result = llm_service.generate_roadmap_llm(sample_input_text, max_retries=2)
            
            # Should succeed on second attempt
            assert result == valid_roadmap_response
            assert mock_call_ollama.call_count == 2


class TestErrorHandling:
    """Tests for error handling scenarios."""
    
    @patch.object(LLMService, '_check_ollama_availability')
    def test_service_unavailable_error(
        self,
        mock_check_availability,
        llm_service,
        sample_input_text
    ):
        """Test error when Ollama service is unavailable."""
        mock_check_availability.return_value = False
        
        with pytest.raises(LLMServiceError, match="Ollama service is not available"):
            llm_service.generate_roadmap_llm(sample_input_text)
    
    @patch('httpx.Client')
    def test_timeout_handling(self, mock_client, llm_service):
        """Test handling of timeout errors."""
        mock_client_instance = MagicMock()
        mock_client_instance.__enter__.return_value.post.side_effect = httpx.TimeoutException("Timeout")
        mock_client.return_value = mock_client_instance
        
        with pytest.raises(LLMServiceError, match="timed out"):
            llm_service._call_ollama("test prompt")
    
    @patch('httpx.Client')
    def test_connection_error_handling(self, mock_client, llm_service):
        """Test handling of connection errors."""
        mock_client_instance = MagicMock()
        mock_client_instance.__enter__.return_value.post.side_effect = httpx.ConnectError("Cannot connect")
        mock_client.return_value = mock_client_instance
        
        with pytest.raises(LLMServiceError, match="Cannot connect"):
            llm_service._call_ollama("test prompt")
    
    @patch('httpx.Client')
    def test_http_error_handling(self, mock_client, llm_service):
        """Test handling of HTTP errors."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Server error",
            request=Mock(),
            response=mock_response
        )
        
        mock_client_instance = MagicMock()
        mock_client_instance.__enter__.return_value.post.return_value = mock_response
        mock_client.return_value = mock_client_instance
        
        with pytest.raises(LLMServiceError, match="error status"):
            llm_service._call_ollama("test prompt")
    
    @patch.object(LLMService, '_check_ollama_availability')
    @patch.object(LLMService, '_call_ollama')
    def test_empty_response_handling(
        self,
        mock_call_ollama,
        mock_check_availability,
        llm_service,
        sample_input_text
    ):
        """Test handling of empty LLM responses."""
        mock_check_availability.return_value = True
        mock_call_ollama.return_value = {"response": ""}
        
        with pytest.raises(LLMServiceError, match="empty response"):
            llm_service.generate_roadmap_llm(sample_input_text, max_retries=0)
    
    @patch.object(LLMService, '_check_ollama_availability')
    @patch.object(LLMService, '_call_ollama')
    def test_invalid_json_handling(
        self,
        mock_call_ollama,
        mock_check_availability,
        llm_service,
        sample_input_text
    ):
        """Test handling of invalid JSON responses."""
        mock_check_availability.return_value = True
        mock_call_ollama.return_value = {"response": "not valid json {"}
        
        with pytest.raises(LLMServiceError, match="Failed to generate valid roadmap"):
            llm_service.generate_roadmap_llm(sample_input_text, max_retries=1)


class TestPromptBuilding:
    """Tests for prompt construction."""
    
    def test_prompt_includes_input_text(self, llm_service):
        """Test that prompt includes the input text."""
        input_text = "Sample educational content"
        allowed_topics = ["sample", "educational"]
        
        prompt = llm_service._build_roadmap_prompt(input_text, "timed", allowed_topics)
        
        assert "Sample educational content" in prompt
    
    def test_prompt_includes_mode(self, llm_service):
        """Test that prompt includes the learning mode."""
        input_text = "Sample content"
        allowed_topics = []
        
        prompt = llm_service._build_roadmap_prompt(input_text, "untimed", allowed_topics)
        
        assert "untimed" in prompt.lower()
    
    def test_prompt_truncates_long_input(self, llm_service):
        """Test that very long input is truncated."""
        long_input = "A" * 5000
        allowed_topics = []
        
        prompt = llm_service._build_roadmap_prompt(long_input, "timed", allowed_topics)
        
        # Prompt should not contain all 5000 characters
        assert len(prompt) < 5000 + 1000  # Some buffer for prompt template
