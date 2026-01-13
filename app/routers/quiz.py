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
    
    Implements strict fallback order (OPTIMIZED FOR PERFORMANCE):
    1. Module Cheat Sheet (preferred - concise, focused, faster LLM processing)
    2. Module Notes (fallback - comprehensive but longer)
    3. Module syllabus scope only (last resort - prevents failure)
    
    NEVER concatenates multiple sources - uses FIRST available only.
    
    Rationale for cheat sheet priority:
    - Cheat sheets are concise summaries of key concepts
    - Shorter content = faster LLM processing = reduced latency
    - Focused content = better quiz relevance = fewer validation failures
    - Still module-scoped and educationally sound
    
    Args:
        module_id: Module identifier
        
    Returns:
        Module content text
        
    Raises:
        HTTPException 404: If no content available
    """
    # Priority 1: Try module cheat sheet (PREFERRED - concise and fast)
    cheat_sheet = cache_service.get_cached_content(module_id, 'cheatsheet')
    if cheat_sheet:
        logger.info(f"Quiz generation using CHEAT SHEET for module {module_id} (preferred source)")
        return cheat_sheet
    
    # Priority 2: Try module notes (fallback - comprehensive but longer)
    notes = cache_service.get_cached_content(module_id, 'notes')
    if notes:
        logger.info(f"Quiz generation using NOTES for module {module_id} (fallback source)")
        return notes
    
    # Priority 3: Use module syllabus scope only (last resort)
    # Extract only the relevant module section from input text
    roadmap_data = cache_service.get_cached_roadmap()
    if not roadmap_data or "input_id" not in roadmap_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No content available for quiz generation. Please generate cheat sheet or notes first."
        )
    
    input_id = roadmap_data["input_id"]
    cached_input = cache_service.get_cached_data(input_id, 'input')
    
    if not cached_input or 'extracted_text' not in cached_input:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Input text not found for ID '{input_id}'"
        )
    
    # Get module details to extract relevant section
    module = _get_module_from_roadmap(module_id)
    input_text = cached_input['extracted_text']
    
    # Use full input text as module syllabus scope
    # Note: This is module-scoped in the sense that the LLM prompt will focus on the module topic
    # The LLM service will be instructed to generate questions only about the specific module topic
    logger.info(f"Quiz generation using SYLLABUS SCOPE for module {module_id} (last resort - recommend generating cheat sheet)")
    return input_text


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


@router.post("/submit/{module_id}", status_code=status.HTTP_200_OK)
async def submit_quiz(
    module_id: str, 
    request: QuizSubmitRequest = Body(...),
    attempt_number: int = 1
) -> Dict[str, Any]:
    """
    Submit quiz answers WITHOUT evaluation (Phase 3 - Deferred Evaluation).
    
    RETRY SUPPORT:
    - attempt_number parameter tracks multiple attempts on same quiz
    - Same questions reused across attempts (resource-aware design)
    
    This endpoint:
    1. Validates that the quiz exists
    2. Stores the submission (answers + time taken + attempt_number)
    3. Returns submission confirmation
    
    Evaluation happens later when user calls /evaluate/{quiz_id}.
    
    Args:
        module_id: Module identifier (from path)
        request: Quiz submission with quiz_id, answers, and time_taken
        attempt_number: Attempt number (default: 1 for backward compatibility)
        
    Returns:
        Dictionary with submission confirmation
        
    Raises:
        HTTPException 404: If quiz not found
        HTTPException 400: If validation fails
        HTTPException 500: If submission storage fails
    """
    try:
        logger.info(f"Quiz submission received for quiz: {request.quiz_id}, attempt {attempt_number}")
        
        # Validate that quiz exists
        quiz_history = cache_service.get_quiz_history(module_id)
        if not quiz_history:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No quiz history found for module '{module_id}'"
            )
        
        # Find the specific quiz
        quiz_exists = any(q.get("quiz_id") == request.quiz_id for q in quiz_history)
        if not quiz_exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Quiz '{request.quiz_id}' not found in history"
            )
        
        # Store submission (no evaluation yet)
        submission_id = quiz_service.submit_quiz_submission(
            quiz_id=request.quiz_id,
            module_id=module_id,
            user_answers=request.answers,
            time_taken_seconds=request.time_taken_seconds,
            attempt_number=attempt_number
        )
        
        logger.info(f"Quiz submission stored: {submission_id} (attempt {attempt_number})")
        
        return {
            "success": True,
            "message": "Quiz submitted successfully",
            "submission_id": submission_id,
            "quiz_id": request.quiz_id,
            "module_id": module_id,
            "attempt_number": attempt_number
        }
        
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


@router.post("/evaluate/{quiz_id}", status_code=status.HTTP_200_OK)
async def evaluate_quiz(quiz_id: str, attempt_number: int = 1) -> Dict[str, Any]:
    """
    Evaluate a submitted quiz on-demand (Phase 3 - Deferred Evaluation).
    
    RETRY SUPPORT:
    - attempt_number parameter specifies which attempt to evaluate
    - Each attempt has its own evaluation (cached separately)
    
    This endpoint:
    1. Retrieves quiz questions and submission (by quiz_id and attempt_number)
    2. Checks if legacy quiz (has correct_answer) → use embedded answers
    3. If new quiz → generates answers with LLM
    4. Computes score, accuracy, per-question results
    5. Stores evaluation for future retrieval
    6. Returns detailed evaluation results
    
    Args:
        quiz_id: Quiz identifier (from path)
        attempt_number: Attempt number (default: 1 for backward compatibility)
        
    Returns:
        Dictionary with evaluation results
        
    Raises:
        HTTPException 404: If quiz or submission not found
        HTTPException 503: If LLM service fails
        HTTPException 500: If evaluation fails
    """
    try:
        logger.info(f"Quiz evaluation requested for quiz: {quiz_id}, attempt {attempt_number}")
        
        # Check if evaluation already exists for this attempt
        existing_evaluation = quiz_service.get_quiz_evaluation(quiz_id, attempt_number)
        if existing_evaluation:
            logger.info(f"Returning cached evaluation for quiz {quiz_id}, attempt {attempt_number}")
            return {
                "success": True,
                "cached": True,
                **existing_evaluation
            }
        
        # Get module_id from quiz history (search all modules)
        module_id = None
        quiz_data = None
        roadmap_data = cache_service.get_cached_roadmap()
        
        if roadmap_data:
            for module in roadmap_data.get("modules", []):
                mod_id = module.get("module_id")
                quiz_history = cache_service.get_quiz_history(mod_id)
                if quiz_history:
                    for quiz in quiz_history:
                        if quiz.get("quiz_id") == quiz_id:
                            module_id = mod_id
                            quiz_data = quiz
                            break
                if module_id:
                    break
        
        if not module_id or not quiz_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Quiz '{quiz_id}' not found"
            )
        
        # Get module content for LLM evaluation
        content = _get_module_content(module_id)
        
        # Evaluate quiz
        evaluation = quiz_service.evaluate_quiz_submission(
            quiz_id=quiz_id,
            module_id=module_id,
            content=content,
            attempt_number=attempt_number
        )
        
        logger.info(f"Quiz evaluation complete for quiz {quiz_id}, attempt {attempt_number}")
        
        return {
            "success": True,
            "cached": False,
            **evaluation
        }
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except ValueError as e:
        # Validation errors
        logger.error(f"Quiz evaluation validation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Quiz evaluation failed: {str(e)}"
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
        logger.error(f"Unexpected error evaluating quiz: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while evaluating the quiz"
        )


@router.get("/evaluation/{quiz_id}", status_code=status.HTTP_200_OK)
async def get_quiz_evaluation(quiz_id: str, attempt_number: int = 1) -> Dict[str, Any]:
    """
    Retrieve cached quiz evaluation (Phase 3 - Deferred Evaluation).
    
    RETRY SUPPORT:
    - attempt_number parameter specifies which attempt's evaluation to retrieve
    
    This endpoint retrieves a previously computed evaluation.
    If no evaluation exists, returns 404.
    
    Args:
        quiz_id: Quiz identifier (from path)
        attempt_number: Attempt number (default: 1 for backward compatibility)
        
    Returns:
        Dictionary with evaluation results
        
    Raises:
        HTTPException 404: If evaluation not found
    """
    try:
        logger.info(f"Retrieving evaluation for quiz: {quiz_id}, attempt {attempt_number}")
        
        evaluation = quiz_service.get_quiz_evaluation(quiz_id, attempt_number)
        
        if not evaluation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No evaluation found for quiz '{quiz_id}', attempt {attempt_number}. Please evaluate the quiz first."
            )
        
        logger.info(f"Retrieved evaluation for quiz {quiz_id}, attempt {attempt_number}")
        
        return {
            "success": True,
            **evaluation
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving evaluation: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while retrieving the evaluation"
        )


@router.post("/retry/{quiz_id}", status_code=status.HTTP_200_OK)
async def retry_quiz(quiz_id: str) -> Dict[str, Any]:
    """
    Retry a quiz with a new attempt (Phase 4 - Retry Flow).
    
    RESOURCE-AWARE DESIGN:
    - Same questions reused across attempts (no regeneration)
    - Increments attempt_number for new submission/evaluation
    - Returns quiz with new attempt_number
    
    This endpoint:
    1. Validates that the quiz exists
    2. Gets latest attempt number
    3. Increments attempt_number
    4. Returns quiz with new attempt_number (questions unchanged)
    
    Args:
        quiz_id: Quiz identifier (from path)
        
    Returns:
        Dictionary with quiz data and new attempt_number
        
    Raises:
        HTTPException 404: If quiz not found
        HTTPException 500: If retry fails
    """
    try:
        logger.info(f"Quiz retry requested for quiz: {quiz_id}")
        
        # Get module_id from quiz history (search all modules)
        module_id = None
        quiz_data = None
        roadmap_data = cache_service.get_cached_roadmap()
        
        if roadmap_data:
            for module in roadmap_data.get("modules", []):
                mod_id = module.get("module_id")
                quiz_history = cache_service.get_quiz_history(mod_id)
                if quiz_history:
                    for quiz in quiz_history:
                        if quiz.get("quiz_id") == quiz_id:
                            module_id = mod_id
                            quiz_data = quiz
                            break
                if module_id:
                    break
        
        if not module_id or not quiz_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Quiz '{quiz_id}' not found"
            )
        
        # Get latest attempt number
        latest_attempt = cache_service.get_latest_attempt_number(quiz_id)
        new_attempt = latest_attempt + 1
        
        logger.info(f"Quiz retry: quiz {quiz_id}, new attempt {new_attempt}")
        
        # Return quiz with new attempt number (questions unchanged)
        return {
            "success": True,
            "message": f"Quiz retry initialized (attempt {new_attempt})",
            "quiz_id": quiz_data.get("quiz_id"),
            "module_id": module_id,
            "questions": quiz_data.get("questions", []),
            "mode": quiz_data.get("mode"),
            "time_limit_seconds": quiz_data.get("time_limit_seconds"),
            "attempt_number": new_attempt,
            "created_at": quiz_data.get("created_at")
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrying quiz: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while retrying the quiz"
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
