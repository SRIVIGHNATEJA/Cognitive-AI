"""
Quiz API Router for the Cognitive AI Learning Platform.

Provides endpoints for generating quizzes, submitting answers, and retrieving quiz history and metrics.
"""

import logging
from fastapi import APIRouter, HTTPException, status, Body
from typing import Dict, Any

from app.models import (
    QuizGenerateRequest,
    QuizSubmitRequest,
    QuizResponse,
    QuizResultResponse,
    QuizMetricsResponse,
    Module,
    LearningMode
)
from app.services.quiz_service import QuizService
from app.services.cache_service import CacheService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/quiz", tags=["quiz"])

# Service instances
quiz_service = QuizService()
cache_service = CacheService()


def _get_module_from_roadmap(module_id: str) -> Module:
    """
    Helper function to get module details from cached roadmap.
    
    Args:
        module_id: Module identifier
        
    Returns:
        Module object
        
    Raises:
        HTTPException 404: If roadmap or module not found
    """
    # Get cached roadmap
    roadmap_data = cache_service.get_cached_roadmap()
    if not roadmap_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No roadmap found. Please generate a roadmap first."
        )
    
    # Find the module
    modules = roadmap_data.get("modules", [])
    for module_data in modules:
        if module_data.get("module_id") == module_id:
            return Module(**module_data)
    
    # Module not found
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Module '{module_id}' not found in roadmap."
    )


def _get_module_content(module_id: str) -> str:
    """
    Helper function to get module-scoped content for quiz generation.
    
    Implements strict fallback order:
    1. Module Notes (preferred)
    2. Module Cheat Sheet (fallback)
    3. Full input text (last resort - not ideal but prevents failure)
    
    NEVER concatenates multiple sources - uses FIRST available only.
    
    Args:
        module_id: Module identifier
        
    Returns:
        Module content text
        
    Raises:
        HTTPException 404: If no content available
    """
    # Fallback 1: Try module notes (preferred - most focused)
    notes = cache_service.get_cached_content(module_id, 'notes')
    if notes:
        logger.info(f"Quiz generation using MODULE NOTES for {module_id}")
        return notes
    
    # Fallback 2: Try module cheat sheet (good alternative)
    cheat_sheet = cache_service.get_cached_content(module_id, 'cheat_sheet')
    if cheat_sheet:
        logger.info(f"Quiz generation using MODULE CHEAT SHEET for {module_id}")
        return cheat_sheet
    
    # Fallback 3: Use full input text (last resort)
    # Note: This is not ideal as it's not module-scoped, but prevents complete failure
    # User should generate notes/cheat sheet first for best results
    roadmap_data = cache_service.get_cached_roadmap()
    if not roadmap_data or "input_id" not in roadmap_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No content available for quiz generation. Please generate notes or cheat sheet first."
        )
    
    input_id = roadmap_data["input_id"]
    cached_input = cache_service.get_cached_data(input_id, 'input')
    
    if not cached_input or 'extracted_text' not in cached_input:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Input text not found for ID '{input_id}'"
        )
    
    logger.warning(f"Quiz generation using FULL INPUT TEXT for {module_id} - recommend generating notes first")
    return cached_input['extracted_text']


