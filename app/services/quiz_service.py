"""
Quiz Service for the Cognitive AI Learning Platform.

Handles quiz generation, evaluation, metrics tracking, and Q&A pruning.
Integrates with LLM service for quiz generation and cache service for persistence.
"""

import hashlib
import logging
from typing import List, Dict, Optional, Any
from datetime import datetime

from app.models import (
    Quiz,
    QuizQuestion,
    QuizResult,
    QuizMetrics,
    LearningMode,
    Module
)
from app.services.llm_service import LLMService
from app.services.cache_service import CacheService

logger = logging.getLogger(__name__)


class QuizService:
    """
    Service for generating and managing quizzes.
    
    Responsibilities:
    - Generate quizzes from module content using LLM
    - Evaluate quiz submissions and calculate scores
    - Track quiz metrics permanently
    - Prune old Q&A data (keep last 2 per module)
    - Generate deterministic quiz IDs
    """
    
    def __init__(
        self,
        llm_service: Optional[LLMService] = None,
        cache_service: Optional[CacheService] = None
    ):
        """
        Initialize the quiz service.
        
        Args:
            llm_service: LLM service instance for quiz generation
            cache_service: Cache service instance for persistence
        """
        self.llm_service = llm_service or LLMService()
        self.cache_service = cache_service or CacheService()
        logger.info("QuizService initialized")
    
    def generate_stable_quiz_id(self, module_id: str, created_at: datetime) -> str:
        """
        Generate a stable, deterministic quiz ID based on module_id and timestamp.
        
        Uses SHA-256 hash of module_id + ISO timestamp with microseconds to ensure
        uniqueness while maintaining determinism for the same exact moment.
        
        Args:
            module_id: Module identifier
            created_at: Quiz creation timestamp
            
        Returns:
            Stable quiz ID string
            
        Example:
            >>> service = QuizService()
            >>> dt = datetime(2024, 1, 7, 10, 30, 0, 123456)
            >>> service.generate_stable_quiz_id("mod_abc123", dt)
            'quiz_a1b2c3d4e5f6'
        """
        # Create deterministic hash from module_id and timestamp with microseconds
        timestamp_str = created_at.isoformat()
        content = f"{module_id}_{timestamp_str}"
        hash_obj = hashlib.sha256(content.encode('utf-8'))
        hash_hex = hash_obj.hexdigest()[:12]  # Use first 12 characters
        
        quiz_id = f"quiz_{hash_hex}"
        logger.debug(f"Generated quiz_id '{quiz_id}' for module '{module_id}'")
        
        return quiz_id
    
    def generate_quiz(
        self,
        module: Module,
        content: str,
        mode: LearningMode,
        time_limit_seconds: Optional[int] = None
    ) -> Quiz:
        """
        Generate a quiz for a module using LLM.
        
        This method:
        1. Calls LLM service to generate 10 MCQ questions
        2. Validates quiz structure (10 questions, 4 options each)
        3. Assigns deterministic quiz ID
        4. Returns Quiz object
        
        Args:
            module: Module to generate quiz for
            content: Source educational content (notes or input text)
            mode: Quiz mode (timed or untimed)
            time_limit_seconds: Time limit in seconds (required for timed mode)
            
        Returns:
            Quiz object with 10 questions
            
        Raises:
            ValueError: If quiz generation fails or validation fails
            RuntimeError: If LLM service fails
        """
        logger.info(f"Generating quiz for module '{module.module_id}' in {mode} mode")
        
        # Validate time limit for timed mode
        if mode == LearningMode.TIMED and time_limit_seconds is None:
            raise ValueError("time_limit_seconds is required for timed mode")
        
        try:
            # Prepare module info for LLM
            module_info = {
                "module_id": module.module_id,
                "topic_name": module.topic_name,
                "estimated_hours": module.estimated_hours
            }
            
            # Call LLM service to generate quiz questions
            questions_data = self.llm_service.generate_quiz_llm(
                module_info=module_info,
                content=content
            )
            
            if not questions_data or len(questions_data) != 10:
                raise ValueError(f"LLM generated invalid number of questions: {len(questions_data) if questions_data else 0}")
            
            logger.info(f"LLM generated {len(questions_data)} questions")
            
            # Convert to QuizQuestion objects
            questions = []
            for q_data in questions_data:
                question = QuizQuestion(
                    question_number=q_data["question_number"],
                    question_text=q_data["question_text"],
                    options=q_data["options"],
                    correct_answer=q_data["correct_answer"],
                    explanation=q_data["explanation"]
                )
                questions.append(question)
            
            # Generate deterministic quiz ID
            created_at = datetime.now()
            quiz_id = self.generate_stable_quiz_id(module.module_id, created_at)
            
            # Create Quiz object
            quiz = Quiz(
                quiz_id=quiz_id,
                module_id=module.module_id,
                questions=questions,
                mode=mode,
                time_limit_seconds=time_limit_seconds if mode == LearningMode.TIMED else None,
                created_at=created_at
            )
            
            logger.info(f"Successfully generated quiz '{quiz_id}' with {len(questions)} questions")
            return quiz
            
        except Exception as e:
            logger.error(f"Failed to generate quiz: {str(e)}")
            raise
    
    def evaluate_quiz(
        self,
        quiz: Quiz,
        answers: Dict[int, str],
        time_taken_seconds: int
    ) -> QuizResult:
        """
        Evaluate a quiz submission and calculate results.
        
        This method:
        1. Validates submitted answers against correct answers
        2. Calculates score and accuracy
        3. Checks if time limit was exceeded (for timed quizzes)
        4. Returns QuizResult object
        
        Backend accepts all submissions regardless of time limit.
        Time limit validation is recorded but does not affect score.
        
        Args:
            quiz: Quiz object being evaluated
            answers: Map of question_number to selected_option
            time_taken_seconds: Time taken to complete quiz
            
        Returns:
            QuizResult object with score, accuracy, and detailed results
            
        Raises:
            ValueError: If answers are invalid
        """
        logger.info(f"Evaluating quiz '{quiz.quiz_id}' with {len(answers)} answers")
        
        # Validate answers
        if not answers:
            raise ValueError("No answers provided")
        
        # Calculate correct and incorrect answers
        correct_count = 0
        incorrect_count = 0
        
        for question in quiz.questions:
            question_num = question.question_number
            
            # Get user's answer (default to empty string if not provided)
            user_answer = answers.get(question_num, "")
            
            # Check if answer is correct
            if user_answer == question.correct_answer:
                correct_count += 1
            else:
                incorrect_count += 1
        
        # Calculate score and accuracy
        score = correct_count
        accuracy = (correct_count / len(quiz.questions)) * 100.0
        
        # Check if time limit was exceeded (for timed quizzes)
        time_limit_exceeded = False
        if quiz.mode == LearningMode.TIMED and quiz.time_limit_seconds is not None:
            time_limit_exceeded = time_taken_seconds > quiz.time_limit_seconds
            
            if time_limit_exceeded:
                logger.warning(
                    f"Quiz '{quiz.quiz_id}' time limit exceeded: "
                    f"{time_taken_seconds}s > {quiz.time_limit_seconds}s"
                )
        
        # Create QuizResult
        result = QuizResult(
            quiz_id=quiz.quiz_id,
            module_id=quiz.module_id,
            score=score,
            accuracy=accuracy,
            time_taken_seconds=time_taken_seconds,
            time_limit_exceeded=time_limit_exceeded,
            correct_answers=correct_count,
            incorrect_answers=incorrect_count,
            submitted_at=datetime.now()
        )
        
        logger.info(
            f"Quiz evaluation complete: score={score}/10, "
            f"accuracy={accuracy:.1f}%, time={time_taken_seconds}s"
        )
        
        return result
    
    def store_quiz_data(
        self,
        quiz: Quiz,
        result: QuizResult
    ) -> None:
        """
        Store quiz Q&A data and update metrics.
        
        This method:
        1. Stores quiz Q&A data (subject to pruning)
        2. Updates quiz metrics (retained permanently)
        3. Triggers automatic pruning if needed
        
        Args:
            quiz: Quiz object
            result: QuizResult object
        """
        logger.info(f"Storing quiz data for quiz '{quiz.quiz_id}'")
        
        try:
            # Store quiz Q&A data
            quiz_qa_data = {
                "quiz_id": quiz.quiz_id,
                "module_id": quiz.module_id,
                "questions": [q.model_dump() for q in quiz.questions],
                "mode": quiz.mode.value,
                "time_limit_seconds": quiz.time_limit_seconds,
                "created_at": quiz.created_at.isoformat(),
                "result": result.model_dump(mode='json')
            }
            
            self.cache_service.cache_quiz_qa(quiz.module_id, quiz_qa_data)
            
            # Update quiz metrics
            self._update_quiz_metrics(quiz.module_id, result)
            
            # Trigger automatic pruning (keep only last 2 Q&As)
            self.prune_old_quiz_qa(quiz.module_id)
            
            logger.info(f"Quiz data stored successfully for quiz '{quiz.quiz_id}'")
            
        except Exception as e:
            logger.error(f"Failed to store quiz data: {str(e)}")
            raise
    
    def _update_quiz_metrics(
        self,
        module_id: str,
        result: QuizResult
    ) -> None:
        """
        Update quiz metrics for a module.
        
        Metrics are retained permanently regardless of Q&A pruning.
        
        Args:
            module_id: Module identifier
            result: QuizResult to add to metrics
        """
        # Get existing metrics
        existing_metrics = self.cache_service.get_quiz_metrics(module_id)
        
        if existing_metrics:
            # Update existing metrics
            total_quizzes = existing_metrics["total_quizzes"] + 1
            
            # Calculate new averages
            old_avg_score = existing_metrics["average_score"]
            new_avg_score = ((old_avg_score * existing_metrics["total_quizzes"]) + result.score) / total_quizzes
            
            old_avg_accuracy = existing_metrics["average_accuracy"]
            new_avg_accuracy = ((old_avg_accuracy * existing_metrics["total_quizzes"]) + result.accuracy) / total_quizzes
            
            # Update best/worst scores
            best_score = max(existing_metrics["best_score"], result.score)
            worst_score = min(existing_metrics["worst_score"], result.score)
            
            metrics = QuizMetrics(
                module_id=module_id,
                total_quizzes=total_quizzes,
                average_score=new_avg_score,
                best_score=best_score,
                worst_score=worst_score,
                average_accuracy=new_avg_accuracy
            )
        else:
            # Create new metrics
            metrics = QuizMetrics(
                module_id=module_id,
                total_quizzes=1,
                average_score=float(result.score),
                best_score=result.score,
                worst_score=result.score,
                average_accuracy=result.accuracy
            )
        
        # Store metrics
        self.cache_service.cache_quiz_metrics(module_id, metrics.model_dump())
        
        logger.debug(f"Updated metrics for module '{module_id}': {metrics.total_quizzes} quizzes")
    
    def prune_old_quiz_qa(self, module_id: str) -> None:
        """
        Prune old quiz Q&A data, keeping only the last 2 quizzes per module.
        
        This method:
        1. Retrieves all quiz Q&A data for the module
        2. Keeps only the 2 most recent quizzes
        3. Deletes older quiz Q&A data
        4. Does NOT affect quiz metrics (retained permanently)
        
        Args:
            module_id: Module identifier
        """
        logger.info(f"Pruning old quiz Q&A data for module '{module_id}'")
        
        try:
            # Delegate to cache service
            self.cache_service.prune_quiz_qa(module_id)
            
            logger.info(f"Quiz Q&A pruning complete for module '{module_id}'")
            
        except Exception as e:
            logger.error(f"Failed to prune quiz Q&A data: {str(e)}")
            raise


# Global quiz service instance
quiz_service = QuizService()
