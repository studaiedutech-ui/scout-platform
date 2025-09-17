"""
Authentication Endpoints for S.C.O.U.T. Platform
Enhanced with comprehensive security, rate limiting, and audit logging
"""

import asyncio
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request, Response, BackgroundTasks
from fastapi.security import OAuth2PasswordRequestForm, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr, Field, validator
from sqlalchemy.orm import Session
import redis
import secrets
import hashlib
import logging

from app.core.database import get_db
from app.core.security import (
    SecurityHeaders, RateLimiter, TokenManager, PasswordValidator,
    verify_password, get_password_hash, get_current_user, get_current_active_user,
    generate_secure_token, hash_sensitive_data, security
)
from app.core.validation import (
    DataSanitizer, validate_and_sanitize_input,
    CompanyRegistrationModel, CandidateProfileModel
)
from app.core.config import settings
from app.core.logging import logger
from app.models.user import User
from app.models.company import Company
from app.models.candidate import Candidate

router = APIRouter()

# Redis client for session management
redis_client = redis.from_url(
    settings.REDIS_URL,
    ssl=settings.REDIS_SSL,
    socket_connect_timeout=settings.REDIS_SOCKET_CONNECT_TIMEOUT
)

# Request/Response Models
class LoginRequest(BaseModel):
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=8, max_length=128, description="User password")
    remember_me: bool = Field(default=False, description="Extended session duration")
    
    @validator('email')
    def validate_email(cls, v):
        return DataSanitizer.sanitize_email(v)

class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: Dict[str, Any]
    permissions: list
    session_id: str

class PasswordResetRequest(BaseModel):
    email: EmailStr = Field(..., description="Email address for password reset")
    
    @validator('email')
    def validate_email(cls, v):
        return DataSanitizer.sanitize_email(v)

class PasswordResetConfirm(BaseModel):
    token: str = Field(..., min_length=32, description="Password reset token")
    new_password: str = Field(..., min_length=8, max_length=128, description="New password")
    confirm_password: str = Field(..., min_length=8, max_length=128, description="Confirm new password")
    
    @validator('confirm_password')
    def passwords_match(cls, v, values):
        if 'new_password' in values and v != values['new_password']:
            raise ValueError('Passwords do not match')
        return v

class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(..., description="Refresh token")

class ChangePasswordRequest(BaseModel):
    current_password: str = Field(..., description="Current password")
    new_password: str = Field(..., min_length=8, max_length=128, description="New password")
    confirm_password: str = Field(..., min_length=8, max_length=128, description="Confirm new password")
    
    @validator('confirm_password')
    def passwords_match(cls, v, values):
        if 'new_password' in values and v != values['new_password']:
            raise ValueError('Passwords do not match')
        return v

# Authentication Helper Functions
def get_client_info(request: Request) -> Dict[str, str]:
    """Extract client information for security logging"""
    return {
        "client_ip": RateLimiter.get_client_ip(request),
        "user_agent": request.headers.get("user-agent", "unknown"),
        "referer": request.headers.get("referer", "unknown"),
        "origin": request.headers.get("origin", "unknown")
    }

def create_session_id() -> str:
    """Generate unique session ID"""
    return secrets.token_urlsafe(32)

def store_user_session(user_id: int, session_id: str, expires_in: int):
    """Store user session in Redis"""
    try:
        session_data = {
            "user_id": user_id,
            "session_id": session_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "expires_at": (datetime.now(timezone.utc) + timedelta(seconds=expires_in)).isoformat()
        }
        
        # Store session
        redis_client.setex(
            f"session:{session_id}",
            expires_in,
            str(session_data)
        )
        
        # Store user active sessions
        redis_client.sadd(f"user_sessions:{user_id}", session_id)
        redis_client.expire(f"user_sessions:{user_id}", expires_in)
        
    except Exception as e:
        logger.error(f"Failed to store user session: {str(e)}")

def log_security_event(event_type: str, user_id: Optional[int], client_info: Dict[str, str], 
                      details: Dict[str, Any] = None):
    """Log security events for audit trail"""
    try:
        security_log = {
            "event_type": event_type,
            "user_id": user_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "client_ip": client_info.get("client_ip"),
            "user_agent": hash_sensitive_data(client_info.get("user_agent", "")),
            "details": details or {}
        }
        
        # Store in Redis for immediate access
        redis_client.lpush("security_events", str(security_log))
        redis_client.ltrim("security_events", 0, 1000)  # Keep last 1000 events
        
        # Log for structured logging
        logger.info(f"Security event: {event_type}", extra=security_log)
        
    except Exception as e:
        logger.error(f"Failed to log security event: {str(e)}")

async def check_failed_login_attempts(email: str, client_ip: str) -> bool:
    """Check for excessive failed login attempts"""
    try:
        # Check attempts by email
        email_key = f"login_attempts:email:{hash_sensitive_data(email)}"
        email_attempts = redis_client.get(email_key)
        
        # Check attempts by IP
        ip_key = f"login_attempts:ip:{client_ip}"
        ip_attempts = redis_client.get(ip_key)
        
        email_count = int(email_attempts) if email_attempts else 0
        ip_count = int(ip_attempts) if ip_attempts else 0
        
        # Block if too many attempts
        if email_count >= settings.MAX_LOGIN_ATTEMPTS_PER_EMAIL or ip_count >= settings.MAX_LOGIN_ATTEMPTS_PER_IP:
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to check login attempts: {str(e)}")
        return True  # Allow login on error

async def record_failed_login_attempt(email: str, client_ip: str):
    """Record failed login attempt"""
    try:
        email_key = f"login_attempts:email:{hash_sensitive_data(email)}"
        ip_key = f"login_attempts:ip:{client_ip}"
        
        # Increment counters with expiration
        redis_client.incr(email_key)
        redis_client.expire(email_key, settings.LOGIN_ATTEMPT_LOCKOUT_DURATION)
        
        redis_client.incr(ip_key)
        redis_client.expire(ip_key, settings.LOGIN_ATTEMPT_LOCKOUT_DURATION)
        
    except Exception as e:
        logger.error(f"Failed to record login attempt: {str(e)}")

async def clear_failed_login_attempts(email: str, client_ip: str):
    """Clear failed login attempts on successful login"""
    try:
        email_key = f"login_attempts:email:{hash_sensitive_data(email)}"
        ip_key = f"login_attempts:ip:{client_ip}"
        
        redis_client.delete(email_key, ip_key)
        
    except Exception as e:
        logger.error(f"Failed to clear login attempts: {str(e)}")

