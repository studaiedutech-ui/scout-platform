"""
Subscription Management API Endpoints
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.core.database import get_db
from app.core.security import get_current_active_user
from app.models.user import User
from app.models.subscription import Subscription, SubscriptionPlan, SubscriptionPlanType, SubscriptionStatus, BillingInterval

router = APIRouter()


# Pydantic Models
class SubscriptionPlanResponse(BaseModel):
    id: int
    name: str
    plan_type: str
    description: Optional[str]
    monthly_price: float
    yearly_price: float
    currency: str
    max_jobs: int
    max_candidates: int
    max_assessments: int
    max_users: int
    max_storage_gb: int
    ai_assessment_enabled: bool
    analytics_enabled: bool
    custom_branding: bool
    api_access: bool
    priority_support: bool
    trial_days: int
    is_active: bool

    class Config:
        from_attributes = True


class SubscriptionResponse(BaseModel):
    id: int
    company_id: int
    plan: SubscriptionPlanResponse
    status: str
    billing_interval: str
    current_period_start: str
    current_period_end: str
    trial_start: Optional[str]
    trial_end: Optional[str]
    cancelled_at: Optional[str]
    ends_at: Optional[str]
    last_payment_at: Optional[str]
    next_billing_date: Optional[str]
    current_jobs: int
    current_candidates: int
    current_assessments: int
    current_users: int
    current_storage_gb: float
    days_until_renewal: int
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class SubscriptionCreateRequest(BaseModel):
    plan_id: int
    billing_interval: BillingInterval = BillingInterval.MONTHLY


class SubscriptionUpdateRequest(BaseModel):
    plan_id: Optional[int] = None
    billing_interval: Optional[BillingInterval] = None


@router.get("/plans", response_model=List[SubscriptionPlanResponse])
async def get_subscription_plans(
    db: Session = Depends(get_db)
):
    """
    Get all available subscription plans
    """
    plans = db.query(SubscriptionPlan).filter(SubscriptionPlan.is_active == True).all()
    return [SubscriptionPlanResponse.from_orm(plan) for plan in plans]


@router.get("/plans/{plan_id}", response_model=SubscriptionPlanResponse)
async def get_subscription_plan(
    plan_id: int,
    db: Session = Depends(get_db)
):
    """
    Get a specific subscription plan
    """
    plan = db.query(SubscriptionPlan).filter(
        SubscriptionPlan.id == plan_id,
        SubscriptionPlan.is_active == True
    ).first()
    
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription plan not found"
        )
    
    return SubscriptionPlanResponse.from_orm(plan)


@router.get("/current", response_model=SubscriptionResponse)
async def get_current_subscription(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get the current user's company subscription
    """
    if not current_user.company_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not associated with a company"
        )
    
    subscription = db.query(Subscription).filter(
        Subscription.company_id == current_user.company_id
    ).first()
    
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No subscription found for company"
        )
    
    return SubscriptionResponse.from_orm(subscription)


