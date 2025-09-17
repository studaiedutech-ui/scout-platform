"""
Comprehensive Data Validation and Sanitization Module for S.C.O.U.T. Platform
Ensures data integrity, security, and compliance with business rules
"""

from typing import Any, Dict, List, Optional, Union
import re
import html
import json
import uuid
from datetime import datetime, date
from decimal import Decimal, InvalidOperation
from email_validator import validate_email, EmailNotValidError
from pydantic import BaseModel, validator, Field
from fastapi import HTTPException, status
import logging

logger = logging.getLogger(__name__)

class DataSanitizer:
    """Comprehensive data sanitization utilities"""
    
    # Regex patterns for validation
    PHONE_PATTERN = re.compile(r'^\+?1?\d{9,15}$')
    SQL_INJECTION_PATTERN = re.compile(r'(\b(SELECT|INSERT|UPDATE|DELETE|DROP|UNION|ALTER|CREATE|EXEC|SCRIPT)\b)', re.IGNORECASE)
    XSS_PATTERNS = [
        re.compile(r'<script[^>]*>.*?</script>', re.IGNORECASE | re.DOTALL),
        re.compile(r'javascript:', re.IGNORECASE),
        re.compile(r'on\w+\s*=', re.IGNORECASE),
        re.compile(r'<iframe[^>]*>.*?</iframe>', re.IGNORECASE | re.DOTALL),
        re.compile(r'<object[^>]*>.*?</object>', re.IGNORECASE | re.DOTALL),
        re.compile(r'<embed[^>]*>', re.IGNORECASE),
    ]
    
    @staticmethod
    def sanitize_string(value: str, max_length: int = None, allow_html: bool = False) -> str:
        """Sanitize string input"""
        if not isinstance(value, str):
            value = str(value)
        
        # Remove null bytes
        value = value.replace('\x00', '')
        
        # Trim whitespace
        value = value.strip()
        
        # Check for SQL injection patterns
        if DataSanitizer.SQL_INJECTION_PATTERN.search(value):
            logger.warning(f"Potential SQL injection attempt detected: {value[:100]}...")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid input detected"
            )
        
        # Handle HTML content
        if not allow_html:
            # Remove XSS patterns
            for pattern in DataSanitizer.XSS_PATTERNS:
                value = pattern.sub('', value)
            
            # HTML escape
            value = html.escape(value)
        else:
            # Sanitize HTML but allow basic tags
            value = DataSanitizer._sanitize_html(value)
        
        # Apply length limit
        if max_length and len(value) > max_length:
            value = value[:max_length]
        
        return value
    
    @staticmethod
    def _sanitize_html(html_content: str) -> str:
        """Sanitize HTML content while preserving safe tags"""
        # This is a basic implementation
        # In production, use a library like bleach for comprehensive HTML sanitization
        allowed_tags = ['p', 'br', 'strong', 'em', 'u', 'ol', 'ul', 'li', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6']
        
        # Remove dangerous patterns
        for pattern in DataSanitizer.XSS_PATTERNS:
            html_content = pattern.sub('', html_content)
        
        return html_content
    
    @staticmethod
    def sanitize_email(email: str) -> str:
        """Sanitize and validate email address"""
        try:
            email = email.lower().strip()
            validated_email = validate_email(email)
            return validated_email.email
        except EmailNotValidError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid email format: {str(e)}"
            )
    
    @staticmethod
    def sanitize_phone(phone: str) -> str:
        """Sanitize and validate phone number"""
        # Remove all non-digit characters except + at the beginning
        phone = re.sub(r'[^\d+]', '', phone)
        
        if not DataSanitizer.PHONE_PATTERN.match(phone):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid phone number format"
            )
        
        return phone
    
    @staticmethod
    def sanitize_numeric(value: Any, min_value: float = None, max_value: float = None) -> Union[int, float]:
        """Sanitize numeric input"""
        try:
            if isinstance(value, str):
                # Remove any non-numeric characters except decimal point and minus
                value = re.sub(r'[^\d.-]', '', value)
            
            if '.' in str(value):
                num_value = float(value)
            else:
                num_value = int(value)
            
            if min_value is not None and num_value < min_value:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Value must be at least {min_value}"
                )
            
            if max_value is not None and num_value > max_value:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Value must not exceed {max_value}"
                )
            
            return num_value
            
        except (ValueError, InvalidOperation):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid numeric value"
            )
    
    @staticmethod
    def sanitize_json(value: str) -> Dict[str, Any]:
        """Sanitize and parse JSON input"""
        try:
            # Remove control characters
            value = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', value)
            
            parsed = json.loads(value)
            
            # Recursively sanitize string values in JSON
            return DataSanitizer._sanitize_json_recursive(parsed)
            
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid JSON format"
            )
    
    @staticmethod
    def _sanitize_json_recursive(obj: Any) -> Any:
        """Recursively sanitize JSON object"""
        if isinstance(obj, dict):
            return {key: DataSanitizer._sanitize_json_recursive(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [DataSanitizer._sanitize_json_recursive(item) for item in obj]
        elif isinstance(obj, str):
            return DataSanitizer.sanitize_string(obj)
        else:
            return obj

class BusinessRuleValidator:
    """Business rule validation for S.C.O.U.T. platform"""
    
    @staticmethod
    def validate_company_name(name: str) -> str:
        """Validate company name"""
        name = DataSanitizer.sanitize_string(name, max_length=100)
        
        if len(name) < 2:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Company name must be at least 2 characters long"
            )
        
        # Check for valid characters (letters, numbers, spaces, hyphens, apostrophes)
        if not re.match(r"^[a-zA-Z0-9\s\-'&.]+$", name):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Company name contains invalid characters"
            )
        
        return name
    
    @staticmethod
    def validate_job_title(title: str) -> str:
        """Validate job title"""
        title = DataSanitizer.sanitize_string(title, max_length=100)
        
        if len(title) < 3:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Job title must be at least 3 characters long"
            )
        
        return title
    
    @staticmethod
    def validate_salary_range(min_salary: float, max_salary: float) -> tuple:
        """Validate salary range"""
        min_salary = DataSanitizer.sanitize_numeric(min_salary, min_value=0, max_value=10000000)
        max_salary = DataSanitizer.sanitize_numeric(max_salary, min_value=0, max_value=10000000)
        
        if min_salary >= max_salary:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Minimum salary must be less than maximum salary"
            )
        
        return min_salary, max_salary
    
    @staticmethod
    def validate_experience_years(years: int) -> int:
        """Validate experience years"""
        years = int(DataSanitizer.sanitize_numeric(years, min_value=0, max_value=50))
        return years
    
    @staticmethod
    def validate_assessment_duration(duration_minutes: int) -> int:
        """Validate assessment duration"""
        duration = int(DataSanitizer.sanitize_numeric(duration_minutes, min_value=5, max_value=480))  # 5 min to 8 hours
        return duration
    
    @staticmethod
    def validate_skills_list(skills: List[str]) -> List[str]:
        """Validate list of skills"""
        if not skills or len(skills) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one skill is required"
            )
        
        if len(skills) > 20:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Maximum 20 skills allowed"
            )
        
        validated_skills = []
        for skill in skills:
            skill = DataSanitizer.sanitize_string(skill, max_length=50)
            if len(skill) < 2:
                continue
            validated_skills.append(skill)
        
        if not validated_skills:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No valid skills provided"
            )
        
        return validated_skills

