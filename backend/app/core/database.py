"""
Production-Ready Database Configuration for S.C.O.U.T. Platform
Enhanced with connection pooling, monitoring, and optimization
"""

import os
import logging
import time
from typing import AsyncGenerator, Generator
from sqlalchemy import create_engine, MetaData, event, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool, StaticPool
from sqlalchemy.engine import Engine

from app.core.config import settings

logger = logging.getLogger(__name__)

# Database metadata and base class
metadata = MetaData()
Base = declarative_base(metadata=metadata)

def create_database_engine() -> Engine:
    """Create synchronous database engine with production optimizations"""
    
    connect_args = {}
    
    if settings.DATABASE_URL.startswith("sqlite"):
        # SQLite configuration for development/testing
        poolclass = StaticPool
        pool_size = 1
        max_overflow = 0
        pool_pre_ping = False
        connect_args = {"check_same_thread": False}
    else:
        # PostgreSQL configuration for production
        poolclass = QueuePool
        pool_size = settings.DATABASE_POOL_SIZE
        max_overflow = settings.DATABASE_MAX_OVERFLOW
        pool_pre_ping = True
        connect_args = {
            "connect_timeout": settings.DATABASE_CONNECT_TIMEOUT,
            "command_timeout": settings.DATABASE_COMMAND_TIMEOUT,
            "server_settings": {
                "application_name": f"scout_platform_{settings.ENVIRONMENT}",
                "timezone": "UTC",
            }
        }
    
    engine = create_engine(
        settings.DATABASE_URL,
        poolclass=poolclass,
        pool_size=pool_size,
        max_overflow=max_overflow,
        pool_pre_ping=pool_pre_ping,
        pool_recycle=settings.DATABASE_POOL_RECYCLE,
        echo=settings.DATABASE_ECHO,
        future=True,
        isolation_level="READ_COMMITTED",
        connect_args=connect_args
    )
    
    setup_database_monitoring(engine)
    return engine

def create_async_database_engine():
    """Create async database engine"""
    if settings.DATABASE_URL.startswith("sqlite"):
        async_url = settings.DATABASE_URL.replace("sqlite://", "sqlite+aiosqlite://")
    else:
        async_url = settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
    
    return create_async_engine(
        async_url,
        echo=settings.DATABASE_ECHO,
        future=True,
        pool_size=settings.DATABASE_POOL_SIZE,
        max_overflow=settings.DATABASE_MAX_OVERFLOW,
        pool_pre_ping=True,
        pool_recycle=settings.DATABASE_POOL_RECYCLE
    )

def setup_database_monitoring(engine: Engine):
    """Setup database monitoring and logging"""
    
    @event.listens_for(engine, "before_cursor_execute")
    def receive_before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        context._query_start_time = time.time()
    
    @event.listens_for(engine, "after_cursor_execute")
    def receive_after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        total = time.time() - context._query_start_time
        
        if total > settings.SLOW_QUERY_THRESHOLD:
            logger.warning(
                f"Slow query detected: {total:.3f}s",
                extra={
                    "query_time": total,
                    "query": statement[:200] + "..." if len(statement) > 200 else statement,
                    "parameters": str(parameters)[:100] if parameters else None
                }
            )
    
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        if "sqlite" in str(engine.url):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA synchronous=NORMAL")
            cursor.close()

# Create engines
engine = create_database_engine()
async_engine = create_async_database_engine()

# Create session factories
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
    class_=Session
)

AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False
)

def get_db() -> Generator[Session, None, None]:
    """Database session dependency for FastAPI (synchronous)"""
    session = SessionLocal()
    try:
        if not settings.DATABASE_URL.startswith("sqlite"):
            session.execute(text("SET statement_timeout = '30s'"))
        
        yield session
        session.commit()
        
    except Exception as e:
        session.rollback()
        logger.error(f"Database session error: {str(e)}")
        raise
    finally:
        session.close()

async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """Async database session dependency for FastAPI"""
    session = AsyncSessionLocal()
    try:
        yield session
        await session.commit()
    except Exception as e:
        await session.rollback()
        logger.error(f"Async database session error: {str(e)}")
        raise
    finally:
        await session.close()

