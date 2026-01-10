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
        time_taken_seconds: int
    ) -> Dict[str, Any]:
        """
        Submit quiz answers and get results.
        
        Args:
            module_id: The module ID
            quiz_id: The quiz ID
            answers: Dictionary mapping question_number to selected_option
            time_taken_seconds: Time taken to complete quiz
            
        Returns:
            Dictionary containing:
                - success: bool
                - quiz_id: str
                - module_id: str
                - score: int (out of 5)
                - accuracy: float (percentage)
                - time_taken_seconds: int
                - time_limit_exceeded: bool
                - correct_answers: int
                - incorrect_answers: int
                - detailed_results: list[dict] (per-question results)
                
        Raises:
            Exception: If API call fails
        """
        endpoint = f"/api/quiz/submit/{module_id}"
        payload = {
            "quiz_id": quiz_id,
            "answers": answers,
            "time_taken_seconds": time_taken_seconds
        }
        
        response = self.client.post(endpoint, json_data=payload)
        return response


# Global quiz service instance
quiz_service = QuizService()
