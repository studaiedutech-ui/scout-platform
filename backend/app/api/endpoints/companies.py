from fastapi import APIRouter

router = APIRouter()

@router.get("/")
async def get_companies():
    """Get all companies"""
    return {"message": "Companies endpoint - coming soon"}

@router.post("/onboard")
async def onboard_company():
    """Company onboarding endpoint"""
    return {"message": "Company onboarding endpoint - coming soon"}