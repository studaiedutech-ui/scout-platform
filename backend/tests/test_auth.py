"""
Comprehensive Unit Tests for S.C.O.U.T. Platform Authentication Module
Tests covering security, validation, and authentication flows
"""

import pytest
import asyncio
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch, AsyncMock
from fastapi import HTTPException, status
from fastapi.testclient import TestClient
import jwt
import redis
from sqlalchemy.orm import Session

from app.api.endpoints.auth import (
    login, logout, refresh_token, change_password, get_current_user_info,
    revoke_all_tokens
)
from app.core.security import (
    PasswordValidator, TokenManager, RateLimiter, SecurityHeaders,
    verify_password, get_password_hash, hash_sensitive_data
)
from app.core.validation import DataSanitizer
from app.models.user import User
from app.core.config import settings

class TestPasswordValidator:
    """Test password validation functionality"""
    
    def test_valid_strong_password(self):
        """Test validation of a strong password"""
        password = "StrongP@ssw0rd123"
        result = PasswordValidator.validate_password(password)
        
        assert result["valid"] is True
        assert result["strength"] in ["strong", "very_strong"]
        assert result["score"] >= 5
        assert len(result["errors"]) == 0
    
    def test_weak_password_too_short(self):
        """Test validation of a password that's too short"""
        password = "weak"
        result = PasswordValidator.validate_password(password)
        
        assert result["valid"] is False
        assert "at least" in str(result["errors"])
        assert result["strength"] == "weak"
    
    def test_password_missing_requirements(self):
        """Test password missing character type requirements"""
        password = "alllowercase"
        result = PasswordValidator.validate_password(password)
        
        assert result["valid"] is False
        assert any("uppercase" in error for error in result["errors"])
        assert any("digit" in error for error in result["errors"])
        assert any("special" in error for error in result["errors"])
    
    def test_password_common_patterns(self):
        """Test detection of common password patterns"""
        passwords = ["password123", "123456789", "qwerty123"]
        
        for password in passwords:
            result = PasswordValidator.validate_password(password)
            assert result["valid"] is False or result["score"] < 4
    
    def test_password_sequential_characters(self):
        """Test detection of sequential characters"""
        password = "Abc123!"
        result = PasswordValidator.validate_password(password)
        
        # Should detect sequential ABC and 123
        assert "sequential" in str(result["errors"]) or result["score"] < 6
    
    def test_password_repeated_characters(self):
        """Test detection of excessive repeated characters"""
        password = "Aaaaa1!"
        result = PasswordValidator.validate_password(password)
        
        assert "repeated" in str(result["errors"]) or result["score"] < 6
    
    def test_password_recommendations(self):
        """Test password improvement recommendations"""
        password = "short1!"
        result = PasswordValidator.validate_password(password)
        
        assert len(result["recommendations"]) > 0
        assert any("12 characters" in rec for rec in result["recommendations"])

