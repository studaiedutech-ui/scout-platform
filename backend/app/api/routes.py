"""
API Router for S.C.O.U.T. Platform
Aggregates all API endpoints
"""

from fastapi import APIRouter
from app.api.endpoints import auth, companies, jobs, assessments, candidates, health, subscriptions, admin, files

api_router = APIRouter()

# Core endpoints
api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])

# Business endpoints
api_router.include_router(companies.router, prefix="/companies", tags=["companies"])
api_router.include_router(jobs.router, prefix="/jobs", tags=["jobs"])
api_router.include_router(assessments.router, prefix="/assessments", tags=["assessments"])
api_router.include_router(candidates.router, prefix="/candidates", tags=["candidates"])

# SaaS endpoints
api_router.include_router(subscriptions.router, prefix="/subscriptions", tags=["subscriptions"])
api_router.include_router(files.router, prefix="/files", tags=["files"])

# Admin endpoints
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])