# Pydantic models for request validation
class BaseValidationModel(BaseModel):
    """Base model with common validation"""
    
    class Config:
        str_strip_whitespace = True
        validate_assignment = True
        use_enum_values = True

class CompanyRegistrationModel(BaseValidationModel):
    """Company registration validation model"""
    name: str = Field(..., min_length=2, max_length=100)
    email: str = Field(..., max_length=255)
    phone: Optional[str] = Field(None, max_length=20)
    website: Optional[str] = Field(None, max_length=255)
    industry: str = Field(..., min_length=2, max_length=100)
    size: str = Field(..., regex=r'^(1-10|11-50|51-200|201-500|501-1000|1000\+)$')
    description: Optional[str] = Field(None, max_length=1000)
    
    @validator('name')
    def validate_name(cls, v):
        return BusinessRuleValidator.validate_company_name(v)
    
    @validator('email')
    def validate_email(cls, v):
        return DataSanitizer.sanitize_email(v)
    
    @validator('phone')
    def validate_phone(cls, v):
        if v:
            return DataSanitizer.sanitize_phone(v)
        return v
    
    @validator('website')
    def validate_website(cls, v):
        if v:
            v = DataSanitizer.sanitize_string(v, max_length=255)
            # Basic URL validation
            if not re.match(r'^https?://', v):
                v = f"https://{v}"
            if not re.match(r'^https?://[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', v):
                raise ValueError("Invalid website URL")
        return v