# Authentication Endpoints
@router.post("/login", response_model=LoginResponse)
async def login(
    request: Request,
    response: Response,
    background_tasks: BackgroundTasks,
    login_data: LoginRequest,
    db: Session = Depends(get_db)
):
    """
    User login with comprehensive security features
    """
    client_info = get_client_info(request)
    
    try:
        # Rate limiting check
        rate_limit_result = RateLimiter.check_rate_limit(
            identifier=client_info["client_ip"],
            limit=5,  # 5 attempts per 5 minutes for login
            window_seconds=300
        )
        
        if not rate_limit_result["allowed"]:
            log_security_event("RATE_LIMIT_EXCEEDED", None, client_info, {
                "endpoint": "/auth/login",
                "email": hash_sensitive_data(login_data.email)
            })
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Too many login attempts. Try again in {rate_limit_result['retry_after']} seconds."
            )
        
        # Check for excessive failed attempts
        if not await check_failed_login_attempts(login_data.email, client_info["client_ip"]):
            log_security_event("LOGIN_BLOCKED_EXCESSIVE_ATTEMPTS", None, client_info, {
                "email": hash_sensitive_data(login_data.email)
            })
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail="Account temporarily locked due to excessive failed login attempts"
            )
        
        # Find user by email
        user = db.query(User).filter(User.email == login_data.email).first()
        
        if not user or not verify_password(login_data.password, user.hashed_password):
            # Record failed attempt
            await record_failed_login_attempt(login_data.email, client_info["client_ip"])
            
            log_security_event("LOGIN_FAILED", user.id if user else None, client_info, {
                "email": hash_sensitive_data(login_data.email),
                "reason": "invalid_credentials"
            })
            
            # Add delay to prevent timing attacks
            await asyncio.sleep(1)
            
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        # Check if user is active
        if not user.is_active:
            log_security_event("LOGIN_FAILED", user.id, client_info, {
                "email": hash_sensitive_data(login_data.email),
                "reason": "account_disabled"
            })
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is disabled"
            )
        
        # Check if account is locked
        if user.locked_until and user.locked_until > datetime.now(timezone.utc):
            log_security_event("LOGIN_FAILED", user.id, client_info, {
                "email": hash_sensitive_data(login_data.email),
                "reason": "account_locked",
                "locked_until": user.locked_until.isoformat()
            })
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail=f"Account is locked until {user.locked_until}"
            )
        
        # Clear failed attempts on successful login
        await clear_failed_login_attempts(login_data.email, client_info["client_ip"])
        
        # Determine token expiration
        expires_in = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        if login_data.remember_me:
            expires_in = settings.REMEMBER_ME_EXPIRE_DAYS * 24 * 60 * 60
        
        # Create tokens
        access_token = TokenManager.create_access_token(
            data={"sub": str(user.id), "email": user.email, "role": user.role},
            expires_delta=timedelta(seconds=expires_in)
        )
        
        refresh_token = TokenManager.create_refresh_token(user.id)
        
        # Create session
        session_id = create_session_id()
        store_user_session(user.id, session_id, expires_in)
        
        # Update user login info
        user.last_login = datetime.now(timezone.utc)
        user.login_count = (user.login_count or 0) + 1
        db.commit()
        
        # Prepare response
        user_data = {
            "id": user.id,
            "email": user.email,
            "name": f"{user.first_name} {user.last_name}",
            "role": user.role,
            "is_active": user.is_active,
            "last_login": user.last_login.isoformat() if user.last_login else None
        }
        
        # Get user permissions (implement based on your permission system)
        permissions = ["read", "write"] if user.role == "admin" else ["read"]
        
        # Add security headers
        SecurityHeaders.add_security_headers(response)
        
        # Set secure cookie for session
        if settings.SECURE_COOKIES:
            response.set_cookie(
                key="session_id",
                value=session_id,
                max_age=expires_in,
                httponly=True,
                secure=True,
                samesite="strict"
            )
        
        # Log successful login
        log_security_event("LOGIN_SUCCESS", user.id, client_info, {
            "session_id": session_id,
            "remember_me": login_data.remember_me,
            "expires_in": expires_in
        })
        
        return LoginResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=expires_in,
            user=user_data,
            permissions=permissions,
            session_id=session_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {str(e)}", exc_info=True)
        log_security_event("LOGIN_ERROR", None, client_info, {
            "error": str(e),
            "email": hash_sensitive_data(login_data.email)
        })
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed due to server error"
        )

@router.post("/logout")
async def logout(
    request: Request,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_active_user),
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """
    User logout with token revocation
    """
    client_info = get_client_info(request)
    
    try:
        # Revoke access token
        TokenManager.revoke_token(credentials.credentials)
        
        # Get session ID from request
        session_id = request.cookies.get("session_id")
        
        if session_id:
            # Remove session from Redis
            redis_client.delete(f"session:{session_id}")
            redis_client.srem(f"user_sessions:{current_user['user_id']}", session_id)
        
        # Log logout event
        log_security_event("LOGOUT_SUCCESS", current_user["user_id"], client_info, {
            "session_id": session_id
        })
        
        return {"message": "Logged out successfully"}
        
    except Exception as e:
        logger.error(f"Logout error: {str(e)}")
        log_security_event("LOGOUT_ERROR", current_user["user_id"], client_info, {
            "error": str(e)
        })
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Logout failed"
        )

