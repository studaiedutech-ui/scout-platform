"""
Candidate Model for Recruitment Platform
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Text, Enum as SQLEnum, JSON, Float
from sqlalchemy.orm import relationship
import enum

from app.core.database import Base


class CandidateStatus(enum.Enum):
    APPLIED = "applied"
    SCREENING = "screening"
    ASSESSMENT = "assessment"
    INTERVIEW = "interview"
    OFFER = "offer"
    HIRED = "hired"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"


class CandidateSource(enum.Enum):
    DIRECT = "direct"
    LINKEDIN = "linkedin"
    INDEED = "indeed"
    GLASSDOOR = "glassdoor"
    REFERRAL = "referral"
    COMPANY_WEBSITE = "company_website"
    OTHER = "other"


class Candidate(Base):
    """
    Candidate application model
    Links job seekers to specific job applications
    """
    __tablename__ = "candidates"

    id = Column(Integer, primary_key=True, index=True)
    
    # User Association (for registered candidates)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    
    # Job Association
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False, index=True)
    
    # Basic Information (for non-registered candidates)
    email = Column(String(255), nullable=False, index=True)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    phone = Column(String(20))
    
    # Professional Information
    current_position = Column(String(255))
    current_company = Column(String(255))
    years_of_experience = Column(Integer)
    expected_salary = Column(Integer)
    available_from = Column(DateTime)
    
    # Location
    country = Column(String(100))
    city = Column(String(100))
    willing_to_relocate = Column(Boolean, default=False)
    
    # Application Details
    status = Column(SQLEnum(CandidateStatus), default=CandidateStatus.APPLIED, index=True)
    source = Column(SQLEnum(CandidateSource), default=CandidateSource.DIRECT)
    cover_letter = Column(Text)
    resume_url = Column(String(500))
    portfolio_url = Column(String(500))
    linkedin_url = Column(String(500))
    
    # Assessment Results
    assessment_score = Column(Float)
    assessment_completed_at = Column(DateTime)
    assessment_data = Column(JSON)  # Detailed assessment results
    
    # AI Analysis
    ai_summary = Column(Text)  # AI-generated candidate summary
    skills_match_score = Column(Float)  # AI-calculated skills match
    cultural_fit_score = Column(Float)  # AI-calculated cultural fit
    
    # Screening and Notes
    recruiter_notes = Column(Text)
    interview_notes = Column(Text)
    rejection_reason = Column(Text)
    
    # Metadata
    applied_at = Column(DateTime, default=datetime.utcnow, index=True)
    last_activity_at = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="candidate_applications")
    job = relationship("Job", back_populates="candidates")
    assessments = relationship("Assessment", back_populates="candidate")
    
    def __repr__(self):
        return f"<Candidate {self.first_name} {self.last_name}>"
    
    @property
    def full_name(self):
        """Get candidate's full name"""
        return f"{self.first_name} {self.last_name}".strip()
    
    @property
    def is_registered_user(self):
        """Check if candidate is a registered platform user"""
        return self.user_id is not None
    
    @property
    def overall_score(self):
        """Calculate overall candidate score"""
        scores = []
        if self.assessment_score is not None:
            scores.append(self.assessment_score)
        if self.skills_match_score is not None:
            scores.append(self.skills_match_score)
        if self.cultural_fit_score is not None:
            scores.append(self.cultural_fit_score)
        
        return sum(scores) / len(scores) if scores else None
    
    @property
    def has_completed_assessment(self):
        """Check if candidate has completed assessment"""
        return self.assessment_completed_at is not None
    
    def to_dict(self, include_sensitive=False):
        """Convert to dictionary for API responses"""
        data = {
            "id": self.id,
            "job_id": self.job_id,
            "email": self.email,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "full_name": self.full_name,
            "phone": self.phone,
            "current_position": self.current_position,
            "current_company": self.current_company,
            "years_of_experience": self.years_of_experience,
            "expected_salary": self.expected_salary,
            "available_from": self.available_from.isoformat() if self.available_from else None,
            "country": self.country,
            "city": self.city,
            "willing_to_relocate": self.willing_to_relocate,
            "status": self.status.value,
            "source": self.source.value,
            "resume_url": self.resume_url,
            "portfolio_url": self.portfolio_url,
            "linkedin_url": self.linkedin_url,
            "assessment_score": self.assessment_score,
            "assessment_completed_at": self.assessment_completed_at.isoformat() if self.assessment_completed_at else None,
            "skills_match_score": self.skills_match_score,
            "cultural_fit_score": self.cultural_fit_score,
            "overall_score": self.overall_score,
            "has_completed_assessment": self.has_completed_assessment,
            "is_registered_user": self.is_registered_user,
            "applied_at": self.applied_at.isoformat(),
            "last_activity_at": self.last_activity_at.isoformat(),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
        
        if include_sensitive:
            data.update({
                "user_id": self.user_id,
                "cover_letter": self.cover_letter,
                "assessment_data": self.assessment_data,
                "ai_summary": self.ai_summary,
                "recruiter_notes": self.recruiter_notes,
                "interview_notes": self.interview_notes,
                "rejection_reason": self.rejection_reason,
            })
            
        return data