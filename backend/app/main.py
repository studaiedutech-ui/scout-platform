"""
S.C.O.U.T. Platform - Production-Ready FastAPI Application
AI-driven talent acquisition and assessment platform
"""

import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse, JSONResponse
from prometheus_fastapi_instrumentator import Instrumentator
import redis
import asyncio

# Import core modules
from app.core.config import settings
from app.core.database import engine, Base, get_db
from app.core.logging import setup_logging, logger
from app.core.middleware import setup_middleware
from app.core.exception_handlers import setup_exception_handlers
from app.api.routes import api_router
from app.api.endpoints.health import router as health_router

# Setup logging first
setup_logging()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    
    # Startup
    logger.info("Starting S.C.O.U.T. Platform...")
    
    try:
        # Create database tables
        logger.info("Creating database tables...")
        Base.metadata.create_all(bind=engine)
        
        # Test database connection
        logger.info("Testing database connection...")
        try:
            from sqlalchemy import text
            with engine.connect() as connection:
                result = connection.execute(text("SELECT 1"))
                logger.info("Database connection successful")
        except Exception as e:
            logger.error(f"Database connection failed: {str(e)}")
            raise
        
        # Test Redis connection
        logger.info("Testing Redis connection...")
        try:
            redis_client = redis.from_url(
                settings.REDIS_URL,
                ssl=settings.REDIS_SSL,
                socket_connect_timeout=settings.REDIS_SOCKET_CONNECT_TIMEOUT
            )
            redis_client.ping()
            logger.info("Redis connection successful")
        except Exception as e:
            logger.error(f"Redis connection failed: {str(e)}")
            raise
        
        # Test Azure OpenAI connection
        logger.info("Testing Azure OpenAI connection...")
        try:
            from app.services.azure_openai_service import AzureOpenAIService
            openai_service = AzureOpenAIService()
            # Test with a simple completion
            await openai_service.test_connection()
            logger.info("Azure OpenAI connection successful")
        except Exception as e:
            logger.warning(f"Azure OpenAI connection test failed: {str(e)}")
            # Don't fail startup for OpenAI issues in development
        
        logger.info("S.C.O.U.T. Platform startup completed successfully")
        
        yield
        
    except Exception as e:
        logger.error(f"Failed to start S.C.O.U.T. Platform: {str(e)}")
        raise
    
    # Shutdown
    logger.info("Shutting down S.C.O.U.T. Platform...")
    
    try:
        # Close database connections
        engine.dispose()
        logger.info("Database connections closed")
        
        # Close Redis connections
        if 'redis_client' in locals():
            redis_client.close()
        logger.info("Redis connections closed")
        
        logger.info("S.C.O.U.T. Platform shutdown completed")
        
    except Exception as e:
        logger.error(f"Error during shutdown: {str(e)}")

# Create FastAPI application
app = FastAPI(
    title=settings.PROJECT_NAME,
    description="""
    S.C.O.U.T. (Strategic Candidate Optimization and Universal Talent) Platform
    
    An AI-driven talent acquisition and assessment platform that revolutionizes 
    how companies discover, evaluate, and hire top talent through advanced 
    analytics and intelligent matching.
    
    ## Features
    
    * **AI-Powered Candidate Matching**: Advanced algorithms for optimal candidate-job matching
    * **Comprehensive Assessments**: Customizable skill assessments with AI analysis
    * **Corporate DNA Analysis**: AI-driven company culture and value assessment
    * **Real-time Analytics**: Advanced reporting and talent analytics
    * **Secure Platform**: Enterprise-grade security and compliance
    
    ## Authentication
    
    The API uses JWT Bearer token authentication. Include your token in the 
    Authorization header: `Authorization: Bearer <your_token>`
    """,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json" if settings.ENVIRONMENT != "production" else None,
    docs_url="/docs" if settings.ENVIRONMENT != "production" else None,
    redoc_url="/redoc" if settings.ENVIRONMENT != "production" else None,
    lifespan=lifespan,
    contact={
        "name": "S.C.O.U.T. Platform Support",
        "email": settings.SUPPORT_EMAIL,
        "url": settings.SUPPORT_URL,
    },
    license_info={
        "name": "Proprietary",
        "url": f"{settings.FRONTEND_URL}/license",
    },
    servers=[
        {
            "url": settings.API_BASE_URL,
            "description": f"{settings.ENVIRONMENT.title()} Environment"
        }
    ]
)

