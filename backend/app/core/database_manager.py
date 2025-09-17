"""
Database Production Management Module for S.C.O.U.T. Platform
Handles database operations, migrations, monitoring, and optimization
"""

import os
import sys
import logging
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone, timedelta
from sqlalchemy import create_engine, text, MetaData, inspect, Table
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import redis
import time

from app.core.config import settings
from app.core.logging import logger

class DatabaseManager:
    """Comprehensive database management for production environments"""
    
    def __init__(self):
        self.engine: Optional[Engine] = None
        self.session_factory: Optional[sessionmaker] = None
        self.redis_client = None
        
    def initialize(self):
        """Initialize database connections and components"""
        try:
            # Create production-optimized engine
            self.engine = create_engine(
                settings.DATABASE_URL,
                poolclass=QueuePool,
                pool_size=settings.DATABASE_POOL_SIZE,
                max_overflow=settings.DATABASE_MAX_OVERFLOW,
                pool_pre_ping=True,
                pool_recycle=settings.DATABASE_POOL_RECYCLE,
                echo=settings.DATABASE_ECHO,
                isolation_level="READ_COMMITTED",
                connect_args={
                    "connect_timeout": settings.DATABASE_CONNECT_TIMEOUT,
                    "command_timeout": settings.DATABASE_COMMAND_TIMEOUT,
                    "server_settings": {
                        "application_name": f"scout_platform_{settings.ENVIRONMENT}",
                        "timezone": "UTC"
                    }
                }
            )
            
            # Create session factory
            self.session_factory = sessionmaker(
                bind=self.engine,
                autocommit=False,
                autoflush=False,
                expire_on_commit=False
            )
            
            # Initialize Redis for caching
            self.redis_client = redis.from_url(
                settings.REDIS_URL,
                ssl=settings.REDIS_SSL,
                socket_connect_timeout=settings.REDIS_SOCKET_CONNECT_TIMEOUT,
                health_check_interval=30
            )
            
            logger.info("Database manager initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize database manager: {str(e)}")
            raise
    
    def test_connection(self) -> Dict[str, Any]:
        """Test database connection and return status"""
        try:
            start_time = time.time()
            
            with self.engine.connect() as connection:
                # Test basic connectivity
                result = connection.execute(text("SELECT version(), current_timestamp, current_database()"))
                row = result.fetchone()
                
                # Test performance
                connection.execute(text("SELECT 1"))
                
            connection_time = time.time() - start_time
            
            return {
                "status": "healthy",
                "connection_time": round(connection_time, 3),
                "database_version": row[0] if row else "unknown",
                "timestamp": row[1] if row else None,
                "database_name": row[2] if row else "unknown",
                "pool_size": self.engine.pool.size(),
                "checked_out_connections": self.engine.pool.checkedout(),
                "overflow": self.engine.pool.overflow(),
                "invalid_connections": self.engine.pool.invalid()
            }
            
        except Exception as e:
            logger.error(f"Database connection test failed: {str(e)}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now(timezone.utc)
            }
    
    def get_database_stats(self) -> Dict[str, Any]:
        """Get comprehensive database statistics"""
        try:
            with self.engine.connect() as connection:
                # Database size and statistics
                stats_query = text("""
                    SELECT 
                        pg_database_size(current_database()) as database_size,
                        pg_size_pretty(pg_database_size(current_database())) as database_size_pretty,
                        (SELECT count(*) FROM pg_stat_activity WHERE state = 'active') as active_connections,
                        (SELECT count(*) FROM pg_stat_activity) as total_connections,
                        (SELECT setting FROM pg_settings WHERE name = 'max_connections') as max_connections
                """)
                
                result = connection.execute(stats_query)
                row = result.fetchone()
                
                # Table statistics
                table_stats_query = text("""
                    SELECT 
                        schemaname,
                        tablename,
                        n_tup_ins as inserts,
                        n_tup_upd as updates,
                        n_tup_del as deletes,
                        n_live_tup as live_tuples,
                        n_dead_tup as dead_tuples,
                        last_vacuum,
                        last_autovacuum,
                        last_analyze,
                        last_autoanalyze
                    FROM pg_stat_user_tables
                    ORDER BY n_live_tup DESC
                    LIMIT 20
                """)
                
                table_result = connection.execute(table_stats_query)
                table_stats = [dict(row._mapping) for row in table_result.fetchall()]
                
                # Index usage statistics
                index_stats_query = text("""
                    SELECT 
                        schemaname,
                        tablename,
                        indexname,
                        idx_tup_read,
                        idx_tup_fetch,
                        idx_scan
                    FROM pg_stat_user_indexes
                    WHERE idx_scan > 0
                    ORDER BY idx_scan DESC
                    LIMIT 20
                """)
                
                index_result = connection.execute(index_stats_query)
                index_stats = [dict(row._mapping) for row in index_result.fetchall()]
                
                return {
                    "database_size": row[0] if row else 0,
                    "database_size_pretty": row[1] if row else "0 bytes",
                    "active_connections": row[2] if row else 0,
                    "total_connections": row[3] if row else 0,
                    "max_connections": int(row[4]) if row else 0,
                    "connection_usage_percent": round((row[3] / int(row[4])) * 100, 2) if row and row[4] else 0,
                    "table_statistics": table_stats,
                    "index_statistics": index_stats,
                    "timestamp": datetime.now(timezone.utc)
                }
                
        except Exception as e:
            logger.error(f"Failed to get database statistics: {str(e)}")
            return {
                "error": str(e),
                "timestamp": datetime.now(timezone.utc)
            }
    
    def check_database_performance(self) -> Dict[str, Any]:
        """Check database performance indicators"""
        try:
            with self.engine.connect() as connection:
                # Slow queries
                slow_queries_query = text("""
                    SELECT 
                        query,
                        calls,
                        total_time,
                        mean_time,
                        max_time,
                        rows
                    FROM pg_stat_statements 
                    WHERE mean_time > 1000  -- queries taking more than 1 second on average
                    ORDER BY mean_time DESC 
                    LIMIT 10
                """)
                
                try:
                    slow_result = connection.execute(slow_queries_query)
                    slow_queries = [dict(row._mapping) for row in slow_result.fetchall()]
                except Exception:
                    # pg_stat_statements might not be enabled
                    slow_queries = []
                
                # Lock information
                locks_query = text("""
                    SELECT 
                        mode,
                        count(*) as count
                    FROM pg_locks 
                    WHERE granted = true
                    GROUP BY mode
                    ORDER BY count DESC
                """)
                
                locks_result = connection.execute(locks_query)
                locks_info = [dict(row._mapping) for row in locks_result.fetchall()]
                
                # Cache hit ratio
                cache_query = text("""
                    SELECT 
                        sum(heap_blks_read) as heap_read,
                        sum(heap_blks_hit) as heap_hit,
                        sum(heap_blks_hit) / (sum(heap_blks_hit) + sum(heap_blks_read)) * 100 as cache_hit_ratio
                    FROM pg_statio_user_tables
                """)
                
                cache_result = connection.execute(cache_query)
                cache_row = cache_result.fetchone()
                
                return {
                    "slow_queries": slow_queries,
                    "locks_info": locks_info,
                    "cache_hit_ratio": round(float(cache_row[2]), 2) if cache_row and cache_row[2] else 0,
                    "heap_blocks_read": cache_row[0] if cache_row else 0,
                    "heap_blocks_hit": cache_row[1] if cache_row else 0,
                    "timestamp": datetime.now(timezone.utc)
                }
                
        except Exception as e:
            logger.error(f"Failed to check database performance: {str(e)}")
            return {
                "error": str(e),
                "timestamp": datetime.now(timezone.utc)
            }
    
    def create_database_backup_info(self) -> Dict[str, Any]:
        """Generate database backup information and commands"""
        backup_timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        backup_filename = f"scout_platform_backup_{backup_timestamp}.sql"
        
        # Parse database URL for backup commands
        from urllib.parse import urlparse
        parsed = urlparse(settings.DATABASE_URL)
        
        pg_dump_command = f"""
        pg_dump \\
            --host={parsed.hostname} \\
            --port={parsed.port or 5432} \\
            --username={parsed.username} \\
            --dbname={parsed.path[1:]} \\
            --verbose \\
            --clean \\
            --no-owner \\
            --no-privileges \\
            --format=custom \\
            --file={backup_filename}
        """
        
        pg_restore_command = f"""
        pg_restore \\
            --host={parsed.hostname} \\
            --port={parsed.port or 5432} \\
            --username={parsed.username} \\
            --dbname={parsed.path[1:]} \\
            --verbose \\
            --clean \\
            --no-owner \\
            --no-privileges \\
            {backup_filename}
        """
        
        return {
            "backup_filename": backup_filename,
            "backup_timestamp": backup_timestamp,
            "pg_dump_command": pg_dump_command.strip(),
            "pg_restore_command": pg_restore_command.strip(),
            "backup_location": f"{settings.BACKUP_STORAGE_PATH}/{backup_filename}" if hasattr(settings, 'BACKUP_STORAGE_PATH') else f"./{backup_filename}",
            "estimated_size": "Run: SELECT pg_size_pretty(pg_database_size(current_database()));"
        }
    
    def run_maintenance_tasks(self) -> Dict[str, Any]:
        """Run database maintenance tasks"""
        results = {
            "timestamp": datetime.now(timezone.utc),
            "tasks": []
        }
        
        try:
            with self.engine.connect() as connection:
                # VACUUM ANALYZE on all tables
                tables_query = text("""
                    SELECT schemaname, tablename 
                    FROM pg_tables 
                    WHERE schemaname = 'public'
                """)
                
                tables_result = connection.execute(tables_query)
                tables = tables_result.fetchall()
                
                for table in tables:
                    try:
                        # Note: VACUUM cannot be run inside a transaction
                        # This would need to be run separately with autocommit
                        vacuum_command = f"VACUUM ANALYZE {table[0]}.{table[1]}"
                        
                        results["tasks"].append({
                            "task": f"ANALYZE {table[1]}",
                            "status": "queued",
                            "command": vacuum_command,
                            "note": "VACUUM must be run with autocommit outside transaction"
                        })
                        
                        # Run ANALYZE (can be run in transaction)
                        connection.execute(text(f"ANALYZE {table[0]}.{table[1]}"))
                        
                        results["tasks"].append({
                            "task": f"ANALYZE {table[1]}",
                            "status": "completed",
                            "timestamp": datetime.now(timezone.utc)
                        })
                        
                    except Exception as e:
                        results["tasks"].append({
                            "task": f"ANALYZE {table[1]}",
                            "status": "failed",
                            "error": str(e)
                        })
                
                # Update table statistics
                connection.execute(text("ANALYZE"))
                results["tasks"].append({
                    "task": "UPDATE_STATISTICS",
                    "status": "completed",
                    "timestamp": datetime.now(timezone.utc)
                })
                
        except Exception as e:
            logger.error(f"Database maintenance failed: {str(e)}")
            results["error"] = str(e)
        
        return results
    
    def check_database_security(self) -> Dict[str, Any]:
        """Check database security configuration"""
        try:
            with self.engine.connect() as connection:
                # Check user privileges
                privileges_query = text("""
                    SELECT 
                        r.rolname,
                        r.rolsuper,
                        r.rolinherit,
                        r.rolcreaterole,
                        r.rolcreatedb,
                        r.rolcanlogin,
                        r.rolreplication,
                        r.rolconnlimit,
                        r.rolvaliduntil
                    FROM pg_roles r
                    WHERE r.rolcanlogin = true
                    ORDER BY r.rolname
                """)
                
                privileges_result = connection.execute(privileges_query)
                user_privileges = [dict(row._mapping) for row in privileges_result.fetchall()]
                
                # Check database configuration
                security_config_query = text("""
                    SELECT name, setting, category, short_desc
                    FROM pg_settings 
                    WHERE name IN (
                        'ssl', 'log_connections', 'log_disconnections', 
                        'log_statement', 'password_encryption', 'row_security'
                    )
                    ORDER BY name
                """)
                
                config_result = connection.execute(security_config_query)
                security_config = [dict(row._mapping) for row in config_result.fetchall()]
                
                # Check for default passwords (basic check)
                weak_passwords_query = text("""
                    SELECT rolname 
                    FROM pg_roles 
                    WHERE rolcanlogin = true 
                    AND rolname IN ('postgres', 'admin', 'user', 'test')
                """)
                
                weak_result = connection.execute(weak_passwords_query)
                potential_weak_users = [row[0] for row in weak_result.fetchall()]
                
                return {
                    "user_privileges": user_privileges,
                    "security_configuration": security_config,
                    "potential_security_issues": {
                        "users_with_default_names": potential_weak_users,
                        "superusers": [u["rolname"] for u in user_privileges if u["rolsuper"]],
                        "users_without_expiry": [u["rolname"] for u in user_privileges if not u["rolvaliduntil"]]
                    },
                    "recommendations": [
                        "Enable SSL connections",
                        "Enable connection logging",
                        "Use strong, unique passwords",
                        "Implement role-based access control",
                        "Set password expiry dates",
                        "Regularly audit user privileges"
                    ],
                    "timestamp": datetime.now(timezone.utc)
                }
                
        except Exception as e:
            logger.error(f"Database security check failed: {str(e)}")
            return {
                "error": str(e),
                "timestamp": datetime.now(timezone.utc)
            }
    
    def close(self):
        """Close database connections"""
        try:
            if self.engine:
                self.engine.dispose()
            if self.redis_client:
                self.redis_client.close()
            logger.info("Database connections closed")
        except Exception as e:
            logger.error(f"Error closing database connections: {str(e)}")

