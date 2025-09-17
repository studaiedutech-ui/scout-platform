from fastapi import APIRouter
from app.api.endpoints import auth, companies, jobs, assessments, candidates

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(companies.router, prefix="/companies", tags=["companies"])
api_router.include_router(jobs.router, prefix="/jobs", tags=["jobs"])
api_router.include_router(assessments.router, prefix="/assessments", tags=["assessments"])
api_router.include_router(candidates.router, prefix="/candidates", tags=["candidates"])