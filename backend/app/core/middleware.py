"""
Production-Ready Middleware Module for S.C.O.U.T. Platform
Handles request/response processing, security, monitoring, and compliance
"""

import time
import uuid
import json
import logging
from typing import Callable, Dict, Any, Optional
from datetime import datetime, timezone
from fastapi import FastAPI, Request, Response, HTTPException, status
from fastapi.middleware.base import BaseHTTPMiddleware
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import JSONResponse
import redis
import asyncio

from app.core.config import settings
from app.core.security import SecurityHeaders, RateLimiter
from app.core.logging import StructuredFormatter

logger = logging.getLogger(__name__)

class RequestTrackingMiddleware(BaseHTTPMiddleware):
    """Track requests with comprehensive logging and monitoring"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate request ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        # Start timing
        start_time = time.time()
        
        # Extract client information
        client_ip = self._get_client_ip(request)
        user_agent = request.headers.get("user-agent", "unknown")
        
        # Log request start
        logger.info(
            "Request started",
            extra={
                "request_id": request_id,
                "method": request.method,
                "url": str(request.url),
                "client_ip": client_ip,
                "user_agent": user_agent,
                "path": request.url.path,
                "query_params": dict(request.query_params),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )
        
        try:
            # Process request
            response = await call_next(request)
            
            # Calculate processing time
            process_time = time.time() - start_time
            
            # Log successful response
            logger.info(
                "Request completed",
                extra={
                    "request_id": request_id,
                    "status_code": response.status_code,
                    "process_time": round(process_time, 4),
                    "response_size": response.headers.get("content-length", "unknown"),
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            )
            
            # Add headers
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Process-Time"] = str(round(process_time, 4))
            
            return response
            
        except Exception as e:
            # Calculate processing time for error
            process_time = time.time() - start_time
            
            # Log error
            logger.error(
                "Request failed",
                extra={
                    "request_id": request_id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "process_time": round(process_time, 4),
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            )
            
            # Return error response
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "error": "Internal server error",
                    "request_id": request_id,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                },
                headers={"X-Request-ID": request_id}
            )
    
    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address handling proxies"""
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        return request.client.host if request.client else "unknown"