# Global database manager instance
db_manager = DatabaseManager()

def get_database_manager() -> DatabaseManager:
    """Get database manager instance"""
    return db_manager

# Dependency for FastAPI endpoints
def get_db_session() -> Session:
    """Get database session for dependency injection"""
    session = db_manager.session_factory()
    try:
        yield session
    finally:
        session.close()

# Migration utilities
class MigrationManager:
    """Database migration management"""
    
    @staticmethod
    def check_migration_status() -> Dict[str, Any]:
        """Check current migration status"""
        try:
            with db_manager.engine.connect() as connection:
                # Check if Alembic version table exists
                version_table_query = text("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                        AND table_name = 'alembic_version'
                    )
                """)
                
                result = connection.execute(version_table_query)
                has_version_table = result.fetchone()[0]
                
                if has_version_table:
                    # Get current version
                    version_query = text("SELECT version_num FROM alembic_version")
                    version_result = connection.execute(version_query)
                    current_version = version_result.fetchone()
                    current_version = current_version[0] if current_version else None
                else:
                    current_version = None
                
                # Get table count
                table_count_query = text("""
                    SELECT count(*) 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public'
                """)
                
                table_result = connection.execute(table_count_query)
                table_count = table_result.fetchone()[0]
                
                return {
                    "has_migration_table": has_version_table,
                    "current_version": current_version,
                    "table_count": table_count,
                    "migration_directory": "backend/alembic/versions",
                    "status": "initialized" if has_version_table else "not_initialized",
                    "timestamp": datetime.now(timezone.utc)
                }
                
        except Exception as e:
            logger.error(f"Failed to check migration status: {str(e)}")
            return {
                "error": str(e),
                "timestamp": datetime.now(timezone.utc)
            }

# Initialize migration manager
migration_manager = MigrationManager()