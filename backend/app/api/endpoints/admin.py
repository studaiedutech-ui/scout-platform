"""
Admin Dashboard API Endpoints
Platform management for super administrators
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from pydantic import BaseModel
from datetime import datetime, timedelta

from app.core.database import get_db
from app.core.security import get_current_active_user
from app.core.tenant import get_tenant_context, TenantContext
from app.models.user import User, UserRole
from app.models.company import Company
from app.models.subscription import Subscription, SubscriptionPlan
from app.models.job import Job
from app.models.candidate import Candidate
from app.models.assessment import Assessment
from app.models.audit import AuditLog, AuditAction

router = APIRouter()


# Pydantic Models
class PlatformStatsResponse(BaseModel):
    total_companies: int
    total_users: int
    total_jobs: int
    total_candidates: int
    total_assessments: int
    active_subscriptions: int
    trial_subscriptions: int
    monthly_revenue: float
    growth_metrics: Dict[str, float]


class CompanyDetailResponse(BaseModel):
    id: int
    name: str
    slug: str
    email: str
    website_url: Optional[str]
    industry: Optional[str]
    size: str
    is_active: bool
    onboarding_completed: bool
    user_count: int
    job_count: int
    candidate_count: int
    subscription_plan: Optional[str]
    subscription_status: Optional[str]
    created_at: str
    trial_ends_at: Optional[str]


class UserDetailResponse(BaseModel):
    id: int
    email: str
    first_name: str
    last_name: str
    full_name: str
    role: str
    company_id: Optional[int]
    company_name: Optional[str]
    is_active: bool
    is_email_verified: bool
    last_login: Optional[str]
    created_at: str


class RevenueMetrics(BaseModel):
    current_month: float
    previous_month: float
    growth_percentage: float
    total_revenue: float
    arr: float  # Annual Recurring Revenue


class UsageMetrics(BaseModel):
    period: str
    companies_created: int
    users_created: int
    jobs_created: int
    assessments_completed: int


def require_super_admin(current_user: User = Depends(get_current_active_user)):
    """
    Dependency to ensure only super admins can access admin endpoints
    """
    if current_user.role != UserRole.SUPER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super admin privileges required"
        )
    return current_user


@router.get("/stats", response_model=PlatformStatsResponse)
async def get_platform_stats(
    admin_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db)
):
    """
    Get overall platform statistics
    """
    # Basic counts
    total_companies = db.query(Company).count()
    total_users = db.query(User).count()
    total_jobs = db.query(Job).count()
    total_candidates = db.query(Candidate).count()
    total_assessments = db.query(Assessment).count()
    
    # Subscription stats
    active_subscriptions = db.query(Subscription).filter(
        Subscription.status == 'active'
    ).count()
    
    trial_subscriptions = db.query(Subscription).filter(
        Subscription.status == 'trial'
    ).count()
    
    # Revenue calculation (simplified - would need actual payment data)
    current_month_start = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    monthly_revenue = db.query(
        func.sum(SubscriptionPlan.monthly_price)
    ).join(Subscription).filter(
        Subscription.status.in_(['active', 'trial']),
        Subscription.created_at >= current_month_start
    ).scalar() or 0.0
    
    # Growth metrics (simplified)
    previous_month_start = (current_month_start - timedelta(days=32)).replace(day=1)
    previous_month_companies = db.query(Company).filter(
        Company.created_at >= previous_month_start,
        Company.created_at < current_month_start
    ).count()
    
    current_month_companies = db.query(Company).filter(
        Company.created_at >= current_month_start
    ).count()
    
    company_growth = (
        (current_month_companies - previous_month_companies) / max(previous_month_companies, 1) * 100
        if previous_month_companies > 0 else 0
    )
    
    return PlatformStatsResponse(
        total_companies=total_companies,
        total_users=total_users,
        total_jobs=total_jobs,
        total_candidates=total_candidates,
        total_assessments=total_assessments,
        active_subscriptions=active_subscriptions,
        trial_subscriptions=trial_subscriptions,
        monthly_revenue=float(monthly_revenue),
        growth_metrics={
            "company_growth_percentage": round(company_growth, 2),
            "user_growth_percentage": 0.0,  # Would calculate similarly
            "revenue_growth_percentage": 0.0  # Would calculate similarly
        }
    )


@router.get("/companies", response_model=List[CompanyDetailResponse])
async def get_companies(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    search: Optional[str] = Query(None),
    admin_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db)
):
    """
    Get list of companies with details
    """
    query = db.query(Company)
    
    # Apply search filter if provided
    if search:
        query = query.filter(
            Company.name.ilike(f"%{search}%") |
            Company.email.ilike(f"%{search}%")
        )
    
    companies = query.offset(skip).limit(limit).all()
    
    result = []
    for company in companies:
        # Get additional stats for each company
        user_count = db.query(User).filter(User.company_id == company.id).count()
        job_count = db.query(Job).filter(Job.company_id == company.id).count()
        candidate_count = db.query(Candidate).join(Job).filter(
            Job.company_id == company.id
        ).count()
        
        # Get subscription info
        subscription = db.query(Subscription).filter(
            Subscription.company_id == company.id
        ).first()
        
        result.append(CompanyDetailResponse(
            id=company.id,
            name=company.name,
            slug=company.slug,
            email=company.email,
            website_url=company.website_url,
            industry=company.industry,
            size=company.size.value if company.size else "unknown",
            is_active=company.is_active,
            onboarding_completed=company.onboarding_completed,
            user_count=user_count,
            job_count=job_count,
            candidate_count=candidate_count,
            subscription_plan=subscription.plan.name if subscription and subscription.plan else None,
            subscription_status=subscription.status.value if subscription else None,
            created_at=company.created_at.isoformat(),
            trial_ends_at=company.trial_ends_at.isoformat() if company.trial_ends_at else None
        ))
    
    return result


@router.get("/companies/{company_id}", response_model=CompanyDetailResponse)
async def get_company_details(
    company_id: int,
    admin_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db)
):
    """
    Get detailed information about a specific company
    """
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found"
        )
    
    # Get stats
    user_count = db.query(User).filter(User.company_id == company.id).count()
    job_count = db.query(Job).filter(Job.company_id == company.id).count()
    candidate_count = db.query(Candidate).join(Job).filter(
        Job.company_id == company.id
    ).count()
    
    subscription = db.query(Subscription).filter(
        Subscription.company_id == company.id
    ).first()
    
    return CompanyDetailResponse(
        id=company.id,
        name=company.name,
        slug=company.slug,
        email=company.email,
        website_url=company.website_url,
        industry=company.industry,
        size=company.size.value if company.size else "unknown",
        is_active=company.is_active,
        onboarding_completed=company.onboarding_completed,
        user_count=user_count,
        job_count=job_count,
        candidate_count=candidate_count,
        subscription_plan=subscription.plan.name if subscription and subscription.plan else None,
        subscription_status=subscription.status.value if subscription else None,
        created_at=company.created_at.isoformat(),
        trial_ends_at=company.trial_ends_at.isoformat() if company.trial_ends_at else None
    )


@router.post("/companies/{company_id}/suspend")
async def suspend_company(
    company_id: int,
    admin_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db)
):
    """
    Suspend a company account
    """
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found"
        )
    
    company.is_active = False
    
    # Also deactivate all users in the company
    db.query(User).filter(User.company_id == company_id).update(
        {"is_active": False}
    )
    
    # Log the action
    AuditLog.log_event(
        session=db,
        action=AuditAction.COMPANY_DELETED,
        user_id=admin_user.id,
        entity_type="company",
        entity_id=company_id,
        entity_name=company.name,
        description=f"Company suspended by admin {admin_user.email}"
    )
    
    db.commit()
    
    return {"message": f"Company {company.name} has been suspended"}


@router.post("/companies/{company_id}/activate")
async def activate_company(
    company_id: int,
    admin_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db)
):
    """
    Activate a suspended company account
    """
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found"
        )
    
    company.is_active = True
    
    # Log the action
    AuditLog.log_event(
        session=db,
        action=AuditAction.COMPANY_UPDATED,
        user_id=admin_user.id,
        entity_type="company",
        entity_id=company_id,
        entity_name=company.name,
        description=f"Company activated by admin {admin_user.email}"
    )
    
    db.commit()
    
    return {"message": f"Company {company.name} has been activated"}


@router.get("/users", response_model=List[UserDetailResponse])
async def get_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    search: Optional[str] = Query(None),
    company_id: Optional[int] = Query(None),
    admin_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db)
):
    """
    Get list of users with details
    """
    query = db.query(User).join(Company, User.company_id == Company.id, isouter=True)
    
    # Apply filters
    if search:
        query = query.filter(
            User.email.ilike(f"%{search}%") |
            User.first_name.ilike(f"%{search}%") |
            User.last_name.ilike(f"%{search}%")
        )
    
    if company_id:
        query = query.filter(User.company_id == company_id)
    
    users = query.offset(skip).limit(limit).all()
    
    result = []
    for user in users:
        result.append(UserDetailResponse(
            id=user.id,
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            full_name=user.full_name,
            role=user.role.value,
            company_id=user.company_id,
            company_name=user.company.name if user.company else None,
            is_active=user.is_active,
            is_email_verified=user.is_email_verified,
            last_login=user.last_login.isoformat() if user.last_login else None,
            created_at=user.created_at.isoformat()
        ))
    
    return result


@router.get("/revenue", response_model=RevenueMetrics)
async def get_revenue_metrics(
    admin_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db)
):
    """
    Get revenue metrics and trends
    """
    current_month_start = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    previous_month_start = (current_month_start - timedelta(days=32)).replace(day=1)
    
    # Current month revenue (from active subscriptions)
    current_month_revenue = db.query(
        func.sum(SubscriptionPlan.monthly_price)
    ).join(Subscription).filter(
        Subscription.status.in_(['active', 'trial']),
        Subscription.created_at >= current_month_start
    ).scalar() or 0.0
    
    # Previous month revenue
    previous_month_revenue = db.query(
        func.sum(SubscriptionPlan.monthly_price)
    ).join(Subscription).filter(
        Subscription.status.in_(['active', 'trial']),
        Subscription.created_at >= previous_month_start,
        Subscription.created_at < current_month_start
    ).scalar() or 0.0
    
    # Calculate growth
    growth_percentage = (
        (current_month_revenue - previous_month_revenue) / max(previous_month_revenue, 1) * 100
        if previous_month_revenue > 0 else 0
    )
    
    # Total revenue (simplified - would need payment history)
    total_revenue = db.query(
        func.sum(SubscriptionPlan.monthly_price)
    ).join(Subscription).filter(
        Subscription.status.in_(['active', 'trial'])
    ).scalar() or 0.0
    
    # ARR (Annual Recurring Revenue)
    arr = total_revenue * 12
    
    return RevenueMetrics(
        current_month=float(current_month_revenue),
        previous_month=float(previous_month_revenue),
        growth_percentage=round(growth_percentage, 2),
        total_revenue=float(total_revenue),
        arr=float(arr)
    )


@router.get("/usage", response_model=List[UsageMetrics])
async def get_usage_metrics(
    days: int = Query(30, ge=1, le=365),
    admin_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db)
):
    """
    Get platform usage metrics over time
    """
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    # Group by week for longer periods, by day for shorter periods
    group_by_week = days > 30
    
    if group_by_week:
        # Weekly metrics
        weeks = []
        current_date = start_date
        while current_date < end_date:
            week_end = current_date + timedelta(days=7)
            
            companies_created = db.query(Company).filter(
                Company.created_at >= current_date,
                Company.created_at < week_end
            ).count()
            
            users_created = db.query(User).filter(
                User.created_at >= current_date,
                User.created_at < week_end
            ).count()
            
            jobs_created = db.query(Job).filter(
                Job.created_at >= current_date,
                Job.created_at < week_end
            ).count()
            
            assessments_completed = db.query(Assessment).filter(
                Assessment.completed_at >= current_date,
                Assessment.completed_at < week_end
            ).count()
            
            weeks.append(UsageMetrics(
                period=f"Week of {current_date.strftime('%Y-%m-%d')}",
                companies_created=companies_created,
                users_created=users_created,
                jobs_created=jobs_created,
                assessments_completed=assessments_completed
            ))
            
            current_date = week_end
        
        return weeks
    else:
        # Daily metrics
        days_list = []
        current_date = start_date
        while current_date < end_date:
            day_end = current_date + timedelta(days=1)
            
            companies_created = db.query(Company).filter(
                Company.created_at >= current_date,
                Company.created_at < day_end
            ).count()
            
            users_created = db.query(User).filter(
                User.created_at >= current_date,
                User.created_at < day_end
            ).count()
            
            jobs_created = db.query(Job).filter(
                Job.created_at >= current_date,
                Job.created_at < day_end
            ).count()
            
            assessments_completed = db.query(Assessment).filter(
                Assessment.completed_at >= current_date,
                Assessment.completed_at < day_end
            ).count()
            
            days_list.append(UsageMetrics(
                period=current_date.strftime('%Y-%m-%d'),
                companies_created=companies_created,
                users_created=users_created,
                jobs_created=jobs_created,
                assessments_completed=assessments_completed
            ))
            
            current_date = day_end
        
        return days_list


@router.get("/audit-logs")
async def get_audit_logs(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    action: Optional[str] = Query(None),
    user_id: Optional[int] = Query(None),
    company_id: Optional[int] = Query(None),
    admin_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db)
):
    """
    Get audit logs for platform monitoring
    """
    query = db.query(AuditLog).order_by(desc(AuditLog.created_at))
    
    # Apply filters
    if action:
        try:
            audit_action = AuditAction(action)
            query = query.filter(AuditLog.action == audit_action)
        except ValueError:
            pass  # Invalid action, ignore filter
    
    if user_id:
        query = query.filter(AuditLog.user_id == user_id)
    
    if company_id:
        query = query.filter(AuditLog.company_id == company_id)
    
    logs = query.offset(skip).limit(limit).all()
    
    return [log.to_dict() for log in logs]