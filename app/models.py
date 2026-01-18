"""
Core data models for the Cognitive AI Learning Platform.
Defines Pydantic models for requests, responses, and domain entities.
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum
from fastapi import UploadFile


class ErrorType(str, Enum):
    """Error type classification for consistent error handling."""
    VALIDATION = "validation"
    PROCESSING = "processing"
    NOT_FOUND = "not_found"
    SERVICE_UNAVAILABLE = "service_unavailable"


class ErrorResponse(BaseModel):
    """
    Standard error response format for all API errors.
    
    Provides consistent error structure across the application.
    """
    success: bool = False
    error_type: ErrorType
    message: str = Field(..., description="User-friendly error message")
    details: Optional[Dict[str, Any]] = Field(
        None, 
        description="Additional error context or field-specific errors"
    )
    timestamp: datetime = Field(default_factory=datetime.now)
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "success": False,
                "error_type": "validation",
                "message": "Invalid file format",
                "details": {
                    "field": "file",
                    "supported_formats": [".pdf", ".ppt", ".pptx", ".doc", ".docx"]
                },
                "timestamp": "2024-01-07T10:30:00"
            }
        }
    }


class SuccessResponse(BaseModel):
    """
    Standard success response format for simple operations.
    
    Used for operations that don't return specific data.
    """
    success: bool = True
    message: str = Field(..., description="Success message")
    timestamp: datetime = Field(default_factory=datetime.now)
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "success": True,
                "message": "Operation completed successfully",
                "timestamp": "2024-01-07T10:30:00"
            }
        }
    }



# Input Processing Models

class InputType(str, Enum):
    """Type of educational input content."""
    SYLLABUS = "syllabus"
    QUESTION_BANK = "question_bank"
    MIXED = "mixed"


class InputData(BaseModel):
    """
    Processed input data with extracted content.
    
    Represents the result of processing uploaded files or text input.
    """
    input_id: str = Field(..., description="Unique identifier for this input")
    detected_type: InputType = Field(..., description="Detected type of input content")
    extracted_text: str = Field(..., description="Extracted and normalized text content")
    original_filename: Optional[str] = Field(None, description="Original filename if uploaded")
    processed_at: datetime = Field(default_factory=datetime.now, description="Processing timestamp")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "input_id": "input_abc123",
                "detected_type": "syllabus",
                "extracted_text": "Introduction to Computer Science...",
                "original_filename": "cs101_syllabus.pdf",
                "processed_at": "2024-01-07T10:30:00"
            }
        }
    }


class TextInputRequest(BaseModel):
    """Request model for direct text input."""
    content: str = Field(..., min_length=1, description="Text content to process")
    input_type: Optional[InputType] = Field(None, description="Optional hint for input type")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "content": "Week 1: Introduction to Python\nWeek 2: Data Structures...",
                "input_type": "syllabus"
            }
        }
    }


class InputProcessingResponse(BaseModel):
    """Response model for input processing operations."""
    success: bool = True
    input_id: str = Field(..., description="Unique identifier for the processed input")
    detected_type: InputType = Field(..., description="Detected type of input content")
    extracted_text_length: int = Field(..., description="Length of extracted text in characters")
    message: str = Field(..., description="Processing status message")
    original_filename: Optional[str] = Field(None, description="Original filename if uploaded")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "success": True,
                "input_id": "input_abc123",
                "detected_type": "syllabus",
                "extracted_text_length": 1523,
                "message": "File processed successfully",
                "original_filename": "cs101_syllabus.pdf"
            }
        }
    }


# Roadmap Models

class LearningMode(str, Enum):
    """Learning mode for roadmaps and quizzes."""
    TIMED = "timed"
    UNTIMED = "untimed"


class Module(BaseModel):
    """
    A discrete learning unit within a subject roadmap.
    
    Each module has a stable identifier that persists across sessions.
    """
    module_id: str = Field(..., description="Stable unique identifier for the module")
    topic_name: str = Field(..., min_length=1, max_length=200, description="Name of the topic")
    estimated_hours: float = Field(..., gt=0, le=100, description="Estimated hours to complete")
    prerequisites: list[str] = Field(default_factory=list, description="List of prerequisite module_ids")
    order: int = Field(..., ge=1, description="Sequential order in the roadmap")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "module_id": "mod_abc123",
                "topic_name": "Introduction to Python",
                "estimated_hours": 5.0,
                "prerequisites": [],
                "order": 1
            }
        }
    }


class RoadmapGenerateRequest(BaseModel):
    """Request model for generating a roadmap."""
    input_id: str = Field(..., description="ID of the processed input to generate roadmap from")
    mode: LearningMode = Field(default=LearningMode.UNTIMED, description="Learning mode (timed or untimed)")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "input_id": "input_abc123",
                "mode": "untimed"
            }
        }
    }


class RoadmapResponse(BaseModel):
    """Response model for roadmap operations."""
    success: bool = True
    modules: list[Module] = Field(..., description="List of modules in the roadmap")
    total_modules: int = Field(..., description="Total number of modules")
    total_estimated_hours: float = Field(..., description="Total estimated hours for all modules")
    mode: LearningMode = Field(..., description="Learning mode for this roadmap")
    cached: bool = Field(default=False, description="Whether this roadmap was retrieved from cache")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "success": True,
                "modules": [
                    {
                        "module_id": "mod_abc123",
                        "topic_name": "Introduction to Python",
                        "estimated_hours": 5.0,
                        "prerequisites": [],
                        "order": 1
                    }
                ],
                "total_modules": 1,
                "total_estimated_hours": 5.0,
                "mode": "untimed",
                "cached": False
            }
        }
    }


# Content Generation Models

class ModuleContent(BaseModel):
    """
    Generated content for a learning module.
    
    Contains detailed notes and concise cheat sheets for study.
    """
    module_id: str = Field(..., description="Module identifier")
    notes: Optional[str] = Field(None, description="Detailed notes for the module")
    cheat_sheet: Optional[str] = Field(None, description="Concise cheat sheet for quick reference")
    generated_at: datetime = Field(default_factory=datetime.now, description="Generation timestamp")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "module_id": "mod_abc123",
                "notes": "Detailed explanation of Python basics...",
                "cheat_sheet": "Quick reference: variables, loops, functions...",
                "generated_at": "2024-01-07T10:30:00"
            }
        }
    }


class NotesResponse(BaseModel):
    """Response model for notes generation."""
    success: bool = True
    module_id: str = Field(..., description="Module identifier")
    notes: str = Field(..., description="Generated notes content")
    cached: bool = Field(default=False, description="Whether notes were retrieved from cache")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "success": True,
                "module_id": "mod_abc123",
                "notes": "Detailed explanation of Python basics...",
                "cached": False
            }
        }
    }


class CheatSheetResponse(BaseModel):
    """Response model for cheat sheet generation."""
    success: bool = True
    module_id: str = Field(..., description="Module identifier")
    cheat_sheet: str = Field(..., description="Generated cheat sheet content")
    cached: bool = Field(default=False, description="Whether cheat sheet was retrieved from cache")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "success": True,
                "module_id": "mod_abc123",
                "cheat_sheet": "Quick reference: variables, loops, functions...",
                "cached": False
            }
        }
    }


# Quiz Models

class QuizQuestion(BaseModel):
    """
    A single multiple-choice question in a quiz.
    
    Each question has exactly 4 options.
    
    LIFECYCLE:
    - Generation: Only question_text and options are generated
    - Evaluation: correct_answer and explanation are generated on-demand
    
    BACKWARD COMPATIBILITY:
    - Old quizzes may have correct_answer and explanation embedded
    - New quizzes will have these fields as None until evaluation
    """
    question_number: int = Field(..., ge=1, le=5, description="Question number (1-5)")
    question_text: str = Field(..., min_length=10, description="The question text")
    options: list[str] = Field(..., min_length=4, max_length=4, description="Exactly 4 answer options")
    correct_answer: Optional[str] = Field(None, description="The correct answer (generated during evaluation)")
    explanation: Optional[str] = Field(None, max_length=200, description="One-line explanation (generated during evaluation)")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "question_number": 1,
                "question_text": "What is the output of print(2 ** 3) in Python?",
                "options": ["6", "8", "9", "16"],
                "correct_answer": None,
                "explanation": None
            }
        }
    }


class Quiz(BaseModel):
    """
    A complete quiz for a module.
    
    Contains exactly 5 questions and can be timed or untimed.
    Quiz ID is deterministic based on module_id and creation timestamp.
    
    LIFECYCLE:
    - Generation: Questions without correct answers/explanations
    - Submission: User answers stored separately
    - Evaluation: Correct answers generated and compared with user answers
    """
    quiz_id: str = Field(..., description="Deterministic quiz identifier")
    module_id: str = Field(..., description="Module this quiz belongs to")
    questions: list[QuizQuestion] = Field(..., min_length=5, max_length=5, description="Exactly 5 questions")
    mode: LearningMode = Field(..., description="Quiz mode (timed or untimed)")
    time_limit_seconds: Optional[int] = Field(None, gt=0, description="Time limit in seconds (for timed mode)")
    created_at: datetime = Field(default_factory=datetime.now, description="Quiz creation timestamp")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "quiz_id": "quiz_abc123def456",
                "module_id": "mod_abc123",
                "questions": [],  # List of 5 QuizQuestion objects
                "mode": "timed",
                "time_limit_seconds": 600,
                "created_at": "2024-01-07T10:30:00.123456"
            }
        }
    }


class QuizSubmission(BaseModel):
    """
    User's submitted answers before evaluation.
    
    LIFECYCLE:
    - Created when user submits quiz answers
    - Stored separately from quiz questions
    - Used later during evaluation to compare with correct answers
    
    RETRY SUPPORT:
    - attempt_number tracks multiple attempts on same quiz
    - Same questions reused across attempts (resource-aware design)
    - Each attempt has its own submission and evaluation
    
    This model separates answer submission from evaluation, enabling:
    - Deferred evaluation (user controls when to see results)
    - Better analytics (explicit submission tracking)
    - Flexible evaluation strategies
    - Multiple retry attempts per quiz
    """
    submission_id: str = Field(..., description="Unique submission identifier")
    quiz_id: str = Field(..., description="Quiz identifier")
    module_id: str = Field(..., description="Module identifier")
    attempt_number: int = Field(default=1, ge=1, description="Attempt number (1-based, supports retries)")
    user_answers: Dict[int, str] = Field(..., description="Map of question_number to selected_option")
    time_taken_seconds: int = Field(..., ge=0, description="Time taken to complete quiz")
    submitted_at: datetime = Field(default_factory=datetime.now, description="Submission timestamp")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "submission_id": "sub_abc123def456",
                "quiz_id": "quiz_abc123def456",
                "module_id": "mod_abc123",
                "attempt_number": 1,
                "user_answers": {
                    1: "8",
                    2: "list",
                    3: "True",
                    4: "O(n)",
                    5: "def"
                },
                "time_taken_seconds": 450,
                "submitted_at": "2024-01-07T10:45:00"
            }
        }
    }


class QuestionResult(BaseModel):
    """
    Evaluation result for a single question.
    
    Contains the question, user's answer, correct answer, and explanation.
    Used in QuizEvaluation to provide detailed per-question feedback.
    """
    question_number: int = Field(..., ge=1, le=5, description="Question number")
    question_text: str = Field(..., description="The question text")
    options: list[str] = Field(..., description="Answer options")
    user_answer: str = Field(..., description="User's selected answer")
    correct_answer: str = Field(..., description="The correct answer")
    is_correct: bool = Field(..., description="Whether user's answer is correct")
    explanation: str = Field(..., max_length=180, description="Explanation of the correct answer (max 180 chars)")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "question_number": 1,
                "question_text": "What is the output of print(2 ** 3) in Python?",
                "options": ["6", "8", "9", "16"],
                "user_answer": "8",
                "correct_answer": "8",
                "is_correct": True,
                "explanation": "The ** operator performs exponentiation, so 2^3 = 8"
            }
        }
    }


class QuizEvaluation(BaseModel):
    """
    Evaluation results with correct answers and scoring.
    
    LIFECYCLE:
    - Created when user explicitly requests evaluation
    - Correct answers and explanations generated by LLM during evaluation
    - Stored permanently for analytics and future reference
    
    RETRY SUPPORT:
    - attempt_number tracks which attempt this evaluation is for
    - Each attempt has its own evaluation (cached separately)
    - Same questions reused, but answers can differ per attempt
    
    This model enables:
    - Explicit evaluation on user demand
    - Permanent storage of evaluation results
    - Rich analytics and progress tracking
    - Re-viewing results without re-evaluation
    - Multiple retry attempts with separate evaluations
    """
    evaluation_id: str = Field(..., description="Unique evaluation identifier")
    quiz_id: str = Field(..., description="Quiz identifier")
    module_id: str = Field(..., description="Module identifier")
    attempt_number: int = Field(default=1, ge=1, description="Attempt number (1-based, supports retries)")
    
    # Scoring
    score: int = Field(..., ge=0, le=5, description="Score out of 5")
    accuracy: float = Field(..., ge=0, le=100, description="Accuracy percentage")
    correct_answers_count: int = Field(..., ge=0, le=5, description="Number of correct answers")
    incorrect_answers_count: int = Field(..., ge=0, le=5, description="Number of incorrect answers")
    
    # Per-question results
    question_results: List[QuestionResult] = Field(..., description="Detailed results for each question")
    
    # Metadata
    time_taken_seconds: int = Field(..., ge=0, description="Time taken to complete quiz")
    time_limit_exceeded: bool = Field(default=False, description="Whether time limit was exceeded")
    evaluated_at: datetime = Field(default_factory=datetime.now, description="Evaluation timestamp")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "evaluation_id": "eval_abc123def456",
                "quiz_id": "quiz_abc123def456",
                "module_id": "mod_abc123",
                "attempt_number": 1,
                "score": 4,
                "accuracy": 80.0,
                "correct_answers_count": 4,
                "incorrect_answers_count": 1,
                "question_results": [],
                "time_taken_seconds": 450,
                "time_limit_exceeded": False,
                "evaluated_at": "2024-01-07T10:50:00"
            }
        }
    }


class QuizResult(BaseModel):
    """
    Results from a completed quiz submission.
    
    Tracks score, accuracy, time taken, and whether time limit was exceeded.
    """
    quiz_id: str = Field(..., description="Quiz identifier")
    module_id: str = Field(..., description="Module identifier")
    score: int = Field(..., ge=0, le=5, description="Score out of 5")
    accuracy: float = Field(..., ge=0, le=100, description="Accuracy percentage")
    time_taken_seconds: int = Field(..., ge=0, description="Time taken to complete quiz")
    time_limit_exceeded: bool = Field(default=False, description="Whether time limit was exceeded (for timed quizzes)")
    correct_answers: int = Field(..., ge=0, le=5, description="Number of correct answers")
    incorrect_answers: int = Field(..., ge=0, le=5, description="Number of incorrect answers")
    submitted_at: datetime = Field(default_factory=datetime.now, description="Submission timestamp")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "quiz_id": "quiz_abc123def456",
                "module_id": "mod_abc123",
                "score": 8,
                "accuracy": 80.0,
                "time_taken_seconds": 450,
                "time_limit_exceeded": False,
                "correct_answers": 8,
                "incorrect_answers": 2,
                "submitted_at": "2024-01-07T10:45:00"
            }
        }
    }


class QuizMetrics(BaseModel):
    """
    Aggregated metrics for all quizzes taken on a module.
    
    Retained permanently regardless of Q&A pruning.
    """
    module_id: str = Field(..., description="Module identifier")
    total_quizzes: int = Field(..., ge=0, description="Total number of quizzes taken")
    average_score: float = Field(..., ge=0, le=5, description="Average score across all quizzes")
    best_score: int = Field(..., ge=0, le=5, description="Best score achieved")
    worst_score: int = Field(..., ge=0, le=5, description="Worst score achieved")
    average_accuracy: float = Field(..., ge=0, le=100, description="Average accuracy percentage")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "module_id": "mod_abc123",
                "total_quizzes": 5,
                "average_score": 7.4,
                "best_score": 9,
                "worst_score": 6,
                "average_accuracy": 74.0
            }
        }
    }


class QuizGenerateRequest(BaseModel):
    """Request model for generating a new quiz."""
    mode: LearningMode = Field(default=LearningMode.UNTIMED, description="Quiz mode (timed or untimed)")
    time_limit_seconds: Optional[int] = Field(None, gt=0, description="Time limit in seconds (required for timed mode)")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "mode": "timed",
                "time_limit_seconds": 600
            }
        }
    }


class QuizSubmitRequest(BaseModel):
    """Request model for submitting quiz answers."""
    quiz_id: str = Field(..., description="Quiz identifier")
    answers: Dict[int, str] = Field(..., description="Map of question_number to selected_option")
    time_taken_seconds: int = Field(..., ge=0, description="Time taken to complete quiz")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "quiz_id": "quiz_abc123def456",
                "answers": {
                    1: "8",
                    2: "list",
                    3: "True"
                },
                "time_taken_seconds": 450
            }
        }
    }


class QuizResponse(BaseModel):
    """Response model for quiz generation."""
    success: bool = True
    quiz_id: str = Field(..., description="Quiz identifier")
    module_id: str = Field(..., description="Module identifier")
    questions: list[QuizQuestion] = Field(..., description="List of 5 quiz questions")
    mode: LearningMode = Field(..., description="Quiz mode")
    time_limit_seconds: Optional[int] = Field(None, description="Time limit in seconds (for timed mode)")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "success": True,
                "quiz_id": "quiz_abc123def456",
                "module_id": "mod_abc123",
                "questions": [],  # List of 10 QuizQuestion objects
                "mode": "timed",
                "time_limit_seconds": 600
            }
        }
    }


class QuizResultResponse(BaseModel):
    """Response model for quiz submission results."""
    success: bool = True
    quiz_id: str = Field(..., description="Quiz identifier")
    module_id: str = Field(..., description="Module identifier")
    score: int = Field(..., description="Score out of 5")
    accuracy: float = Field(..., description="Accuracy percentage")
    time_taken_seconds: int = Field(..., description="Time taken")
    time_limit_exceeded: bool = Field(..., description="Whether time limit was exceeded")
    correct_answers: int = Field(..., description="Number of correct answers")
    incorrect_answers: int = Field(..., description="Number of incorrect answers")
    detailed_results: list[Dict[str, Any]] = Field(..., description="Per-question results with correctness")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "success": True,
                "quiz_id": "quiz_abc123def456",
                "module_id": "mod_abc123",
                "score": 8,
                "accuracy": 80.0,
                "time_taken_seconds": 450,
                "time_limit_exceeded": False,
                "correct_answers": 8,
                "incorrect_answers": 2,
                "detailed_results": [
                    {
                        "question_number": 1,
                        "user_answer": "8",
                        "correct_answer": "8",
                        "is_correct": True,
                        "explanation": "The ** operator performs exponentiation"
                    }
                ]
            }
        }
    }


class QuizMetricsResponse(BaseModel):
    """Response model for quiz metrics retrieval."""
    success: bool = True
    module_id: str = Field(..., description="Module identifier")
    total_quizzes: int = Field(..., description="Total quizzes taken")
    average_score: float = Field(..., description="Average score")
    best_score: int = Field(..., description="Best score")
    worst_score: int = Field(..., description="Worst score")
    average_accuracy: float = Field(..., description="Average accuracy")
    metrics_history: list[Dict[str, Any]] = Field(..., description="All historical metrics")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "success": True,
                "module_id": "mod_abc123",
                "total_quizzes": 5,
                "average_score": 7.4,
                "best_score": 9,
                "worst_score": 6,
                "average_accuracy": 74.0,
                "metrics_history": [
                    {
                        "quiz_id": "quiz_001",
                        "score": 8,
                        "accuracy": 80.0,
                        "submitted_at": "2024-01-07T10:00:00"
                    }
                ]
            }
        }
    }


# Analytics Models

class ModuleProgress(BaseModel):
    """
    Progress tracking for a single module.
    
    Tracks completion percentage, quiz performance, and learning metrics.
    """
    module_id: str = Field(..., description="Module identifier")
    topic_name: str = Field(..., description="Module topic name")
    completion_percentage: float = Field(..., ge=0, le=100, description="Completion percentage (0-100)")
    quizzes_taken: int = Field(..., ge=0, description="Number of quizzes taken")
    average_accuracy: float = Field(..., ge=0, le=100, description="Average quiz accuracy percentage")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "module_id": "mod_abc123",
                "topic_name": "Introduction to Python",
                "completion_percentage": 75.0,
                "quizzes_taken": 3,
                "average_accuracy": 82.5
            }
        }
    }


class AnalyticsOverviewResponse(BaseModel):
    """Response model for overall analytics overview."""
    success: bool = True
    overall_progress: float = Field(..., ge=0, le=100, description="Overall progress percentage")
    modules_completed: int = Field(..., ge=0, description="Number of modules completed")
    total_modules: int = Field(..., ge=0, description="Total number of modules")
    average_quiz_accuracy: float = Field(..., ge=0, le=100, description="Average quiz accuracy across all modules")
    module_progress: list[ModuleProgress] = Field(..., description="Progress for each module")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "success": True,
                "overall_progress": 60.0,
                "modules_completed": 3,
                "total_modules": 5,
                "average_quiz_accuracy": 78.5,
                "module_progress": [
                    {
                        "module_id": "mod_abc123",
                        "topic_name": "Introduction to Python",
                        "completion_percentage": 100.0,
                        "quizzes_taken": 3,
                        "average_accuracy": 82.5
                    }
                ]
            }
        }
    }


class WeakAreasResponse(BaseModel):
    """Response model for weak areas identification."""
    success: bool = True
    weak_modules: list[Dict[str, Any]] = Field(..., description="Modules with accuracy below threshold")
    recommendations: list[str] = Field(..., description="Recommendations for improvement")
    threshold: float = Field(default=60.0, description="Accuracy threshold used for identification")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "success": True,
                "weak_modules": [
                    {
                        "module_id": "mod_abc123",
                        "topic_name": "Advanced Python",
                        "average_accuracy": 55.0,
                        "quizzes_taken": 2
                    }
                ],
                "recommendations": [
                    "Review notes for 'Advanced Python'",
                    "Retake quizzes for 'Advanced Python' to improve understanding"
                ],
                "threshold": 60.0
            }
        }
    }


class QuizAttemptData(BaseModel):
    """Data for a single quiz attempt."""
    attempt_number: int = Field(..., ge=1, description="Attempt number (1, 2, 3, ...)")
    score: int = Field(..., ge=0, description="Raw score (number of correct answers)")
    accuracy: float = Field(..., ge=0, le=100, description="Accuracy percentage")
    time_taken_seconds: int = Field(..., ge=0, description="Time taken in seconds")
    evaluated_at: str = Field(..., description="Evaluation timestamp (ISO format)")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "attempt_number": 1,
                "score": 3,
                "accuracy": 60.0,
                "time_taken_seconds": 20,
                "evaluated_at": "2026-01-19T10:30:00"
            }
        }
    }


class QuizAttemptHistoryResponse(BaseModel):
    """Response model for quiz attempt history analytics."""
    success: bool = True
    quiz_id: str = Field(..., description="Quiz identifier")
    module_id: str = Field(..., description="Module identifier")
    attempts: list[QuizAttemptData] = Field(..., description="List of attempts ordered by attempt_number")
    improvement_rate: Optional[float] = Field(None, description="Improvement rate from first to latest attempt (%)")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "success": True,
                "quiz_id": "quiz_abc123",
                "module_id": "mod_xyz789",
                "attempts": [
                    {
                        "attempt_number": 1,
                        "score": 2,
                        "accuracy": 40.0,
                        "time_taken_seconds": 20,
                        "evaluated_at": "2026-01-19T10:30:00"
                    },
                    {
                        "attempt_number": 2,
                        "score": 4,
                        "accuracy": 80.0,
                        "time_taken_seconds": 15,
                        "evaluated_at": "2026-01-19T11:00:00"
                    }
                ],
                "improvement_rate": 100.0
            }
        }
    }


# Doubt Resolution Models

class DoubtRequest(BaseModel):
    """Request model for asking a doubt/question about a module."""
    module_id: str = Field(..., description="Module identifier for context")
    question: str = Field(..., min_length=5, max_length=500, description="Question to ask")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "module_id": "mod_abc123",
                "question": "What is the difference between a list and a tuple in Python?"
            }
        }
    }


class DoubtResponse(BaseModel):
    """Response model for doubt resolution."""
    success: bool = True
    module_id: str = Field(..., description="Module identifier")
    question: str = Field(..., description="Original question")
    answer: str = Field(..., description="Answer to the question")
    in_scope: bool = Field(..., description="Whether question is within module scope")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "success": True,
                "module_id": "mod_abc123",
                "question": "What is the difference between a list and a tuple in Python?",
                "answer": "A list is mutable (can be modified after creation) while a tuple is immutable (cannot be modified). Lists use square brackets [] while tuples use parentheses ().",
                "in_scope": True
            }
        }
    }


# Session Management Models

class SessionData(BaseModel):
    """
    Session state data for tracking user progress across the platform.
    
    Maintains session information including current state, progress tracking,
    and module completion status.
    """
    session_id: str = Field(..., description="Unique session identifier")
    created_at: datetime = Field(default_factory=datetime.now, description="Session creation timestamp")
    last_accessed: datetime = Field(default_factory=datetime.now, description="Last access timestamp")
    current_input_id: Optional[str] = Field(None, description="Current input identifier")
    roadmap_generated: bool = Field(default=False, description="Whether roadmap has been generated")
    current_module_id: Optional[str] = Field(None, description="Currently active module")
    modules_completed: list[str] = Field(default_factory=list, description="List of completed module IDs")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "session_id": "session_abc123def456",
                "created_at": "2024-01-07T10:00:00",
                "last_accessed": "2024-01-07T15:30:00",
                "current_input_id": "input_xyz789",
                "roadmap_generated": True,
                "current_module_id": "mod_abc123",
                "modules_completed": ["mod_abc123", "mod_def456"]
            }
        }
    }