# Setup middleware
setup_middleware(app)

# Setup Prometheus metrics
if settings.ENABLE_METRICS:
    instrumentator = Instrumentator(
        should_group_status_codes=True,
        should_ignore_untemplated=True,
        should_respect_env_var=True,
        should_instrument_requests_inprogress=True,
        excluded_handlers=["/health", "/health/ready", "/health/live", "/metrics"],
        env_var_name="ENABLE_METRICS",
        inprogress_name="scout_http_requests_inprogress",
        inprogress_labels=True,
    )
    
    instrumentator.instrument(app).expose(
        app, 
        endpoint="/metrics",
        tags=["monitoring"],
        include_in_schema=False
    )

# Include routers
app.include_router(health_router, tags=["health"])
app.include_router(api_router, prefix=settings.API_V1_STR)

# Static files (for production deployments)
if settings.SERVE_STATIC_FILES:
    static_dir = os.path.join(os.path.dirname(__file__), "..", "static")
    if os.path.exists(static_dir):
        app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Root endpoint
@app.get("/", include_in_schema=False)
async def root():
    """Root endpoint - redirect to appropriate interface"""
    if settings.ENVIRONMENT == "production":
        return RedirectResponse(url=settings.FRONTEND_URL)
    else:
        return RedirectResponse(url="/docs")

# Global exception handler
@app.exception_handler(500)
async def internal_server_error_handler(request: Request, exc: Exception):
    """Handle internal server errors"""
    request_id = getattr(request.state, "request_id", "unknown")
    
    logger.error(
        f"Internal server error: {str(exc)}",
        extra={
            "request_id": request_id,
            "path": request.url.path,
            "method": request.method,
            "client_ip": request.client.host if request.client else "unknown"
        },
        exc_info=True
    )
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": "An unexpected error occurred. Please try again later.",
            "request_id": request_id,
            "support_email": settings.SUPPORT_EMAIL
        },
        headers={"X-Request-ID": request_id}
    )

# 404 handler
@app.exception_handler(404)
async def not_found_handler(request: Request, exc: Exception):
    """Handle 404 errors"""
    request_id = getattr(request.state, "request_id", "unknown")
    
    logger.warning(
        f"404 Not Found: {request.url.path}",
        extra={
            "request_id": request_id,
            "path": request.url.path,
            "method": request.method,
            "client_ip": request.client.host if request.client else "unknown"
        }
    )
    
    return JSONResponse(
        status_code=404,
        content={
            "error": "Not Found",
            "message": f"The requested resource '{request.url.path}' was not found.",
            "request_id": request_id
        },
        headers={"X-Request-ID": request_id}
    )

# Health check for application readiness
@app.get("/ready", include_in_schema=False, tags=["health"])
async def readiness_check():
    """Kubernetes readiness probe"""
    try:
        # Quick database check
        from sqlalchemy import text
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        
        return {"status": "ready", "timestamp": settings.get_current_timestamp()}
    except Exception as e:
        logger.error(f"Readiness check failed: {str(e)}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "not ready",
                "error": str(e),
                "timestamp": settings.get_current_timestamp()
            }
        )

# Health check for application liveness
@app.get("/live", include_in_schema=False, tags=["health"])
async def liveness_check():
    """Kubernetes liveness probe"""
    return {"status": "alive", "timestamp": settings.get_current_timestamp()}

# Application info endpoint
@app.get("/info", include_in_schema=False, tags=["meta"])
async def app_info():
    """Application information"""
    return {
        "name": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "python_version": settings.PYTHON_VERSION,
        "build_timestamp": settings.BUILD_TIMESTAMP,
        "git_commit": settings.GIT_COMMIT_HASH,
        "features": {
            "ai_assessments": settings.ENABLE_AI_ASSESSMENTS,
            "metrics": settings.ENABLE_METRICS,
            "caching": settings.ENABLE_CACHING,
            "audit_logging": settings.ENABLE_AUDIT_LOGGING,
            "rate_limiting": settings.ENABLE_RATE_LIMITING
        }
    }

if __name__ == "__main__":
    import uvicorn
    
    # Development server configuration
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.ENVIRONMENT == "development",
        log_level="info",
        access_log=True,
        server_header=False,
        date_header=False
    )