@router.post("/generate/{module_id}", response_model=QuizResponse, status_code=status.HTTP_200_OK)
async def generate_quiz(module_id: str, request: QuizGenerateRequest = Body(...)) -> QuizResponse:
    """
    Generate a new quiz for a module.
    
    This endpoint:
    1. Validates that the module exists in the roadmap
    2. Retrieves module-scoped content (notes → cheat sheet → input text fallback)
    3. Generates quiz using LLM (5 MCQs with 4 options each)
    4. Stores quiz Q&A data in cache
    5. Returns the quiz
    
    Args:
        module_id: Module identifier (from path)
        request: Quiz generation request with mode and optional time_limit
        
    Returns:
        QuizResponse with generated quiz
        
    Raises:
        HTTPException 404: If module or content not found
        HTTPException 400: If validation fails (e.g., timed mode without time limit)
        HTTPException 503: If LLM service fails
        HTTPException 500: If quiz generation fails
    """
    try:
        logger.info(f"Quiz generation requested for module: {module_id}")
        
        # Validate module exists
        module = _get_module_from_roadmap(module_id)
        
        # Get module content
        content = _get_module_content(module_id)
        
        # Validate time limit for timed mode
        if request.mode == LearningMode.TIMED and request.time_limit_seconds is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="time_limit_seconds is required for timed mode"
            )
        
        # Generate quiz
        logger.info(f"Generating quiz for module {module_id} in {request.mode} mode")
        quiz = quiz_service.generate_quiz(
            module=module,
            content=content,
            mode=request.mode,
            time_limit_seconds=request.time_limit_seconds
        )
        
        logger.info(f"Quiz generated successfully: {quiz.quiz_id}")
        
        # Cache the quiz Q&A data for later submission
        quiz_data = {
            "quiz_id": quiz.quiz_id,
            "module_id": quiz.module_id,
            "questions": [q.model_dump() for q in quiz.questions],
            "mode": quiz.mode.value,
            "time_limit_seconds": quiz.time_limit_seconds,
            "created_at": quiz.created_at.isoformat()
        }
        cache_service.cache_quiz_qa(module_id, quiz_data)
        
        return QuizResponse(
            success=True,
            quiz_id=quiz.quiz_id,
            module_id=quiz.module_id,
            questions=quiz.questions,
            mode=quiz.mode,
            time_limit_seconds=quiz.time_limit_seconds
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except ValueError as e:
        # Validation errors
        logger.error(f"Quiz generation validation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Quiz generation failed: {str(e)}"
        )
    except RuntimeError as e:
        # LLM service errors
        logger.error(f"LLM service error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"LLM service unavailable: {str(e)}. Please ensure Ollama is running."
        )
    except Exception as e:
        # Unexpected errors
        logger.error(f"Unexpected error generating quiz: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while generating the quiz"
        )


@router.post("/submit/{module_id}", response_model=QuizResultResponse, status_code=status.HTTP_200_OK)
async def submit_quiz(module_id: str, request: QuizSubmitRequest = Body(...)) -> QuizResultResponse:
    """
    Submit quiz answers and get evaluation results.
    
    This endpoint:
    1. Retrieves the quiz from history
    2. Evaluates submitted answers
    3. Calculates score, accuracy, and checks time limit
    4. Stores quiz result and updates metrics
    5. Triggers automatic Q&A pruning (keeps last 2)
    6. Returns detailed results
    
    Backend accepts all submissions regardless of time limit.
    Time limit validation is recorded but does not affect score.
    
    Args:
        module_id: Module identifier (from path)
        request: Quiz submission with quiz_id, answers, and time_taken
        
    Returns:
        QuizResultResponse with score, accuracy, and detailed results
        
    Raises:
        HTTPException 404: If quiz not found
        HTTPException 400: If validation fails
        HTTPException 500: If evaluation fails
    """
    try:
        logger.info(f"Quiz submission received for quiz: {request.quiz_id}")
        
        # Retrieve quiz from history
        quiz_history = cache_service.get_quiz_history(module_id)
        if not quiz_history:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No quiz history found for module '{module_id}'"
            )
        
        # Find the specific quiz
        quiz_data = None
        for quiz in quiz_history:
            if quiz.get("quiz_id") == request.quiz_id:
                quiz_data = quiz
                break
        
        if not quiz_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Quiz '{request.quiz_id}' not found in history"
            )
        
        # Reconstruct Quiz object from cached data
        from app.models import Quiz, QuizQuestion
        from datetime import datetime
        
        questions = [QuizQuestion(**q) for q in quiz_data["questions"]]
        quiz = Quiz(
            quiz_id=quiz_data["quiz_id"],
            module_id=quiz_data["module_id"],
            questions=questions,
            mode=LearningMode(quiz_data["mode"]),
            time_limit_seconds=quiz_data.get("time_limit_seconds"),
            created_at=datetime.fromisoformat(quiz_data["created_at"])
        )
        
        # Evaluate quiz
        logger.info(f"Evaluating quiz {request.quiz_id}")
        result = quiz_service.evaluate_quiz(
            quiz=quiz,
            answers=request.answers,
            time_taken_seconds=request.time_taken_seconds
        )
        
        # Store quiz data (updates metrics and triggers pruning)
        quiz_service.store_quiz_data(quiz, result)
        
        # Build detailed results
        detailed_results = []
        for question in quiz.questions:
            user_answer = request.answers.get(question.question_number, "")
            is_correct = user_answer == question.correct_answer
            
            detailed_results.append({
                "question_number": question.question_number,
                "question_text": question.question_text,
                "user_answer": user_answer,
                "correct_answer": question.correct_answer,
                "is_correct": is_correct,
                "explanation": question.explanation
            })
        
        logger.info(f"Quiz evaluation complete: score={result.score}/{len(quiz.questions)}")
        
        return QuizResultResponse(
            success=True,
            quiz_id=result.quiz_id,
            module_id=result.module_id,
            score=result.score,
            accuracy=result.accuracy,
            time_taken_seconds=result.time_taken_seconds,
            time_limit_exceeded=result.time_limit_exceeded,
            correct_answers=result.correct_answers,
            incorrect_answers=result.incorrect_answers,
            detailed_results=detailed_results
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except ValueError as e:
        # Validation errors
        logger.error(f"Quiz submission validation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Quiz submission failed: {str(e)}"
        )
    except Exception as e:
        # Unexpected errors
        logger.error(f"Unexpected error submitting quiz: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while submitting the quiz"
        )


@router.get("/history/{module_id}", status_code=status.HTTP_200_OK)
async def get_quiz_history(module_id: str) -> Dict[str, Any]:
    """
    Retrieve quiz history (last 2 Q&As) for a module.
    
    This endpoint returns the last 2 quizzes' full Q&A data.
    Older quizzes are automatically pruned.
    
    Args:
        module_id: Module identifier
        
    Returns:
        Dictionary with quiz history (last 2 quizzes)
        
    Raises:
        HTTPException 404: If no quiz history found
    """
    try:
        logger.info(f"Quiz history requested for module: {module_id}")
        
        # Validate module exists
        _get_module_from_roadmap(module_id)
        
        # Get quiz history
        quiz_history = cache_service.get_quiz_history(module_id)
        
        if not quiz_history:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No quiz history found for module '{module_id}'"
            )
        
        logger.info(f"Retrieved {len(quiz_history)} quizzes for module {module_id}")
        
        return {
            "success": True,
            "module_id": module_id,
            "quiz_count": len(quiz_history),
            "quizzes": quiz_history
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving quiz history: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while retrieving quiz history"
        )


