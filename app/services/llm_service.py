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
    get_forbidden_domains_prompt,
    ROADMAP_SCHEMA
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
        format_json: bool = True,
        num_predict: Optional[int] = None,
        repeat_penalty: Optional[float] = None,
        format_schema: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Make a request to Ollama API.
        
        Args:
            prompt: The prompt to send to the LLM
            temperature: Temperature for generation (defaults to settings)
            format_json: Whether to request JSON format output
            num_predict: Maximum tokens to generate (optional)
            repeat_penalty: Repetition penalty (defaults to 1.15 to prevent loops)
            format_schema: Optional JSON schema / GBNF grammar for Ollama structured output
            
        Returns:
            Response dictionary from Ollama
            
        Raises:
            LLMServiceError: If the request fails
        """
        if temperature is None:
            temperature = settings.llm_temperature
        
        options = {
            "temperature": temperature,
            "repeat_penalty": repeat_penalty if repeat_penalty is not None else 1.15,
            "num_ctx": 4096,
            "num_thread": 4
        }
        if num_predict is not None:
            options["num_predict"] = num_predict
        elif format_json:
            options["num_predict"] = settings.llm_num_predict
        
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": options
        }
        
        if format_schema:
            payload["format"] = format_schema
        elif format_json:
            payload["format"] = "json"
        
        try:
            with httpx.Client(timeout=self.timeout) as client:
                logger.debug(f"Calling Ollama API with model: {self.model}")
                
                try:
                    response = client.post(
                        f"{self.base_url}/api/generate",
                        json=payload
                    )
                    response.raise_for_status()
                except httpx.HTTPStatusError as e:
                    if format_schema and e.response.status_code == 400:
                        logger.warning(
                            f"Ollama returned 400 with format_schema, falling back to format='json': {e.response.text}"
                        )
                        payload["format"] = "json"
                        response = client.post(
                            f"{self.base_url}/api/generate",
                            json=payload
                        )
                        response.raise_for_status()
                    else:
                        raise
                
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
                
                # Call Ollama with GBNF roadmap schema
                response = self._call_ollama(prompt, format_json=True, format_schema=ROADMAP_SCHEMA)
                
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
                # Note: strict_topic_check=False for roadmaps to allow semantic abstraction
                # Small models abstract concepts correctly but not lexically
                # Safety remains enforced via schema validation and forbidden domain checks
                is_valid, error_msg = validate_roadmap_output(
                    roadmap_data,
                    allowed_topics=allowed_topics,
                    strict_topic_check=False
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
            # Call Ollama (temperature=0.3 and repeat_penalty prevent SLM degeneration loops)
            response = self._call_ollama(
                prompt,
                temperature=0.3,
                format_json=False,
                num_predict=1500,
                repeat_penalty=1.15
            )
            
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
            # Call Ollama (temperature=0.3 and repeat_penalty prevent SLM degeneration loops)
            response = self._call_ollama(
                prompt,
                temperature=0.3,
                format_json=False,
                num_predict=800,
                repeat_penalty=1.15
            )
            
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
    
    def _build_shared_module_prefix(
        self,
        topic_name: str,
        truncated_content: str
    ) -> str:
        """
        Build a byte-identical ChatML prefix for module content.
        Enables Ollama KV prefix cache reuse across generation tasks.
        
        Args:
            topic_name: Name of the module topic
            truncated_content: Truncated source content (3000 chars)
            
        Returns:
            Byte-identical ChatML prefix string
        """
        return (
            "<|im_start|>system\n"
            "You are an expert educational AI assistant specialized in curriculum instruction.<|im_end|>\n"
            "<|im_start|>user\n"
            f"TOPIC: {topic_name}\n\n"
            "SOURCE MATERIAL:\n"
            f"{truncated_content}\n\n"
        )

    def _build_notes_prompt(
        self,
        module_info: Dict[str, Any],
        content: str
    ) -> str:
        """
        Build the prompt for notes generation using shared ChatML prefix.
        
        Args:
            module_info: Module details
            content: Source educational content
            
        Returns:
            Complete prompt string
        """
        topic_name = module_info.get('topic_name', 'Unknown Topic')
        estimated_hours = module_info.get('estimated_hours', 0)
        
        # Unified 3000-character content truncation for KV prefix caching
        truncated_content = content[:3000] if len(content) > 3000 else content
        prefix = self._build_shared_module_prefix(topic_name, truncated_content)
        
        instructions = f"""TASK: Generate comprehensive, well-structured study notes for this module.