@router.post("/subscribe", response_model=SubscriptionResponse)
async def create_subscription(
    request: SubscriptionCreateRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Create a new subscription for the company
    """
    if not current_user.company_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not associated with a company"
        )
    
    # Check if company already has a subscription
    existing_subscription = db.query(Subscription).filter(
        Subscription.company_id == current_user.company_id
    ).first()
    
    if existing_subscription:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Company already has an active subscription"
        )
    
    # Validate the plan exists
    plan = db.query(SubscriptionPlan).filter(
        SubscriptionPlan.id == request.plan_id,
        SubscriptionPlan.is_active == True
    ).first()
    
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription plan not found"
        )
    
    # Create subscription logic here
    # This would integrate with payment processors like Stripe
    # For now, we'll create a basic subscription
    
    from datetime import datetime, timedelta
    
    now = datetime.utcnow()
    trial_end = now + timedelta(days=plan.trial_days)
    
    subscription = Subscription(
        company_id=current_user.company_id,
        plan_id=plan.id,
        status=SubscriptionStatus.TRIAL if plan.trial_days > 0 else SubscriptionStatus.ACTIVE,
        billing_interval=request.billing_interval,
        current_period_start=now,
        current_period_end=trial_end,
        trial_start=now if plan.trial_days > 0 else None,
        trial_end=trial_end if plan.trial_days > 0 else None,
        next_billing_date=trial_end
    )
    
    db.add(subscription)
    db.commit()
    db.refresh(subscription)
    
    return SubscriptionResponse.from_orm(subscription)


@router.put("/update", response_model=SubscriptionResponse)
async def update_subscription(
    request: SubscriptionUpdateRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Update the company's subscription
    """
    if not current_user.company_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not associated with a company"
        )
    
    subscription = db.query(Subscription).filter(
        Subscription.company_id == current_user.company_id
    ).first()
    
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No subscription found for company"
        )
    
    # Update plan if requested
    if request.plan_id:
        plan = db.query(SubscriptionPlan).filter(
            SubscriptionPlan.id == request.plan_id,
            SubscriptionPlan.is_active == True
        ).first()
        
        if not plan:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Subscription plan not found"
            )
        
        subscription.plan_id = request.plan_id
    
    # Update billing interval if requested
    if request.billing_interval:
        subscription.billing_interval = request.billing_interval
    
    subscription.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(subscription)
    
    return SubscriptionResponse.from_orm(subscription)


@router.post("/cancel")
async def cancel_subscription(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Cancel the company's subscription
    """
    if not current_user.company_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not associated with a company"
        )
    
    subscription = db.query(Subscription).filter(
        Subscription.company_id == current_user.company_id
    ).first()
    
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No subscription found for company"
        )
    
    if subscription.status == SubscriptionStatus.CANCELLED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Subscription is already cancelled"
        )
    
    from datetime import datetime
    
    subscription.status = SubscriptionStatus.CANCELLED
    subscription.cancelled_at = datetime.utcnow()
    subscription.ends_at = subscription.current_period_end
    
    db.commit()
    
    return {"message": "Subscription cancelled successfully"}


@router.get("/usage")
async def get_subscription_usage(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get current subscription usage statistics
    """
    if not current_user.company_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not associated with a company"
        )
    
    subscription = db.query(Subscription).filter(
        Subscription.company_id == current_user.company_id
    ).first()
    
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No subscription found for company"
        )
    
    # Calculate actual usage
    from app.models.job import Job
    from app.models.candidate import Candidate
    from app.models.assessment import Assessment
    from app.models.user import User as UserModel
    
    actual_jobs = db.query(Job).filter(Job.company_id == current_user.company_id).count()
    actual_candidates = db.query(Candidate).join(Job).filter(Job.company_id == current_user.company_id).count()
    actual_assessments = db.query(Assessment).join(Job).filter(Job.company_id == current_user.company_id).count()
    actual_users = db.query(UserModel).filter(UserModel.company_id == current_user.company_id).count()
    
    usage = {
        "jobs": {
            "current": actual_jobs,
            "limit": subscription.plan.max_jobs,
            "unlimited": subscription.plan.max_jobs == 0
        },
        "candidates": {
            "current": actual_candidates,
            "limit": subscription.plan.max_candidates,
            "unlimited": subscription.plan.max_candidates == 0
        },
        "assessments": {
            "current": actual_assessments,
            "limit": subscription.plan.max_assessments,
            "unlimited": subscription.plan.max_assessments == 0
        },
        "users": {
            "current": actual_users,
            "limit": subscription.plan.max_users,
            "unlimited": subscription.plan.max_users == 0
        },
        "storage": {
            "current": float(subscription.current_storage_gb),
            "limit": subscription.plan.max_storage_gb,
            "unlimited": subscription.plan.max_storage_gb == 0
        }
    }
    
    return usage