class JobPositionModel(BaseValidationModel):
    """Job position validation model"""
    title: str = Field(..., min_length=3, max_length=100)
    department: str = Field(..., min_length=2, max_length=50)
    location: str = Field(..., min_length=2, max_length=100)
    employment_type: str = Field(..., regex=r'^(full-time|part-time|contract|internship)$')
    experience_level: str = Field(..., regex=r'^(entry|mid|senior|executive)$')
    min_salary: Optional[float] = Field(None, ge=0, le=10000000)
    max_salary: Optional[float] = Field(None, ge=0, le=10000000)
    required_skills: List[str] = Field(..., min_items=1, max_items=20)
    preferred_skills: Optional[List[str]] = Field(None, max_items=10)
    description: str = Field(..., min_length=50, max_length=5000)
    requirements: str = Field(..., min_length=20, max_length=2000)
    benefits: Optional[str] = Field(None, max_length=1000)
    
    @validator('title')
    def validate_title(cls, v):
        return BusinessRuleValidator.validate_job_title(v)
    
    @validator('min_salary', 'max_salary')
    def validate_salary(cls, v):
        if v is not None:
            return DataSanitizer.sanitize_numeric(v, min_value=0, max_value=10000000)
        return v
    
    @validator('required_skills', 'preferred_skills')
    def validate_skills(cls, v):
        if v:
            return BusinessRuleValidator.validate_skills_list(v)
        return v
    
    @validator('description', 'requirements', 'benefits')
    def validate_text_fields(cls, v):
        if v:
            return DataSanitizer.sanitize_string(v, allow_html=True)
        return v

class CandidateProfileModel(BaseValidationModel):
    """Candidate profile validation model"""
    first_name: str = Field(..., min_length=1, max_length=50)
    last_name: str = Field(..., min_length=1, max_length=50)
    email: str = Field(..., max_length=255)
    phone: Optional[str] = Field(None, max_length=20)
    location: str = Field(..., min_length=2, max_length=100)
    linkedin_url: Optional[str] = Field(None, max_length=255)
    github_url: Optional[str] = Field(None, max_length=255)
    portfolio_url: Optional[str] = Field(None, max_length=255)
    experience_years: int = Field(..., ge=0, le=50)
    current_position: Optional[str] = Field(None, max_length=100)
    current_company: Optional[str] = Field(None, max_length=100)
    skills: List[str] = Field(..., min_items=1, max_items=30)
    education: Optional[str] = Field(None, max_length=500)
    summary: Optional[str] = Field(None, max_length=1000)
    
    @validator('first_name', 'last_name')
    def validate_names(cls, v):
        v = DataSanitizer.sanitize_string(v, max_length=50)
        if not re.match(r"^[a-zA-Z\s\-']+$", v):
            raise ValueError("Name contains invalid characters")
        return v
    
    @validator('email')
    def validate_email(cls, v):
        return DataSanitizer.sanitize_email(v)
    
    @validator('phone')
    def validate_phone(cls, v):
        if v:
            return DataSanitizer.sanitize_phone(v)
        return v
    
    @validator('linkedin_url', 'github_url', 'portfolio_url')
    def validate_urls(cls, v):
        if v:
            v = DataSanitizer.sanitize_string(v, max_length=255)
            if not re.match(r'^https?://', v):
                v = f"https://{v}"
            if not re.match(r'^https?://[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', v):
                raise ValueError("Invalid URL format")
        return v
    
    @validator('experience_years')
    def validate_experience(cls, v):
        return BusinessRuleValidator.validate_experience_years(v)
    
    @validator('skills')
    def validate_skills(cls, v):
        return BusinessRuleValidator.validate_skills_list(v)

class AssessmentConfigModel(BaseValidationModel):
    """Assessment configuration validation model"""
    name: str = Field(..., min_length=3, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    duration_minutes: int = Field(..., ge=5, le=480)
    question_count: int = Field(..., ge=1, le=100)
    difficulty_level: str = Field(..., regex=r'^(beginner|intermediate|advanced|expert)$')
    skills_to_assess: List[str] = Field(..., min_items=1, max_items=10)
    passing_score: int = Field(..., ge=0, le=100)
    allow_retakes: bool = Field(default=False)
    randomize_questions: bool = Field(default=True)
    show_results_immediately: bool = Field(default=False)
    
    @validator('name')
    def validate_name(cls, v):
        return DataSanitizer.sanitize_string(v, max_length=100)
    
    @validator('duration_minutes')
    def validate_duration(cls, v):
        return BusinessRuleValidator.validate_assessment_duration(v)
    
    @validator('skills_to_assess')
    def validate_skills(cls, v):
        return BusinessRuleValidator.validate_skills_list(v)

# Export validation functions
def validate_and_sanitize_input(data: Dict[str, Any], model_class: BaseModel) -> BaseModel:
    """Validate and sanitize input data using Pydantic model"""
    try:
        return model_class(**data)
    except Exception as e:
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Validation error: {str(e)}"
        )

# Initialize sanitizer
data_sanitizer = DataSanitizer()
business_validator = BusinessRuleValidator()