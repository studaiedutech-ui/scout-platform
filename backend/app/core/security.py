"""
Comprehensive Security Module for S.C.O.U.T. Platform
Handles authentication, authorization, password security, and rate limiting
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Union, Optional, Dict
import jwt
import bcrypt
import secrets
import re
from fastapi import HTTPException, status, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from passlib.context import CryptContext
import redis
import time
import hashlib
from functools import wraps
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT token security
security = HTTPBearer()

# Redis client for rate limiting and session management
redis_client = redis.from_url(
    settings.REDIS_URL,
    ssl=settings.REDIS_SSL,
    socket_connect_timeout=settings.REDIS_SOCKET_CONNECT_TIMEOUT
)

class PasswordValidator:
    """Enhanced password validation with security policies"""
    
    @staticmethod
    def validate_password(password: str) -> Dict[str, Any]:
        """Comprehensive password validation"""
        errors = []
        score = 0
        
        # Length check
        if len(password) < settings.MIN_PASSWORD_LENGTH:
            errors.append(f"Password must be at least {settings.MIN_PASSWORD_LENGTH} characters long")
        else:
            score += 1
        
        # Uppercase letter check
        if settings.REQUIRE_UPPERCASE and not re.search(r"[A-Z]", password):
            errors.append("Password must contain at least one uppercase letter")
        elif re.search(r"[A-Z]", password):
            score += 1
        
        # Number check
        if settings.REQUIRE_NUMBERS and not re.search(r"\d", password):
            errors.append("Password must contain at least one number")
        elif re.search(r"\d", password):
            score += 1
        
        # Special character check
        if settings.REQUIRE_SPECIAL_CHARS and not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
            errors.append("Password must contain at least one special character")
        elif re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
            score += 1
        
        # Common password patterns
        common_patterns = [
            r"123456", r"password", r"qwerty", r"admin", r"letmein",
            r"welcome", r"monkey", r"1234567890"
        ]
        
        for pattern in common_patterns:
            if re.search(pattern, password.lower()):
                errors.append("Password contains common patterns that are easily guessed")
                score -= 1
                break
        
        # Calculate strength
        if score >= 4:
            strength = "strong"
        elif score >= 2:
            strength = "medium"
        else:
            strength = "weak"
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "strength": strength,
            "score": max(0, score)
        }

class TokenManager:
    """JWT token management with enhanced security"""
    
    @staticmethod
    def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """Create JWT access token with enhanced security"""
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        
        to_encode.update({
            "exp": expire,
            "iat": datetime.now(timezone.utc),
            "jti": secrets.token_urlsafe(32),  # JWT ID for token revocation
            "token_type": "access"
        })
        
        encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        return encoded_jwt
    
    @staticmethod
    def create_refresh_token(user_id: int) -> str:
        """Create refresh token"""
        to_encode = {
            "sub": str(user_id),
            "exp": datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
            "iat": datetime.now(timezone.utc),
            "jti": secrets.token_urlsafe(32),
            "token_type": "refresh"
        }
        
        encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        
        # Store refresh token in Redis with expiration
        redis_client.setex(
            f"refresh_token:{user_id}:{to_encode['jti']}",
            timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
            encoded_jwt
        )
        
        return encoded_jwt
    
    @staticmethod
    def verify_token(token: str) -> Dict[str, Any]:
        """Verify and decode JWT token"""
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            
            # Check if token is blacklisted
            jti = payload.get("jti")
            if jti and redis_client.get(f"blacklisted_token:{jti}"):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token has been revoked"
                )
            
            return payload
            
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired"
            )
        except jwt.JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials"
            )
    
    @staticmethod
    def revoke_token(token: str):
        """Revoke a token by adding it to blacklist"""
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            jti = payload.get("jti")
            exp = payload.get("exp")
            
            if jti and exp:
                # Calculate remaining TTL
                ttl = exp - int(datetime.now(timezone.utc).timestamp())
                if ttl > 0:
                    redis_client.setex(f"blacklisted_token:{jti}", ttl, "revoked")
                    
        except jwt.JWTError:
            pass  # Token is invalid anyway

class RateLimiter:
    """Advanced rate limiting with multiple strategies"""
    
    @staticmethod
    def get_client_ip(request: Request) -> str:
        """Get client IP address handling proxies with validation"""
        import ipaddress
        
        # Check for real IP from reverse proxy
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # Take the first IP in the chain
            ip = forwarded_for.split(",")[0].strip()
            try:
                # Validate IP address
                ipaddress.ip_address(ip)
                return ip
            except ValueError:
                pass
        
        # Check for real IP header
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            try:
                ipaddress.ip_address(real_ip)
                return real_ip
            except ValueError:
                pass
        
        # Fallback to client host
        return request.client.host if request.client else "unknown"
        
        return request.client.host if request.client else "unknown"
    
    @staticmethod
    def create_rate_limit_key(identifier: str, window: str) -> str:
        """Create rate limit key"""
        return f"rate_limit:{identifier}:{window}"
    
    @staticmethod
    def check_rate_limit(identifier: str, limit: int, window_seconds: int) -> Dict[str, Any]:
        """Check if request is within rate limit"""
        current_time = int(time.time())
        window_start = current_time - window_seconds
        
        # Use sliding window log approach
        key = f"rate_limit:{identifier}"
        
        # Remove old entries
        redis_client.zremrangebyscore(key, 0, window_start)
        
        # Count current requests
        current_requests = redis_client.zcard(key)
        
        if current_requests >= limit:
            # Get time until next allowed request
            oldest_request = redis_client.zrange(key, 0, 0, withscores=True)
            if oldest_request:
                reset_time = oldest_request[0][1] + window_seconds
                return {
                    "allowed": False,
                    "limit": limit,
                    "remaining": 0,
                    "reset_time": reset_time,
                    "retry_after": max(0, reset_time - current_time)
                }
        
        # Add current request
        redis_client.zadd(key, {str(current_time): current_time})
        redis_client.expire(key, window_seconds)
        
        return {
            "allowed": True,
            "limit": limit,
            "remaining": max(0, limit - current_requests - 1),
            "reset_time": current_time + window_seconds,
            "retry_after": 0
        }

def rate_limit(max_requests: int = None, window_seconds: int = 60):
    """Rate limiting decorator"""
    def decorator(func):
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            # Use configured defaults if not specified
            limit = max_requests or settings.RATE_LIMIT_PER_MINUTE
            window = window_seconds
            
            # Get client identifier
            client_ip = RateLimiter.get_client_ip(request)
            
            # Check rate limit
            rate_limit_result = RateLimiter.check_rate_limit(
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
                        "endpoint": request.url.path
                    }
                )
                
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Rate limit exceeded",
                    headers={
                        "X-Rate-Limit-Limit": str(limit),
                        "X-Rate-Limit-Remaining": str(rate_limit_result["remaining"]),
                        "X-Rate-Limit-Reset": str(rate_limit_result["reset_time"]),
                        "Retry-After": str(rate_limit_result["retry_after"])
                    }
                )
            
            # Add rate limit headers to response
            response = await func(request, *args, **kwargs)
            if hasattr(response, "headers"):
                response.headers["X-Rate-Limit-Limit"] = str(limit)
                response.headers["X-Rate-Limit-Remaining"] = str(rate_limit_result["remaining"])
                response.headers["X-Rate-Limit-Reset"] = str(rate_limit_result["reset_time"])
            
            return response
        return wrapper
    return decorator

class SecurityHeaders:
    """Security headers middleware"""
    
    @staticmethod
    def add_security_headers(response):
        """Add comprehensive security headers"""
        # HTTPS enforcement
        if settings.SECURE_COOKIES:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        # Content Security Policy
        response.headers["Content-Security-Policy"] = settings.CONTENT_SECURITY_POLICY
        
        # Frame options
        response.headers["X-Frame-Options"] = settings.X_FRAME_OPTIONS
        
        # Content type sniffing prevention
        response.headers["X-Content-Type-Options"] = "nosniff"
        
        # XSS protection
        response.headers["X-XSS-Protection"] = "1; mode=block"
        
        # Referrer policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # Permissions policy
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        
        return response

# Authentication dependencies
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get current authenticated user"""
    token = credentials.credentials
    payload = TokenManager.verify_token(token)
    
    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials"
        )
    
    # Here you would typically fetch the user from database
    # For now, return user_id
    return {"user_id": int(user_id), "payload": payload}

