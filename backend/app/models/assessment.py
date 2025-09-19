"""
Assessment Models for AI-driven Evaluation
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Text, Enum as SQLEnum, JSON, Float
from sqlalchemy.orm import relationship
import enum

from app.core.database import Base


class AssessmentType(enum.Enum):
    SKILLS = "skills"
    PERSONALITY = "personality"
    COGNITIVE = "cognitive"
    CULTURAL_FIT = "cultural_fit"
    TECHNICAL = "technical"
    CUSTOM = "custom"


class QuestionType(enum.Enum):
    MULTIPLE_CHOICE = "multiple_choice"
    SINGLE_CHOICE = "single_choice"
    TEXT = "text"
    CODE = "code"
    VIDEO = "video"
    FILE_UPLOAD = "file_upload"


class AssessmentStatus(enum.Enum):
    CREATED = "created"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class Assessment(Base):
    """
    Assessment session for candidates
    """
    __tablename__ = "assessments"

    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id"), nullable=False, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False, index=True)
    
    # Assessment Configuration
    assessment_type = Column(SQLEnum(AssessmentType), default=AssessmentType.SKILLS)
    session_id = Column(String(255), unique=True, nullable=False, index=True)
    
    # Status and Timing
    status = Column(SQLEnum(AssessmentStatus), default=AssessmentStatus.CREATED, index=True)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    expires_at = Column(DateTime)
    duration_minutes = Column(Integer, default=60)
    
    # Scoring
    total_score = Column(Float)
    max_score = Column(Float)
    percentage_score = Column(Float)
    
    # AI Analysis
    ai_analysis = Column(JSON)  # AI-generated analysis
    skills_assessment = Column(JSON)  # Skills breakdown
    personality_insights = Column(JSON)  # Personality analysis
    strengths = Column(JSON)  # List of strengths
    areas_for_improvement = Column(JSON)  # Areas needing improvement
    
    # Proctoring and Security
    browser_lockdown = Column(Boolean, default=True)
    webcam_required = Column(Boolean, default=False)
    screen_recording = Column(Boolean, default=False)
    tab_switches = Column(Integer, default=0)
    suspicious_activities = Column(JSON)  # Log of suspicious activities
    
    # Metadata
    ip_address = Column(String(45))
    user_agent = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    candidate = relationship("Candidate", back_populates="assessments")
    job = relationship("Job")
    questions = relationship("AssessmentQuestion", back_populates="assessment")
    responses = relationship("AssessmentResponse", back_populates="assessment")
    
    def __repr__(self):
        return f"<Assessment {self.session_id}>"
    
    @property
    def is_active(self):
        """Check if assessment is currently active"""
        if self.status != AssessmentStatus.IN_PROGRESS:
            return False
        if self.expires_at and datetime.utcnow() > self.expires_at:
            return False
        return True
    
    @property
    def is_expired(self):
        """Check if assessment has expired"""
        if not self.expires_at:
            return False
        return datetime.utcnow() > self.expires_at
    
    @property
    def time_remaining_minutes(self):
        """Get remaining time in minutes"""
        if not self.expires_at:
            return None
        delta = self.expires_at - datetime.utcnow()
        return max(0, int(delta.total_seconds() / 60))
    
    @property
    def completion_rate(self):
        """Get assessment completion rate"""
        total_questions = len(self.questions)
        answered_questions = len([r for r in self.responses if r.response_data])
        return (answered_questions / total_questions * 100) if total_questions > 0 else 0
    
    def to_dict(self, include_sensitive=False):
        """Convert to dictionary for API responses"""
        data = {
            "id": self.id,
            "candidate_id": self.candidate_id,
            "job_id": self.job_id,
            "assessment_type": self.assessment_type.value,
            "session_id": self.session_id,
            "status": self.status.value,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "duration_minutes": self.duration_minutes,
            "total_score": self.total_score,
            "max_score": self.max_score,
            "percentage_score": self.percentage_score,
            "completion_rate": self.completion_rate,
            "time_remaining_minutes": self.time_remaining_minutes,
            "is_active": self.is_active,
            "is_expired": self.is_expired,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
        
        if include_sensitive:
            data.update({
                "ai_analysis": self.ai_analysis,
                "skills_assessment": self.skills_assessment,
                "personality_insights": self.personality_insights,
                "strengths": self.strengths,
                "areas_for_improvement": self.areas_for_improvement,
                "tab_switches": self.tab_switches,
                "suspicious_activities": self.suspicious_activities,
                "ip_address": self.ip_address,
                "user_agent": self.user_agent,
            })
            
        return data


class AssessmentQuestion(Base):
    """
    Questions within an assessment
    """
    __tablename__ = "assessment_questions"

    id = Column(Integer, primary_key=True, index=True)
    assessment_id = Column(Integer, ForeignKey("assessments.id"), nullable=False, index=True)
    
    # Question Details
    question_text = Column(Text, nullable=False)
    question_type = Column(SQLEnum(QuestionType), nullable=False)
    order_index = Column(Integer, nullable=False)
    
    # Configuration
    options = Column(JSON)  # For multiple choice questions
    correct_answer = Column(JSON)  # Correct answer(s)
    max_score = Column(Float, default=1.0)
    time_limit_seconds = Column(Integer)
    
    # AI-Generated Metadata
    difficulty = Column(String(20))  # easy, medium, hard
    skills_assessed = Column(JSON)  # List of skills this question assesses
    ai_generated = Column(Boolean, default=False)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    assessment = relationship("Assessment", back_populates="questions")
    responses = relationship("AssessmentResponse", back_populates="question")
    
    def __repr__(self):
        return f"<AssessmentQuestion {self.id}>"
    
    def to_dict(self, include_answers=False):
        """Convert to dictionary for API responses"""
        data = {
            "id": self.id,
            "assessment_id": self.assessment_id,
            "question_text": self.question_text,
            "question_type": self.question_type.value,
            "order_index": self.order_index,
            "options": self.options,
            "max_score": self.max_score,
            "time_limit_seconds": self.time_limit_seconds,
            "difficulty": self.difficulty,
            "skills_assessed": self.skills_assessed,
            "ai_generated": self.ai_generated,
            "created_at": self.created_at.isoformat(),
        }
        
        if include_answers:
            data["correct_answer"] = self.correct_answer
            
        return data


class AssessmentResponse(Base):
    """
    Candidate responses to assessment questions
    """
    __tablename__ = "assessment_responses"

    id = Column(Integer, primary_key=True, index=True)
    assessment_id = Column(Integer, ForeignKey("assessments.id"), nullable=False, index=True)
    question_id = Column(Integer, ForeignKey("assessment_questions.id"), nullable=False, index=True)
    
    # Response Data
    response_data = Column(JSON)  # The actual response
    score = Column(Float)
    is_correct = Column(Boolean)
    
    # Timing
    time_taken_seconds = Column(Integer)
    started_at = Column(DateTime)
    submitted_at = Column(DateTime, default=datetime.utcnow)
    
    # AI Analysis
    ai_feedback = Column(Text)  # AI-generated feedback
    confidence_score = Column(Float)  # AI confidence in the response
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    assessment = relationship("Assessment", back_populates="responses")
    question = relationship("AssessmentQuestion", back_populates="responses")
    
    def __repr__(self):
        return f"<AssessmentResponse {self.assessment_id}:{self.question_id}>"
    
    def to_dict(self, include_ai_analysis=False):
        """Convert to dictionary for API responses"""
        data = {
            "id": self.id,
            "assessment_id": self.assessment_id,
            "question_id": self.question_id,
            "response_data": self.response_data,
            "score": self.score,
            "is_correct": self.is_correct,
            "time_taken_seconds": self.time_taken_seconds,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "submitted_at": self.submitted_at.isoformat(),
            "created_at": self.created_at.isoformat(),
        }
        
        if include_ai_analysis:
            data.update({
                "ai_feedback": self.ai_feedback,
                "confidence_score": self.confidence_score,
            })
            
        return data