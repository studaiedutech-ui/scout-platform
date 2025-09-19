from pydantic_settings import BaseSettings
from typing import List, Optional
import os
from functools import lru_cache

class Settings(BaseSettings):
    """
    Application settings using Pydantic with production-ready configurations
    """
    # Application
    APP_NAME: str = "S.C.O.U.T. Platform"
    DEBUG: bool = False
    VERSION: str = "1.0.0"
    ENVIRONMENT: str = "production"
    
    # URLs
    FRONTEND_URL: str = "https://app.scout-platform.com"
    BACKEND_URL: str = "https://api.scout-platform.com"
    API_BASE_URL: str = "https://api.scout-platform.com/api/v1"
    
    # Database with connection pooling
    DATABASE_URL: str = "postgresql://scout_user:scout_password@localhost:5432/scout_db"
    DATABASE_ECHO: bool = False
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 30
    DATABASE_POOL_TIMEOUT: int = 30
    DATABASE_POOL_RECYCLE: int = 3600
    
    # Redis with SSL support
    REDIS_URL: str = "redis://localhost:6379"
    REDIS_SSL: bool = False
    REDIS_CONNECTION_POOL_SIZE: int = 50
    REDIS_SOCKET_CONNECT_TIMEOUT: int = 5
    REDIS_SOCKET_TIMEOUT: int = 5
    
    # Security
    SECRET_KEY: str = "your-super-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    
    # Password Policy
    MIN_PASSWORD_LENGTH: int = 12
    REQUIRE_SPECIAL_CHARS: bool = True
    REQUIRE_NUMBERS: bool = True
    REQUIRE_UPPERCASE: bool = True
    
    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 100
    RATE_LIMIT_BURST: int = 20
    
    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "https://app.scout-platform.com"]
    ALLOWED_HOSTS: List[str] = ["localhost", "127.0.0.1", "scout-platform.com"]
    
    # Security Headers
    SECURE_COOKIES: bool = True
    SAME_SITE_COOKIES: str = "strict"
    X_FRAME_OPTIONS: str = "deny"
    CONTENT_SECURITY_POLICY: str = "default-src 'self'"
    
    # AI Services - Azure OpenAI
    AZURE_OPENAI_API_KEY: str = ""
    AZURE_OPENAI_ENDPOINT: str = ""
    AZURE_OPENAI_API_VERSION: str = "2024-02-15-preview"
    AZURE_OPENAI_DEPLOYMENT_NAME: str = "gpt-4"
    AZURE_OPENAI_EMBEDDING_DEPLOYMENT: str = "text-embedding-ada-002"
    
    # Pinecone
    PINECONE_API_KEY: str = ""
    PINECONE_ENVIRONMENT: str = ""
    PINECONE_INDEX_NAME: str = "scout-corporate-dna"
    
    # Azure Storage
    AZURE_STORAGE_ACCOUNT: str = ""
    AZURE_STORAGE_KEY: str = ""
    AZURE_STORAGE_CONTAINER: str = "uploads"
    MAX_FILE_SIZE: int = 10485760  # 10MB
    ALLOWED_FILE_TYPES: List[str] = ["pdf", "doc", "docx", "txt", "png", "jpg", "jpeg"]
    
    # Email
    SENDGRID_API_KEY: str = ""
    FROM_EMAIL: str = "noreply@scout-platform.com"
    SUPPORT_EMAIL: str = "support@scout-platform.com"
    
    # Payment Processing
    STRIPE_PUBLISHABLE_KEY: str = ""
    STRIPE_SECRET_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""
    
    # OAuth
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    MICROSOFT_CLIENT_ID: str = ""
    MICROSOFT_CLIENT_SECRET: str = ""
    
    # Monitoring
    APPINSIGHTS_CONNECTION_STRING: str = ""
    SENTRY_DSN: str = ""
    SENTRY_ENVIRONMENT: str = "production"
    SENTRY_TRACES_SAMPLE_RATE: float = 0.1
    
    # Background Jobs
    CELERY_BROKER_URL: str = ""
    CELERY_RESULT_BACKEND: str = ""
    CELERY_TASK_ALWAYS_EAGER: bool = False
    CELERY_WORKER_CONCURRENCY: int = 4
    
    # Assessment Configuration
    DEFAULT_ASSESSMENT_DURATION: int = 3600
    MAX_ASSESSMENT_QUESTIONS: int = 25
    ASSESSMENT_TIMEOUT_WARNING: int = 300
    AUTO_SAVE_INTERVAL: int = 30
    
    # WebSocket
    WS_MAX_CONNECTIONS: int = 1000
    WS_HEARTBEAT_INTERVAL: int = 30
    WS_CONNECTION_TIMEOUT: int = 60
    
    # Feature Flags
    FEATURE_VIDEO_INTERVIEWS: bool = True
    FEATURE_AI_VOICE_ANALYSIS: bool = True
    FEATURE_ADVANCED_ANALYTICS: bool = True
    FEATURE_API_V2: bool = False
    
    # Compliance
    DATA_RETENTION_DAYS: int = 2555  # 7 years
    GDPR_COMPLIANCE: bool = True
    CCPA_COMPLIANCE: bool = True
    AUDIT_LOG_RETENTION_DAYS: int = 2555
    
    # Performance
    WORKER_PROCESSES: int = 4
    WORKER_THREADS: int = 2
    MAX_REQUESTS_PER_WORKER: int = 1000
    WORKER_TIMEOUT: int = 30
    KEEPALIVE_TIMEOUT: int = 5
    
    # Cache
    CACHE_TTL: int = 3600
    CACHE_MAX_ENTRIES: int = 10000
    
    # Health Checks
    HEALTH_CHECK_INTERVAL: int = 30
    HEALTH_CHECK_TIMEOUT: int = 5
    METRICS_COLLECTION_INTERVAL: int = 60

    class Config:
        env_file = ".env"
        case_sensitive = True

