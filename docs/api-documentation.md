# S.C.O.U.T. Platform API Documentation

## Table of Contents

1. [Overview](#overview)
2. [Authentication](#authentication)
3. [API Endpoints](#api-endpoints)
4. [Data Models](#data-models)
5. [Error Handling](#error-handling)
6. [Rate Limiting](#rate-limiting)
7. [Code Examples](#code-examples)
8. [WebSocket Events](#websocket-events)

## Overview

The S.C.O.U.T. (Strategic Candidate Operations and Unified Talent) platform provides a comprehensive REST API for AI-driven talent acquisition and assessment.

**Base URL**: `https://api.scout-platform.com/api/v1`

**API Version**: v1

**Content Type**: `application/json`

**Authentication**: Bearer Token (JWT)

## Authentication

### Overview

The API uses JWT (JSON Web Tokens) for authentication. All protected endpoints require a valid access token in the Authorization header.

### Authentication Flow

1. **Register/Login** → Receive access token and refresh token
2. **Include access token** in all subsequent requests
3. **Refresh token** when access token expires
4. **Logout** to invalidate tokens

### Endpoints

#### POST /auth/register
Register a new company account.

```http
POST /api/v1/auth/register
Content-Type: application/json

{
  "email": "admin@company.com",
  "password": "SecurePassword123!",
  "company_name": "Tech Solutions Inc",
  "first_name": "John",
  "last_name": "Doe"
}
```

**Response (201 Created):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 1800,
  "user": {
    "id": 1,
    "email": "admin@company.com",
    "first_name": "John",
    "last_name": "Doe",
    "company_id": 1,
    "is_active": true
  }
}
```

#### POST /auth/login
Authenticate with email and password.

```http
POST /api/v1/auth/login
Content-Type: application/json

{
  "email": "admin@company.com",
  "password": "SecurePassword123!"
}
```

**Response (200 OK):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 1800,
  "user": {
    "id": 1,
    "email": "admin@company.com",
    "first_name": "John",
    "last_name": "Doe",
    "company_id": 1,
    "last_login": "2024-01-15T10:30:00Z"
  }
}
```

#### POST /auth/refresh
Refresh an expired access token.

```http
POST /api/v1/auth/refresh
Content-Type: application/json

{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

#### POST /auth/logout
Logout and invalidate tokens.

```http
POST /api/v1/auth/logout
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

#### POST /auth/change-password
Change user password.

```http
POST /api/v1/auth/change-password
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Content-Type: application/json

{
  "current_password": "OldPassword123!",
  "new_password": "NewSecurePassword456!"
}
```

## API Endpoints

### Company Management

#### GET /companies
Get company information.

```http
GET /api/v1/companies
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Response (200 OK):**
```json
{
  "id": 1,
  "name": "Tech Solutions Inc",
  "industry": "Technology",
  "size": "medium",
  "website": "https://techsolutions.com",
  "description": "Leading technology solutions provider",
  "created_at": "2024-01-01T00:00:00Z",
  "settings": {
    "ai_assessment_enabled": true,
    "auto_screening": true,
    "notification_preferences": {
      "email": true,
      "sms": false
    }
  }
}
```

#### PUT /companies
Update company information.

```http
PUT /api/v1/companies
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Content-Type: application/json

{
  "name": "Tech Solutions Inc",
  "industry": "Technology",
  "size": "large",
  "website": "https://techsolutions.com",
  "description": "Updated description"
}
```

### Job Management

#### GET /jobs
List all jobs for the company.

```http
GET /api/v1/jobs?page=1&limit=10&status=active
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Query Parameters:**
- `page` (int): Page number (default: 1)
- `limit` (int): Items per page (default: 10, max: 100)
- `status` (string): Filter by status (active, draft, closed)
- `title` (string): Filter by job title
- `location` (string): Filter by location

**Response (200 OK):**
```json
{
  "items": [
    {
      "id": 1,
      "title": "Senior Python Developer",
      "description": "We are looking for an experienced Python developer...",
      "requirements": [
        "5+ years Python experience",
        "FastAPI framework knowledge",
        "PostgreSQL database skills"
      ],
      "location": "Remote",
      "employment_type": "full_time",
      "experience_level": "senior",
      "salary_range": {
        "min": 80000,
        "max": 120000,
        "currency": "USD"
      },
      "status": "active",
      "created_at": "2024-01-10T00:00:00Z",
      "expires_at": "2024-02-10T00:00:00Z",
      "applications_count": 25,
      "views_count": 150
    }
  ],
  "total": 1,
  "page": 1,
  "pages": 1,
  "per_page": 10
}
```

#### POST /jobs
Create a new job posting.

```http
POST /api/v1/jobs
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Content-Type: application/json

{
  "title": "Senior Python Developer",
  "description": "We are looking for an experienced Python developer to join our team...",
  "requirements": [
    "5+ years Python experience",
    "FastAPI framework knowledge",
    "PostgreSQL database skills"
  ],
  "location": "Remote",
  "employment_type": "full_time",
  "experience_level": "senior",
  "salary_range": {
    "min": 80000,
    "max": 120000,
    "currency": "USD"
  },
  "expires_at": "2024-02-10T00:00:00Z"
}
```

#### GET /jobs/{job_id}
Get specific job details.

```http
GET /api/v1/jobs/1
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

#### PUT /jobs/{job_id}
Update job information.

```http
PUT /api/v1/jobs/1
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Content-Type: application/json

{
  "title": "Updated Job Title",
  "status": "active"
}
```

#### DELETE /jobs/{job_id}
Delete a job posting.

```http
DELETE /api/v1/jobs/1
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### Candidate Management

#### GET /candidates
List candidates who applied to company jobs.

```http
GET /api/v1/candidates?page=1&limit=10&job_id=1&status=applied
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Query Parameters:**
- `page` (int): Page number
- `limit` (int): Items per page
- `job_id` (int): Filter by specific job
- `status` (string): Filter by application status
- `experience_level` (string): Filter by experience level
- `search` (string): Search by name or skills

**Response (200 OK):**
```json
{
  "items": [
    {
      "id": 1,
      "email": "candidate@example.com",
      "first_name": "Jane",
      "last_name": "Smith",
      "phone": "+1-555-0123",
      "experience_level": "senior",
      "skills": ["Python", "FastAPI", "PostgreSQL", "Docker"],
      "resume_url": "https://storage.com/resumes/candidate_1.pdf",
      "application": {
        "job_id": 1,
        "status": "applied",
        "applied_at": "2024-01-12T10:00:00Z",
        "cover_letter": "I am excited to apply for this position..."
      },
      "assessment_score": 85.5,
      "created_at": "2024-01-12T10:00:00Z"
    }
  ],
  "total": 15,
  "page": 1,
  "pages": 2,
  "per_page": 10
}
```

#### GET /candidates/{candidate_id}
Get specific candidate details.

```http
GET /api/v1/candidates/1
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

#### PUT /candidates/{candidate_id}/status
Update candidate application status.

```http
PUT /api/v1/candidates/1/status
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Content-Type: application/json

{
  "status": "interview_scheduled",
  "notes": "Impressed with technical skills, scheduling technical interview"
}
```

### Assessment Management

#### GET /assessments
List AI assessments for candidates.

```http
GET /api/v1/assessments?job_id=1&candidate_id=1
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Response (200 OK):**
```json
{
  "items": [
    {
      "id": 1,
      "job_id": 1,
      "candidate_id": 1,
      "status": "completed",
      "overall_score": 85.5,
      "technical_score": 90.0,
      "soft_skills_score": 80.0,
      "cultural_fit_score": 86.0,
      "recommendations": "Strong technical candidate with excellent problem-solving skills...",
      "strengths": [
        "Advanced Python programming",
        "System design expertise",
        "Strong communication skills"
      ],
      "areas_for_improvement": [
        "Could benefit from more experience with cloud platforms"
      ],
      "created_at": "2024-01-12T15:00:00Z",
      "completed_at": "2024-01-12T15:30:00Z"
    }
  ],
  "total": 1,
  "page": 1,
  "pages": 1,
  "per_page": 10
}
```

#### POST /assessments
Create a new AI assessment for a candidate.

```http
POST /api/v1/assessments
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Content-Type: application/json

{
  "job_id": 1,
  "candidate_id": 1,
  "assessment_type": "full"
}
```

#### GET /assessments/{assessment_id}
Get detailed assessment results.

```http
GET /api/v1/assessments/1
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### Analytics and Reporting

#### GET /analytics/dashboard
Get dashboard analytics data.

```http
GET /api/v1/analytics/dashboard?period=30d
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Response (200 OK):**
```json
{
  "summary": {
    "total_jobs": 25,
    "active_jobs": 15,
    "total_applications": 450,
    "new_applications": 35,
    "assessments_completed": 120,
    "interviews_scheduled": 28
  },
  "trends": {
    "applications_per_day": [
      {"date": "2024-01-01", "count": 12},
      {"date": "2024-01-02", "count": 15}
    ],
    "top_skills": [
      {"skill": "Python", "count": 89},
      {"skill": "JavaScript", "count": 76}
    ]
  },
  "performance": {
    "avg_time_to_hire": 14.5,
    "application_to_interview_rate": 0.15,
    "offer_acceptance_rate": 0.78
  }
}
```

### Health and Status

#### GET /health
Basic health check endpoint.

```http
GET /api/v1/health
```

**Response (200 OK):**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00Z",
  "version": "1.0.0"
}
```

#### GET /health/detailed
Detailed health check with component status.

```http
GET /api/v1/health/detailed
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Response (200 OK):**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00Z",
  "version": "1.0.0",
  "components": {
    "database": {
      "status": "healthy",
      "response_time": 45
    },
    "redis": {
      "status": "healthy",
      "response_time": 12
    },
    "azure_openai": {
      "status": "healthy",
      "response_time": 234
    }
  }
}
```

## Data Models

### User
```json
{
  "id": "integer",
  "email": "string (email format)",
  "first_name": "string",
  "last_name": "string",
  "company_id": "integer",
  "is_active": "boolean",
  "created_at": "string (ISO 8601)",
  "last_login": "string (ISO 8601)",
  "password_changed_at": "string (ISO 8601)"
}
```

### Company
```json
{
  "id": "integer",
  "name": "string",
  "industry": "string",
  "size": "string (enum: startup, small, medium, large, enterprise)",
  "website": "string (URL)",
  "description": "string",
  "settings": "object",
  "created_at": "string (ISO 8601)",
  "updated_at": "string (ISO 8601)"
}
```

### Job
```json
{
  "id": "integer",
  "company_id": "integer",
  "title": "string",
  "description": "string",
  "requirements": "array of strings",
  "location": "string",
  "employment_type": "string (enum: full_time, part_time, contract, internship)",
  "experience_level": "string (enum: entry, junior, mid, senior, lead, executive)",
  "salary_range": {
    "min": "integer",
    "max": "integer", 
    "currency": "string"
  },
  "status": "string (enum: draft, active, paused, closed)",
  "created_at": "string (ISO 8601)",
  "updated_at": "string (ISO 8601)",
  "expires_at": "string (ISO 8601)"
}
```

### Candidate
```json
{
  "id": "integer",
  "email": "string (email format)",
  "first_name": "string",
  "last_name": "string",
  "phone": "string",
  "experience_level": "string (enum: entry, junior, mid, senior, lead, executive)",
  "skills": "array of strings",
  "resume_url": "string (URL)",
  "portfolio_url": "string (URL)",
  "linkedin_url": "string (URL)",
  "created_at": "string (ISO 8601)",
  "updated_at": "string (ISO 8601)"
}
```

### Assessment
```json
{
  "id": "integer",
  "job_id": "integer",
  "candidate_id": "integer",
  "status": "string (enum: pending, in_progress, completed, failed)",
  "assessment_type": "string (enum: full, technical, soft_skills, cultural_fit)",
  "overall_score": "number (0-100)",
  "technical_score": "number (0-100)",
  "soft_skills_score": "number (0-100)",
  "cultural_fit_score": "number (0-100)",
  "recommendations": "string",
  "strengths": "array of strings",
  "areas_for_improvement": "array of strings",
  "detailed_results": "object",
  "created_at": "string (ISO 8601)",
  "completed_at": "string (ISO 8601)"
}
```

## Error Handling

### Error Response Format

All errors follow a consistent format:

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human readable error message",
    "details": "Additional error details (optional)",
    "timestamp": "2024-01-15T10:30:00Z",
    "request_id": "uuid-string"
  }
}
```

### HTTP Status Codes

| Status Code | Description |
|-------------|-------------|
| 200 | OK - Successful request |
| 201 | Created - Resource successfully created |
| 204 | No Content - Successful request with no response body |
| 400 | Bad Request - Invalid request format or parameters |
| 401 | Unauthorized - Authentication required or invalid |
| 403 | Forbidden - Access denied |
| 404 | Not Found - Resource not found |
| 409 | Conflict - Resource already exists |
| 422 | Unprocessable Entity - Validation error |
| 429 | Too Many Requests - Rate limit exceeded |
| 500 | Internal Server Error - Server error |
| 503 | Service Unavailable - Service temporarily unavailable |

### Common Error Codes

| Error Code | Description |
|------------|-------------|
| `INVALID_CREDENTIALS` | Invalid email or password |
| `TOKEN_EXPIRED` | Access token has expired |
| `TOKEN_INVALID` | Invalid or malformed token |
| `RATE_LIMIT_EXCEEDED` | Too many requests |
| `VALIDATION_ERROR` | Request validation failed |
| `RESOURCE_NOT_FOUND` | Requested resource not found |
| `PERMISSION_DENIED` | Insufficient permissions |
| `ACCOUNT_LOCKED` | Account temporarily locked |
| `PASSWORD_TOO_WEAK` | Password doesn't meet requirements |

### Example Error Responses

**Validation Error (422):**
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Validation failed",
    "details": {
      "email": ["Invalid email format"],
      "password": ["Password must be at least 12 characters"]
    },
    "timestamp": "2024-01-15T10:30:00Z",
    "request_id": "12345678-1234-1234-1234-123456789012"
  }
}
```

**Rate Limit Error (429):**
```json
{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Too many requests",
    "details": "Rate limit exceeded. Try again in 60 seconds.",
    "timestamp": "2024-01-15T10:30:00Z",
    "request_id": "12345678-1234-1234-1234-123456789012"
  },
  "retry_after": 60
}
```

## Rate Limiting

### Rate Limits

| Endpoint Category | Limit |
|------------------|-------|
| Authentication | 10 requests per minute |
| Job Management | 100 requests per minute |
| Candidate Search | 50 requests per minute |
| AI Assessments | 20 requests per minute |
| General API | 200 requests per minute |

### Rate Limit Headers

All responses include rate limiting headers:

```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1642248600
X-RateLimit-Window: 60
```

## Code Examples

### Python Example

```python
import requests
import json

class ScoutPlatformAPI:
    def __init__(self, base_url, api_key=None):
        self.base_url = base_url
        self.access_token = api_key
        self.session = requests.Session()
        
    def login(self, email, password):
        """Authenticate and get access token"""
        response = self.session.post(
            f"{self.base_url}/auth/login",
            json={"email": email, "password": password}
        )
        
        if response.status_code == 200:
            data = response.json()
            self.access_token = data["access_token"]
            return data
        else:
            raise Exception(f"Login failed: {response.text}")
    
    def _get_headers(self):
        """Get headers with authentication"""
        headers = {"Content-Type": "application/json"}
        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
        return headers
    
    def create_job(self, job_data):
        """Create a new job posting"""
        response = self.session.post(
            f"{self.base_url}/jobs",
            json=job_data,
            headers=self._get_headers()
        )
        
        if response.status_code == 201:
            return response.json()
        else:
            raise Exception(f"Job creation failed: {response.text}")
    
    def get_candidates(self, job_id=None, page=1, limit=10):
        """Get candidates list"""
        params = {"page": page, "limit": limit}
        if job_id:
            params["job_id"] = job_id
            
        response = self.session.get(
            f"{self.base_url}/candidates",
            params=params,
            headers=self._get_headers()
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Failed to get candidates: {response.text}")

# Usage example
api = ScoutPlatformAPI("https://api.scout-platform.com/api/v1")

# Login
api.login("admin@company.com", "password123")

# Create a job
job_data = {
    "title": "Senior Python Developer",
    "description": "We are looking for an experienced Python developer...",
    "requirements": ["Python", "FastAPI", "PostgreSQL"],
    "location": "Remote",
    "employment_type": "full_time",
    "experience_level": "senior"
}

job = api.create_job(job_data)
print(f"Created job: {job['id']}")

# Get candidates
candidates = api.get_candidates(job_id=job["id"])
print(f"Found {candidates['total']} candidates")
```

### JavaScript Example

```javascript
class ScoutPlatformAPI {
    constructor(baseUrl, apiKey = null) {
        this.baseUrl = baseUrl;
        this.accessToken = apiKey;
    }

    async login(email, password) {
        const response = await fetch(`${this.baseUrl}/auth/login`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ email, password })
        });

        if (response.ok) {
            const data = await response.json();
            this.accessToken = data.access_token;
            return data;
        } else {
            throw new Error(`Login failed: ${await response.text()}`);
        }
    }

    getHeaders() {
        const headers = {
            'Content-Type': 'application/json'
        };
        
        if (this.accessToken) {
            headers['Authorization'] = `Bearer ${this.accessToken}`;
        }
        
        return headers;
    }

    async createJob(jobData) {
        const response = await fetch(`${this.baseUrl}/jobs`, {
            method: 'POST',
            headers: this.getHeaders(),
            body: JSON.stringify(jobData)
        });

        if (response.ok) {
            return await response.json();
        } else {
            throw new Error(`Job creation failed: ${await response.text()}`);
        }
    }

    async getCandidates(jobId = null, page = 1, limit = 10) {
        const params = new URLSearchParams({
            page: page.toString(),
            limit: limit.toString()
        });
        
        if (jobId) {
            params.append('job_id', jobId.toString());
        }

        const response = await fetch(`${this.baseUrl}/candidates?${params}`, {
            method: 'GET',
            headers: this.getHeaders()
        });

        if (response.ok) {
            return await response.json();
        } else {
            throw new Error(`Failed to get candidates: ${await response.text()}`);
        }
    }
}

// Usage example
const api = new ScoutPlatformAPI('https://api.scout-platform.com/api/v1');

// Login and create job
(async () => {
    try {
        await api.login('admin@company.com', 'password123');
        
        const jobData = {
            title: 'Senior Python Developer',
            description: 'We are looking for an experienced Python developer...',
            requirements: ['Python', 'FastAPI', 'PostgreSQL'],
            location: 'Remote',
            employment_type: 'full_time',
            experience_level: 'senior'
        };

        const job = await api.createJob(jobData);
        console.log(`Created job: ${job.id}`);

        const candidates = await api.getCandidates(job.id);
        console.log(`Found ${candidates.total} candidates`);
        
    } catch (error) {
        console.error('API Error:', error.message);
    }
})();
```

### cURL Examples

```bash
# Login
curl -X POST https://api.scout-platform.com/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@company.com",
    "password": "password123"
  }'

# Create job (replace TOKEN with actual token)
curl -X POST https://api.scout-platform.com/api/v1/jobs \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer TOKEN" \
  -d '{
    "title": "Senior Python Developer",
    "description": "We are looking for an experienced Python developer...",
    "requirements": ["Python", "FastAPI", "PostgreSQL"],
    "location": "Remote",
    "employment_type": "full_time",
    "experience_level": "senior"
  }'

# Get candidates
curl -X GET "https://api.scout-platform.com/api/v1/candidates?page=1&limit=10" \
  -H "Authorization: Bearer TOKEN"

# Get job analytics
curl -X GET "https://api.scout-platform.com/api/v1/analytics/dashboard?period=30d" \
  -H "Authorization: Bearer TOKEN"
```

## WebSocket Events

The API supports real-time updates via WebSocket connections for certain events.

### Connection

```javascript
const ws = new WebSocket('wss://api.scout-platform.com/ws');

// Authenticate after connection
ws.onopen = function() {
    ws.send(JSON.stringify({
        type: 'auth',
        token: 'your-access-token'
    }));
};
```

### Event Types

#### New Application
```json
{
  "type": "new_application",
  "data": {
    "job_id": 1,
    "candidate_id": 123,
    "candidate_name": "Jane Smith",
    "timestamp": "2024-01-15T10:30:00Z"
  }
}
```

#### Assessment Complete
```json
{
  "type": "assessment_complete",
  "data": {
    "assessment_id": 456,
    "job_id": 1,
    "candidate_id": 123,
    "overall_score": 85.5,
    "timestamp": "2024-01-15T10:30:00Z"
  }
}
```

#### Job Status Update
```json
{
  "type": "job_status_update", 
  "data": {
    "job_id": 1,
    "old_status": "active",
    "new_status": "paused",
    "timestamp": "2024-01-15T10:30:00Z"
  }
}
```

---

This API documentation provides comprehensive information for integrating with the S.C.O.U.T. platform. For additional support or questions, please contact our development team.