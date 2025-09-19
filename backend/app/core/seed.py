"""
Database seeding script for initial subscription plans
"""

from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.subscription import SubscriptionPlan, SubscriptionPlanType


def create_default_subscription_plans(db: Session):
    """
    Create default subscription plans for the SaaS platform
    """
    
    # Check if plans already exist
    existing_plans = db.query(SubscriptionPlan).count()
    if existing_plans > 0:
        print("Subscription plans already exist, skipping creation")
        return
    
    plans = [
        {
            "name": "Free",
            "plan_type": SubscriptionPlanType.FREE,
            "description": "Perfect for trying out SCOUT with basic features",
            "monthly_price": 0,
            "yearly_price": 0,
            "max_jobs": 1,
            "max_candidates": 10,
            "max_assessments": 5,
            "max_users": 1,
            "max_storage_gb": 1,
            "ai_assessment_enabled": False,
            "analytics_enabled": False,
            "custom_branding": False,
            "api_access": False,
            "priority_support": False,
            "trial_days": 14,
        },
        {
            "name": "Starter",
            "plan_type": SubscriptionPlanType.STARTER,
            "description": "Great for small teams getting started with AI recruitment",
            "monthly_price": 49,
            "yearly_price": 490,  # 2 months free
            "max_jobs": 5,
            "max_candidates": 100,
            "max_assessments": 50,
            "max_users": 3,
            "max_storage_gb": 10,
            "ai_assessment_enabled": True,
            "analytics_enabled": True,
            "custom_branding": False,
            "api_access": False,
            "priority_support": False,
            "trial_days": 14,
        },
        {
            "name": "Professional",
            "plan_type": SubscriptionPlanType.PROFESSIONAL,
            "description": "Ideal for growing companies with advanced recruitment needs",
            "monthly_price": 149,
            "yearly_price": 1490,  # 2 months free
            "max_jobs": 25,
            "max_candidates": 1000,
            "max_assessments": 500,
            "max_users": 10,
            "max_storage_gb": 100,
            "ai_assessment_enabled": True,
            "analytics_enabled": True,
            "custom_branding": True,
            "api_access": True,
            "priority_support": True,
            "trial_days": 14,
        },
        {
            "name": "Enterprise",
            "plan_type": SubscriptionPlanType.ENTERPRISE,
            "description": "Unlimited power for large organizations with custom requirements",
            "monthly_price": 499,
            "yearly_price": 4990,  # 2 months free
            "max_jobs": 0,  # unlimited
            "max_candidates": 0,  # unlimited
            "max_assessments": 0,  # unlimited
            "max_users": 0,  # unlimited
            "max_storage_gb": 0,  # unlimited
            "ai_assessment_enabled": True,
            "analytics_enabled": True,
            "custom_branding": True,
            "api_access": True,
            "priority_support": True,
            "trial_days": 30,
        }
    ]
    
    for plan_data in plans:
        plan = SubscriptionPlan(**plan_data)
        db.add(plan)
    
    db.commit()
    print(f"Created {len(plans)} subscription plans")


def seed_database():
    """
    Seed the database with initial data
    """
    db = SessionLocal()
    try:
        print("Seeding database with initial data...")
        create_default_subscription_plans(db)
        print("Database seeding completed successfully")
    except Exception as e:
        print(f"Error seeding database: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()