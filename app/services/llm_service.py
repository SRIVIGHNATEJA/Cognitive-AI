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
                
                # Call Ollama with JSON format
                response = self._call_ollama(prompt, format_json=True)
                
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
                
                # Validate the answers structure
                is_valid, error_msg = self._validate_quiz_answers_structure(answers_data, questions)
                
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
        
        # Truncate content if too long
        truncated_content = content[:3000] if len(content) > 3000 else content
        
        prompt = f"""You are an expert educator creating multiple-choice quiz questions.

Generate quiz questions for the following topic:

TOPIC: {topic_name}

SOURCE MATERIAL:
{truncated_content}

STRICT REQUIREMENTS:
1. Generate EXACTLY 5 multiple-choice questions
2. Each question MUST have EXACTLY 4 plausible options
3. DO NOT include correct answers or explanations
4. Questions should cover the key concepts from the material
5. Options should be plausible but clearly distinguishable
6. Number questions from 1 to 5

OUTPUT FORMAT (JSON):
{{
  "questions": [
    {{
      "question_number": 1,
      "question_text": "What is...?",
      "options": ["Option A", "Option B", "Option C", "Option D"]
    }},
    ... (repeat for all 5 questions)
  ]
}}

CRITICAL RULES:
- Output ONLY valid JSON, no additional text
- DO NOT include "correct_answer" or "explanation" fields
- Make questions clear and unambiguous
- Ensure all 5 questions are included
- Questions should test understanding, not just memorization
- All 4 options should be plausible

Generate the quiz questions now:"""
        
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
        
        # Truncate content if too long
        truncated_content = content[:3000] if len(content) > 3000 else content
        
        # Format questions for the prompt
        questions_text = ""
        for q in questions:
            questions_text += f"\nQuestion {q['question_number']}: {q['question_text']}\n"
            for i, option in enumerate(q['options'], 1):
                questions_text += f"  {chr(64+i)}. {option}\n"
        
        prompt = f"""You are an expert educator providing correct answers and explanations for quiz questions.

TOPIC: {topic_name}

SOURCE MATERIAL:
{truncated_content}

QUIZ QUESTIONS:
{questions_text}

TASK:
For each question, provide:
1. The correct answer (must match one of the options EXACTLY)
2. A VERY brief explanation (MAXIMUM 120 characters - count every character!)

EXPLANATION EXAMPLES (all under 120 chars):
- "DevOps combines development and operations for faster, automated deployments." (79 chars) ✓
- "Microservices split apps into small, independent services for better scalability." (83 chars) ✓
- "CI/CD automates testing and deployment to speed up software delivery." (71 chars) ✓

BAD EXAMPLES (too long):
- "DevOps is a set of practices that combines software development and IT operations to shorten the development lifecycle and provide continuous delivery." (155 chars) ✗

OUTPUT FORMAT (JSON):
{{
  "answers": [
    {{
      "question_number": 1,
      "correct_answer": "Option B",
      "explanation": "Very brief explanation (max 120 chars)"
    }},
    ... (repeat for all 5 questions)
  ]
}}

CRITICAL RULES:
- Output ONLY valid JSON, no additional text
- Ensure correct_answer matches one of the options EXACTLY
- Keep explanations under 120 characters - BE EXTREMELY CONCISE
- Remove all unnecessary words - every character counts
- Use short sentences - avoid complex phrases
- Provide answers for all 5 questions
- Base answers on the source material
- IMPORTANT: Explanations over 120 characters will be REJECTED

Generate the answers now:"""
        
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
        
        # If we get here, normalization failed
        raise ValueError(f"Could not normalize correct_answer '{correct_answer}' to any of the options")
    
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
        questions: List[Dict[str, Any]]
    ) -> tuple[bool, str]:
        """
        Validate quiz answers structure.
        
        NEW METHOD for Phase 2 - Validates correct answers and explanations.
        
        Args:
            answers_data: The answers data to validate
            questions: The original questions (for option validation)
            
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
            # Check required fields
            required_fields = ["question_number", "correct_answer", "explanation"]
            for field in required_fields:
                if field not in answer:
                    return False, f"Answer {i} missing required field: {field}"
            
            # Check question number
            if answer["question_number"] != i:
                return False, f"Answer {i} has incorrect question_number: {answer['question_number']}"
            
            # Get corresponding question
            question = questions[i - 1]
            options = question["options"]
            
            # Normalize and validate correct answer
            correct_answer = answer["correct_answer"]
            try:
                normalized_answer = self._normalize_correct_answer(correct_answer, options)
                # Update the answer with normalized answer
                answer["correct_answer"] = normalized_answer
            except ValueError as e:
                return False, f"Answer {i} validation failed: {str(e)}"
            
            # Check explanation length (ask for 120, validate at 180 for buffer)
            explanation = answer["explanation"]
            if not isinstance(explanation, str):
                return False, f"Answer {i} explanation must be a string, got {type(explanation).__name__}"
            
            if len(explanation) > 180:
                return False, f"Answer {i} explanation too long: {len(explanation)} chars (max 180). Please be more concise."
            
            if not explanation.strip():
                return False, f"Answer {i} explanation cannot be empty"
        
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
