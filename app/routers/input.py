"""
Input router for handling file uploads and text input.

Provides API endpoints for processing educational materials.
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, status
from typing import Optional

from app.models import (
    TextInputRequest,
    InputProcessingResponse,
    InputData,
    ErrorResponse,
    ErrorType
)
from app.services.input_service import input_service
from app.services.file_processor import FileProcessingError
from app.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.post(
    "/upload",
    response_model=InputProcessingResponse,
    status_code=status.HTTP_200_OK,
    summary="Upload and process a file",
    description="Upload a PDF, PPT, PPTX, DOC, or DOCX file for processing"
)
async def upload_file(
    file: UploadFile = File(..., description="File to upload and process")
) -> InputProcessingResponse:
    """
    Upload and process an educational material file.
    
    Supported formats: PDF, PPT, PPTX, DOC, DOCX
    Maximum file size: 10 MB (configurable)
    
    Args:
        file: Uploaded file
        
    Returns:
        InputProcessingResponse with processing results
        
    Raises:
        HTTPException: If file processing fails
    """
    try:
        logger.info(f"Received file upload request: {file.filename}")
        
        # Process the file
        response = await input_service.process_file_upload(file)
        
        return response
        
    except ValueError as e:
        # Validation errors (format, size, etc.)
        logger.warning(f"File validation failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_type": ErrorType.VALIDATION,
                "message": str(e)
            }
        )
    
    except FileProcessingError as e:
        # File processing errors (extraction failed, etc.)
        logger.error(f"File processing failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_type": ErrorType.PROCESSING,
                "message": f"Failed to process file: {str(e)}"
            }
        )
    
    except Exception as e:
        # Unexpected errors
        logger.error(f"Unexpected error during file upload: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_type": ErrorType.PROCESSING,
                "message": "An unexpected error occurred while processing the file"
            }
        )


@router.post(
    "/text",
    response_model=InputProcessingResponse,
    status_code=status.HTTP_200_OK,
    summary="Process direct text input",
    description="Submit text content directly for processing"
)
def process_text(
    request: TextInputRequest
) -> InputProcessingResponse:
    """
    Process direct text input.
    
    Accepts text content and optional type hint for processing.
    
    Args:
        request: Text input request with content and optional type hint
        
    Returns:
        InputProcessingResponse with processing results
        
    Raises:
        HTTPException: If text processing fails
    """
    try:
        logger.info("Received text input request")
        
        # Process the text
        response = input_service.process_text_input(
            content=request.content,
            hint_type=request.input_type
        )
        
        return response
        
    except ValueError as e:
        # Validation errors (empty content, too short, etc.)
        logger.warning(f"Text validation failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_type": ErrorType.VALIDATION,
                "message": str(e)
            }
        )
    
    except Exception as e:
        # Unexpected errors
        logger.error(f"Unexpected error during text processing: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_type": ErrorType.PROCESSING,
                "message": "An unexpected error occurred while processing the text"
            }
        )


@router.get(
    "/status/{input_id}",
    response_model=InputData,
    status_code=status.HTTP_200_OK,
    summary="Get input processing status",
    description="Retrieve the status and details of a processed input"
)
def get_input_status(
    input_id: str
) -> InputData:
    """
    Get the status and details of a processed input.
    
    Args:
        input_id: Unique identifier for the input
        
    Returns:
        InputData with processing details
        
    Raises:
        HTTPException: If input not found
    """
    try:
        logger.info(f"Retrieving status for input: {input_id}")
        
        # Get input status
        input_data = input_service.get_input_status(input_id)
        
        if input_data is None:
            logger.warning(f"Input not found: {input_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error_type": ErrorType.NOT_FOUND,
                    "message": f"Input with ID '{input_id}' not found"
                }
            )
        
        return input_data
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    
    except Exception as e:
        # Unexpected errors
        logger.error(f"Unexpected error retrieving input status: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_type": ErrorType.PROCESSING,
                "message": "An unexpected error occurred while retrieving input status"
            }
        )