class TestTokenManager:
    """Test JWT token management functionality"""
    
    @pytest.fixture
    def mock_redis(self):
        """Mock Redis client"""
        with patch('app.core.security.redis_client') as mock:
            yield mock
    
    def test_create_access_token(self):
        """Test access token creation"""
        data = {"sub": "123", "email": "test@example.com", "role": "hr"}
        token = TokenManager.create_access_token(data)
        
        assert isinstance(token, str)
        assert len(token) > 50  # JWT tokens are typically long
        
        # Decode and verify payload
        payload = jwt.decode(
            token, 
            settings.SECRET_KEY, 
            algorithms=[settings.ALGORITHM]
        )
        assert payload["sub"] == "123"
        assert payload["email"] == "test@example.com"
        assert payload["token_type"] == "access"
        assert "jti" in payload
        assert "exp" in payload
    
    def test_create_refresh_token(self, mock_redis):
        """Test refresh token creation"""
        user_id = 123
        mock_redis.setex.return_value = True
        
        token = TokenManager.create_refresh_token(user_id)
        
        assert isinstance(token, str)
        mock_redis.setex.assert_called_once()
        
        # Decode and verify payload
        payload = jwt.decode(
            token, 
            settings.SECRET_KEY, 
            algorithms=[settings.ALGORITHM]
        )
        assert payload["sub"] == str(user_id)
        assert payload["token_type"] == "refresh"
    
    def test_verify_valid_token(self):
        """Test verification of a valid token"""
        data = {"sub": "123", "email": "test@example.com"}
        token = TokenManager.create_access_token(data)
        
        payload = TokenManager.verify_token(token)
        
        assert payload["sub"] == "123"
        assert payload["email"] == "test@example.com"
    
    def test_verify_expired_token(self):
        """Test verification of an expired token"""
        data = {"sub": "123", "email": "test@example.com"}
        expires_delta = timedelta(seconds=-1)  # Already expired
        token = TokenManager.create_access_token(data, expires_delta)
        
        with pytest.raises(HTTPException) as exc_info:
            TokenManager.verify_token(token)
        
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert "expired" in exc_info.value.detail.lower()
    
    def test_verify_invalid_token(self):
        """Test verification of an invalid token"""
        invalid_token = "invalid.token.here"
        
        with pytest.raises(HTTPException) as exc_info:
            TokenManager.verify_token(invalid_token)
        
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_revoke_token(self, mock_redis):
        """Test token revocation"""
        data = {"sub": "123", "email": "test@example.com"}
        token = TokenManager.create_access_token(data)
        mock_redis.setex.return_value = True
        
        TokenManager.revoke_token(token)
        
        mock_redis.setex.assert_called_once()
        # Verify the revocation key format
        call_args = mock_redis.setex.call_args[0]
        assert call_args[0].startswith("revoked_token:")

class TestRateLimiter:
    """Test rate limiting functionality"""
    
    @pytest.fixture
    def mock_redis(self):
        """Mock Redis client"""
        with patch('app.core.security.redis_client') as mock:
            yield mock
    
    @pytest.fixture
    def mock_request(self):
        """Mock FastAPI request object"""
        request = Mock()
        request.client.host = "192.168.1.1"
        request.headers = {}
        return request
    
    def test_get_client_ip_direct(self, mock_request):
        """Test getting client IP from direct connection"""
        ip = RateLimiter.get_client_ip(mock_request)
        assert ip == "192.168.1.1"
    
    def test_get_client_ip_forwarded(self, mock_request):
        """Test getting client IP from X-Forwarded-For header"""
        mock_request.headers = {"X-Forwarded-For": "203.0.113.1, 192.168.1.1"}
        
        ip = RateLimiter.get_client_ip(mock_request)
        assert ip == "203.0.113.1"
    
    def test_get_client_ip_real_ip(self, mock_request):
        """Test getting client IP from X-Real-IP header"""
        mock_request.headers = {"X-Real-IP": "203.0.113.2"}
        
        ip = RateLimiter.get_client_ip(mock_request)
        assert ip == "203.0.113.2"
    
    def test_rate_limit_allowed(self, mock_redis):
        """Test rate limiting when requests are within limit"""
        mock_redis.pipeline.return_value.__enter__.return_value.execute.return_value = [
            None, 5, None, None  # 5 requests in window
        ]
        mock_redis.zrange.return_value = []
        
        result = RateLimiter.check_rate_limit("test_user", 10, 60)
        
        assert result["allowed"] is True
        assert result["remaining"] == 4  # 10 - 5 - 1
    
    def test_rate_limit_exceeded(self, mock_redis):
        """Test rate limiting when limit is exceeded"""
        mock_redis.pipeline.return_value.__enter__.return_value.execute.return_value = [
            None, 10, None, None  # 10 requests in window, limit is 10
        ]
        mock_redis.zrange.return_value = [(b"", 1640995200.0)]  # Mock oldest request
        
        result = RateLimiter.check_rate_limit("test_user", 10, 60)
        
        assert result["allowed"] is False
        assert result["remaining"] == 0
        assert result["retry_after"] > 0

