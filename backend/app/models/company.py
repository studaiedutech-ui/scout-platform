"""
Company Model for Multi-tenant SaaS Platform
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, Enum as SQLEnum
from sqlalchemy.orm import relationship
import enum

from app.core.database import Base


class CompanySize(enum.Enum):
    STARTUP = "startup"
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"
    ENTERPRISE = "enterprise"


class Company(Base):
    """
    Company model for multi-tenant architecture
    Each company is a separate tenant in the SaaS platform
    """
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    email = Column(String(255), nullable=False)
    website_url = Column(String(500))
    industry = Column(String(100))
    size = Column(SQLEnum(CompanySize), default=CompanySize.STARTUP)
    description = Column(Text)
    logo_url = Column(String(500))
    
    # Location
    country = Column(String(100))
    city = Column(String(100))
    address = Column(Text)
    
    # SaaS Configuration
    subscription_id = Column(Integer, index=True)  # FK to subscription
    is_active = Column(Boolean, default=True)
    trial_ends_at = Column(DateTime)
    onboarding_completed = Column(Boolean, default=False)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    users = relationship("User", back_populates="company")
    jobs = relationship("Job", back_populates="company")
    subscription = relationship("Subscription", back_populates="company", uselist=False, foreign_keys="[Subscription.company_id]")
    
    def __repr__(self):
        return f"<Company {self.name}>"
    
    @property
    def is_trial_expired(self):
        """Check if trial period has expired"""
        if not self.trial_ends_at:
            return False
        return datetime.utcnow() > self.trial_ends_at
    
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            "id": self.id,
            "name": self.name,
            "slug": self.slug,
            "email": self.email,
            "website_url": self.website_url,
            "industry": self.industry,
            "size": self.size.value if self.size else None,
            "description": self.description,
            "logo_url": self.logo_url,
            "country": self.country,
            "city": self.city,
            "is_active": self.is_active,
            "trial_ends_at": self.trial_ends_at.isoformat() if self.trial_ends_at else None,
            "onboarding_completed": self.onboarding_completed,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }