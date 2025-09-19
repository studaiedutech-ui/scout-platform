"""
Job Model for Recruitment Platform
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Text, Enum as SQLEnum, JSON
from sqlalchemy.orm import relationship
import enum

from app.core.database import Base


class JobStatus(enum.Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    CLOSED = "closed"
    ARCHIVED = "archived"


class JobType(enum.Enum):
    FULL_TIME = "full_time"
    PART_TIME = "part_time"
    CONTRACT = "contract"
    TEMPORARY = "temporary"
    INTERNSHIP = "internship"


class ExperienceLevel(enum.Enum):
    ENTRY = "entry"
    MID = "mid"
    SENIOR = "senior"
    LEAD = "lead"
    EXECUTIVE = "executive"


class Job(Base):
    """
    Job posting model for recruitment
    """
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False, index=True)
    slug = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=False)
    
    # Company Association (Multi-tenant)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Job Details
    department = Column(String(100))
    location = Column(String(255))
    remote_allowed = Column(Boolean, default=False)
    job_type = Column(SQLEnum(JobType), default=JobType.FULL_TIME)
    experience_level = Column(SQLEnum(ExperienceLevel), default=ExperienceLevel.MID)
    
    # Status and Visibility
    status = Column(SQLEnum(JobStatus), default=JobStatus.DRAFT, index=True)
    is_featured = Column(Boolean, default=False)
    expires_at = Column(DateTime)
    
    # Requirements and Qualifications
    required_skills = Column(JSON)  # List of required skills
    preferred_skills = Column(JSON)  # List of preferred skills
    qualifications = Column(Text)
    responsibilities = Column(Text)
    
    # Compensation (Optional)
    salary_min = Column(Integer)
    salary_max = Column(Integer)
    salary_currency = Column(String(3), default="USD")
    benefits = Column(Text)
    
    # Assessment Configuration
    assessment_enabled = Column(Boolean, default=True)
    assessment_config = Column(JSON)  # Assessment configuration
    assessment_link = Column(String(500))  # Public assessment link
    
    # Analytics
    views_count = Column(Integer, default=0)
    applications_count = Column(Integer, default=0)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    company = relationship("Company", back_populates="jobs")
    created_by_user = relationship("User", back_populates="created_jobs")
    candidates = relationship("Candidate", back_populates="job")
    
    def __repr__(self):
        return f"<Job {self.title}>"
    
    @property
    def is_active(self):
        """Check if job is active and accepting applications"""
        if self.status != JobStatus.ACTIVE:
            return False
        if self.expires_at and datetime.utcnow() > self.expires_at:
            return False
        return True
    
    @property
    def is_expired(self):
        """Check if job has expired"""
        if not self.expires_at:
            return False
        return datetime.utcnow() > self.expires_at
    
    @property
    def salary_range(self):
        """Get formatted salary range"""
        if not self.salary_min and not self.salary_max:
            return None
        
        currency_symbol = {"USD": "$", "EUR": "€", "GBP": "£"}.get(self.salary_currency, self.salary_currency)
        
        if self.salary_min and self.salary_max:
            return f"{currency_symbol}{self.salary_min:,} - {currency_symbol}{self.salary_max:,}"
        elif self.salary_min:
            return f"{currency_symbol}{self.salary_min:,}+"
        else:
            return f"Up to {currency_symbol}{self.salary_max:,}"
    
    def generate_assessment_link(self):
        """Generate public assessment link"""
        if not self.company or not self.company.slug:
            return None
        return f"/apply/{self.company.slug}/{self.slug}"
    
    def to_dict(self, include_sensitive=False):
        """Convert to dictionary for API responses"""
        data = {
            "id": self.id,
            "title": self.title,
            "slug": self.slug,
            "description": self.description,
            "company_id": self.company_id,
            "department": self.department,
            "location": self.location,
            "remote_allowed": self.remote_allowed,
            "job_type": self.job_type.value,
            "experience_level": self.experience_level.value,
            "status": self.status.value,
            "is_featured": self.is_featured,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "required_skills": self.required_skills,
            "preferred_skills": self.preferred_skills,
            "qualifications": self.qualifications,
            "responsibilities": self.responsibilities,
            "benefits": self.benefits,
            "salary_range": self.salary_range,
            "assessment_enabled": self.assessment_enabled,
            "assessment_link": self.assessment_link,
            "views_count": self.views_count,
            "applications_count": self.applications_count,
            "is_active": self.is_active,
            "is_expired": self.is_expired,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
        
        if include_sensitive:
            data.update({
                "created_by": self.created_by,
                "salary_min": self.salary_min,
                "salary_max": self.salary_max,
                "salary_currency": self.salary_currency,
                "assessment_config": self.assessment_config,
            })
            
        return data