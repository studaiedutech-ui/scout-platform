"""
Comprehensive API Integration Tests for S.C.O.U.T. Platform
Tests covering API endpoints, data flows, and system integration
"""

import pytest
import asyncio
import json
from datetime import datetime, timezone
from typing import Dict, Any
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from unittest.mock import Mock, patch, AsyncMock
import redis
import uuid

from app.main import app
from app.core.database import get_db, Base
from app.core.config import settings
from app.models.user import User
from app.models.company import Company
from app.models.candidate import Candidate
from app.models.job import Job
from app.core.security import get_password_hash

# Test database configuration
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_scout_platform.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    """Override database dependency for testing"""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

# Override dependencies
app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    """Setup test database"""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def test_db():
    """Create test database session"""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

@pytest.fixture(scope="function")
def client():
    """Create test client"""
    return TestClient(app)

@pytest.fixture
def test_company(test_db):
    """Create test company"""
    company = Company(
        name="Test Company Inc.",
        domain="testcompany.com",
        description="A test company for integration testing",
        industry="Technology",
        size="50-100",
        location="San Francisco, CA",
        website="https://testcompany.com",
        is_active=True,
        subscription_tier="premium"
    )
    test_db.add(company)
    test_db.commit()
    test_db.refresh(company)
    return company