@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()

settings = get_settings()
    
    # Pinecone
    PINECONE_API_KEY: str = ""
    PINECONE_ENVIRONMENT: str = ""
    PINECONE_INDEX_NAME: str = "scout-corporate-dna"
    
    # Firebase/Firestore (Optional - can use Azure SignalR instead)
    # GOOGLE_APPLICATION_CREDENTIALS: str = ""
    # FIREBASE_PROJECT_ID: str = ""
    
    # Email
    SENDGRID_API_KEY: str = ""
    FROM_EMAIL: str = "noreply@scout-platform.com"
    
    # Storage
    AZURE_STORAGE_ACCOUNT: str = ""
    AZURE_STORAGE_KEY: str = ""
    AZURE_STORAGE_CONTAINER: str = "uploads"
    
    # Payment
    STRIPE_PUBLISHABLE_KEY: str = ""
    STRIPE_SECRET_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""
    
    # OAuth
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    MICROSOFT_CLIENT_ID: str = ""
    MICROSOFT_CLIENT_SECRET: str = ""
    
    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 100
    RATE_LIMIT_BURST: int = 200
    
    # File Upload
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB
    ALLOWED_FILE_TYPES: List[str] = ["pdf", "docx", "doc", "txt"]
    
    # WebRTC
    TURN_SERVER_URL: str = ""
    TURN_USERNAME: str = ""
    TURN_PASSWORD: str = ""
    
    # Monitoring
    SENTRY_DSN: str = ""
    
    # SaaS-specific configurations
    
    # Payment Processing (Stripe)
    STRIPE_PUBLISHABLE_KEY: str = ""
    STRIPE_SECRET_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""
    
    # Subscription Management
    DEFAULT_TRIAL_DAYS: int = 14
    
    # Email Configuration for notifications
    SMTP_SERVER: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    FROM_EMAIL: str = "noreply@scout-platform.com"
    FROM_NAME: str = "S.C.O.U.T. Platform"
    
    # File Upload Settings
    MAX_FILE_SIZE_MB: int = 10
    MAX_FILES_PER_UPLOAD: int = 5
    STORAGE_PROVIDER: str = "local"  # local, azure_blob, s3
    
    # Feature Flags for SaaS
    ENABLE_SIGNUP: bool = True
    ENABLE_PAYMENTS: bool = True
    ENABLE_EMAIL_NOTIFICATIONS: bool = True
    ENABLE_ADMIN_DASHBOARD: bool = True
    
    class Config:
        env_file = ".env"
        case_sensitive = True

# Create settings instance
settings = Settings()

# SaaS Plan Configuration
SUBSCRIPTION_PLANS = {
    "free": {
        "name": "Free",
        "description": "Perfect for trying out SCOUT",
        "monthly_price": 0,
        "yearly_price": 0,
        "features": {
            "max_jobs": 1,
            "max_candidates": 10,
            "max_assessments": 5,
            "max_users": 1,
            "max_storage_gb": 1,
            "ai_assessment_enabled": False,
            "analytics_enabled": False,
            "custom_branding": False,
            "api_access": False,
            "priority_support": False
        }
    },
    "starter": {
        "name": "Starter", 
        "description": "Great for small teams",
        "monthly_price": 49,
        "yearly_price": 490,
        "features": {
            "max_jobs": 5,
            "max_candidates": 100,
            "max_assessments": 50,
            "max_users": 3,
            "max_storage_gb": 10,
            "ai_assessment_enabled": True,
            "analytics_enabled": True,
            "custom_branding": False,
            "api_access": False,
            "priority_support": False
        }
    },
    "professional": {
        "name": "Professional",
        "description": "Ideal for growing companies",
        "monthly_price": 149,
        "yearly_price": 1490,
        "features": {
            "max_jobs": 25,
            "max_candidates": 1000,
            "max_assessments": 500,
            "max_users": 10,
            "max_storage_gb": 100,
            "ai_assessment_enabled": True,
            "analytics_enabled": True,
            "custom_branding": True,
            "api_access": True,
            "priority_support": True
        }
    },
    "enterprise": {
        "name": "Enterprise",
        "description": "Unlimited power for large organizations",
        "monthly_price": 499,
        "yearly_price": 4990,
        "features": {
            "max_jobs": 0,  # unlimited
            "max_candidates": 0,  # unlimited
            "max_assessments": 0,  # unlimited
            "max_users": 0,  # unlimited
            "max_storage_gb": 0,  # unlimited
            "ai_assessment_enabled": True,
            "analytics_enabled": True,
            "custom_branding": True,
            "api_access": True,
            "priority_support": True
        }
    }
}
settings = Settings()