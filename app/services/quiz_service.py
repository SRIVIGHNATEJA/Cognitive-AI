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
        
        PHASE 3 UPDATE: Now generates questions WITHOUT correct answers/explanations.
        Uses generate_quiz_questions_llm() for deferred evaluation architecture.
        
        This method:
        1. Calls LLM service to generate 5 MCQ questions (questions + options only)
        2. Validates quiz structure (5 questions, 4 options each)
        3. Assigns deterministic quiz ID
        4. Returns Quiz object WITHOUT correct_answer/explanation
        
        Args:
            module: Module to generate quiz for
            content: Source educational content (notes or input text)
            mode: Quiz mode (timed or untimed)
            time_limit_seconds: Time limit in seconds (required for timed mode)
            
        Returns:
            Quiz object with 5 questions (without correct_answer/explanation)
            
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
            
            # Call LLM service to generate quiz questions (WITHOUT answers)
            questions_data = self.llm_service.generate_quiz_questions_llm(
                module_info=module_info,
                content=content
            )
            
            if not questions_data or len(questions_data) != 5:
                raise ValueError(f"LLM generated invalid number of questions: {len(questions_data) if questions_data else 0}")
            
            logger.info(f"LLM generated {len(questions_data)} questions (without answers)")
            
            # Convert to QuizQuestion objects (without correct_answer/explanation)
            questions = []
            for q_data in questions_data:
                question = QuizQuestion(
                    question_number=q_data["question_number"],
                    question_text=q_data["question_text"],
                    options=q_data["options"]
                    # correct_answer and explanation are None
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
            
            logger.info(f"Successfully generated quiz '{quiz_id}' with {len(questions)} questions (deferred evaluation)")
            return quiz
            
        except Exception as e:
            logger.error(f"Failed to generate quiz: {str(e)}")
            raise
    
    def submit_quiz_submission(
        self,
        quiz_id: str,
        module_id: str,
        user_answers: Dict[int, str],
        time_taken_seconds: int
    ) -> str:
        """
        Store quiz submission WITHOUT evaluation (Phase 3 - Deferred Evaluation).
        
        This method:
        1. Generates a unique submission ID
        2. Creates QuizSubmission object
        3. Stores submission in cache
        4. Returns submission ID
        
        Evaluation happens later when user explicitly requests it.
        
        Args:
            quiz_id: Quiz identifier
            module_id: Module identifier
            user_answers: Map of question_number to selected_option
            time_taken_seconds: Time taken to complete quiz
            
        Returns:
            Submission ID
            
        Raises:
            ValueError: If submission data is invalid
        """
        logger.info(f"Storing quiz submission for quiz '{quiz_id}'")
        
        # Validate inputs
        if not user_answers:
            raise ValueError("No answers provided")
        
        # Generate submission ID
        from app.models import QuizSubmission
        timestamp = datetime.now()
        submission_id = f"sub_{hashlib.sha256(f'{quiz_id}_{timestamp.isoformat()}'.encode()).hexdigest()[:12]}"
        
        # Create submission object
        submission = QuizSubmission(
            submission_id=submission_id,
            quiz_id=quiz_id,
            module_id=module_id,
            user_answers=user_answers,
            time_taken_seconds=time_taken_seconds,
            submitted_at=timestamp
        )
        
        # Store in cache
        self.cache_service.cache_quiz_submission(submission.model_dump())
        
        logger.info(f"Quiz submission stored: {submission_id}")
        return submission_id
    
    def evaluate_quiz_submission(
        self,
        quiz_id: str,
        module_id: str,
        content: str
    ) -> Dict[str, Any]:
        """
        Evaluate a quiz submission on-demand (Phase 3 - Deferred Evaluation).
        
        This method:
        1. Retrieves quiz questions from cache
        2. Retrieves submission from cache (by quiz_id)
        3. Checks if legacy quiz (has correct_answer) → use embedded answers
        4. If new quiz → call generate_quiz_answers_llm()
        5. Computes score, accuracy, per-question results
        6. Creates and stores QuizEvaluation
        7. Returns evaluation
        
        Args:
            quiz_id: Quiz identifier
            module_id: Module identifier
            content: Source educational content for LLM evaluation
            
        Returns:
            Evaluation dictionary with score, accuracy, and detailed results
            
        Raises:
            ValueError: If quiz or submission not found
            RuntimeError: If LLM service fails
        """
        logger.info(f"Evaluating quiz submission for quiz '{quiz_id}'")
        
        # Retrieve quiz from history
        quiz_history = self.cache_service.get_quiz_history(module_id)
        if not quiz_history:
            raise ValueError(f"No quiz history found for module '{module_id}'")
        
        # Find the specific quiz
        quiz_data = None
        for quiz in quiz_history:
            if quiz.get("quiz_id") == quiz_id:
                quiz_data = quiz
                break
        
        if not quiz_data:
            raise ValueError(f"Quiz '{quiz_id}' not found in history")
        
        # Retrieve submission by quiz_id
        # Search through all submissions to find one matching this quiz_id
        submission_data = None
        quizzes_dir = self.cache_service.cache_dir / 'quizzes'
        for sub_file in quizzes_dir.glob('submission_*.json'):
            try:
                json_data = sub_file.read_text(encoding='utf-8')
                data = self.cache_service._deserialize_data(json_data)
                if data.get("quiz_id") == quiz_id:
                    submission_data = data
                    break
            except Exception:
                continue
        
        if not submission_data:
            raise ValueError(f"No submission found for quiz '{quiz_id}'")
        
        # Check if this is a legacy quiz (has correct_answer in questions)
        questions_data = quiz_data.get("questions", [])
        is_legacy = any(q.get("correct_answer") is not None for q in questions_data)
        
        if is_legacy:
            # Legacy quiz - use embedded answers
            logger.info(f"Quiz '{quiz_id}' is legacy - using embedded answers")
            answers_data = [
                {
                    "question_number": q["question_number"],
                    "correct_answer": q["correct_answer"],
                    "explanation": q.get("explanation", "")
                }
                for q in questions_data
            ]
        else:
            # New quiz - generate answers with LLM
            logger.info(f"Quiz '{quiz_id}' is new - generating answers with LLM")
            
            # Get module info from roadmap
            roadmap_data = self.cache_service.get_cached_roadmap()
            if not roadmap_data:
                raise ValueError("No roadmap found")
            
            module_info = None
            for mod in roadmap_data.get("modules", []):
                if mod.get("module_id") == module_id:
                    module_info = mod
                    break
            
            if not module_info:
                raise ValueError(f"Module '{module_id}' not found in roadmap")
            
            # Call LLM to generate answers
            try:
                answers_data = self.llm_service.generate_quiz_answers_llm(
                    module_info=module_info,
                    questions=questions_data,
                    content=content
                )
            except Exception as e:
                logger.error(f"Failed to generate quiz answers: {str(e)}")
                raise RuntimeError(f"LLM service failed: {str(e)}")
        
        # Evaluate submission
        user_answers = submission_data.get("user_answers", {})
        time_taken_seconds = submission_data.get("time_taken_seconds", 0)
        
        # Calculate score and build question results
        from app.models import QuestionResult
        question_results = []
        correct_count = 0
        incorrect_count = 0
        
        for i, q_data in enumerate(questions_data):
            question_num = q_data["question_number"]
            user_answer = user_answers.get(str(question_num), "")  # Convert to string for dict key
            
            # Find correct answer from answers_data
            correct_answer = None
            explanation = ""
            for ans in answers_data:
                if ans["question_number"] == question_num:
                    correct_answer = ans["correct_answer"]
                    explanation = ans.get("explanation", "")
                    break
            
            if correct_answer is None:
                raise ValueError(f"No answer found for question {question_num}")
            
            is_correct = user_answer == correct_answer
            if is_correct:
                correct_count += 1
            else:
                incorrect_count += 1
            
            question_results.append(QuestionResult(
                question_number=question_num,
                question_text=q_data["question_text"],
                options=q_data["options"],
                user_answer=user_answer,
                correct_answer=correct_answer,
                is_correct=is_correct,
                explanation=explanation
            ))
        
        # Calculate score and accuracy
        score = correct_count
        accuracy = (correct_count / len(questions_data)) * 100.0
        
        # Check time limit
        time_limit_exceeded = False
        if quiz_data.get("mode") == LearningMode.TIMED.value:
            time_limit = quiz_data.get("time_limit_seconds")
            if time_limit and time_taken_seconds > time_limit:
                time_limit_exceeded = True
        
        # Create evaluation
        from app.models import QuizEvaluation
        evaluation_id = f"eval_{hashlib.sha256(f'{quiz_id}_{datetime.now().isoformat()}'.encode()).hexdigest()[:12]}"
        
        evaluation = QuizEvaluation(
            evaluation_id=evaluation_id,
            quiz_id=quiz_id,
            module_id=module_id,
            score=score,
            accuracy=accuracy,
            correct_answers_count=correct_count,
            incorrect_answers_count=incorrect_count,
            question_results=question_results,
            time_taken_seconds=time_taken_seconds,
            time_limit_exceeded=time_limit_exceeded,
            evaluated_at=datetime.now()
        )
        
        # Store evaluation
        self.cache_service.cache_quiz_evaluation(evaluation.model_dump(mode='json'))
        
        logger.info(f"Quiz evaluation complete: score={score}/{len(questions_data)}, accuracy={accuracy:.1f}%")
        
        return evaluation.model_dump(mode='json')
    
    def get_quiz_evaluation(self, quiz_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve cached quiz evaluation.
        
        Args:
            quiz_id: Quiz identifier
            
        Returns:
            Evaluation dictionary if found, None otherwise
        """
        logger.info(f"Retrieving evaluation for quiz '{quiz_id}'")
        
        evaluation = self.cache_service.get_quiz_evaluation_by_quiz_id(quiz_id)
        
        if evaluation:
            logger.info(f"Found evaluation for quiz '{quiz_id}'")
        else:
            logger.debug(f"No evaluation found for quiz '{quiz_id}'")
        
        return evaluation
    
    def evaluate_quiz(
        self,
        quiz: Quiz,
        answers: Dict[int, str],
        time_taken_seconds: int
    ) -> QuizResult:
        """
        Evaluate a quiz submission and calculate results (LEGACY METHOD).
        
        BACKWARD COMPATIBILITY: This method is retained for legacy quizzes
        that have correct_answer embedded in questions.
        
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
        logger.info(f"Evaluating quiz '{quiz.quiz_id}' with {len(answers)} answers (LEGACY)")
        
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
            f"Quiz evaluation complete: score={score}/{len(quiz.questions)}, "
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
