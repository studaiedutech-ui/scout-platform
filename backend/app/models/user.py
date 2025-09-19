"""
User Model for SaaS Platform
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Text, Enum as SQLEnum
from sqlalchemy.orm import relationship
import enum

from app.core.database import Base


class UserRole(enum.Enum):
    SUPER_ADMIN = "super_admin"      # Platform administrators
    COMPANY_ADMIN = "company_admin"   # Company administrators
    HR_MANAGER = "hr_manager"         # HR team members
    RECRUITER = "recruiter"           # Recruiters
    CANDIDATE = "candidate"           # Job candidates


class User(Base):
    """
    User model supporting multi-tenant architecture
    Users belong to companies (tenants) and have roles
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    
    # Profile Information
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    phone = Column(String(20))
    avatar_url = Column(String(500))
    bio = Column(Text)
    
    # Role and Permissions
    role = Column(SQLEnum(UserRole), nullable=False, default=UserRole.CANDIDATE)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=True, index=True)
    
    # Account Status
    is_active = Column(Boolean, default=True)
    is_email_verified = Column(Boolean, default=False)
    email_verified_at = Column(DateTime)
    
    # Security
    last_login = Column(DateTime)
    failed_login_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime)
    mfa_enabled = Column(Boolean, default=False)
    mfa_secret = Column(String(255))
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    company = relationship("Company", back_populates="users")
    created_jobs = relationship("Job", back_populates="created_by_user")
    candidate_applications = relationship("Candidate", back_populates="user")
    
    def __repr__(self):
        return f"<User {self.email}>"
    
    @property
    def full_name(self):
        """Get user's full name"""
        return f"{self.first_name} {self.last_name}".strip()
    
    @property
    def is_company_user(self):
        """Check if user belongs to a company"""
        return self.company_id is not None
    
    @property
    def is_admin(self):
        """Check if user has admin privileges"""
        return self.role in [UserRole.SUPER_ADMIN, UserRole.COMPANY_ADMIN]
    
    @property
    def is_locked(self):
        """Check if account is locked"""
        if not self.locked_until:
            return False
        return datetime.utcnow() < self.locked_until
    
    def to_dict(self, include_sensitive=False):
        """Convert to dictionary for API responses"""
        data = {
            "id": self.id,
            "email": self.email,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "full_name": self.full_name,
            "phone": self.phone,
            "avatar_url": self.avatar_url,
            "bio": self.bio,
            "role": self.role.value,
            "company_id": self.company_id,
            "is_active": self.is_active,
            "is_email_verified": self.is_email_verified,
            "email_verified_at": self.email_verified_at.isoformat() if self.email_verified_at else None,
            "last_login": self.last_login.isoformat() if self.last_login else None,
            "mfa_enabled": self.mfa_enabled,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
        
        if include_sensitive:
            data.update({
                "failed_login_attempts": self.failed_login_attempts,
                "locked_until": self.locked_until.isoformat() if self.locked_until else None,
            })
            
        return data