@router.post("/refresh")
async def refresh_token(
    request: Request,
    refresh_data: RefreshTokenRequest,
    db: Session = Depends(get_db)
):
    """
    Refresh access token using refresh token
    """
    client_info = get_client_info(request)
    
    try:
        # Verify refresh token
        payload = TokenManager.verify_token(refresh_data.refresh_token)
        
        if payload.get("token_type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type"
            )
        
        user_id = int(payload.get("sub"))
        jti = payload.get("jti")
        
        # Check if refresh token exists in Redis
        if not redis_client.get(f"refresh_token:{user_id}:{jti}"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token has been revoked"
            )
        
        # Get user
        user = db.query(User).filter(User.id == user_id).first()
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive"
            )
        
        # Create new access token
        access_token = TokenManager.create_access_token(
            data={"sub": str(user.id), "email": user.email, "role": user.role}
        )
        
        # Log token refresh
        log_security_event("TOKEN_REFRESH", user.id, client_info)
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token refresh error: {str(e)}")
        log_security_event("TOKEN_REFRESH_ERROR", None, client_info, {"error": str(e)})
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )

@router.post("/change-password")
async def change_password(
    request: Request,
    password_data: ChangePasswordRequest,
    current_user: dict = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Change user password with validation
    """
    client_info = get_client_info(request)
    
    try:
        # Get current user from database
        user = db.query(User).filter(User.id == current_user["user_id"]).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Verify current password
        if not verify_password(password_data.current_password, user.hashed_password):
            log_security_event("PASSWORD_CHANGE_FAILED", user.id, client_info, {
                "reason": "invalid_current_password"
            })
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect"
            )
        
        # Validate new password
        password_validation = PasswordValidator.validate_password(password_data.new_password)
        if not password_validation["valid"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"errors": password_validation["errors"]}
            )
        
        # Check if new password is different from current
        if verify_password(password_data.new_password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="New password must be different from current password"
            )
        
        # Update password
        user.hashed_password = get_password_hash(password_data.new_password)
        user.password_changed_at = datetime.now(timezone.utc)
        db.commit()
        
        # Log password change
        log_security_event("PASSWORD_CHANGE_SUCCESS", user.id, client_info)
        
        return {"message": "Password changed successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Password change error: {str(e)}")
        log_security_event("PASSWORD_CHANGE_ERROR", current_user["user_id"], client_info, {
            "error": str(e)
        })
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to change password"
        )

@router.get("/me")
async def get_current_user_info(
    current_user: dict = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get current user information
    """
    try:
        user = db.query(User).filter(User.id == current_user["user_id"]).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        return {
            "id": user.id,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "role": user.role,
            "is_active": user.is_active,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "last_login": user.last_login.isoformat() if user.last_login else None,
            "login_count": user.login_count or 0
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get user info error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get user information"
        )

@router.post("/revoke-all-tokens")
async def revoke_all_tokens(
    request: Request,
    current_user: dict = Depends(get_current_active_user)
):
    """
    Revoke all user tokens and sessions
    """
    client_info = get_client_info(request)
    
    try:
        user_id = current_user["user_id"]
        
        # Get all user sessions
        session_keys = redis_client.smembers(f"user_sessions:{user_id}")
        
        # Remove all sessions
        if session_keys:
            redis_client.delete(*[f"session:{session_id}" for session_id in session_keys])
            redis_client.delete(f"user_sessions:{user_id}")
        
        # Remove refresh tokens (pattern matching)
        refresh_token_keys = redis_client.keys(f"refresh_token:{user_id}:*")
        if refresh_token_keys:
            redis_client.delete(*refresh_token_keys)
        
        # Log security event
        log_security_event("ALL_TOKENS_REVOKED", user_id, client_info, {
            "revoked_sessions": len(session_keys),
            "revoked_refresh_tokens": len(refresh_token_keys)
        })
        
        return {
            "message": "All tokens and sessions revoked successfully",
            "revoked_sessions": len(session_keys)
        }
        
    except Exception as e:
        logger.error(f"Token revocation error: {str(e)}")
        log_security_event("TOKEN_REVOCATION_ERROR", current_user["user_id"], client_info, {
            "error": str(e)
        })
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to revoke tokens"
        )

# Export router
__all__ = ["router"]