ESTIMATED STUDY TIME: {estimated_hours} hours

INSTRUCTIONS:
- Create detailed, easy-to-understand notes
- Include key concepts, definitions, and explanations
- Use clear headings and bullet points for organization
- Include examples where appropriate
- Focus on the most important information
- Make the notes suitable for self-study
- Keep the content educational and appropriate
- Format for readability (use markdown-style formatting if helpful)

Generate the detailed notes now:<|im_end|>
<|im_start|>assistant
"""
        return prefix + instructions
    
    def _build_cheatsheet_prompt(
        self,
        module_info: Dict[str, Any],
        content: str
    ) -> str:
        """
        Build the prompt for cheat sheet generation using shared ChatML prefix.
        
        Args:
            module_info: Module details
            content: Source educational content
            
        Returns:
            Complete prompt string
        """
        topic_name = module_info.get('topic_name', 'Unknown Topic')
        
        # Unified 3000-character content truncation for KV prefix caching
        truncated_content = content[:3000] if len(content) > 3000 else content
        prefix = self._build_shared_module_prefix(topic_name, truncated_content)
        
        instructions = """TASK: Generate a concise quick-reference cheat sheet for this module.

INSTRUCTIONS:
- Create a concise, one-page cheat sheet
- Include only the most essential information
- Use bullet points and short phrases
- Focus on key terms, formulas, and concepts
- Make it perfect for quick review before exams
- Keep it brief but comprehensive
- Format for easy scanning (use clear sections)
- Avoid lengthy explanations