@router.get("/metrics/{module_id}", response_model=QuizMetricsResponse, status_code=status.HTTP_200_OK)
async def get_quiz_metrics(module_id: str) -> QuizMetricsResponse:
    """
    Retrieve quiz metrics for a module.
    
    This endpoint returns all historical quiz metrics.
    Metrics are retained permanently regardless of Q&A pruning.
    
    Args:
        module_id: Module identifier
        
    Returns:
        QuizMetricsResponse with aggregated metrics
        
    Raises:
        HTTPException 404: If no metrics found
    """
    try:
        logger.info(f"Quiz metrics requested for module: {module_id}")
        
        # Validate module exists
        _get_module_from_roadmap(module_id)
        
        # Get quiz metrics
        metrics = cache_service.get_quiz_metrics(module_id)
        
        if not metrics:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No quiz metrics found for module '{module_id}'"
            )
        
        # Get quiz history for metrics_history
        quiz_history = cache_service.get_quiz_history(module_id) or []
        metrics_history = []
        
        for quiz in quiz_history:
            if "result" in quiz:
                result = quiz["result"]
                metrics_history.append({
                    "quiz_id": quiz["quiz_id"],
                    "score": result["score"],
                    "accuracy": result["accuracy"],
                    "time_taken_seconds": result["time_taken_seconds"],
                    "submitted_at": result["submitted_at"]
                })
        
        logger.info(f"Retrieved metrics for module {module_id}: {metrics['total_quizzes']} quizzes")
        
        return QuizMetricsResponse(
            success=True,
            module_id=metrics["module_id"],
            total_quizzes=metrics["total_quizzes"],
            average_score=metrics["average_score"],
            best_score=metrics["best_score"],
            worst_score=metrics["worst_score"],
            average_accuracy=metrics["average_accuracy"],
            metrics_history=metrics_history
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving quiz metrics: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while retrieving quiz metrics"
        )