class TestDataSanitizer:
    """Test data sanitization functionality"""
    
    def test_sanitize_email_valid(self):
        """Test sanitizing a valid email"""
        email = "  Test.User+123@Example.COM  "
        sanitized = DataSanitizer.sanitize_email(email)
        
        assert sanitized == "test.user+123@example.com"
    
    def test_sanitize_email_invalid(self):
        """Test sanitizing invalid email raises error"""
        with pytest.raises(ValueError):
            DataSanitizer.sanitize_email("invalid-email")
    
    def test_sanitize_string(self):
        """Test string sanitization"""
        malicious_string = "<script>alert('xss')</script>Hello"
        sanitized = DataSanitizer.sanitize_string(malicious_string)
        
        assert "<script>" not in sanitized
        assert "Hello" in sanitized
    
    def test_sanitize_filename(self):
        """Test filename sanitization"""
        dangerous_filename = "../../../etc/passwd"
        sanitized = DataSanitizer.sanitize_filename(dangerous_filename)
        
        assert "../" not in sanitized
        assert sanitized != dangerous_filename

class TestSecurityUtilities:
    """Test security utility functions"""
    
    def test_verify_password_correct(self):
        """Test password verification with correct password"""
        password = "test_password"
        hashed = get_password_hash(password)
        
        assert verify_password(password, hashed) is True
    
    def test_verify_password_incorrect(self):
        """Test password verification with incorrect password"""
        password = "test_password"
        wrong_password = "wrong_password"
        hashed = get_password_hash(password)
        
        assert verify_password(wrong_password, hashed) is False
    
    def test_hash_sensitive_data(self):
        """Test sensitive data hashing for logging"""
        sensitive_data = "user@example.com"
        hashed = hash_sensitive_data(sensitive_data)
        
        assert len(hashed) == 16  # SHA256 hash truncated to 16 chars
        assert hashed != sensitive_data
        
        # Same input should produce same hash
        assert hash_sensitive_data(sensitive_data) == hashed

class TestSecurityHeaders:
    """Test security headers functionality"""
    
    def test_add_security_headers(self):
        """Test adding security headers to response"""
        response = Mock()
        response.headers = {}
        
        SecurityHeaders.add_security_headers(response)
        
        # Check for essential security headers
        assert "X-Content-Type-Options" in response.headers
        assert "X-Frame-Options" in response.headers
        assert "X-XSS-Protection" in response.headers
        assert "Strict-Transport-Security" in response.headers
        assert "Content-Security-Policy" in response.headers
        assert "Permissions-Policy" in response.headers
        
        # Verify header values
        assert response.headers["X-Content-Type-Options"] == "nosniff"
        assert response.headers["X-Frame-Options"] == "DENY"

