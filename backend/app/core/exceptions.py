"""
Custom exception classes for the S.C.O.U.T. platform
"""

from typing import Any, Dict, Optional
from fastapi import HTTPException, status


class BaseCustomException(Exception):
    """Base exception for all custom exceptions"""
    
    def __init__(
        self,
        message: str,
        error_code: str,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class ValidationError(BaseCustomException):
    """Raised when validation fails"""
    
    def __init__(self, message: str, field: str = None, details: Dict[str, Any] = None):
        super().__init__(
            message=message,
            error_code="VALIDATION_ERROR",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details={"field": field, **(details or {})}
        )


class AuthenticationError(BaseCustomException):
    """Raised when authentication fails"""
    
    def __init__(self, message: str = "Authentication failed", details: Dict[str, Any] = None):
        super().__init__(
            message=message,
            error_code="AUTHENTICATION_ERROR",
            status_code=status.HTTP_401_UNAUTHORIZED,
            details=details
        )


class AuthorizationError(BaseCustomException):
    """Raised when authorization fails"""
    
    def __init__(self, message: str = "Access denied", details: Dict[str, Any] = None):
        super().__init__(
            message=message,
            error_code="AUTHORIZATION_ERROR",
            status_code=status.HTTP_403_FORBIDDEN,
            details=details
        )


class NotFoundError(BaseCustomException):
    """Raised when a resource is not found"""
    
    def __init__(self, resource: str, identifier: str = None, details: Dict[str, Any] = None):
        message = f"{resource} not found"
        if identifier:
            message += f" with identifier: {identifier}"
        
        super().__init__(
            message=message,
            error_code="NOT_FOUND",
            status_code=status.HTTP_404_NOT_FOUND,
            details={"resource": resource, "identifier": identifier, **(details or {})}
        )


class ConflictError(BaseCustomException):
    """Raised when there's a conflict with existing data"""
    
    def __init__(self, message: str, resource: str = None, details: Dict[str, Any] = None):
        super().__init__(
            message=message,
            error_code="CONFLICT_ERROR",
            status_code=status.HTTP_409_CONFLICT,
            details={"resource": resource, **(details or {})}
        )


class BusinessLogicError(BaseCustomException):
    """Raised when business logic rules are violated"""
    
    def __init__(self, message: str, rule: str = None, details: Dict[str, Any] = None):
        super().__init__(
            message=message,
            error_code="BUSINESS_LOGIC_ERROR",
            status_code=status.HTTP_400_BAD_REQUEST,
            details={"rule": rule, **(details or {})}
        )


class ExternalServiceError(BaseCustomException):
    """Raised when external service calls fail"""
    
    def __init__(
        self, 
        service: str, 
        message: str = None, 
        original_error: Exception = None,
        details: Dict[str, Any] = None
    ):
        message = message or f"{service} service is unavailable"
        super().__init__(
            message=message,
            error_code="EXTERNAL_SERVICE_ERROR",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            details={
                "service": service,
                "original_error": str(original_error) if original_error else None,
                **(details or {})
            }
        )


class RateLimitError(BaseCustomException):
    """Raised when rate limit is exceeded"""
    
    def __init__(self, message: str = "Rate limit exceeded", retry_after: int = None, details: Dict[str, Any] = None):
        super().__init__(
            message=message,
            error_code="RATE_LIMIT_ERROR",
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            details={"retry_after": retry_after, **(details or {})}
        )


class AssessmentError(BaseCustomException):
    """Raised when assessment-related errors occur"""
    
    def __init__(self, message: str, assessment_id: str = None, details: Dict[str, Any] = None):
        super().__init__(
            message=message,
            error_code="ASSESSMENT_ERROR",
            status_code=status.HTTP_400_BAD_REQUEST,
            details={"assessment_id": assessment_id, **(details or {})}
        )


class AIServiceError(BaseCustomException):
    """Raised when AI service errors occur"""
    
    def __init__(
        self, 
        message: str = "AI service error", 
        service_type: str = None,
        details: Dict[str, Any] = None
    ):
        super().__init__(
            message=message,
            error_code="AI_SERVICE_ERROR",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            details={"service_type": service_type, **(details or {})}
        )


class DatabaseError(BaseCustomException):
    """Raised when database errors occur"""
    
    def __init__(self, message: str = "Database error", operation: str = None, details: Dict[str, Any] = None):
        super().__init__(
            message=message,
            error_code="DATABASE_ERROR",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details={"operation": operation, **(details or {})}
        )


# Exception handler function
def create_error_response(exception: BaseCustomException) -> Dict[str, Any]:
    """Create standardized error response"""
    return {
        "error": {
            "code": exception.error_code,
            "message": exception.message,
            "details": exception.details
        },
        "status": "error"
    }


# Custom HTTP exception with additional context
class CustomHTTPException(HTTPException):
    """Enhanced HTTP exception with structured error response"""
    
    def __init__(
        self,
        status_code: int,
        error_code: str,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ):
        self.error_code = error_code
        self.details = details or {}
        
        detail = {
            "error": {
                "code": error_code,
                "message": message,
                "details": self.details
            },
            "status": "error"
        }
        
        super().__init__(status_code=status_code, detail=detail)