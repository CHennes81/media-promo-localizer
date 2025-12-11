"""
Error handling utilities for consistent error responses.
"""
from typing import Optional

from fastapi import HTTPException, status
from fastapi.responses import JSONResponse

from app.models import ErrorInfo


class APIError(Exception):
    """Base exception for API errors."""

    def __init__(
        self,
        code: str,
        message: str,
        http_status: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        retryable: bool = False,
        details: Optional[dict] = None,
    ):
        self.code = code
        self.message = message
        self.http_status = http_status
        self.retryable = retryable
        self.details = details or {}
        super().__init__(self.message)


def create_error_response(error: APIError) -> JSONResponse:
    """
    Create a standardized error response.

    Args:
        error: APIError instance

    Returns:
        JSONResponse with error envelope
    """
    error_info = ErrorInfo(
        code=error.code,
        message=error.message,
        retryable=error.retryable,
        details=error.details if error.details else None,
    )
    return JSONResponse(
        status_code=error.http_status,
        content={"error": error_info.model_dump(exclude_none=True)},
    )


def handle_exception(e: Exception) -> JSONResponse:
    """
    Map exceptions to API error responses.

    Args:
        e: Exception to handle

    Returns:
        JSONResponse with appropriate error
    """
    if isinstance(e, APIError):
        return create_error_response(e)

    # Map common FastAPI/HTTP exceptions
    if isinstance(e, HTTPException):
        code_map = {
            status.HTTP_400_BAD_REQUEST: "INVALID_INPUT",
            status.HTTP_404_NOT_FOUND: "NOT_FOUND",
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE: "PAYLOAD_TOO_LARGE",
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE: "UNSUPPORTED_MEDIA_TYPE",
        }
        code = code_map.get(e.status_code, "INTERNAL_ERROR")
        return create_error_response(
            APIError(
                code=code,
                message=e.detail,
                http_status=e.status_code,
            )
        )

    # Unknown exception
    return create_error_response(
        APIError(
            code="INTERNAL_ERROR",
            message="An unexpected error occurred.",
            http_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
    )


# Standard error codes
class ErrorCodes:
    """Standard error codes."""

    INVALID_INPUT = "INVALID_INPUT"
    NOT_FOUND = "NOT_FOUND"
    PAYLOAD_TOO_LARGE = "PAYLOAD_TOO_LARGE"
    UNSUPPORTED_MEDIA_TYPE = "UNSUPPORTED_MEDIA_TYPE"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    OCR_MODEL_ERROR = "OCR_MODEL_ERROR"
    TRANSLATION_MODEL_ERROR = "TRANSLATION_MODEL_ERROR"
    INPAINT_MODEL_ERROR = "INPAINT_MODEL_ERROR"
    OCR_MODEL_TIMEOUT = "OCR_MODEL_TIMEOUT"
    TRANSLATION_MODEL_TIMEOUT = "TRANSLATION_MODEL_TIMEOUT"
    INPAINT_MODEL_TIMEOUT = "INPAINT_MODEL_TIMEOUT"