class SecurityMiddleware(BaseHTTPMiddleware):
    """Comprehensive security middleware"""
    
    def __init__(self, app, trusted_hosts: list = None):
        super().__init__(app)
        self.trusted_hosts = trusted_hosts or settings.ALLOWED_HOSTS
        self.security_headers = SecurityHeaders()
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Security checks before processing
        await self._perform_security_checks(request)
        
        # Process request
        response = await call_next(request)
        
        # Add security headers
        response = self.security_headers.add_security_headers(response)
        
        return response
    
    async def _perform_security_checks(self, request: Request):
        """Perform various security checks"""
        
        # Check host header
        if self.trusted_hosts and request.url.hostname not in self.trusted_hosts:
            logger.warning(
                f"Untrusted host: {request.url.hostname}",
                extra={
                    "client_ip": self._get_client_ip(request),
                    "host": request.url.hostname,
                    "user_agent": request.headers.get("user-agent", "unknown")
                }
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid host header"
            )
        
        # Check content length
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > settings.MAX_REQUEST_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="Request too large"
            )
        
        # Check for suspicious patterns in URL
        path = request.url.path.lower()
        suspicious_patterns = [
            "../", "..\\", "%2e%2e", "%252e%252e",
            "union+select", "script>", "javascript:",
            "<iframe", "<object", "<embed"
        ]
        
        for pattern in suspicious_patterns:
            if pattern in path:
                logger.warning(
                    f"Suspicious pattern detected in URL: {pattern}",
                    extra={
                        "client_ip": self._get_client_ip(request),
                        "path": path,
                        "pattern": pattern
                    }
                )
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid request"
                )
    
    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address handling proxies"""
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        return request.client.host if request.client else "unknown"

class RateLimitMiddleware(BaseHTTPMiddleware):
    """Advanced rate limiting middleware"""
    
    def __init__(self, app):
        super().__init__(app)
        self.rate_limiter = RateLimiter()
        self.redis_client = redis.from_url(
            settings.REDIS_URL,
            ssl=settings.REDIS_SSL,
            socket_connect_timeout=settings.REDIS_SOCKET_CONNECT_TIMEOUT
        )
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip rate limiting for health checks
        if request.url.path in ["/health", "/health/ready", "/health/live", "/metrics"]:
            return await call_next(request)
        
        # Get client identifier
        client_ip = self._get_client_ip(request)
        
        # Different rate limits for different endpoint types
        limit, window = self._get_rate_limit_for_endpoint(request.url.path, request.method)
        
        # Check rate limit
        rate_limit_result = self.rate_limiter.check_rate_limit(
            identifier=client_ip,
            limit=limit,
            window_seconds=window
        )
        
        if not rate_limit_result["allowed"]:
            logger.warning(
                f"Rate limit exceeded for IP: {client_ip}",
                extra={
                    "client_ip": client_ip,
                    "limit": limit,
                    "window_seconds": window,
                    "endpoint": request.url.path,
                    "method": request.method
                }
            )
            
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": "Rate limit exceeded",
                    "message": f"Too many requests. Try again in {rate_limit_result['retry_after']} seconds.",
                    "retry_after": rate_limit_result["retry_after"]
                },
                headers={
                    "X-Rate-Limit-Limit": str(limit),
                    "X-Rate-Limit-Remaining": str(rate_limit_result["remaining"]),
                    "X-Rate-Limit-Reset": str(rate_limit_result["reset_time"]),
                    "Retry-After": str(rate_limit_result["retry_after"])
                }
            )
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers
        response.headers["X-Rate-Limit-Limit"] = str(limit)
        response.headers["X-Rate-Limit-Remaining"] = str(rate_limit_result["remaining"])
        response.headers["X-Rate-Limit-Reset"] = str(rate_limit_result["reset_time"])
        
        return response
    
    def _get_rate_limit_for_endpoint(self, path: str, method: str) -> tuple:
        """Get rate limit configuration for specific endpoint"""
        
        # Authentication endpoints - more restrictive
        if "/auth/login" in path or "/auth/register" in path:
            return 5, 300  # 5 requests per 5 minutes
        
        # Password reset - very restrictive
        if "/auth/reset-password" in path:
            return 3, 3600  # 3 requests per hour
        
        # Assessment creation/submission - moderate
        if "/assessments" in path and method in ["POST", "PUT"]:
            return 10, 300  # 10 requests per 5 minutes
        
        # File uploads - restrictive
        if "upload" in path:
            return 5, 60  # 5 requests per minute
        
        # API endpoints - standard
        if path.startswith("/api/"):
            return settings.RATE_LIMIT_PER_MINUTE, 60
        
        # Default rate limit
        return settings.RATE_LIMIT_PER_MINUTE, 60
    
    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address handling proxies"""
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        return request.client.host if request.client else "unknown"

