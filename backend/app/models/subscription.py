"""
Subscription and Billing Models for SaaS Platform
"""

from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Numeric, Text, Enum as SQLEnum
from sqlalchemy.orm import relationship
import enum

from app.core.database import Base


class SubscriptionPlanType(enum.Enum):
    FREE = "free"
    STARTER = "starter"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"


class SubscriptionStatus(enum.Enum):
    ACTIVE = "active"
    TRIAL = "trial"
    PAST_DUE = "past_due"
    CANCELLED = "cancelled"
    UNPAID = "unpaid"


class BillingInterval(enum.Enum):
    MONTHLY = "monthly"
    YEARLY = "yearly"


class SubscriptionPlan(Base):
    """
    Subscription plans for the SaaS platform
    Defines features and pricing for different tiers
    """
    __tablename__ = "subscription_plans"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    plan_type = Column(SQLEnum(SubscriptionPlanType), nullable=False, unique=True)
    description = Column(Text)
    
    # Pricing
    monthly_price = Column(Numeric(10, 2), default=0)
    yearly_price = Column(Numeric(10, 2), default=0)
    currency = Column(String(3), default="USD")
    
    # Feature Limits
    max_jobs = Column(Integer, default=0)  # 0 = unlimited
    max_candidates = Column(Integer, default=0)  # 0 = unlimited
    max_assessments = Column(Integer, default=0)  # 0 = unlimited
    max_users = Column(Integer, default=1)
    max_storage_gb = Column(Integer, default=1)
    
    # Features
    ai_assessment_enabled = Column(Boolean, default=False)
    analytics_enabled = Column(Boolean, default=False)
    custom_branding = Column(Boolean, default=False)
    api_access = Column(Boolean, default=False)
    priority_support = Column(Boolean, default=False)
    
    # Metadata
    is_active = Column(Boolean, default=True)
    trial_days = Column(Integer, default=14)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    subscriptions = relationship("Subscription", back_populates="plan")
    
    def __repr__(self):
        return f"<SubscriptionPlan {self.name}>"
    
    def get_price(self, billing_interval: BillingInterval):
        """Get price for specific billing interval"""
        if billing_interval == BillingInterval.MONTHLY:
            return self.monthly_price
        return self.yearly_price
    
    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "plan_type": self.plan_type.value,
            "description": self.description,
            "monthly_price": float(self.monthly_price),
            "yearly_price": float(self.yearly_price),
            "currency": self.currency,
            "max_jobs": self.max_jobs,
            "max_candidates": self.max_candidates,
            "max_assessments": self.max_assessments,
            "max_users": self.max_users,
            "max_storage_gb": self.max_storage_gb,
            "ai_assessment_enabled": self.ai_assessment_enabled,
            "analytics_enabled": self.analytics_enabled,
            "custom_branding": self.custom_branding,
            "api_access": self.api_access,
            "priority_support": self.priority_support,
            "trial_days": self.trial_days,
            "is_active": self.is_active,
        }


class Subscription(Base):
    """
    Company subscriptions linking companies to subscription plans
    """
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    plan_id = Column(Integer, ForeignKey("subscription_plans.id"), nullable=False)
    
    # Subscription Details
    status = Column(SQLEnum(SubscriptionStatus), default=SubscriptionStatus.TRIAL)
    billing_interval = Column(SQLEnum(BillingInterval), default=BillingInterval.MONTHLY)
    
    # Billing
    current_period_start = Column(DateTime, nullable=False)
    current_period_end = Column(DateTime, nullable=False)
    trial_start = Column(DateTime)
    trial_end = Column(DateTime)
    cancelled_at = Column(DateTime)
    ends_at = Column(DateTime)
    
    # Payment
    stripe_subscription_id = Column(String(255), unique=True)
    stripe_customer_id = Column(String(255))
    last_payment_at = Column(DateTime)
    next_billing_date = Column(DateTime)
    
    # Usage Tracking
    current_jobs = Column(Integer, default=0)
    current_candidates = Column(Integer, default=0)
    current_assessments = Column(Integer, default=0)
    current_users = Column(Integer, default=0)
    current_storage_gb = Column(Numeric(10, 2), default=0)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    company = relationship("Company", back_populates="subscription", foreign_keys=[company_id])
    plan = relationship("SubscriptionPlan", back_populates="subscriptions")
    
    def __repr__(self):
        return f"<Subscription {self.company_id}:{self.plan.name}>"
    
    @property
    def is_active(self):
        """Check if subscription is active"""
        return self.status == SubscriptionStatus.ACTIVE
    
    @property
    def is_trial(self):
        """Check if subscription is in trial"""
        return self.status == SubscriptionStatus.TRIAL
    
    @property
    def is_expired(self):
        """Check if subscription has expired"""
        if self.ends_at:
            return datetime.utcnow() > self.ends_at
        return datetime.utcnow() > self.current_period_end
    
    @property
    def days_until_renewal(self):
        """Get days until next renewal"""
        if self.next_billing_date:
            delta = self.next_billing_date - datetime.utcnow()
            return max(0, delta.days)
        return 0
    
    def can_use_feature(self, feature: str):
        """Check if subscription allows specific feature"""
        return getattr(self.plan, f"{feature}_enabled", False)
    
    def is_within_limits(self, resource: str, current_count: int = None):
        """Check if subscription is within resource limits"""
        if current_count is None:
            current_count = getattr(self, f"current_{resource}", 0)
            
        limit = getattr(self.plan, f"max_{resource}", 0)
        return limit == 0 or current_count < limit  # 0 means unlimited
    
    def to_dict(self):
        return {
            "id": self.id,
            "company_id": self.company_id,
            "plan": self.plan.to_dict() if self.plan else None,
            "status": self.status.value,
            "billing_interval": self.billing_interval.value,
            "current_period_start": self.current_period_start.isoformat(),
            "current_period_end": self.current_period_end.isoformat(),
            "trial_start": self.trial_start.isoformat() if self.trial_start else None,
            "trial_end": self.trial_end.isoformat() if self.trial_end else None,
            "cancelled_at": self.cancelled_at.isoformat() if self.cancelled_at else None,
            "ends_at": self.ends_at.isoformat() if self.ends_at else None,
            "last_payment_at": self.last_payment_at.isoformat() if self.last_payment_at else None,
            "next_billing_date": self.next_billing_date.isoformat() if self.next_billing_date else None,
            "current_jobs": self.current_jobs,
            "current_candidates": self.current_candidates,
            "current_assessments": self.current_assessments,
            "current_users": self.current_users,
            "current_storage_gb": float(self.current_storage_gb),
            "days_until_renewal": self.days_until_renewal,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }