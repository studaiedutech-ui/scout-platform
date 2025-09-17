"""
Comprehensive Error Handling and Logging System for S.C.O.U.T. Platform
"""

import logging
import traceback
import sys
from typing import Any, Dict, Optional
from datetime import datetime, timezone
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

from app.core.config import settings

# Configure structured logging
def setup_logging():
    """Configure structured logging for the application"""
    
    # Create custom formatter
    class StructuredFormatter(logging.Formatter):
        def format(self, record):
            log_data = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "level": record.levelname,
                "logger": record.name,
                "message": record.getMessage(),
                "module": record.module,
                "function": record.funcName,
                "line": record.lineno,
            }
            
            # Add exception info if present
            if record.exc_info:
                log_data["exception"] = {
                    "type": record.exc_info[0].__name__,
                    "message": str(record.exc_info[1]),
                    "traceback": traceback.format_exception(*record.exc_info)
                }
            
            # Add extra fields
            if hasattr(record, "extra"):
                log_data.update(record.extra)
            
            return self._format_json(log_data)
        
        def _format_json(self, data):
            import json
            return json.dumps(data, ensure_ascii=False)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))
    
    # Remove default handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Create console handler with structured formatting
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(StructuredFormatter())
    root_logger.addHandler(console_handler)
    
    # Configure specific loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    
    return root_logger

# Initialize Sentry for error tracking
def setup_sentry():
    """Initialize Sentry for error tracking and performance monitoring"""
    if settings.SENTRY_DSN:
        sentry_sdk.init(
            dsn=settings.SENTRY_DSN,
            environment=settings.SENTRY_ENVIRONMENT,
            traces_sample_rate=settings.SENTRY_TRACES_SAMPLE_RATE,
            integrations=[
                FastApiIntegration(auto_enable=True),
                SqlalchemyIntegration(),
            ],
            before_send=filter_sensitive_data,
            attach_stacktrace=True,
            send_default_pii=False  # Don't send PII by default
        )

def filter_sensitive_data(event, hint):
    """Filter sensitive data from Sentry events"""
    # Remove sensitive headers
    if "request" in event and "headers" in event["request"]:
        headers = event["request"]["headers"]
        sensitive_headers = ["authorization", "cookie", "x-api-key"]
        for header in sensitive_headers:
            if header in headers:
                headers[header] = "[REDACTED]"
    
    # Remove sensitive form data
    if "request" in event and "data" in event["request"]:
        data = event["request"]["data"]
        if isinstance(data, dict):
            sensitive_fields = ["password", "token", "secret", "key"]
            for field in sensitive_fields:
                if field in data:
                    data[field] = "[REDACTED]"
    
    return event

# Custom exception classes
class ScoutPlatformException(Exception):
    """Base exception for S.C.O.U.T. Platform"""
    def __init__(self, message: str, error_code: str = None, details: Dict = None):
        self.message = message
        self.error_code = error_code or "SCOUT_ERROR"
        self.details = details or {}
        super().__init__(self.message)

class DatabaseException(ScoutPlatformException):
    """Database-related exceptions"""
    def __init__(self, message: str, details: Dict = None):
        super().__init__(message, "DATABASE_ERROR", details)

class AuthenticationException(ScoutPlatformException):
    """Authentication-related exceptions"""
    def __init__(self, message: str, details: Dict = None):
        super().__init__(message, "AUTH_ERROR", details)

class ValidationException(ScoutPlatformException):
    """Validation-related exceptions"""
    def __init__(self, message: str, details: Dict = None):
        super().__init__(message, "VALIDATION_ERROR", details)

class ExternalServiceException(ScoutPlatformException):
    """External service-related exceptions"""
    def __init__(self, service: str, message: str, details: Dict = None):
        details = details or {}
        details["service"] = service
        super().__init__(message, "EXTERNAL_SERVICE_ERROR", details)

class BusinessLogicException(ScoutPlatformException):
    """Business logic-related exceptions"""
    def __init__(self, message: str, details: Dict = None):
        super().__init__(message, "BUSINESS_LOGIC_ERROR", details)

# Error handlers
async def scout_platform_exception_handler(request: Request, exc: ScoutPlatformException):
    """Handle custom S.C.O.U.T. Platform exceptions"""
    logger = logging.getLogger(__name__)
    
    # Log the error with context
    logger.error(
        f"ScoutPlatformException: {exc.message}",
        extra={
            "error_code": exc.error_code,
            "details": exc.details,
            "request_url": str(request.url),
            "request_method": request.method,
            "user_agent": request.headers.get("user-agent"),
            "client_ip": request.client.host if request.client else None
        }
    )
    
    # Determine HTTP status code based on error type
    status_code_map = {
        "AUTH_ERROR": status.HTTP_401_UNAUTHORIZED,
        "VALIDATION_ERROR": status.HTTP_400_BAD_REQUEST,
        "DATABASE_ERROR": status.HTTP_500_INTERNAL_SERVER_ERROR,
        "EXTERNAL_SERVICE_ERROR": status.HTTP_503_SERVICE_UNAVAILABLE,
        "BUSINESS_LOGIC_ERROR": status.HTTP_422_UNPROCESSABLE_ENTITY,
    }
    
    status_code = status_code_map.get(exc.error_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": exc.error_code,
                "message": exc.message,
                "details": exc.details if settings.DEBUG else {},
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "request_id": getattr(request.state, "request_id", None)
            }
        }
    )

async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle FastAPI HTTP exceptions"""
    logger = logging.getLogger(__name__)
    
    logger.warning(
        f"HTTP Exception: {exc.detail}",
        extra={
            "status_code": exc.status_code,
            "request_url": str(request.url),
            "request_method": request.method,
            "user_agent": request.headers.get("user-agent"),
            "client_ip": request.client.host if request.client else None
        }
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": f"HTTP_{exc.status_code}",
                "message": exc.detail,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "request_id": getattr(request.state, "request_id", None)
            }
        }
    )

async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle Pydantic validation errors"""
    logger = logging.getLogger(__name__)
    
    logger.warning(
        f"Validation Error: {exc.errors()}",
        extra={
            "request_url": str(request.url),
            "request_method": request.method,
            "validation_errors": exc.errors()
        }
    )
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Request validation failed",
                "details": {
                    "validation_errors": exc.errors()
                },
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "request_id": getattr(request.state, "request_id", None)
            }
        }
    )

async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions"""
    logger = logging.getLogger(__name__)
    
    # Log the full exception with traceback
    logger.error(
        f"Unexpected error: {str(exc)}",
        exc_info=True,
        extra={
            "request_url": str(request.url),
            "request_method": request.method,
            "user_agent": request.headers.get("user-agent"),
            "client_ip": request.client.host if request.client else None
        }
    )
    
    # Send to Sentry if configured
    if settings.SENTRY_DSN:
        sentry_sdk.capture_exception(exc)
    
    # Return generic error in production, detailed in development
    if settings.DEBUG:
        error_details = {
            "exception_type": type(exc).__name__,
            "exception_message": str(exc),
            "traceback": traceback.format_exc()
        }
    else:
        error_details = {}
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred",
                "details": error_details,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "request_id": getattr(request.state, "request_id", None)
            }
        }
    )

# Request logging middleware
import uuid
from starlette.middleware.base import BaseHTTPMiddleware

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log all requests and responses"""
    
    async def dispatch(self, request: Request, call_next):
        # Generate unique request ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        # Log request
        logger = logging.getLogger(__name__)
        start_time = datetime.now(timezone.utc)
        
        logger.info(
            f"Request started: {request.method} {request.url}",
            extra={
                "request_id": request_id,
                "method": request.method,
                "url": str(request.url),
                "user_agent": request.headers.get("user-agent"),
                "client_ip": request.client.host if request.client else None,
                "content_type": request.headers.get("content-type"),
                "content_length": request.headers.get("content-length")
            }
        )
        
        # Process request
        try:
            response = await call_next(request)
            
            # Calculate processing time
            end_time = datetime.now(timezone.utc)
            processing_time = (end_time - start_time).total_seconds()
            
            # Log response
            logger.info(
                f"Request completed: {request.method} {request.url} - {response.status_code}",
                extra={
                    "request_id": request_id,
                    "status_code": response.status_code,
                    "processing_time_seconds": processing_time,
                    "response_size": response.headers.get("content-length")
                }
            )
            
            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id
            
            return response
            
        except Exception as exc:
            # Log exception
            end_time = datetime.now(timezone.utc)
            processing_time = (end_time - start_time).total_seconds()
            
            logger.error(
                f"Request failed: {request.method} {request.url}",
                exc_info=True,
                extra={
                    "request_id": request_id,
                    "processing_time_seconds": processing_time,
                    "exception_type": type(exc).__name__,
                    "exception_message": str(exc)
                }
            )
            
            raise

# Initialize logging and error tracking
logger = setup_logging()
setup_sentry()