"""
Main FastAPI application for the Cognitive AI Learning Platform.

This module initializes the FastAPI application, configures middleware,
and registers all API routers.
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from contextlib import asynccontextmanager
import logging

from app.config import settings
from app.logging_config import setup_logging, get_logger
from app.models import ErrorResponse, ErrorType


# Setup logging before anything else
setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    
    Handles startup and shutdown events for the application.
    """
    # Startup
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    logger.info(f"Cache directory: {settings.cache_dir}")
    logger.info(f"Ollama URL: {settings.ollama_base_url}")
    logger.info(f"Ollama Model: {settings.ollama_model}")
    
    # Initialize cache service and verify directory structure
    from app.services.cache_service import cache_service
    cache_service._ensure_cache_structure()
    logger.info("Cache directory structure verified")
    
    # Initialize or load session
    from app.services.session_service import session_service
    session = session_service.get_or_create_session()
    logger.info(f"Session initialized: {session.session_id}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down application")
    # No cleanup needed - all data is persisted to cache


# Initialize FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Backend API for personalized learning with local LLM integration",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)


# Exception Handlers

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Handle Pydantic validation errors with consistent error format.
    
    Converts validation errors into user-friendly error responses.
    """
    logger.warning(f"Validation error on {request.url.path}: {exc.errors()}")
    
    # Extract field-specific errors
    error_details = {}
    for error in exc.errors():
        field = ".".join(str(loc) for loc in error["loc"] if loc != "body")
        error_details[field] = error["msg"]
    
    error_response = ErrorResponse(
        error_type=ErrorType.VALIDATION,
        message="Request validation failed",
        details=error_details
    )
    
    return JSONResponse(
        status_code=422,
        content=error_response.model_dump(mode='json')
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """
    Handle unexpected exceptions with generic error response.
    
    Logs the full error for debugging while returning user-friendly message.
    """
    logger.error(f"Unexpected error on {request.url.path}: {str(exc)}", exc_info=True)
    
    error_response = ErrorResponse(
        error_type=ErrorType.PROCESSING,
        message="An internal error occurred. Please try again later.",
        details={"path": str(request.url.path)} if settings.debug else None
    )
    
    return JSONResponse(
        status_code=500,
        content=error_response.model_dump(mode='json')
    )


# Health Check Endpoint

@app.get("/health", tags=["System"])
async def health_check():
    """
    Health check endpoint to verify the service is running.
    
    Returns:
        Simple status response
    """
    return {
        "status": "healthy",
        "service": settings.app_name,
        "version": settings.app_version
    }


@app.get("/", tags=["System"])
async def root():
    """
    Root endpoint with API information.
    
    Returns:
        Welcome message and API documentation links
    """
    return {
        "message": f"Welcome to {settings.app_name}",
        "version": settings.app_version,
        "docs": "/docs",
        "redoc": "/redoc"
    }


# Router Registration
from app.routers import input as input_router
from app.routers import roadmap as roadmap_router
from app.routers import content as content_router
from app.routers import quiz as quiz_router
from app.routers import analytics as analytics_router
from app.routers import doubt as doubt_router
from app.routers import session as session_router

app.include_router(input_router.router, prefix="/api/input", tags=["Input"])
app.include_router(roadmap_router.router)
app.include_router(content_router.router)
app.include_router(quiz_router.router)
app.include_router(analytics_router.router)
app.include_router(doubt_router.router)
app.include_router(session_router.router)


if __name__ == "__main__":
    import uvicorn
    
    logger.info(f"Starting server on {settings.host}:{settings.port}")
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )
