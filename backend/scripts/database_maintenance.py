#!/usr/bin/env python3
"""
Database Backup and Maintenance Script for S.C.O.U.T. Platform
Handles automated backups, maintenance tasks, and monitoring
"""

import os
import sys
import subprocess
import argparse
import logging
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any
from pathlib import Path
import json
import boto3
from urllib.parse import urlparse

# Add the parent directory to Python path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings
from app.core.database import engine, check_database_health
from app.core.database_manager import db_manager, migration_manager

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('database_maintenance.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class DatabaseBackupManager:
    """Manages database backups and restoration"""
    
    def __init__(self):
        self.backup_dir = Path(getattr(settings, 'BACKUP_STORAGE_PATH', './backups'))
        self.backup_dir.mkdir(exist_ok=True)
        
        # Parse database URL
        parsed_url = urlparse(settings.DATABASE_URL)
        self.db_config = {
            'host': parsed_url.hostname,
            'port': parsed_url.port or 5432,
            'username': parsed_url.username,
            'password': parsed_url.password,
            'database': parsed_url.path[1:] if parsed_url.path else 'postgres'
        }
        
        # Initialize S3 client if configured
        self.s3_client = None
        if hasattr(settings, 'AWS_S3_BACKUP_BUCKET'):
            try:
                self.s3_client = boto3.client(
                    's3',
                    aws_access_key_id=getattr(settings, 'AWS_ACCESS_KEY_ID', None),
                    aws_secret_access_key=getattr(settings, 'AWS_SECRET_ACCESS_KEY', None),
                    region_name=getattr(settings, 'AWS_DEFAULT_REGION', 'us-east-1')
                )
            except Exception as e:
                logger.warning(f"Failed to initialize S3 client: {str(e)}")
    
    def create_backup(self, backup_type: str = "full") -> Dict[str, Any]:
        """Create database backup"""
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        backup_filename = f"scout_platform_{backup_type}_backup_{timestamp}.sql"
        backup_path = self.backup_dir / backup_filename
        
        try:
            logger.info(f"Starting {backup_type} backup: {backup_filename}")
            
            # Set environment for pg_dump
            env = os.environ.copy()
            if self.db_config['password']:
                env['PGPASSWORD'] = self.db_config['password']
            
            # Build pg_dump command
            cmd = [
                'pg_dump',
                '--host', self.db_config['host'],
                '--port', str(self.db_config['port']),
                '--username', self.db_config['username'],
                '--dbname', self.db_config['database'],
                '--verbose',
                '--clean',
                '--no-owner',
                '--no-privileges',
                '--format=custom',
                '--file', str(backup_path)
            ]
            
            # Add additional options based on backup type
            if backup_type == "schema_only":
                cmd.append('--schema-only')
            elif backup_type == "data_only":
                cmd.append('--data-only')
            
            # Execute backup
            start_time = time.time()
            result = subprocess.run(cmd, env=env, capture_output=True, text=True)
            backup_duration = time.time() - start_time
            
            if result.returncode == 0:
                backup_size = backup_path.stat().st_size
                
                backup_info = {
                    "status": "success",
                    "filename": backup_filename,
                    "path": str(backup_path),
                    "size_bytes": backup_size,
                    "size_mb": round(backup_size / (1024 * 1024), 2),
                    "duration_seconds": round(backup_duration, 2),
                    "timestamp": timestamp,
                    "backup_type": backup_type,
                    "database": self.db_config['database']
                }
                
                # Upload to S3 if configured
                if self.s3_client and hasattr(settings, 'AWS_S3_BACKUP_BUCKET'):
                    try:
                        s3_key = f"database_backups/{backup_filename}"
                        self.s3_client.upload_file(
                            str(backup_path),
                            settings.AWS_S3_BACKUP_BUCKET,
                            s3_key
                        )
                        backup_info["s3_location"] = f"s3://{settings.AWS_S3_BACKUP_BUCKET}/{s3_key}"
                        logger.info(f"Backup uploaded to S3: {backup_info['s3_location']}")
                    except Exception as e:
                        logger.warning(f"Failed to upload backup to S3: {str(e)}")
                        backup_info["s3_error"] = str(e)
                
                logger.info(f"Backup completed successfully: {backup_info}")
                return backup_info
                
            else:
                error_msg = result.stderr or "Unknown error"
                logger.error(f"Backup failed: {error_msg}")
                return {
                    "status": "failed",
                    "error": error_msg,
                    "command": " ".join(cmd),
                    "timestamp": timestamp
                }
                
        except Exception as e:
            logger.error(f"Backup operation failed: {str(e)}")
            return {
                "status": "failed",
                "error": str(e),
                "timestamp": timestamp
            }
    
    def restore_backup(self, backup_path: str, drop_existing: bool = False) -> Dict[str, Any]:
        """Restore database from backup"""
        try:
            logger.info(f"Starting database restore from: {backup_path}")
            
            # Set environment for pg_restore
            env = os.environ.copy()
            if self.db_config['password']:
                env['PGPASSWORD'] = self.db_config['password']
            
            # Build pg_restore command
            cmd = [
                'pg_restore',
                '--host', self.db_config['host'],
                '--port', str(self.db_config['port']),
                '--username', self.db_config['username'],
                '--dbname', self.db_config['database'],
                '--verbose',
                '--no-owner',
                '--no-privileges'
            ]
            
            if drop_existing:
                cmd.append('--clean')
            
            cmd.append(backup_path)
            
            # Execute restore
            start_time = time.time()
            result = subprocess.run(cmd, env=env, capture_output=True, text=True)
            restore_duration = time.time() - start_time
            
            if result.returncode == 0:
                restore_info = {
                    "status": "success",
                    "backup_file": backup_path,
                    "duration_seconds": round(restore_duration, 2),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "database": self.db_config['database'],
                    "drop_existing": drop_existing
                }
                
                logger.info(f"Restore completed successfully: {restore_info}")
                return restore_info
                
            else:
                error_msg = result.stderr or "Unknown error"
                logger.error(f"Restore failed: {error_msg}")
                return {
                    "status": "failed",
                    "error": error_msg,
                    "command": " ".join(cmd),
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                
        except Exception as e:
            logger.error(f"Restore operation failed: {str(e)}")
            return {
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
    
    def list_backups(self) -> List[Dict[str, Any]]:
        """List available backups"""
        backups = []
        
        try:
            # Local backups
            for backup_file in self.backup_dir.glob("scout_platform_*_backup_*.sql"):
                stat = backup_file.stat()
                backups.append({
                    "filename": backup_file.name,
                    "path": str(backup_file),
                    "size_bytes": stat.st_size,
                    "size_mb": round(stat.st_size / (1024 * 1024), 2),
                    "created": datetime.fromtimestamp(stat.st_ctime, tz=timezone.utc).isoformat(),
                    "location": "local"
                })
            
            # S3 backups (if configured)
            if self.s3_client and hasattr(settings, 'AWS_S3_BACKUP_BUCKET'):
                try:
                    response = self.s3_client.list_objects_v2(
                        Bucket=settings.AWS_S3_BACKUP_BUCKET,
                        Prefix="database_backups/"
                    )
                    
                    for obj in response.get('Contents', []):
                        backups.append({
                            "filename": os.path.basename(obj['Key']),
                            "path": f"s3://{settings.AWS_S3_BACKUP_BUCKET}/{obj['Key']}",
                            "size_bytes": obj['Size'],
                            "size_mb": round(obj['Size'] / (1024 * 1024), 2),
                            "created": obj['LastModified'].isoformat(),
                            "location": "s3"
                        })
                        
                except Exception as e:
                    logger.warning(f"Failed to list S3 backups: {str(e)}")
            
            # Sort by creation date
            backups.sort(key=lambda x: x['created'], reverse=True)
            
        except Exception as e:
            logger.error(f"Failed to list backups: {str(e)}")
        
        return backups
    
    def cleanup_old_backups(self, keep_days: int = 30) -> Dict[str, Any]:
        """Clean up old backup files"""
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=keep_days)
        deleted_files = []
        errors = []
        
        try:
            # Clean local backups
            for backup_file in self.backup_dir.glob("scout_platform_*_backup_*.sql"):
                file_date = datetime.fromtimestamp(backup_file.stat().st_ctime, tz=timezone.utc)
                
                if file_date < cutoff_date:
                    try:
                        backup_file.unlink()
                        deleted_files.append({
                            "filename": backup_file.name,
                            "location": "local",
                            "created": file_date.isoformat()
                        })
                    except Exception as e:
                        errors.append(f"Failed to delete {backup_file.name}: {str(e)}")
            
            # Clean S3 backups (if configured)
            if self.s3_client and hasattr(settings, 'AWS_S3_BACKUP_BUCKET'):
                try:
                    response = self.s3_client.list_objects_v2(
                        Bucket=settings.AWS_S3_BACKUP_BUCKET,
                        Prefix="database_backups/"
                    )
                    
                    for obj in response.get('Contents', []):
                        if obj['LastModified'].replace(tzinfo=timezone.utc) < cutoff_date:
                            try:
                                self.s3_client.delete_object(
                                    Bucket=settings.AWS_S3_BACKUP_BUCKET,
                                    Key=obj['Key']
                                )
                                deleted_files.append({
                                    "filename": os.path.basename(obj['Key']),
                                    "location": "s3",
                                    "created": obj['LastModified'].isoformat()
                                })
                            except Exception as e:
                                errors.append(f"Failed to delete S3 object {obj['Key']}: {str(e)}")
                                
                except Exception as e:
                    errors.append(f"Failed to list S3 backups for cleanup: {str(e)}")
            
            return {
                "status": "completed",
                "deleted_count": len(deleted_files),
                "deleted_files": deleted_files,
                "errors": errors,
                "cutoff_date": cutoff_date.isoformat(),
                "keep_days": keep_days
            }
            
        except Exception as e:
            logger.error(f"Backup cleanup failed: {str(e)}")
            return {
                "status": "failed",
                "error": str(e),
                "deleted_files": deleted_files,
                "errors": errors
            }

class DatabaseMaintenanceManager:
    """Manages database maintenance tasks"""
    
    def __init__(self):
        self.backup_manager = DatabaseBackupManager()
    
    def run_full_maintenance(self) -> Dict[str, Any]:
        """Run complete maintenance routine"""
        maintenance_start = time.time()
        results = {
            "start_time": datetime.now(timezone.utc).isoformat(),
            "tasks": {}
        }
        
        try:
            # Initialize database manager
            db_manager.initialize()
            
            # 1. Health check
            logger.info("Running database health check...")
            results["tasks"]["health_check"] = check_database_health()
            
            # 2. Database statistics
            logger.info("Collecting database statistics...")
            results["tasks"]["database_stats"] = db_manager.get_database_stats()
            
            # 3. Performance check
            logger.info("Checking database performance...")
            results["tasks"]["performance_check"] = db_manager.check_database_performance()
            
            # 4. Security check
            logger.info("Running security audit...")
            results["tasks"]["security_check"] = db_manager.check_database_security()
            
            # 5. Migration status
            logger.info("Checking migration status...")
            results["tasks"]["migration_status"] = migration_manager.check_migration_status()
            
            # 6. Create backup
            logger.info("Creating database backup...")
            results["tasks"]["backup"] = self.backup_manager.create_backup("full")
            
            # 7. Maintenance tasks
            logger.info("Running maintenance tasks...")
            results["tasks"]["maintenance"] = db_manager.run_maintenance_tasks()
            
            # 8. Cleanup old backups
            logger.info("Cleaning up old backups...")
            results["tasks"]["backup_cleanup"] = self.backup_manager.cleanup_old_backups(
                keep_days=getattr(settings, 'BACKUP_RETENTION_DAYS', 30)
            )
            
            results["duration_seconds"] = round(time.time() - maintenance_start, 2)
            results["end_time"] = datetime.now(timezone.utc).isoformat()
            results["status"] = "completed"
            
            logger.info(f"Full maintenance completed in {results['duration_seconds']} seconds")
            
        except Exception as e:
            results["status"] = "failed"
            results["error"] = str(e)
            results["duration_seconds"] = round(time.time() - maintenance_start, 2)
            results["end_time"] = datetime.now(timezone.utc).isoformat()
            logger.error(f"Maintenance failed: {str(e)}")
        
        finally:
            db_manager.close()
        
        return results

def main():
    """Main CLI interface"""
    parser = argparse.ArgumentParser(description="S.C.O.U.T. Database Management")
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Backup commands
    backup_parser = subparsers.add_parser('backup', help='Backup operations')
    backup_parser.add_argument('--type', choices=['full', 'schema_only', 'data_only'], 
                              default='full', help='Backup type')
    
    # Restore commands
    restore_parser = subparsers.add_parser('restore', help='Restore operations')
    restore_parser.add_argument('backup_file', help='Path to backup file')
    restore_parser.add_argument('--drop-existing', action='store_true', 
                               help='Drop existing data before restore')
    
    # List backups
    subparsers.add_parser('list-backups', help='List available backups')
    
    # Health check
    subparsers.add_parser('health', help='Check database health')
    
    # Maintenance
    maintenance_parser = subparsers.add_parser('maintenance', help='Run maintenance tasks')
    maintenance_parser.add_argument('--full', action='store_true', help='Run full maintenance')
    
    # Migration status
    subparsers.add_parser('migration-status', help='Check migration status')
    
    args = parser.parse_args()
    
    if args.command == 'backup':
        backup_manager = DatabaseBackupManager()
        result = backup_manager.create_backup(args.type)
        print(json.dumps(result, indent=2))
        
    elif args.command == 'restore':
        backup_manager = DatabaseBackupManager()
        result = backup_manager.restore_backup(args.backup_file, args.drop_existing)
        print(json.dumps(result, indent=2))
        
    elif args.command == 'list-backups':
        backup_manager = DatabaseBackupManager()
        backups = backup_manager.list_backups()
        print(json.dumps(backups, indent=2))
        
    elif args.command == 'health':
        result = check_database_health()
        print(json.dumps(result, indent=2))
        
    elif args.command == 'maintenance':
        maintenance_manager = DatabaseMaintenanceManager()
        if args.full:
            result = maintenance_manager.run_full_maintenance()
        else:
            db_manager.initialize()
            result = db_manager.run_maintenance_tasks()
            db_manager.close()
        print(json.dumps(result, indent=2))
        
    elif args.command == 'migration-status':
        result = migration_manager.check_migration_status()
        print(json.dumps(result, indent=2))
        
    else:
        parser.print_help()

if __name__ == "__main__":
    main()