# Legacy compatibility
async def get_session() -> AsyncSession:
    """Legacy compatibility function"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

def create_db_and_tables():
    """Create database tables (synchronous)"""
    try:
        logger.info("Creating database tables...")
        
        # Import all models to ensure they're registered
        from app.models.user import User
        from app.models.company import Company
        from app.models.job import Job
        from app.models.candidate import Candidate
        from app.models.assessment import Assessment
        
        # Create all tables
        Base.metadata.create_all(bind=engine)
        
        logger.info("Database tables created successfully")
        
        # Verify table creation
        with engine.connect() as connection:
            from sqlalchemy import inspect
            inspector = inspect(engine)
            tables = inspector.get_table_names()
            
            logger.info(f"Created {len(tables)} tables: {', '.join(tables)}")
            
            # Create performance indexes
            create_performance_indexes(connection)
            
    except Exception as e:
        logger.error(f"Failed to create database tables: {str(e)}")
        raise

async def create_db_and_tables_async():
    """Create database tables (asynchronous)"""
    try:
        logger.info("Creating database tables (async)...")
        
        # Import all models
        from app.models.user import User
        from app.models.company import Company
        from app.models.job import Job
        from app.models.candidate import Candidate
        from app.models.assessment import Assessment
        
        async with async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        logger.info("Database tables created successfully (async)")
        
    except Exception as e:
        logger.error(f"Failed to create database tables (async): {str(e)}")
        raise

def create_performance_indexes(connection):
    """Create additional indexes for performance optimization"""
    try:
        indexes = [
            # User table indexes
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_email ON users(email)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_created_at ON users(created_at)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_active ON users(is_active) WHERE is_active = true",
            
            # Company table indexes
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_companies_industry ON companies(industry)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_companies_size ON companies(size)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_companies_created_at ON companies(created_at)",
            
            # Job table indexes
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_jobs_company_id ON jobs(company_id)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_jobs_status ON jobs(status)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_jobs_location ON jobs(location)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_jobs_employment_type ON jobs(employment_type)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_jobs_created_at ON jobs(created_at)",
            
            # Candidate table indexes
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_candidates_email ON candidates(email)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_candidates_location ON candidates(location)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_candidates_experience_years ON candidates(experience_years)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_candidates_created_at ON candidates(created_at)",
            
            # Assessment table indexes
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_assessments_candidate_id ON assessments(candidate_id)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_assessments_job_id ON assessments(job_id)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_assessments_status ON assessments(status)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_assessments_created_at ON assessments(created_at)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_assessments_score ON assessments(score)",
            
            # Composite indexes
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_jobs_company_status ON jobs(company_id, status)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_assessments_candidate_job ON assessments(candidate_id, job_id)",
        ]
        
        # Only create indexes for PostgreSQL
        if not settings.DATABASE_URL.startswith("sqlite"):
            for index_sql in indexes:
                try:
                    connection.execute(text(index_sql))
                    logger.debug(f"Created index: {index_sql.split('idx_')[1].split(' ')[0] if 'idx_' in index_sql else 'unknown'}")
                except Exception as e:
                    logger.debug(f"Index creation skipped: {str(e)}")
        
        logger.info("Performance indexes created/verified")
        
    except Exception as e:
        logger.warning(f"Failed to create some performance indexes: {str(e)}")

def check_database_health() -> dict:
    """Check database health and connection status"""
    try:
        start_time = time.time()
        
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1"))
            result.fetchone()
            
            if not settings.DATABASE_URL.startswith("sqlite"):
                connection.execute(text("SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public'"))
        
        connection_time = time.time() - start_time
        
        # Get pool status
        pool = engine.pool
        
        return {
            "status": "healthy",
            "connection_time": round(connection_time, 3),
            "pool_size": pool.size(),
            "checked_out_connections": pool.checkedout(),
            "overflow": pool.overflow(),
            "invalid_connections": pool.invalid(),
            "timestamp": time.time()
        }
        
    except Exception as e:
        logger.error(f"Database health check failed: {str(e)}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": time.time()
        }

def close_database_connections():
    """Close all database connections"""
    try:
        engine.dispose()
        async_engine.sync_dispose() if hasattr(async_engine, 'sync_dispose') else None
        logger.info("Database connections closed")
    except Exception as e:
        logger.error(f"Error closing database connections: {str(e)}")

# Export commonly used objects
__all__ = [
    "Base",
    "engine", 
    "async_engine",
    "SessionLocal",
    "AsyncSessionLocal",
    "get_db",
    "get_async_db",
    "get_session",  # Legacy compatibility
    "create_db_and_tables",
    "create_db_and_tables_async",
    "check_database_health",
    "close_database_connections"
]