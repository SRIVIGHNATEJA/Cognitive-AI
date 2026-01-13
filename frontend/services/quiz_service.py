"""
Quiz service for the Cognitive AI Learning Platform frontend.

Handles API calls for generating quizzes and submitting answers.
"""

from typing import Dict, Any, Optional
from .api_client import api_client


class QuizService:
    """Service for quiz-related API operations."""
    
    def __init__(self):
        """Initialize the quiz service."""
        self.client = api_client
    
    def generate_quiz(
        self, 
        module_id: str, 
        mode: str = "untimed",
        time_limit_seconds: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Generate a quiz for a module.
        
        Args:
            module_id: The module ID to generate quiz for
            mode: Quiz mode ('timed' or 'untimed')
            time_limit_seconds: Time limit in seconds (required for timed mode)
            
        Returns:
            Dictionary containing:
                - success: bool
                - quiz_id: str
                - module_id: str
                - questions: list[dict] (5 MCQs)
                - mode: str
                - time_limit_seconds: int (optional)
                
        Raises:
            Exception: If API call fails
        """
        endpoint = f"/api/quiz/generate/{module_id}"
        payload = {"mode": mode}
        
        if time_limit_seconds is not None:
            payload["time_limit_seconds"] = time_limit_seconds
        
        response = self.client.post(endpoint, json_data=payload)
        return response
    
    def submit_quiz(
        self,
        module_id: str,
        quiz_id: str,
        answers: Dict[int, str],
        time_taken_seconds: int,
        attempt_number: int = 1
    ) -> Dict[str, Any]:
        """
        Submit quiz answers WITHOUT evaluation (Phase 4 - Deferred Evaluation).
        
        RETRY SUPPORT:
        - attempt_number parameter tracks multiple attempts on same quiz
        
        Args:
            module_id: The module ID
            quiz_id: The quiz ID
            answers: Dictionary mapping question_number to selected_option
            time_taken_seconds: Time taken to complete quiz
            attempt_number: Attempt number (default: 1)
            
        Returns:
            Dictionary containing:
                - success: bool
                - message: str
                - submission_id: str
                - quiz_id: str
                - module_id: str
                - attempt_number: int
                
        Raises:
            Exception: If API call fails
        """
        endpoint = f"/api/quiz/submit/{module_id}?attempt_number={attempt_number}"
        payload = {
            "quiz_id": quiz_id,
            "answers": answers,
            "time_taken_seconds": time_taken_seconds
        }
        
        response = self.client.post(endpoint, json_data=payload)
        return response
    
    def evaluate_quiz(self, quiz_id: str, attempt_number: int = 1) -> Dict[str, Any]:
        """
        Evaluate a submitted quiz on-demand (Phase 4 - Deferred Evaluation).
        
        RETRY SUPPORT:
        - attempt_number parameter specifies which attempt to evaluate
        
        Args:
            quiz_id: The quiz ID to evaluate
            attempt_number: Attempt number (default: 1)
            
        Returns:
            Dictionary containing:
                - success: bool
                - cached: bool (whether evaluation was cached)
                - evaluation_id: str
                - quiz_id: str
                - module_id: str
                - attempt_number: int
                - score: int (out of 5)
                - accuracy: float (percentage)
                - correct_answers_count: int
                - incorrect_answers_count: int
                - question_results: list[dict] (per-question results)
                - time_taken_seconds: int
                - time_limit_exceeded: bool
                - evaluated_at: str (ISO timestamp)
                
        Raises:
            Exception: If API call fails
        """
        endpoint = f"/api/quiz/evaluate/{quiz_id}?attempt_number={attempt_number}"
        response = self.client.post(endpoint, json_data={})
        return response
    
    def get_evaluation(self, quiz_id: str, attempt_number: int = 1) -> Dict[str, Any]:
        """
        Retrieve cached quiz evaluation (Phase 4 - Deferred Evaluation).
        
        RETRY SUPPORT:
        - attempt_number parameter specifies which attempt's evaluation to retrieve
        
        Args:
            quiz_id: The quiz ID
            attempt_number: Attempt number (default: 1)
            
        Returns:
            Dictionary containing evaluation results (same as evaluate_quiz)
            
        Raises:
            Exception: If API call fails or evaluation not found
        """
        endpoint = f"/api/quiz/evaluation/{quiz_id}?attempt_number={attempt_number}"
        response = self.client.get(endpoint)
        return response
    
    def retry_quiz(self, quiz_id: str) -> Dict[str, Any]:
        """
        Retry a quiz with a new attempt (Phase 4 - Retry Flow).
        
        RESOURCE-AWARE DESIGN:
        - Same questions reused across attempts (no regeneration)
        - Increments attempt_number for new submission/evaluation
        
        Args:
            quiz_id: The quiz ID to retry
            
        Returns:
            Dictionary containing:
                - success: bool
                - message: str
                - quiz_id: str
                - module_id: str
                - questions: list[dict] (same questions)
                - mode: str
                - time_limit_seconds: int (optional)
                - attempt_number: int (new attempt number)
                - created_at: str (ISO timestamp)
                
        Raises:
            Exception: If API call fails
        """
        endpoint = f"/api/quiz/retry/{quiz_id}"
        response = self.client.post(endpoint, json_data={})
        return response


# Global quiz service instance
quiz_service = QuizService()