@pytest.mark.asyncio
class TestAuthenticationEndpoints:
    """Test authentication endpoint functionality"""
    
    @pytest.fixture
    def mock_db(self):
        """Mock database session"""
        return Mock(spec=Session)
    
    @pytest.fixture
    def mock_user(self):
        """Mock user object"""
        user = Mock(spec=User)
        user.id = 1
        user.email = "test@example.com"
        user.first_name = "Test"
        user.last_name = "User"
        user.role = "hr"
        user.is_active = True
        user.hashed_password = get_password_hash("test_password")
        user.locked_until = None
        user.login_count = 5
        user.last_login = datetime.now(timezone.utc)
        return user
    
    @pytest.fixture
    def mock_request(self):
        """Mock FastAPI request"""
        request = Mock()
        request.client.host = "192.168.1.1"
        request.headers = {"user-agent": "test-agent"}
        request.cookies = {}
        return request
    
    @patch('app.api.endpoints.auth.redis_client')
    @patch('app.api.endpoints.auth.RateLimiter.check_rate_limit')
    @patch('app.api.endpoints.auth.check_failed_login_attempts')
    @patch('app.api.endpoints.auth.clear_failed_login_attempts')
    async def test_login_success(self, mock_clear_attempts, mock_check_attempts, 
                                mock_rate_limit, mock_redis, mock_db, mock_user, mock_request):
        """Test successful login"""
        # Setup mocks
        mock_rate_limit.return_value = {"allowed": True, "retry_after": 0}
        mock_check_attempts.return_value = True
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user
        mock_redis.setex.return_value = True
        mock_redis.sadd.return_value = True
        mock_redis.expire.return_value = True
        
        from app.api.endpoints.auth import LoginRequest, LoginResponse
        login_data = LoginRequest(email="test@example.com", password="test_password")
        response = Mock()
        background_tasks = Mock()
        
        result = await login(mock_request, response, background_tasks, login_data, mock_db)
        
        assert isinstance(result, LoginResponse)
        assert result.user["email"] == "test@example.com"
        assert "access_token" in result.__dict__
        assert "refresh_token" in result.__dict__
        mock_clear_attempts.assert_called_once()
    
    @patch('app.api.endpoints.auth.RateLimiter.check_rate_limit')
    async def test_login_rate_limited(self, mock_rate_limit, mock_db, mock_request):
        """Test login with rate limiting"""
        mock_rate_limit.return_value = {"allowed": False, "retry_after": 60}
        
        from app.api.endpoints.auth import LoginRequest
        login_data = LoginRequest(email="test@example.com", password="test_password")
        response = Mock()
        background_tasks = Mock()
        
        with pytest.raises(HTTPException) as exc_info:
            await login(mock_request, response, background_tasks, login_data, mock_db)
        
        assert exc_info.value.status_code == status.HTTP_429_TOO_MANY_REQUESTS
    
    @patch('app.api.endpoints.auth.RateLimiter.check_rate_limit')
    @patch('app.api.endpoints.auth.check_failed_login_attempts')
    @patch('app.api.endpoints.auth.record_failed_login_attempt')
    async def test_login_invalid_credentials(self, mock_record_attempt, mock_check_attempts,
                                           mock_rate_limit, mock_db, mock_request):
        """Test login with invalid credentials"""
        mock_rate_limit.return_value = {"allowed": True, "retry_after": 0}
        mock_check_attempts.return_value = True
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        from app.api.endpoints.auth import LoginRequest
        login_data = LoginRequest(email="test@example.com", password="wrong_password")
        response = Mock()
        background_tasks = Mock()
        
        with pytest.raises(HTTPException) as exc_info:
            await login(mock_request, response, background_tasks, login_data, mock_db)
        
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        mock_record_attempt.assert_called_once()

# Integration test configuration
@pytest.fixture(scope="session")
def test_app():
    """Create test FastAPI application"""
    from app.main import app
    return app

@pytest.fixture(scope="session")
def test_client(test_app):
    """Create test client"""
    return TestClient(test_app)

class TestIntegrationAuth:
    """Integration tests for authentication endpoints"""
    
    def test_health_endpoint(self, test_client):
        """Test health check endpoint"""
        response = test_client.get("/api/v1/health/ready")
        assert response.status_code in [200, 503]  # May not be ready in test
    
    def test_login_endpoint_structure(self, test_client):
        """Test login endpoint accepts correct structure"""
        login_data = {
            "email": "test@example.com",
            "password": "test_password"
        }
        
        response = test_client.post("/api/v1/auth/login", json=login_data)
        # Should return 401 for invalid credentials, not 422 for bad structure
        assert response.status_code != 422
    
    def test_protected_endpoint_without_token(self, test_client):
        """Test accessing protected endpoint without token"""
        response = test_client.get("/api/v1/auth/me")
        assert response.status_code == 403  # Forbidden without token

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])