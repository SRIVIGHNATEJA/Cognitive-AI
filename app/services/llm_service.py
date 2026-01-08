"""
LLM service for interfacing with Ollama.

Provides isolated LLM integration with structured output validation,
retry logic, and error handling.
"""

import json
import httpx
from typing import Dict, Any, List, Optional
from datetime import datetime

from app.config import settings
from app.logging_config import get_logger
from app.services.llm_schemas import (
    extract_allowed_topics,
    validate_roadmap_output,
    get_roadmap_schema_prompt,
    get_topic_constraint_prompt,
    get_forbidden_domains_prompt
)

logger = get_logger(__name__)


class LLMServiceError(Exception):
    """Exception raised when LLM service operations fail."""
    pass


class LLMService:
    """
    Service for interacting with Ollama LLM.
    
    Provides methods for generating structured outputs with validation,
    retry logic, and comprehensive error handling.
    """
    
    def __init__(
        self,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: Optional[int] = None
    ):
        """
        Initialize the LLM service.
        
        Args:
            base_url: Ollama service URL (defaults to settings)
            model: Model name to use (defaults to settings)
            timeout: Request timeout in seconds (defaults to settings)
        """
        self.base_url = base_url or settings.ollama_base_url
        self.model = model or settings.ollama_model
        self.timeout = timeout or settings.llm_timeout
        
        logger.info(f"LLM Service initialized: {self.base_url}, model: {self.model}")
    
    def _check_ollama_availability(self) -> bool:
        """
        Check if Ollama service is available.
        
        Returns:
            True if service is available, False otherwise
        """
        try:
            with httpx.Client(timeout=5.0) as client:
                response = client.get(f"{self.base_url}/api/tags")
                return response.status_code == 200
        except Exception as e:
            logger.error(f"Ollama availability check failed: {str(e)}")
            return False
    
    def _call_ollama(
        self,
        prompt: str,
        temperature: float = None,
        format_json: bool = True
    ) -> Dict[str, Any]:
        """
        Make a request to Ollama API.
        
        Args:
            prompt: The prompt to send to the LLM
            temperature: Temperature for generation (defaults to settings)
            format_json: Whether to request JSON format output
            
        Returns:
            Response dictionary from Ollama
            
        Raises:
            LLMServiceError: If the request fails
        """
        if temperature is None:
            temperature = settings.llm_temperature
        
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature
            }
        }
        
        if format_json:
            payload["format"] = "json"
        
        try:
            with httpx.Client(timeout=self.timeout) as client:
                logger.debug(f"Calling Ollama API with model: {self.model}")
                
                response = client.post(
                    f"{self.base_url}/api/generate",
                    json=payload
                )
                
                response.raise_for_status()
                result = response.json()
                
                logger.debug(f"Ollama API call successful")
                return result
                
        except httpx.TimeoutException as e:
            error_msg = f"Ollama request timed out after {self.timeout} seconds"
            logger.error(error_msg)
            raise LLMServiceError(error_msg) from e
        
        except httpx.HTTPStatusError as e:
            error_msg = f"Ollama API returned error status: {e.response.status_code}"
            logger.error(error_msg)
            raise LLMServiceError(error_msg) from e
        
        except httpx.ConnectError as e:
            error_msg = f"Cannot connect to Ollama service at {self.base_url}"
            logger.error(error_msg)
            raise LLMServiceError(error_msg) from e
        
        except Exception as e:
            error_msg = f"Unexpected error calling Ollama: {str(e)}"
            logger.error(error_msg)
            raise LLMServiceError(error_msg) from e
    
    def generate_roadmap_llm(
        self,
        input_text: str,
        mode: str = "timed",
        max_retries: int = 2
    ) -> Dict[str, Any]:
        """
        Generate a learning roadmap using the LLM.
        
        Includes output validation and retry logic to ensure valid,
        on-topic roadmap generation.
        
        Args:
            input_text: The educational content to generate roadmap from
            mode: Learning mode ("timed" or "untimed")
            max_retries: Maximum number of retry attempts on validation failure
            
        Returns:
            Validated roadmap dictionary with modules
            
        Raises:
            LLMServiceError: If generation fails or validation fails after retries
        """
        logger.info(f"Generating roadmap for {len(input_text)} characters of input")
        
        # Check Ollama availability
        if not self._check_ollama_availability():
            raise LLMServiceError(
                "Ollama service is not available. Please ensure Ollama is running "
                f"at {self.base_url}"
            )
        
        # Extract allowed topics from input
        allowed_topics = extract_allowed_topics(input_text)
        logger.info(f"Extracted {len(allowed_topics)} allowed topics")
        
        # Build the prompt
        prompt = self._build_roadmap_prompt(input_text, mode, allowed_topics)
        
        # Attempt generation with retries
        last_error = None
        for attempt in range(max_retries + 1):
            try:
                logger.info(f"Roadmap generation attempt {attempt + 1}/{max_retries + 1}")
                
                # Call Ollama
                response = self._call_ollama(prompt, format_json=True)
                
                # Extract the generated text
                generated_text = response.get("response", "")
                
                if not generated_text:
                    raise LLMServiceError("Ollama returned empty response")
                
                # Parse JSON
                try:
                    roadmap_data = json.loads(generated_text)
                except json.JSONDecodeError as e:
                    error_msg = f"Failed to parse LLM output as JSON: {str(e)}"
                    logger.warning(error_msg)
                    last_error = error_msg
                    continue
                
                # Validate the output
                is_valid, error_msg = validate_roadmap_output(
                    roadmap_data,
                    allowed_topics=allowed_topics,
                    strict_topic_check=True
                )
                
                if is_valid:
                    logger.info(f"Roadmap generation successful on attempt {attempt + 1}")
                    return roadmap_data
                else:
                    logger.warning(f"Validation failed: {error_msg}")
                    last_error = error_msg
                    
                    # If not the last attempt, continue to retry
                    if attempt < max_retries:
                        logger.info("Retrying roadmap generation...")
                        continue
                
            except LLMServiceError:
                # Re-raise LLM service errors immediately (no retry)
                raise
            
            except Exception as e:
                error_msg = f"Unexpected error during generation: {str(e)}"
                logger.error(error_msg)
                last_error = error_msg
                
                if attempt < max_retries:
                    continue
        
        # All retries exhausted
        raise LLMServiceError(
            f"Failed to generate valid roadmap after {max_retries + 1} attempts. "
            f"Last error: {last_error}"
        )
    
    def _build_roadmap_prompt(
        self,
        input_text: str,
        mode: str,
        allowed_topics: List[str]
    ) -> str:
        """
        Build the complete prompt for roadmap generation.
        
        Args:
            input_text: The educational content
            mode: Learning mode
            allowed_topics: List of allowed topics
            
        Returns:
            Complete prompt string
        """
        # Truncate input text if too long (keep first 3000 chars)
        truncated_input = input_text[:3000] if len(input_text) > 3000 else input_text
        
        prompt = f"""You are an expert educational content analyzer and curriculum designer.

Based on the following educational material, generate a structured learning roadmap.

EDUCATIONAL MATERIAL:
{truncated_input}

LEARNING MODE: {mode}

{get_roadmap_schema_prompt()}

{get_topic_constraint_prompt(allowed_topics)}

{get_forbidden_domains_prompt()}

IMPORTANT INSTRUCTIONS:
- Analyze the provided material carefully
- Create a logical progression of topics
- Ensure prerequisites are correctly identified
- Estimate realistic learning hours for each module
- Number modules sequentially starting from 1
- Output ONLY valid JSON, no additional text
- Stay strictly within the subject matter of the provided material

Generate the roadmap now:"""
        
        return prompt
    
    def generate_notes_llm(
        self,
        module_info: Dict[str, Any],
        content: str
    ) -> str:
        """
        Generate detailed notes for a module using the LLM.
        
        Args:
            module_info: Dictionary with module details (topic_name, estimated_hours, etc.)
            content: The source educational content
            
        Returns:
            Generated notes as a string
            
        Raises:
            LLMServiceError: If generation fails
        """
        logger.info(f"Generating notes for module: {module_info.get('topic_name', 'Unknown')}")
        
        # Check Ollama availability
        if not self._check_ollama_availability():
            raise LLMServiceError(
                "Ollama service is not available. Please ensure Ollama is running "
                f"at {self.base_url}"
            )
        
        # Build the prompt
        prompt = self._build_notes_prompt(module_info, content)
        
        try:
            # Call Ollama (no JSON format for notes)
            response = self._call_ollama(prompt, format_json=False)
            
            # Extract the generated text
            notes = response.get("response", "")
            
            if not notes:
                raise LLMServiceError("Ollama returned empty notes")
            
            logger.info(f"Notes generation successful ({len(notes)} characters)")
            return notes.strip()
            
        except LLMServiceError:
            raise
        except Exception as e:
            error_msg = f"Unexpected error generating notes: {str(e)}"
            logger.error(error_msg)
            raise LLMServiceError(error_msg) from e
    
    def generate_cheatsheet_llm(
        self,
        module_info: Dict[str, Any],
        content: str
    ) -> str:
        """
        Generate a concise cheat sheet for a module using the LLM.
        
        Args:
            module_info: Dictionary with module details (topic_name, estimated_hours, etc.)
            content: The source educational content
            
        Returns:
            Generated cheat sheet as a string
            
        Raises:
            LLMServiceError: If generation fails
        """
        logger.info(f"Generating cheat sheet for module: {module_info.get('topic_name', 'Unknown')}")
        
        # Check Ollama availability
        if not self._check_ollama_availability():
            raise LLMServiceError(
                "Ollama service is not available. Please ensure Ollama is running "
                f"at {self.base_url}"
            )
        
        # Build the prompt
        prompt = self._build_cheatsheet_prompt(module_info, content)
        
        try:
            # Call Ollama (no JSON format for cheat sheet)
            response = self._call_ollama(prompt, format_json=False)
            
            # Extract the generated text
            cheat_sheet = response.get("response", "")
            
            if not cheat_sheet:
                raise LLMServiceError("Ollama returned empty cheat sheet")
            
            logger.info(f"Cheat sheet generation successful ({len(cheat_sheet)} characters)")
            return cheat_sheet.strip()
            
        except LLMServiceError:
            raise
        except Exception as e:
            error_msg = f"Unexpected error generating cheat sheet: {str(e)}"
            logger.error(error_msg)
            raise LLMServiceError(error_msg) from e
    
    def _build_notes_prompt(
        self,
        module_info: Dict[str, Any],
        content: str
    ) -> str:
        """
        Build the prompt for notes generation.
        
        Args:
            module_info: Module details
            content: Source educational content
            
        Returns:
            Complete prompt string
        """
        topic_name = module_info.get('topic_name', 'Unknown Topic')
        estimated_hours = module_info.get('estimated_hours', 0)
        
        # Truncate content if too long
        truncated_content = content[:3000] if len(content) > 3000 else content
        
        prompt = f"""You are an expert educator creating detailed study notes.

Generate comprehensive, well-structured notes for the following topic:

TOPIC: {topic_name}
ESTIMATED STUDY TIME: {estimated_hours} hours

SOURCE MATERIAL:
{truncated_content}

INSTRUCTIONS:
- Create detailed, easy-to-understand notes
- Include key concepts, definitions, and explanations
- Use clear headings and bullet points for organization
- Include examples where appropriate
- Focus on the most important information
- Make the notes suitable for self-study
- Keep the content educational and appropriate
- Format for readability (use markdown-style formatting if helpful)

Generate the detailed notes now:"""
        
        return prompt
    
    def _build_cheatsheet_prompt(
        self,
        module_info: Dict[str, Any],
        content: str
    ) -> str:
        """
        Build the prompt for cheat sheet generation.
        
        Args:
            module_info: Module details
            content: Source educational content
            
        Returns:
            Complete prompt string
        """
        topic_name = module_info.get('topic_name', 'Unknown Topic')
        
        # Truncate content if too long
        truncated_content = content[:3000] if len(content) > 3000 else content
        
        prompt = f"""You are an expert educator creating a concise cheat sheet.

Generate a quick-reference cheat sheet for the following topic:

TOPIC: {topic_name}

SOURCE MATERIAL:
{truncated_content}

INSTRUCTIONS:
- Create a concise, one-page cheat sheet
- Include only the most essential information
- Use bullet points and short phrases
- Focus on key terms, formulas, and concepts
- Make it perfect for quick review before exams
- Keep it brief but comprehensive
- Format for easy scanning (use clear sections)
- Avoid lengthy explanations

Generate the cheat sheet now:"""
        
        return prompt
    
    def generate_quiz_llm(
        self,
        module_info: Dict[str, Any],
        content: str,
        max_retries: int = 2
    ) -> List[Dict[str, Any]]:
        """
        Generate a quiz with exactly 10 MCQs for a module using the LLM.
        
        Each question must have:
        - Exactly 4 options
        - One correct answer
        - A brief explanation (max 200 characters)
        
        Args:
            module_info: Dictionary with module details (topic_name, etc.)
            content: The source educational content
            max_retries: Maximum number of retry attempts on validation failure
            
        Returns:
            List of 10 quiz question dictionaries
            
        Raises:
            LLMServiceError: If generation fails or validation fails after retries
        """
        logger.info(f"Generating quiz for module: {module_info.get('topic_name', 'Unknown')}")
        
        # Check Ollama availability
        if not self._check_ollama_availability():
            raise LLMServiceError(
                "Ollama service is not available. Please ensure Ollama is running "
                f"at {self.base_url}"
            )
        
        # Build the prompt
        prompt = self._build_quiz_prompt(module_info, content)
        
        # Attempt generation with retries
        last_error = None
        for attempt in range(max_retries + 1):
            try:
                logger.info(f"Quiz generation attempt {attempt + 1}/{max_retries + 1}")
                
                # Call Ollama with JSON format
                response = self._call_ollama(prompt, format_json=True)
                
                # Extract the generated text
                generated_text = response.get("response", "")
                
                if not generated_text:
                    raise LLMServiceError("Ollama returned empty response")
                
                # Parse JSON
                try:
                    quiz_data = json.loads(generated_text)
                except json.JSONDecodeError as e:
                    error_msg = f"Failed to parse quiz output as JSON: {str(e)}"
                    logger.warning(error_msg)
                    last_error = error_msg
                    continue
                
                # Validate the quiz structure
                is_valid, error_msg = self._validate_quiz_structure(quiz_data)
                
                if is_valid:
                    logger.info(f"Quiz generation successful on attempt {attempt + 1}")
                    return quiz_data.get("questions", [])
                else:
                    logger.warning(f"Quiz validation failed: {error_msg}")
                    last_error = error_msg
                    
                    # If not the last attempt, continue to retry
                    if attempt < max_retries:
                        logger.info("Retrying quiz generation...")
                        continue
                
            except LLMServiceError:
                # Re-raise LLM service errors immediately (no retry)
                raise
            
            except Exception as e:
                error_msg = f"Unexpected error during quiz generation: {str(e)}"
                logger.error(error_msg)
                last_error = error_msg
                
                if attempt < max_retries:
                    continue
        
        # All retries exhausted
        raise LLMServiceError(
            f"Failed to generate valid quiz after {max_retries + 1} attempts. "
            f"Last error: {last_error}"
        )
    
    def _build_quiz_prompt(
        self,
        module_info: Dict[str, Any],
        content: str
    ) -> str:
        """
        Build the prompt for quiz generation with strict format requirements.
        
        Args:
            module_info: Module details
            content: Source educational content
            
        Returns:
            Complete prompt string
        """
        topic_name = module_info.get('topic_name', 'Unknown Topic')
        
        # Truncate content if too long
        truncated_content = content[:3000] if len(content) > 3000 else content
        
        prompt = f"""You are an expert educator creating a multiple-choice quiz.

Generate a quiz for the following topic:

TOPIC: {topic_name}

SOURCE MATERIAL:
{truncated_content}

STRICT REQUIREMENTS:
1. Generate EXACTLY 10 multiple-choice questions
2. Each question MUST have EXACTLY 4 options
3. Each question MUST have ONE correct answer
4. Each question MUST have a brief explanation (maximum 200 characters)
5. Questions should cover the key concepts from the material
6. Options should be plausible but clearly distinguishable
7. Number questions from 1 to 10

OUTPUT FORMAT (JSON):
{{
  "questions": [
    {{
      "question_number": 1,
      "question_text": "What is...?",
      "options": ["Option A", "Option B", "Option C", "Option D"],
      "correct_answer": "Option B",
      "explanation": "Brief explanation here (max 200 chars)"
    }},
    ... (repeat for all 10 questions)
  ]
}}

CRITICAL RULES:
- Output ONLY valid JSON, no additional text
- Ensure correct_answer matches one of the 4 options EXACTLY
- Keep explanations under 200 characters
- Make questions clear and unambiguous
- Ensure all 10 questions are included
- Questions should test understanding, not just memorization

Generate the quiz now:"""
        
        return prompt
    
    def _validate_quiz_structure(self, quiz_data: Dict[str, Any]) -> tuple[bool, str]:
        """
        Validate that the quiz data meets all structural requirements.
        
        Args:
            quiz_data: The quiz data to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check if questions key exists
        if "questions" not in quiz_data:
            return False, "Missing 'questions' key in quiz data"
        
        questions = quiz_data["questions"]
        
        # Check if it's a list
        if not isinstance(questions, list):
            return False, "'questions' must be a list"
        
        # Check exactly 10 questions
        if len(questions) != 10:
            return False, f"Expected exactly 10 questions, got {len(questions)}"
        
        # Validate each question
        for i, question in enumerate(questions, 1):
            # Check required fields
            required_fields = ["question_number", "question_text", "options", "correct_answer", "explanation"]
            for field in required_fields:
                if field not in question:
                    return False, f"Question {i} missing required field: {field}"
            
            # Check question number
            if question["question_number"] != i:
                return False, f"Question {i} has incorrect question_number: {question['question_number']}"
            
            # Check question text is not empty
            if not question["question_text"] or len(question["question_text"]) < 10:
                return False, f"Question {i} has invalid question_text (must be at least 10 characters)"
            
            # Check exactly 4 options
            options = question["options"]
            if not isinstance(options, list) or len(options) != 4:
                return False, f"Question {i} must have exactly 4 options, got {len(options) if isinstance(options, list) else 'invalid'}"
            
            # Check all options are non-empty strings
            for j, option in enumerate(options, 1):
                if not isinstance(option, str) or not option.strip():
                    return False, f"Question {i}, option {j} is invalid"
            
            # Check correct answer is one of the options
            correct_answer = question["correct_answer"]
            if correct_answer not in options:
                return False, f"Question {i} correct_answer '{correct_answer}' not in options"
            
            # Check explanation length
            explanation = question["explanation"]
            if not isinstance(explanation, str) or len(explanation) > 200:
                return False, f"Question {i} explanation must be a string with max 200 characters, got {len(explanation) if isinstance(explanation, str) else 'invalid'}"
            
            if not explanation.strip():
                return False, f"Question {i} explanation cannot be empty"
        
        return True, ""
    
    def answer_question_llm(
        self,
        module_info: Dict[str, Any],
        question: str,
        module_content: str
    ) -> Dict[str, Any]:
        """
        Answer a user's question about a module using context-aware LLM.
        
        The LLM will:
        - Use module content as context
        - Determine if question is within scope
        - Provide a helpful answer if in scope
        - Politely decline if out of scope
        
        Args:
            module_info: Dictionary with module details (topic_name, etc.)
            question: User's question
            module_content: Module notes/content for context
            
        Returns:
            Dictionary with 'answer' and 'in_scope' keys
            
        Raises:
            LLMServiceError: If generation fails
        """
        logger.info(f"Answering question for module: {module_info.get('topic_name', 'Unknown')}")
        
        # Check Ollama availability
        if not self._check_ollama_availability():
            raise LLMServiceError(
                "Ollama service is not available. Please ensure Ollama is running "
                f"at {self.base_url}"
            )
        
        # Build the prompt
        prompt = self._build_question_answer_prompt(module_info, question, module_content)
        
        try:
            # Call Ollama with JSON format
            response = self._call_ollama(prompt, format_json=True)
            
            # Extract the generated text
            generated_text = response.get("response", "")
            
            if not generated_text:
                raise LLMServiceError("Ollama returned empty response")
            
            # Parse JSON
            try:
                answer_data = json.loads(generated_text)
            except json.JSONDecodeError as e:
                error_msg = f"Failed to parse answer output as JSON: {str(e)}"
                logger.error(error_msg)
                raise LLMServiceError(error_msg) from e
            
            # Validate response structure
            if "answer" not in answer_data or "in_scope" not in answer_data:
                raise LLMServiceError("Invalid answer format: missing required fields")
            
            logger.info(f"Question answered successfully (in_scope: {answer_data.get('in_scope', False)})")
            return answer_data
            
        except LLMServiceError:
            raise
        except Exception as e:
            error_msg = f"Unexpected error answering question: {str(e)}"
            logger.error(error_msg)
            raise LLMServiceError(error_msg) from e
    
    def _build_question_answer_prompt(
        self,
        module_info: Dict[str, Any],
        question: str,
        module_content: str
    ) -> str:
        """
        Build the prompt for context-aware question answering.
        
        Args:
            module_info: Module details
            question: User's question
            module_content: Module content for context
            
        Returns:
            Complete prompt string
        """
        topic_name = module_info.get('topic_name', 'Unknown Topic')
        
        # Truncate content if too long
        truncated_content = module_content[:2500] if len(module_content) > 2500 else module_content
        
        prompt = f"""You are a helpful educational assistant answering student questions.

CONTEXT - MODULE TOPIC: {topic_name}

MODULE CONTENT:
{truncated_content}

STUDENT QUESTION:
{question}

INSTRUCTIONS:
1. Determine if the question is related to the module topic and content
2. If IN SCOPE (related to the module):
   - Provide a clear, helpful answer based on the module content
   - Keep the answer concise but informative (2-4 sentences)
   - Use simple language appropriate for students
   - Set "in_scope" to true
3. If OUT OF SCOPE (unrelated to the module):
   - Politely explain that the question is outside the module scope
   - Suggest focusing on the module topic
   - Set "in_scope" to false

OUTPUT FORMAT (JSON):
{{
  "answer": "Your answer here...",
  "in_scope": true or false
}}

SCOPE RULES:
- Questions about the module topic are IN SCOPE
- Questions about related concepts mentioned in the content are IN SCOPE
- Questions about completely different topics are OUT OF SCOPE
- Questions about politics, religion, or controversial topics are OUT OF SCOPE
- Personal questions unrelated to learning are OUT OF SCOPE

Generate the response now:"""
        
        return prompt


# Global LLM service instance
llm_service = LLMService()
