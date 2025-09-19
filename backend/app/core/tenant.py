"""
Multi-tenant Middleware for SaaS Platform
Ensures proper tenant isolation and data security
"""

from typing import Optional
from fastapi import HTTPException, status, Request
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session
import logging

from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.user import User
from app.models.company import Company

logger = logging.getLogger(__name__)


class TenantContext:
    """
    Tenant context for the current request
    """
    def __init__(self):
        self.company_id: Optional[int] = None
        self.user_id: Optional[int] = None
        self.user: Optional[User] = None
        self.company: Optional[Company] = None
        self.is_super_admin: bool = False


# Global tenant context for the current request
tenant_context = TenantContext()


def get_tenant_context() -> TenantContext:
    """
    Get the current tenant context
    """
    return tenant_context


async def set_tenant_context(request: Request, db: Session):
    """
    Set the tenant context based on the current user
    """
    global tenant_context
    tenant_context = TenantContext()
    
    # Extract token from Authorization header
    authorization = request.headers.get("Authorization")
    if not authorization:
        return
    
    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            return
            
        # Decode token
        payload = decode_access_token(token)
        if not payload:
            return
            
        user_id = payload.get("sub")
        if not user_id:
            return
            
        # Get user from database
        user = db.query(User).filter(User.id == int(user_id)).first()
        if not user:
            return
            
        # Set tenant context
        tenant_context.user_id = user.id
        tenant_context.user = user
        tenant_context.company_id = user.company_id
        tenant_context.is_super_admin = user.role.value == "super_admin" if user.role else False
        
        # Get company if user belongs to one
        if user.company_id:
            company = db.query(Company).filter(Company.id == user.company_id).first()
            tenant_context.company = company
            
        logger.debug(f"Tenant context set: user_id={user.id}, company_id={user.company_id}")
        
    except Exception as e:
        logger.warning(f"Failed to set tenant context: {str(e)}")
        # Reset context on error
        tenant_context = TenantContext()


def ensure_tenant_access(company_id: int):
    """
    Ensure the current user has access to the specified company/tenant
    """
    if tenant_context.is_super_admin:
        return  # Super admins can access all tenants
        
    if not tenant_context.company_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is not associated with any company"
        )
        
    if tenant_context.company_id != company_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: insufficient permissions for this tenant"
        )


def filter_by_tenant(query, model_class, company_field="company_id"):
    """
    Filter a SQLAlchemy query by the current tenant
    """
    if tenant_context.is_super_admin:
        return query  # Super admins see all data
        
    if not tenant_context.company_id:
        # Return empty query if no tenant context
        return query.filter(False)
        
    # Filter by company_id
    company_filter = getattr(model_class, company_field) == tenant_context.company_id
    return query.filter(company_filter)


def validate_tenant_resource_access(resource_company_id: Optional[int]):
    """
    Validate that the current user can access a resource belonging to a specific company
    """
    if resource_company_id is None:
        return  # Public resource or no company association
        
    ensure_tenant_access(resource_company_id)


class TenantMiddleware:
    """
    Middleware to set tenant context for each request
    """
    
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            request = Request(scope, receive)
            
            # Set tenant context for API requests
            if request.url.path.startswith("/api/"):
                try:
                    # Get database session
                    db_gen = get_db()
                    db = next(db_gen)
                    
                    try:
                        await set_tenant_context(request, db)
                    finally:
                        db.close()
                        
                except Exception as e:
                    logger.error(f"Error in tenant middleware: {str(e)}")
        
        await self.app(scope, receive, send)


# Dependency to ensure user has company access
def get_current_tenant_user():
    """
    Get the current user and ensure they belong to a company
    """
    if not tenant_context.user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
        
    if not tenant_context.company_id and not tenant_context.is_super_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is not associated with any company"
        )
        
    return tenant_context.user


def get_current_company():
    """
    Get the current user's company
    """
    if not tenant_context.company:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is not associated with any company"
        )
        
    return tenant_context.company


def check_subscription_limits(resource_type: str, current_count: Optional[int] = None):
    """
    Check if the current tenant is within subscription limits for a resource
    """
    if tenant_context.is_super_admin:
        return  # Super admins bypass limits
        
    if not tenant_context.company:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Company information required"
        )
    
    # Get subscription from company
    subscription = tenant_context.company.subscription
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="No active subscription found"
        )
    
    # Check if subscription is active
    if not subscription.is_active:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Subscription is not active"
        )
    
    # Check specific resource limits
    if not subscription.is_within_limits(resource_type, current_count):
        limit = getattr(subscription.plan, f"max_{resource_type}", 0)
        limit_text = "unlimited" if limit == 0 else str(limit)
        
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=f"Subscription limit exceeded for {resource_type}. Current limit: {limit_text}"
        )


def check_feature_access(feature: str):
    """
    Check if the current tenant has access to a specific feature
    """
    if tenant_context.is_super_admin:
        return  # Super admins have access to all features
        
    if not tenant_context.company:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Company information required"
        )
    
    subscription = tenant_context.company.subscription
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="No active subscription found"
        )
    
    if not subscription.can_use_feature(feature):
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=f"Feature '{feature}' is not available in your current subscription plan"
        )