Generate the cheat sheet now:<|im_end|>
<|im_start|>assistant
"""
        return prefix + instructions
    
    def generate_quiz_llm(
        self,
        module_info: Dict[str, Any],
        content: str,
        max_retries: int = 2
    ) -> List[Dict[str, Any]]:
        """
        Generate a quiz with exactly 5 MCQs for a module using the LLM.
        
        LEGACY METHOD - Maintained for backward compatibility with old quizzes.
        New code should use generate_quiz_questions_llm() instead.
        
        Optimized for small models (qwen2.5:1.5b) with reduced question count.
        
        Each question must have:
        - Exactly 4 options
        - One correct answer
        - A brief explanation (max 200 characters)
        
        Args:
            module_info: Dictionary with module details (topic_name, etc.)
            content: The source educational content (module-scoped)
            max_retries: Maximum number of retry attempts on validation failure
            
        Returns:
            List of 5 quiz question dictionaries
            
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
                
                # Scale temperature per attempt to break greedy repetition
                # Attempt 0: 0.15 | Attempt 1: 0.35 | Attempt 2: 0.55
                current_temp = min(0.15 + (attempt * 0.2), 0.6)
                
                # Call Ollama with JSON format and dynamic jitter temperature
                response = self._call_ollama(prompt, format_json=True, temperature=current_temp)
                
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
    
    def generate_quiz_questions_llm(
        self,
        module_info: Dict[str, Any],
        content: str,
        max_retries: int = 2
    ) -> List[Dict[str, Any]]:
        """
        Generate quiz questions WITHOUT correct answers or explanations.
        
        NEW METHOD for Phase 2 - Deferred evaluation architecture.
        Generates only questions and options. Correct answers and explanations
        are generated later during evaluation via generate_quiz_answers_llm().
        
        Args:
            module_info: Dictionary with module details (topic_name, etc.)
            content: The source educational content (module-scoped)
            max_retries: Maximum number of retry attempts on validation failure
            
        Returns:
            List of 5 quiz question dictionaries (without correct_answer/explanation)
            
        Raises:
            LLMServiceError: If generation fails or validation fails after retries
        """
        logger.info(f"Generating quiz questions (no answers) for module: {module_info.get('topic_name', 'Unknown')}")
        
        # Check Ollama availability
        if not self._check_ollama_availability():
            raise LLMServiceError(
                "Ollama service is not available. Please ensure Ollama is running "
                f"at {self.base_url}"
            )
        
        # Build the prompt for questions only
        prompt = self._build_quiz_questions_prompt(module_info, content)
        
        # Attempt generation with retries
        last_error = None
        for attempt in range(max_retries + 1):
            try:
                logger.info(f"Quiz questions generation attempt {attempt + 1}/{max_retries + 1}")
                
                # Scale temperature per attempt to break greedy repetition
                # Attempt 0: 0.15 | Attempt 1: 0.35 | Attempt 2: 0.55
                current_temp = min(0.15 + (attempt * 0.2), 0.6)
                
                # Call Ollama with JSON format and dynamic jitter temperature
                response = self._call_ollama(prompt, format_json=True, temperature=current_temp)
                
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
                
                # Validate the quiz structure (questions only)
                is_valid, error_msg = self._validate_quiz_questions_structure(quiz_data)
                
                if is_valid:
                    logger.info(f"Quiz questions generation successful on attempt {attempt + 1}")
                    return quiz_data.get("questions", [])
                else:
                    logger.warning(f"Quiz questions validation failed: {error_msg}")
                    last_error = error_msg
                    
                    # If not the last attempt, continue to retry
                    if attempt < max_retries:
                        logger.info("Retrying quiz questions generation...")
                        continue
                
            except LLMServiceError:
                # Re-raise LLM service errors immediately (no retry)
                raise
            
            except Exception as e:
                error_msg = f"Unexpected error during quiz questions generation: {str(e)}"
                logger.error(error_msg)
                last_error = error_msg
                
                if attempt < max_retries:
                    continue
        
        # All retries exhausted
        raise LLMServiceError(
            f"Failed to generate valid quiz questions after {max_retries + 1} attempts. "
            f"Last error: {last_error}"
        )
    
    def generate_quiz_answers_llm(
        self,
        module_info: Dict[str, Any],
        questions: List[Dict[str, Any]],
        content: str,
        max_retries: int = 2
    ) -> List[Dict[str, Any]]:
        """
        Generate correct answers and explanations for quiz questions.
        
        NEW METHOD for Phase 2 - Deferred evaluation architecture.
        Takes questions with options and generates correct_answer and explanation
        for each question.
        
        Args:
            module_info: Dictionary with module details (topic_name, etc.)
            questions: List of question dictionaries (with question_text and options)
            content: The source educational content (module-scoped)
            max_retries: Maximum number of retry attempts on validation failure
            
        Returns:
            List of answer dictionaries with correct_answer and explanation
            
        Raises:
            LLMServiceError: If generation fails or validation fails after retries
        """
        logger.info(f"Generating quiz answers for {len(questions)} questions")
        
        # Check Ollama availability
        if not self._check_ollama_availability():
            raise LLMServiceError(
                "Ollama service is not available. Please ensure Ollama is running "
                f"at {self.base_url}"
            )
        
        # Build the prompt for answers
        prompt = self._build_quiz_answers_prompt(module_info, questions, content)
        
        # Attempt generation with retries
        last_error = None
        for attempt in range(max_retries + 1):
            try:
                logger.info(f"Quiz answers generation attempt {attempt + 1}/{max_retries + 1}")
                
                # Scale temperature per attempt to break greedy repetition
                # Attempt 0: 0.15 | Attempt 1: 0.35 | Attempt 2: 0.55
                current_temp = min(0.15 + (attempt * 0.2), 0.6)
                
                # Call Ollama with JSON format and dynamic jitter temperature
                response = self._call_ollama(prompt, format_json=True, temperature=current_temp)
                
                # Extract the generated text
                generated_text = response.get("response", "")
                
                if not generated_text:
                    raise LLMServiceError("Ollama returned empty response")
                
                # Parse JSON
                try:
                    answers_data = json.loads(generated_text)
                except json.JSONDecodeError as e:
                    error_msg = f"Failed to parse answers output as JSON: {str(e)}"
                    logger.warning(error_msg)
                    last_error = error_msg
                    continue
                
                # Validate the answers structure (allow fallback on final attempt)
                is_valid, error_msg = self._validate_quiz_answers_structure(
                    answers_data, questions, allow_fallback=(attempt == max_retries)
                )
                
                if is_valid:
                    logger.info(f"Quiz answers generation successful on attempt {attempt + 1}")
                    return answers_data.get("answers", [])
                else:
                    logger.warning(f"Quiz answers validation failed: {error_msg}")
                    last_error = error_msg
                    
                    # If not the last attempt, continue to retry
                    if attempt < max_retries:
                        logger.info("Retrying quiz answers generation...")
                        continue
                
            except LLMServiceError:
                # Re-raise LLM service errors immediately (no retry)
                raise
            
            except Exception as e:
                error_msg = f"Unexpected error during quiz answers generation: {str(e)}"
                logger.error(error_msg)
                last_error = error_msg
                
                if attempt < max_retries:
                    continue
        
        # All retries exhausted
        raise LLMServiceError(
            f"Failed to generate valid quiz answers after {max_retries + 1} attempts. "
            f"Last error: {last_error}"
        )
    
    def _build_quiz_prompt(
        self,
        module_info: Dict[str, Any],
        content: str
    ) -> str:
        """
        Build the prompt for quiz generation with strict format requirements.
        
        LEGACY METHOD - Generates questions WITH correct answers and explanations.
        Maintained for backward compatibility.
        
        Optimized for small models with reduced question count (5 instead of 10).
        
        Args:
            module_info: Module details
            content: Source educational content (module-scoped)
            
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
1. Generate EXACTLY 5 multiple-choice questions
2. Each question MUST have EXACTLY 4 options
3. Each question MUST have ONE correct answer
4. Each question MUST have a brief explanation (maximum 200 characters)
5. Questions should cover the key concepts from the material
6. Options should be plausible but clearly distinguishable
7. Number questions from 1 to 5

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
    ... (repeat for all 5 questions)
  ]
}}

CRITICAL RULES:
- Output ONLY valid JSON, no additional text
- Ensure correct_answer matches one of the 4 options EXACTLY
- Keep explanations under 200 characters
- Make questions clear and unambiguous
- Ensure all 5 questions are included
- Questions should test understanding, not just memorization

Generate the quiz now:"""
        
        return prompt
    
    def _build_quiz_questions_prompt(
        self,
        module_info: Dict[str, Any],
        content: str
    ) -> str:
        """
        Build the prompt for quiz questions generation (WITHOUT answers).
        
        NEW METHOD for Phase 2 - Generates only questions and options.
        
        Args:
            module_info: Module details
            content: Source educational content (module-scoped)
            
        Returns:
            Complete prompt string
        """
        topic_name = module_info.get('topic_name', 'Unknown Topic')
        
        # Truncate content if too long (optimized for qwen2.5:1.5b on CPU)
        truncated_content = content[:3000] if len(content) > 3000 else content
        
        # OPTIMIZATION: Short, direct prompt for faster generation on small models
        prompt = f"""Create 5 simple quiz questions about: {topic_name}

SOURCE:
{truncated_content}

RULES:
1. EXACTLY 5 questions
2. Each question: max 20 words, direct and clear
3. Each option: max 10 words
4. EXACTLY 4 options per question (A, B, C, D)
5. CRITICAL MCQ FORMAT RULE:
   - Every question MUST contain an "options" array with EXACTLY 4 distinct choices.
   - If the topic in SOURCE describes fewer than 4 items (e.g., 3 types, 2 categories), you MUST supply a plausible distractor or "None of the above" as the 4th option. Never output fewer than 4 options.
6. NO scenarios, NO "best/most appropriate" phrasing
7. Test ONE concept per question
8. Stay strictly within the source material

QUESTION STYLE (GOOD):
"What is DevOps?"
"Which tool automates deployment?"
"What does CI/CD stand for?"

QUESTION STYLE (BAD - TOO LONG):
"In a scenario where a team needs to deploy frequently, which methodology would be most appropriate?"

OUTPUT (JSON only, no extra text):
{{
  "questions": [
    {{
      "question_number": 1,
      "question_text": "Short direct question?",
      "options": ["Short option A", "Short option B", "Short option C", "Short option D"]
    }},
    {{
      "question_number": 2,
      "question_text": "Another short question?",
      "options": ["Option A", "Option B", "Option C", "Option D"]
    }},
    ... (3 more questions)
  ]
}}

CRITICAL:
- Output ONLY valid JSON
- Every question MUST have an "options" array with EXACTLY 4 distinct choices
- NO "correct_answer" or "explanation" fields
- Questions must be under 20 words
- Options must be under 10 words each
- Number questions 1 to 5

Generate now:"""
        
        return prompt
    
    def _build_quiz_answers_prompt(
        self,
        module_info: Dict[str, Any],
        questions: List[Dict[str, Any]],
        content: str
    ) -> str:
        """
        Build the prompt for generating correct answers and explanations.
        
        NEW METHOD for Phase 2 - Generates answers for existing questions.
        
        Args:
            module_info: Module details
            questions: List of question dictionaries
            content: Source educational content (module-scoped)
            
        Returns:
            Complete prompt string
        """
        topic_name = module_info.get('topic_name', 'Unknown Topic')
        
        # Truncate content if too long (optimized for qwen2.5:1.5b on CPU)
        truncated_content = content[:3000] if len(content) > 3000 else content
        
        # Format questions for the prompt (compact format)
        questions_text = ""
        for q in questions:
            questions_text += f"\n{q['question_number']}. {q['question_text']}\n"
            for i, option in enumerate(q['options']):
                questions_text += f"   {chr(65+i)}) {option}\n"
        
        # OPTIMIZATION: Ultra-concise prompt for faster generation on small models
        prompt = f"""Provide correct answers for these quiz questions about: {topic_name}

QUESTIONS:
{questions_text}

TASK:
For each of the 5 questions above, identify the single correct option.

OUTPUT (JSON only):
{{
  "answers": [
    {{
      "question_number": 1,
      "correct_answer": "A",
      "explanation": "Brief explanation why this option is correct"
    }},
    {{
      "question_number": 2,
      "correct_answer": "B",
      "explanation": "Brief explanation why this option is correct"
    }},
    {{
      "question_number": 3,
      "correct_answer": "C",
      "explanation": "Brief explanation why this option is correct"
    }},
    {{
      "question_number": 4,
      "correct_answer": "D",
      "explanation": "Brief explanation why this option is correct"
    }},
    {{
      "question_number": 5,
      "correct_answer": "A",
      "explanation": "Brief explanation why this option is correct"
    }}
  ]
}}

CRITICAL:
- Output ONLY valid JSON, no markdown, no other text
- "correct_answer" MUST be the option letter ("A", "B", "C", or "D") or the exact option text
- Provide an entry for ALL 5 questions (numbered 1 to 5)
- Explanations must be concise (max 80 chars)

Generate now:"""
        
        return prompt
    
    def _normalize_correct_answer(self, correct_answer: str, options: List[str]) -> str:
        """
        Normalize the correct_answer to match one of the option strings.
        
        Handles common LLM output formats:
        - Single letter labels: "A", "B", "C", "D"
        - Prefixed labels: "Option A", "Option B", etc.
        - Formatted labels: "A.", "B)", "A:", etc.
        
        Args:
            correct_answer: The correct answer string from LLM
            options: List of 4 option strings
            
        Returns:
            Normalized correct answer that matches one of the options
            
        Raises:
            ValueError: If normalization fails to find a match
        """
        # If already matches exactly, return as-is
        if correct_answer in options:
            return correct_answer
        
        # Strip whitespace
        normalized = correct_answer.strip()
        
        # Try direct match after stripping
        if normalized in options:
            return normalized
        
        # Extract label if it's a single letter (A-D)
        if len(normalized) == 1 and normalized.upper() in ['A', 'B', 'C', 'D']:
            label_index = ord(normalized.upper()) - ord('A')
            if 0 <= label_index < len(options):
                logger.info(f"Normalized answer '{correct_answer}' to option {label_index}: '{options[label_index]}'")
                return options[label_index]
        
        # Try to extract label from common formats
        # Formats: "A.", "B)", "A:", "Option A", "Option B", "A. text", "B) text", etc.
        import re
        
        # Pattern to match label at start: optional "Option" + optional space + letter + optional punctuation/space/end
        # Made the trailing character class optional with ?
        pattern = r'^(?:Option\s*)?([A-D])(?:[\.\)\:\s]|$)'
        match = re.match(pattern, normalized, re.IGNORECASE)
        
        if match:
            label = match.group(1).upper()
            label_index = ord(label) - ord('A')
            if 0 <= label_index < len(options):
                logger.info(f"Normalized answer '{correct_answer}' to option {label_index}: '{options[label_index]}'")
                return options[label_index]
        
        # Try case-insensitive match with options
        normalized_lower = normalized.lower()
        for option in options:
            if option.lower() == normalized_lower:
                logger.info(f"Normalized answer '{correct_answer}' to '{option}' (case-insensitive match)")
                return option
        
        # Try stripped-prefix match (e.g. option is 'A. None of the above' and answer is 'None of the above')
        def strip_opt_prefix(text: str) -> str:
            return re.sub(r'^(?:Option\s*)?[A-D][\.\)\:\s\-]+\s*', '', text, flags=re.IGNORECASE).strip().lower()

        clean_norm = strip_opt_prefix(normalized)
        if clean_norm:
            for option in options:
                if strip_opt_prefix(option) == clean_norm:
                    logger.info(f"Normalized answer '{correct_answer}' to '{option}' (stripped prefix match)")
                    return option
        
        # If we get here, normalization failed
        raise ValueError(f"Could not normalize correct_answer '{correct_answer}' to any of the options")
    
    def _auto_repair_options(self, question: Dict[str, Any], question_index: int) -> None:
        """
        Auto-repair options array to enforce exactly 4 options.
        - Under-generated (3 options): appends 'None of the above' (or 'Cannot be determined' if duplicate).
        - Over-generated (>4 options): slices to first 4 options.
        
        Args:
            question: Question dictionary containing 'options'
            question_index: 1-based index of the question for logging
        """
        options = question.get("options")
        if isinstance(options, list):
            if len(options) == 3:
                existing_lower = [str(opt).strip().lower() for opt in options]
                distractor = "None of the above" if "none of the above" not in existing_lower else "Cannot be determined"
                options.append(distractor)
                question["options"] = options
                logger.info(f"Auto-repaired Question {question_index}: appended distractor '{distractor}'")
            elif len(options) > 4:
                question["options"] = options[:4]
                logger.info(f"Auto-repaired Question {question_index}: sliced options to 4 items")

    def _validate_quiz_structure(self, quiz_data: Dict[str, Any]) -> tuple[bool, str]:
        """
        Validate that the quiz data meets all structural requirements.
        
        LEGACY METHOD - Validates questions WITH correct answers and explanations.
        Maintained for backward compatibility.
        
        Enforces exactly 5 questions (optimized for small models).
        Includes normalization of correct_answer to handle common LLM output formats.
        
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
        
        # Check exactly 5 questions (optimized for performance)
        if len(questions) != 5:
            return False, f"Expected exactly 5 questions, got {len(questions)}"
        
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
            
            # Auto-repair options if model generated 3 or >4 options
            self._auto_repair_options(question, i)
            
            # Check exactly 4 options
            options = question["options"]
            if not isinstance(options, list) or len(options) != 4:
                return False, f"Question {i} must have exactly 4 options, got {len(options) if isinstance(options, list) else 'invalid'}"
            
            # Check all options are non-empty strings
            for j, option in enumerate(options, 1):
                if not isinstance(option, str) or not option.strip():
                    return False, f"Question {i}, option {j} is invalid"
            
            # Normalize and validate correct answer
            correct_answer = question["correct_answer"]
            try:
                normalized_answer = self._normalize_correct_answer(correct_answer, options)
                # Update the question with normalized answer
                question["correct_answer"] = normalized_answer
            except ValueError as e:
                return False, f"Question {i} validation failed: {str(e)}"
            
            # Check explanation length
            explanation = question["explanation"]
            if not isinstance(explanation, str) or len(explanation) > 200:
                return False, f"Question {i} explanation must be a string with max 200 characters, got {len(explanation) if isinstance(explanation, str) else 'invalid'}"
            
            if not explanation.strip():
                return False, f"Question {i} explanation cannot be empty"
        
        return True, ""
    
    def _validate_quiz_questions_structure(self, quiz_data: Dict[str, Any]) -> tuple[bool, str]:
        """
        Validate quiz questions structure (WITHOUT correct answers/explanations).
        
        NEW METHOD for Phase 2 - Validates questions with only question_text and options.
        
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
        
        # Check exactly 5 questions
        if len(questions) != 5:
            return False, f"Expected exactly 5 questions, got {len(questions)}"
        
        # Validate each question
        for i, question in enumerate(questions, 1):
            # Check required fields (no correct_answer or explanation)
            required_fields = ["question_number", "question_text", "options"]
            for field in required_fields:
                if field not in question:
                    return False, f"Question {i} missing required field: {field}"
            
            # Ensure correct_answer and explanation are NOT present
            if "correct_answer" in question:
                return False, f"Question {i} should not have 'correct_answer' field"
            if "explanation" in question:
                return False, f"Question {i} should not have 'explanation' field"
            
            # Check question number
            if question["question_number"] != i:
                return False, f"Question {i} has incorrect question_number: {question['question_number']}"
            
            # Check question text is not empty
            if not question["question_text"] or len(question["question_text"]) < 10:
                return False, f"Question {i} has invalid question_text (must be at least 10 characters)"
            
            # Auto-repair options if model generated 3 or >4 options
            self._auto_repair_options(question, i)
            
            # Check exactly 4 options
            options = question["options"]
            if not isinstance(options, list) or len(options) != 4:
                return False, f"Question {i} must have exactly 4 options, got {len(options) if isinstance(options, list) else 'invalid'}"
            
            # Check all options are non-empty strings
            for j, option in enumerate(options, 1):
                if not isinstance(option, str) or not option.strip():
                    return False, f"Question {i}, option {j} is invalid"
        
        return True, ""
    
    def _validate_quiz_answers_structure(
        self,
        answers_data: Dict[str, Any],
        questions: List[Dict[str, Any]],
        allow_fallback: bool = False
    ) -> tuple[bool, str]:
        """
        Validate quiz answers structure.
        
        NEW METHOD for Phase 2 - Validates correct answers and explanations.
        
        Args:
            answers_data: The answers data to validate
            questions: The original questions (for option validation)
            allow_fallback: Whether to auto-repair options on final retry
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check if answers key exists
        if "answers" not in answers_data:
            return False, "Missing 'answers' key in answers data"
        
        answers = answers_data["answers"]
        
        # Check if it's a list
        if not isinstance(answers, list):
            return False, "'answers' must be a list"
        
        # Check exactly 5 answers
        if len(answers) != 5:
            return False, f"Expected exactly 5 answers, got {len(answers)}"
        
        # Validate each answer
        for i, answer in enumerate(answers, 1):
            if not isinstance(answer, dict):
                return False, f"Answer {i} must be a dictionary"
            
            # Check question number
            if "question_number" not in answer:
                if allow_fallback:
                    answer["question_number"] = i
                else:
                    return False, f"Answer {i} missing required field: question_number"
            elif answer["question_number"] != i:
                if allow_fallback:
                    answer["question_number"] = i
                else:
                    return False, f"Answer {i} has incorrect question_number: {answer['question_number']}"
            
            # Get corresponding question
            question = questions[i - 1]
            options = question["options"]
            
            # Normalize and validate correct answer
            correct_answer = answer.get("correct_answer")
            if not correct_answer:
                if allow_fallback:
                    fallback_option = options[0] if options else "A"
                    logger.warning(f"Answer {i} missing correct_answer. Defaulting to: '{fallback_option}'")
                    answer["correct_answer"] = fallback_option
                else:
                    return False, f"Answer {i} missing required field: correct_answer"
            else:
                try:
                    normalized_answer = self._normalize_correct_answer(correct_answer, options)
                    answer["correct_answer"] = normalized_answer
                except ValueError as e:
                    if allow_fallback:
                        fallback_option = options[0] if options else "A"
                        logger.warning(
                            f"Answer {i} normalization failed for '{correct_answer}'. "
                            f"Applying fallback to option 0: '{fallback_option}'"
                        )
                        answer["correct_answer"] = fallback_option
                    else:
                        return False, f"Answer {i} validation failed: {str(e)}"
            
            # Check explanation
            explanation = answer.get("explanation")
            if not explanation or not isinstance(explanation, str) or not explanation.strip():
                if allow_fallback:
                    answer["explanation"] = "Correct option based on course material."
                else:
                    return False, f"Answer {i} missing required field: explanation"
            elif len(explanation) > 180:
                if allow_fallback:
                    answer["explanation"] = explanation[:177] + "..."
                else:
                    return False, f"Answer {i} explanation too long: {len(explanation)} chars (max 180). Please be more concise."
        
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
            # Call Ollama with isolated greedy decoding options for doubt resolution
            response = self._call_ollama(
                prompt,
                format_json=True,
                temperature=0.0,
                repeat_penalty=1.05,
                num_predict=300
            )
            
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
        Build the prompt for context-aware question answering using ChatML.
        
        Args:
            module_info: Module details
            question: User's question
            module_content: Module content for context
            
        Returns:
            Complete ChatML prompt string with inverted JSON schema (in_scope first)
        """
        topic_name = module_info.get('topic_name', 'Unknown Topic')
        
        # Truncate content if too long
        truncated_content = module_content[:2500] if len(module_content) > 2500 else module_content
        
        prompt = f"""<|im_start|>system
You are a strict academic verification guard.
Determine if the student's question can be directly answered using ONLY the provided MODULE CONTENT.

CRITICAL RULES:
1. If the direct answer is explicitly stated in MODULE CONTENT -> "in_scope": true.
2. If the question asks about concepts NOT covered in MODULE CONTENT, general knowledge, or other subjects -> "in_scope": false.
3. If "in_scope" is false, "answer" MUST be exactly: "This question is outside the scope of this module. Please ask questions covered in the module notes."
4. Never use external knowledge. Rely strictly on the text provided.

OUTPUT FORMAT (Strict JSON only):
{{
  "in_scope": true or false,
  "answer": "string"
}}
<|im_end|>
<|im_start|>user
MODULE TOPIC: {topic_name}

MODULE CONTENT:
{truncated_content}

STUDENT QUESTION:
{question}
<|im_end|>
<|im_start|>assistant
"""
        return prompt


# Global LLM service instance
llm_service = LLMService()