async def get_current_active_user(current_user: dict = Depends(get_current_user)):
    """Get current active user (extend with additional checks)"""
    # Add additional checks here (user active status, etc.)
    return current_user

def require_permission(permission: str):
    """Require specific permission for endpoint access"""
    def decorator(func):
        @wraps(func)
        async def wrapper(current_user: dict = Depends(get_current_active_user), *args, **kwargs):
            # Check user permissions (implement based on your permission system)
            user_permissions = current_user.get("permissions", [])
            
            if permission not in user_permissions and "admin" not in user_permissions:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Insufficient permissions. Required: {permission}"
                )
            
            return await func(current_user=current_user, *args, **kwargs)
        return wrapper
    return decorator

# Password utilities
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash"""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Hash password with bcrypt"""
    return pwd_context.hash(password)

def generate_secure_token(length: int = 32) -> str:
    """Generate cryptographically secure random token"""
    return secrets.token_urlsafe(length)

def hash_sensitive_data(data: str) -> str:
    """Hash sensitive data for logging/storage"""
    return hashlib.sha256(data.encode()).hexdigest()

# Initialize components
password_validator = PasswordValidator()
token_manager = TokenManager()
rate_limiter = RateLimiter()
security_headers = SecurityHeaders()

# Legacy compatibility functions
def create_access_token(data: dict, expires_delta: timedelta = None):
    """Legacy compatibility function"""
    return TokenManager.create_access_token(data, expires_delta)

def verify_token(token: str):
    """Legacy compatibility function"""
    return TokenManager.verify_token(token)