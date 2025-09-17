"""
Exception handlers for the S.C.O.U.T. platform
"""

import logging
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
import traceback

from app.core.exceptions import (
    BaseCustomException,
    CustomHTTPException,
    create_error_response
)

logger = logging.getLogger(__name__)


async def custom_exception_handler(request: Request, exc: BaseCustomException) -> JSONResponse:
    """Handle custom exceptions"""
    
    # Log the exception
    logger.error(
        f"Custom exception occurred: {exc.error_code}",
        extra={
            "request_id": getattr(request.state, "request_id", None),
            "error_code": exc.error_code,
            "message": exc.message,
            "details": exc.details,
            "path": request.url.path,
            "method": request.method
        }
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content=create_error_response(exc)
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Handle HTTP exceptions"""
    
    # Check if it's our custom HTTP exception
    if isinstance(exc, CustomHTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content=exc.detail
        )
    
    # Log the exception
    logger.warning(
        f"HTTP exception: {exc.status_code}",
        extra={
            "request_id": getattr(request.state, "request_id", None),
            "status_code": exc.status_code,
            "detail": exc.detail,
            "path": request.url.path,
            "method": request.method
        }
    )
    
    # Create standardized response
    error_response = {
        "error": {
            "code": f"HTTP_{exc.status_code}",
            "message": exc.detail if isinstance(exc.detail, str) else "HTTP error",
            "details": exc.detail if isinstance(exc.detail, dict) else {}
        },
        "status": "error"
    }
    
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handle validation errors"""
    
    # Extract validation errors
    errors = []
    for error in exc.errors():
        field = ".".join(str(loc) for loc in error["loc"][1:])  # Skip 'body'
        errors.append({
            "field": field,
            "message": error["msg"],
            "type": error["type"],
            "input": error.get("input")
        })
    
    logger.warning(
        f"Validation error: {len(errors)} field(s)",
        extra={
            "request_id": getattr(request.state, "request_id", None),
            "errors": errors,
            "path": request.url.path,
            "method": request.method
        }
    )
    
    error_response = {
        "error": {
            "code": "VALIDATION_ERROR",
            "message": "Validation failed",
            "details": {
                "errors": errors,
                "total_errors": len(errors)
            }
        },
        "status": "error"
    }
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=error_response
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle all other exceptions"""
    
    # Generate request ID if not present
    request_id = getattr(request.state, "request_id", "unknown")
    
    # Log the full exception
    logger.error(
        f"Unhandled exception: {type(exc).__name__}",
        extra={
            "request_id": request_id,
            "exception_type": type(exc).__name__,
            "exception_message": str(exc),
            "traceback": traceback.format_exc(),
            "path": request.url.path,
            "method": request.method
        }
    )
    
    # Don't expose internal errors in production
    if hasattr(request.app.state, "environment") and request.app.state.environment == "production":
        error_message = "An internal error occurred"
        error_details = {"request_id": request_id}
    else:
        error_message = str(exc)
        error_details = {
            "request_id": request_id,
            "exception_type": type(exc).__name__,
            "traceback": traceback.format_exc().split('\n') if hasattr(request.app.state, "debug") and request.app.state.debug else None
        }
    
    error_response = {
        "error": {
            "code": "INTERNAL_SERVER_ERROR",
            "message": error_message,
            "details": error_details
        },
        "status": "error"
    }
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_response
    )


def setup_exception_handlers(app: FastAPI):
    """Set up all exception handlers"""
    
    # Custom exception handlers
    app.add_exception_handler(BaseCustomException, custom_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, general_exception_handler)
    
    logger.info("Exception handlers configured")