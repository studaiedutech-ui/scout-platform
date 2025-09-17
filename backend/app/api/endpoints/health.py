"""
Health Check and Monitoring System for S.C.O.U.T. Platform
Provides comprehensive health checks for all system components
"""

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy import text
from redis import Redis
from typing import Dict, Any
import time
import psutil
import asyncio
import logging
from datetime import datetime, timezone

from app.core.config import settings
from app.core.database import get_database
from app.services.azure_openai_service import azure_openai_service

logger = logging.getLogger(__name__)
router = APIRouter()

class HealthChecker:
    """Comprehensive health check service"""
    
    async def check_database(self) -> Dict[str, Any]:
        """Check PostgreSQL database connectivity and performance"""
        try:
            start_time = time.time()
            async with get_database() as db:
                # Test basic connectivity
                result = await db.execute(text("SELECT 1"))
                
                # Test table access
                await db.execute(text("SELECT COUNT(*) FROM users LIMIT 1"))
                
            response_time = (time.time() - start_time) * 1000
            
            return {
                "status": "healthy",
                "response_time_ms": round(response_time, 2),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        except Exception as e:
            logger.error(f"Database health check failed: {str(e)}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
    
    async def check_redis(self) -> Dict[str, Any]:
        """Check Redis connectivity and performance"""
        try:
            start_time = time.time()
            redis_client = Redis.from_url(
                settings.REDIS_URL,
                ssl=settings.REDIS_SSL,
                socket_connect_timeout=settings.REDIS_SOCKET_CONNECT_TIMEOUT
            )
            
            # Test basic connectivity
            await asyncio.to_thread(redis_client.ping)
            
            # Test read/write
            test_key = "health_check_test"
            await asyncio.to_thread(redis_client.set, test_key, "test_value", ex=60)
            value = await asyncio.to_thread(redis_client.get, test_key)
            await asyncio.to_thread(redis_client.delete, test_key)
            
            response_time = (time.time() - start_time) * 1000
            
            return {
                "status": "healthy",
                "response_time_ms": round(response_time, 2),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        except Exception as e:
            logger.error(f"Redis health check failed: {str(e)}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
    
    async def check_azure_openai(self) -> Dict[str, Any]:
        """Check Azure OpenAI service connectivity"""
        try:
            start_time = time.time()
            
            if not azure_openai_service.client:
                return {
                    "status": "not_configured",
                    "message": "Azure OpenAI service not configured",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            
            # Test with a simple completion request
            response = await azure_openai_service.client.chat.completions.create(
                model=settings.AZURE_OPENAI_DEPLOYMENT_NAME,
                messages=[{"role": "user", "content": "Health check test"}],
                max_tokens=1,
                temperature=0
            )
            
            response_time = (time.time() - start_time) * 1000
            
            return {
                "status": "healthy",
                "response_time_ms": round(response_time, 2),
                "model": settings.AZURE_OPENAI_DEPLOYMENT_NAME,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        except Exception as e:
            logger.error(f"Azure OpenAI health check failed: {str(e)}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
    
    def check_system_resources(self) -> Dict[str, Any]:
        """Check system resource usage"""
        try:
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            cpu_percent = psutil.cpu_percent(interval=1)
            
            return {
                "status": "healthy",
                "cpu_usage_percent": cpu_percent,
                "memory": {
                    "total_gb": round(memory.total / (1024**3), 2),
                    "available_gb": round(memory.available / (1024**3), 2),
                    "usage_percent": memory.percent
                },
                "disk": {
                    "total_gb": round(disk.total / (1024**3), 2),
                    "free_gb": round(disk.free / (1024**3), 2),
                    "usage_percent": round((disk.used / disk.total) * 100, 2)
                },
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        except Exception as e:
            logger.error(f"System resources check failed: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

health_checker = HealthChecker()

@router.get("/health")
async def health_check():
    """Basic health check endpoint"""
    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "version": settings.VERSION,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

@router.get("/health/detailed")
async def detailed_health_check():
    """Comprehensive health check for all system components"""
    try:
        # Run all health checks concurrently
        database_health, redis_health, openai_health = await asyncio.gather(
            health_checker.check_database(),
            health_checker.check_redis(),
            health_checker.check_azure_openai(),
            return_exceptions=True
        )
        
        system_health = health_checker.check_system_resources()
        
        # Determine overall status
        components = [database_health, redis_health, openai_health, system_health]
        overall_status = "healthy"
        
        for component in components:
            if isinstance(component, Exception):
                overall_status = "unhealthy"
                break
            elif component.get("status") == "unhealthy":
                overall_status = "unhealthy"
                break
            elif component.get("status") == "not_configured":
                overall_status = "degraded"
        
        response = {
            "status": overall_status,
            "service": settings.APP_NAME,
            "version": settings.VERSION,
            "environment": settings.ENVIRONMENT,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "components": {
                "database": database_health if not isinstance(database_health, Exception) else {"status": "error", "error": str(database_health)},
                "redis": redis_health if not isinstance(redis_health, Exception) else {"status": "error", "error": str(redis_health)},
                "azure_openai": openai_health if not isinstance(openai_health, Exception) else {"status": "error", "error": str(openai_health)},
                "system": system_health
            }
        }
        
        # Return appropriate HTTP status code
        if overall_status == "healthy":
            return JSONResponse(content=response, status_code=200)
        elif overall_status == "degraded":
            return JSONResponse(content=response, status_code=200)
        else:
            return JSONResponse(content=response, status_code=503)
            
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return JSONResponse(
            content={
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            },
            status_code=503
        )

@router.get("/health/ready")
async def readiness_check():
    """Kubernetes readiness probe endpoint"""
    try:
        # Check critical dependencies only
        database_health, redis_health = await asyncio.gather(
            health_checker.check_database(),
            health_checker.check_redis()
        )
        
        if (database_health.get("status") == "healthy" and 
            redis_health.get("status") == "healthy"):
            return {"status": "ready"}
        else:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Service not ready"
            )
            
    except Exception as e:
        logger.error(f"Readiness check failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service not ready"
        )

@router.get("/health/live")
async def liveness_check():
    """Kubernetes liveness probe endpoint"""
    return {"status": "alive"}

@router.get("/metrics")
async def metrics():
    """Prometheus-style metrics endpoint"""
    try:
        system_info = health_checker.check_system_resources()
        
        metrics_data = f"""
# HELP scout_platform_cpu_usage_percent Current CPU usage percentage
# TYPE scout_platform_cpu_usage_percent gauge
scout_platform_cpu_usage_percent {system_info['cpu_usage_percent']}

# HELP scout_platform_memory_usage_percent Current memory usage percentage
# TYPE scout_platform_memory_usage_percent gauge
scout_platform_memory_usage_percent {system_info['memory']['usage_percent']}

# HELP scout_platform_disk_usage_percent Current disk usage percentage
# TYPE scout_platform_disk_usage_percent gauge
scout_platform_disk_usage_percent {system_info['disk']['usage_percent']}

# HELP scout_platform_memory_available_gb Available memory in GB
# TYPE scout_platform_memory_available_gb gauge
scout_platform_memory_available_gb {system_info['memory']['available_gb']}

# HELP scout_platform_disk_free_gb Free disk space in GB
# TYPE scout_platform_disk_free_gb gauge
scout_platform_disk_free_gb {system_info['disk']['free_gb']}
"""
        
        return JSONResponse(
            content=metrics_data,
            media_type="text/plain"
        )
        
    except Exception as e:
        logger.error(f"Metrics collection failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Metrics collection failed"
        )