@pytest.fixture
def test_user(test_db, test_company):
    """Create test user"""
    user = User(
        email="test.user@testcompany.com",
        hashed_password=get_password_hash("TestPassword123!"),
        first_name="Test",
        last_name="User",
        role="hr",
        is_active=True,
        is_email_verified=True,
        company_id=test_company.id
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user

@pytest.fixture
def test_admin_user(test_db, test_company):
    """Create test admin user"""
    user = User(
        email="admin@testcompany.com",
        hashed_password=get_password_hash("AdminPassword123!"),
        first_name="Admin",
        last_name="User",
        role="admin",
        is_active=True,
        is_email_verified=True,
        company_id=test_company.id
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user

@pytest.fixture
def test_candidate(test_db):
    """Create test candidate"""
    candidate = Candidate(
        email="candidate@example.com",
        first_name="Jane",
        last_name="Candidate",
        phone="+1234567890",
        location="New York, NY",
        skills=["Python", "FastAPI", "PostgreSQL"],
        experience_years=5,
        current_position="Senior Developer",
        current_company="Tech Corp",
        education="Computer Science, MIT",
        resume_text="Experienced software developer...",
        linkedin_url="https://linkedin.com/in/jane-candidate",
        github_url="https://github.com/jane-candidate"
    )
    test_db.add(candidate)
    test_db.commit()
    test_db.refresh(candidate)
    return candidate

@pytest.fixture
def test_job(test_db, test_company, test_user):
    """Create test job position"""
    job = Job(
        title="Senior Python Developer",
        description="We are looking for a senior Python developer...",
        requirements=["5+ years Python experience", "FastAPI knowledge", "PostgreSQL"],
        location="San Francisco, CA",
        job_type="full-time",
        experience_level="senior",
        salary_min=120000,
        salary_max=180000,
        is_remote=True,
        status="active",
        company_id=test_company.id,
        created_by=test_user.id
    )
    test_db.add(job)
    test_db.commit()
    test_db.refresh(job)
    return job

@pytest.fixture
def auth_headers(client, test_user):
    """Get authentication headers for test user"""
    login_data = {
        "email": test_user.email,
        "password": "TestPassword123!"
    }
    
    with patch('app.api.endpoints.auth.redis_client'), \
         patch('app.api.endpoints.auth.RateLimiter.check_rate_limit') as mock_rate_limit, \
         patch('app.api.endpoints.auth.check_failed_login_attempts') as mock_check_attempts:
        
        mock_rate_limit.return_value = {"allowed": True, "retry_after": 0}
        mock_check_attempts.return_value = True
        
        response = client.post("/api/v1/auth/login", json=login_data)
        assert response.status_code == 200
        
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def admin_auth_headers(client, test_admin_user):
    """Get authentication headers for admin user"""
    login_data = {
        "email": test_admin_user.email,
        "password": "AdminPassword123!"
    }
    
    with patch('app.api.endpoints.auth.redis_client'), \
         patch('app.api.endpoints.auth.RateLimiter.check_rate_limit') as mock_rate_limit, \
         patch('app.api.endpoints.auth.check_failed_login_attempts') as mock_check_attempts:
        
        mock_rate_limit.return_value = {"allowed": True, "retry_after": 0}
        mock_check_attempts.return_value = True
        
        response = client.post("/api/v1/auth/login", json=login_data)
        assert response.status_code == 200
        
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

class TestHealthEndpoints:
    """Test health check endpoints"""
    
    def test_basic_health_check(self, client):
        """Test basic health endpoint"""
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        
        data = response.json()
        assert "status" in data
        assert "timestamp" in data
        assert "version" in data
    
    def test_readiness_check(self, client):
        """Test readiness endpoint"""
        with patch('app.api.endpoints.health.check_database_connection') as mock_db, \
             patch('app.api.endpoints.health.check_redis_connection') as mock_redis:
            
            mock_db.return_value = True
            mock_redis.return_value = True
            
            response = client.get("/api/v1/health/ready")
            assert response.status_code == 200
            
            data = response.json()
            assert data["status"] == "ready"
            assert data["checks"]["database"] is True
            assert data["checks"]["redis"] is True
    
    def test_liveness_check(self, client):
        """Test liveness endpoint"""
        response = client.get("/api/v1/health/live")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "alive"

class TestAuthenticationFlow:
    """Test complete authentication flows"""
    
    @patch('app.api.endpoints.auth.redis_client')
    @patch('app.api.endpoints.auth.RateLimiter.check_rate_limit')
    @patch('app.api.endpoints.auth.check_failed_login_attempts')
    def test_complete_login_flow(self, mock_check_attempts, mock_rate_limit, 
                                mock_redis, client, test_user):
        """Test complete login flow"""
        # Setup mocks
        mock_rate_limit.return_value = {"allowed": True, "retry_after": 0}
        mock_check_attempts.return_value = True
        mock_redis.setex.return_value = True
        mock_redis.sadd.return_value = True
        mock_redis.expire.return_value = True
        
        # Login
        login_data = {
            "email": test_user.email,
            "password": "TestPassword123!"
        }
        
        response = client.post("/api/v1/auth/login", json=login_data)
        assert response.status_code == 200
        
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert "user" in data
        assert data["user"]["email"] == test_user.email
        assert data["token_type"] == "bearer"
    
    def test_login_invalid_credentials(self, client, test_user):
        """Test login with invalid credentials"""
        with patch('app.api.endpoints.auth.RateLimiter.check_rate_limit') as mock_rate_limit, \
             patch('app.api.endpoints.auth.check_failed_login_attempts') as mock_check_attempts:
            
            mock_rate_limit.return_value = {"allowed": True, "retry_after": 0}
            mock_check_attempts.return_value = True
            
            login_data = {
                "email": test_user.email,
                "password": "wrong_password"
            }
            
            response = client.post("/api/v1/auth/login", json=login_data)
            assert response.status_code == 401
    
    def test_login_inactive_user(self, client, test_user, test_db):
        """Test login with inactive user"""
        # Deactivate user
        test_user.is_active = False
        test_db.commit()
        
        with patch('app.api.endpoints.auth.RateLimiter.check_rate_limit') as mock_rate_limit, \
             patch('app.api.endpoints.auth.check_failed_login_attempts') as mock_check_attempts:
            
            mock_rate_limit.return_value = {"allowed": True, "retry_after": 0}
            mock_check_attempts.return_value = True
            
            login_data = {
                "email": test_user.email,
                "password": "TestPassword123!"
            }
            
            response = client.post("/api/v1/auth/login", json=login_data)
            assert response.status_code == 403
    
    def test_get_current_user_info(self, client, auth_headers, test_user):
        """Test getting current user information"""
        response = client.get("/api/v1/auth/me", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert data["email"] == test_user.email
        assert data["first_name"] == test_user.first_name
        assert data["role"] == test_user.role
    
    def test_protected_endpoint_without_auth(self, client):
        """Test accessing protected endpoint without authentication"""
        response = client.get("/api/v1/auth/me")
        assert response.status_code == 403

class TestCompanyEndpoints:
    """Test company management endpoints"""
    
    def test_get_company_info(self, client, auth_headers, test_company):
        """Test getting company information"""
        response = client.get(f"/api/v1/companies/{test_company.id}", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert data["name"] == test_company.name
        assert data["domain"] == test_company.domain
        assert data["industry"] == test_company.industry
    
    def test_update_company_info(self, client, admin_auth_headers, test_company):
        """Test updating company information"""
        update_data = {
            "name": "Updated Company Name",
            "description": "Updated company description",
            "website": "https://updated-company.com"
        }
        
        response = client.put(
            f"/api/v1/companies/{test_company.id}", 
            json=update_data, 
            headers=admin_auth_headers
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["name"] == update_data["name"]
        assert data["description"] == update_data["description"]
    
    def test_update_company_unauthorized(self, client, auth_headers, test_company):
        """Test updating company with insufficient permissions"""
        update_data = {"name": "Unauthorized Update"}
        
        response = client.put(
            f"/api/v1/companies/{test_company.id}", 
            json=update_data, 
            headers=auth_headers
        )
        assert response.status_code == 403

class TestJobPositionEndpoints:
    """Test job position management endpoints"""
    
    def test_create_job_position(self, client, auth_headers, test_company):
        """Test creating a new job position"""
        job_data = {
            "title": "Software Engineer",
            "description": "We are looking for a talented software engineer...",
            "requirements": ["Python", "FastAPI", "PostgreSQL"],
            "location": "Remote",
            "job_type": "full-time",
            "experience_level": "mid",
            "salary_min": 80000,
            "salary_max": 120000,
            "is_remote": True
        }
        
        response = client.post("/api/v1/jobs", json=job_data, headers=auth_headers)
        assert response.status_code == 201
        
        data = response.json()
        assert data["title"] == job_data["title"]
        assert data["status"] == "active"
        assert data["company_id"] == test_company.id
    
    def test_get_job_positions(self, client, auth_headers, test_job):
        """Test getting job positions"""
        response = client.get("/api/v1/jobs", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert len(data) >= 1
        assert any(job["id"] == test_job.id for job in data)
    
    def test_get_job_position_by_id(self, client, auth_headers, test_job):
        """Test getting specific job position"""
        response = client.get(f"/api/v1/jobs/{test_job.id}", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert data["id"] == test_job.id
        assert data["title"] == test_job.title
    
    def test_update_job_position(self, client, auth_headers, test_job):
        """Test updating job position"""
        update_data = {
            "title": "Updated Job Title",
            "salary_max": 200000
        }
        
        response = client.put(
            f"/api/v1/jobs/{test_job.id}", 
            json=update_data, 
            headers=auth_headers
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["title"] == update_data["title"]
        assert data["salary_max"] == update_data["salary_max"]
    
    def test_delete_job_position(self, client, auth_headers, test_job):
        """Test deleting job position"""
        response = client.delete(f"/api/v1/jobs/{test_job.id}", headers=auth_headers)
        assert response.status_code == 204
        
        # Verify deletion
        get_response = client.get(f"/api/v1/jobs/{test_job.id}", headers=auth_headers)
        assert get_response.status_code == 404

class TestCandidateEndpoints:
    """Test candidate management endpoints"""
    
    def test_create_candidate_profile(self, client):
        """Test creating candidate profile"""
        candidate_data = {
            "email": "newcandidate@example.com",
            "first_name": "New",
            "last_name": "Candidate",
            "phone": "+1987654321",
            "location": "Boston, MA",
            "skills": ["JavaScript", "React", "Node.js"],
            "experience_years": 3,
            "current_position": "Frontend Developer",
            "education": "Computer Science, Harvard"
        }
        
        response = client.post("/api/v1/candidates", json=candidate_data)
        assert response.status_code == 201
        
        data = response.json()
        assert data["email"] == candidate_data["email"]
        assert data["skills"] == candidate_data["skills"]
    
    def test_get_candidates(self, client, auth_headers, test_candidate):
        """Test getting candidates list"""
        response = client.get("/api/v1/candidates", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert len(data) >= 1
        assert any(candidate["id"] == test_candidate.id for candidate in data)
    
    def test_get_candidate_by_id(self, client, auth_headers, test_candidate):
        """Test getting specific candidate"""
        response = client.get(f"/api/v1/candidates/{test_candidate.id}", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert data["id"] == test_candidate.id
        assert data["email"] == test_candidate.email
    
    def test_search_candidates(self, client, auth_headers, test_candidate):
        """Test searching candidates"""
        search_params = {
            "skills": "Python",
            "experience_min": 3,
            "location": "New York"
        }
        
        response = client.get("/api/v1/candidates/search", params=search_params, headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)

class TestAssessmentEndpoints:
    """Test assessment functionality"""
    
    @patch('app.services.azure_openai_service.AzureOpenAIService.generate_assessment')
    def test_create_assessment(self, mock_ai_service, client, auth_headers, test_job, test_candidate):
        """Test creating candidate assessment"""
        # Mock AI service response
        mock_ai_service.return_value = {
            "overall_score": 85,
            "technical_score": 88,
            "cultural_fit_score": 82,
            "strengths": ["Strong Python skills", "Good problem-solving"],
            "weaknesses": ["Limited DevOps experience"],
            "recommendation": "Highly recommended for the position"
        }
        
        assessment_data = {
            "job_id": test_job.id,
            "candidate_id": test_candidate.id
        }
        
        response = client.post("/api/v1/assessments", json=assessment_data, headers=auth_headers)
        assert response.status_code == 201
        
        data = response.json()
        assert data["overall_score"] == 85
        assert "strengths" in data
        assert "recommendation" in data
    
    def test_get_assessments(self, client, auth_headers):
        """Test getting assessments list"""
        response = client.get("/api/v1/assessments", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)

class TestErrorHandling:
    """Test error handling and edge cases"""
    
    def test_not_found_endpoint(self, client):
        """Test accessing non-existent endpoint"""
        response = client.get("/api/v1/nonexistent")
        assert response.status_code == 404
    
    def test_invalid_json_format(self, client):
        """Test sending invalid JSON"""
        response = client.post(
            "/api/v1/auth/login", 
            data="invalid json",
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 422
    
    def test_missing_required_fields(self, client):
        """Test missing required fields in request"""
        incomplete_data = {"email": "test@example.com"}  # Missing password
        
        response = client.post("/api/v1/auth/login", json=incomplete_data)
        assert response.status_code == 422
        
        data = response.json()
        assert "detail" in data
    
    def test_invalid_email_format(self, client):
        """Test invalid email format"""
        invalid_data = {
            "email": "invalid-email-format",
            "password": "password123"
        }
        
        response = client.post("/api/v1/auth/login", json=invalid_data)
        assert response.status_code == 422
    
    def test_sql_injection_protection(self, client, auth_headers):
        """Test protection against SQL injection"""
        malicious_id = "1 OR 1=1--"
        
        response = client.get(f"/api/v1/jobs/{malicious_id}", headers=auth_headers)
        assert response.status_code in [400, 404, 422]  # Should not return valid data

class TestSecurityFeatures:
    """Test security features and protections"""
    
    def test_cors_headers(self, client):
        """Test CORS headers are present"""
        response = client.options("/api/v1/health")
        assert response.status_code in [200, 405]  # OPTIONS may not be implemented
        
        # Test with a simple GET request
        response = client.get("/api/v1/health")
        assert "access-control-allow-origin" in [h.lower() for h in response.headers.keys()]
    
    def test_security_headers(self, client):
        """Test security headers are present"""
        response = client.get("/api/v1/health")
        
        headers = {h.lower(): v for h, v in response.headers.items()}
        
        # Check for security headers
        expected_headers = [
            "x-content-type-options",
            "x-frame-options",
            "strict-transport-security"
        ]
        
        for header in expected_headers:
            assert header in headers
    
    def test_rate_limiting_simulation(self, client):
        """Test rate limiting behavior simulation"""
        # This would typically require actual rate limiting setup
        # For now, test that the endpoint responds appropriately
        
        for i in range(5):
            response = client.get("/api/v1/health")
            assert response.status_code == 200
    
    def test_input_validation_xss(self, client, auth_headers):
        """Test XSS protection in input validation"""
        xss_payload = "<script>alert('xss')</script>"
        
        job_data = {
            "title": xss_payload,
            "description": "Normal description",
            "requirements": ["Python"],
            "location": "Remote",
            "job_type": "full-time",
            "experience_level": "mid"
        }
        
        response = client.post("/api/v1/jobs", json=job_data, headers=auth_headers)
        
        if response.status_code == 201:
            # If created, ensure XSS payload is sanitized
            data = response.json()
            assert "<script>" not in data["title"]

class TestPerformanceAndReliability:
    """Test performance and reliability aspects"""
    
    def test_concurrent_requests(self, client, test_user):
        """Test handling concurrent requests"""
        import concurrent.futures
        import time
        
        def make_request():
            return client.get("/api/v1/health")
        
        start_time = time.time()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request) for _ in range(10)]
            responses = [future.result() for future in futures]
        
        end_time = time.time()
        
        # All requests should succeed
        assert all(response.status_code == 200 for response in responses)
        
        # Should complete within reasonable time
        assert end_time - start_time < 5.0
    
    def test_large_payload_handling(self, client, auth_headers):
        """Test handling of large payloads"""
        large_description = "x" * 10000  # 10KB description
        
        job_data = {
            "title": "Large Payload Test",
            "description": large_description,
            "requirements": ["Python"] * 100,  # Large requirements list
            "location": "Remote",
            "job_type": "full-time",
            "experience_level": "mid"
        }
        
        response = client.post("/api/v1/jobs", json=job_data, headers=auth_headers)
        # Should either accept or reject gracefully (not crash)
        assert response.status_code in [201, 400, 413, 422]

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "--maxfail=5"])