class MetricsMiddleware(BaseHTTPMiddleware):
    """Middleware for collecting application metrics"""
    
    def __init__(self, app):
        super().__init__(app)
        self.redis_client = redis.from_url(
            settings.REDIS_URL,
            ssl=settings.REDIS_SSL,
            socket_connect_timeout=settings.REDIS_SOCKET_CONNECT_TIMEOUT
        )
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()
        
        try:
            response = await call_next(request)
            
            # Record metrics
            await self._record_metrics(
                request=request,
                response=response,
                duration=time.time() - start_time
            )
            
            return response
            
        except Exception as e:
            # Record error metrics
            await self._record_error_metrics(
                request=request,
                error=e,
                duration=time.time() - start_time
            )
            raise
    
    async def _record_metrics(self, request: Request, response: Response, duration: float):
        """Record request metrics"""
        try:
            metrics_data = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration": duration,
                "client_ip": self._get_client_ip(request)
            }
            
            # Store in Redis for metrics collection
            await asyncio.get_event_loop().run_in_executor(
                None,
                self._store_metrics,
                metrics_data
            )
            
        except Exception as e:
            logger.error(f"Failed to record metrics: {str(e)}")
    
    async def _record_error_metrics(self, request: Request, error: Exception, duration: float):
        """Record error metrics"""
        try:
            error_data = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "method": request.method,
                "path": request.url.path,
                "error_type": type(error).__name__,
                "error_message": str(error),
                "duration": duration,
                "client_ip": self._get_client_ip(request)
            }
            
            # Store in Redis for error tracking
            await asyncio.get_event_loop().run_in_executor(
                None,
                self._store_error_metrics,
                error_data
            )
            
        except Exception as e:
            logger.error(f"Failed to record error metrics: {str(e)}")
    
    def _store_metrics(self, metrics_data: dict):
        """Store metrics in Redis"""
        try:
            # Use Redis sorted sets for time-series data
            timestamp = int(time.time())
            
            # Request count by endpoint
            key = f"metrics:requests:{metrics_data['method']}:{metrics_data['path']}"
            self.redis_client.zadd(key, {json.dumps(metrics_data): timestamp})
            self.redis_client.expire(key, settings.METRICS_RETENTION_SECONDS)
            
            # Response time tracking
            key = f"metrics:response_time:{metrics_data['method']}:{metrics_data['path']}"
            self.redis_client.zadd(key, {str(metrics_data['duration']): timestamp})
            self.redis_client.expire(key, settings.METRICS_RETENTION_SECONDS)
            
            # Status code tracking
            key = f"metrics:status_codes:{metrics_data['status_code']}"
            self.redis_client.zadd(key, {json.dumps(metrics_data): timestamp})
            self.redis_client.expire(key, settings.METRICS_RETENTION_SECONDS)
            
        except Exception as e:
            logger.error(f"Failed to store metrics: {str(e)}")
    
    def _store_error_metrics(self, error_data: dict):
        """Store error metrics in Redis"""
        try:
            timestamp = int(time.time())
            
            # Error tracking by endpoint
            key = f"metrics:errors:{error_data['method']}:{error_data['path']}"
            self.redis_client.zadd(key, {json.dumps(error_data): timestamp})
            self.redis_client.expire(key, settings.METRICS_RETENTION_SECONDS)
            
            # Error tracking by type
            key = f"metrics:error_types:{error_data['error_type']}"
            self.redis_client.zadd(key, {json.dumps(error_data): timestamp})
            self.redis_client.expire(key, settings.METRICS_RETENTION_SECONDS)
            
        except Exception as e:
            logger.error(f"Failed to store error metrics: {str(e)}")
    
    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address handling proxies"""
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        return request.client.host if request.client else "unknown"

class ComplianceMiddleware(BaseHTTPMiddleware):
    """Middleware for compliance and audit logging"""
    
    def __init__(self, app):
        super().__init__(app)
        self.redis_client = redis.from_url(
            settings.REDIS_URL,
            ssl=settings.REDIS_SSL,
            socket_connect_timeout=settings.REDIS_SOCKET_CONNECT_TIMEOUT
        )
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Check if this is a sensitive operation
        is_sensitive = self._is_sensitive_operation(request)
        
        if is_sensitive:
            # Log sensitive operation
            await self._log_sensitive_operation(request)
        
        response = await call_next(request)
        
        # Log data access for compliance
        if self._is_data_access_operation(request, response):
            await self._log_data_access(request, response)
        
        return response
    
    def _is_sensitive_operation(self, request: Request) -> bool:
        """Check if operation is sensitive and requires audit logging"""
        sensitive_patterns = [
            "/auth/",
            "/admin/",
            "/users/",
            "/companies/",
            "/candidates/",
            "/assessments/"
        ]
        
        sensitive_methods = ["POST", "PUT", "DELETE"]
        
        return (
            any(pattern in request.url.path for pattern in sensitive_patterns) and
            request.method in sensitive_methods
        )
    
    def _is_data_access_operation(self, request: Request, response: Response) -> bool:
        """Check if operation involves data access"""
        return (
            request.method == "GET" and
            response.status_code == 200 and
            any(pattern in request.url.path for pattern in [
                "/api/companies/", "/api/candidates/", "/api/assessments/"
            ])
        )
    
    async def _log_sensitive_operation(self, request: Request):
        """Log sensitive operations for audit trail"""
        try:
            audit_data = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "operation_type": "sensitive_operation",
                "method": request.method,
                "path": request.url.path,
                "client_ip": self._get_client_ip(request),
                "user_agent": request.headers.get("user-agent", "unknown"),
                "request_id": getattr(request.state, "request_id", "unknown")
            }
            
            # Store audit log
            await asyncio.get_event_loop().run_in_executor(
                None,
                self._store_audit_log,
                audit_data
            )
            
        except Exception as e:
            logger.error(f"Failed to log sensitive operation: {str(e)}")
    
    async def _log_data_access(self, request: Request, response: Response):
        """Log data access for compliance"""
        try:
            access_data = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "operation_type": "data_access",
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "client_ip": self._get_client_ip(request),
                "request_id": getattr(request.state, "request_id", "unknown")
            }
            
            # Store access log
            await asyncio.get_event_loop().run_in_executor(
                None,
                self._store_audit_log,
                access_data
            )
            
        except Exception as e:
            logger.error(f"Failed to log data access: {str(e)}")
    
    def _store_audit_log(self, audit_data: dict):
        """Store audit log in Redis"""
        try:
            timestamp = int(time.time())
            key = f"audit:logs:{audit_data['operation_type']}"
            
            self.redis_client.zadd(key, {json.dumps(audit_data): timestamp})
            self.redis_client.expire(key, settings.AUDIT_LOG_RETENTION_SECONDS)
            
        except Exception as e:
            logger.error(f"Failed to store audit log: {str(e)}")
    
    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address handling proxies"""
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        return request.client.host if request.client else "unknown"

def setup_middleware(app: FastAPI):
    """Setup all middleware for the application"""
    
    # Add middleware in reverse order (last added is executed first)
    
    # Compliance and audit logging
    app.add_middleware(ComplianceMiddleware)
    
    # Metrics collection
    app.add_middleware(MetricsMiddleware)
    
    # Rate limiting
    app.add_middleware(RateLimitMiddleware)
    
    # Security middleware
    app.add_middleware(SecurityMiddleware, trusted_hosts=settings.ALLOWED_HOSTS)
    
    # Request tracking and logging
    app.add_middleware(RequestTrackingMiddleware)
    
    # Session middleware
    if settings.SECRET_KEY:
        app.add_middleware(
            SessionMiddleware,
            secret_key=settings.SECRET_KEY,
            max_age=settings.SESSION_EXPIRE_SECONDS,
            same_site="strict" if settings.SECURE_COOKIES else "lax",
            https_only=settings.SECURE_COOKIES
        )
    
    # GZIP compression
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    
    # CORS middleware
    if settings.BACKEND_CORS_ORIGINS:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.BACKEND_CORS_ORIGINS,
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            allow_headers=["*"],
            expose_headers=["X-Request-ID", "X-Process-Time", "X-Rate-Limit-*"]
        )
    
    # Trusted host middleware
    if settings.ALLOWED_HOSTS:
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=settings.ALLOWED_HOSTS
        )

# Export middleware components
__all__ = [
    "RequestTrackingMiddleware",
    "SecurityMiddleware", 
    "RateLimitMiddleware",
    "MetricsMiddleware",
    "ComplianceMiddleware",
    "setup_middleware"
]