"""
Audit Log Model for Security and Compliance
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Enum as SQLEnum, JSON
from sqlalchemy.orm import relationship
import enum

from app.core.database import Base


class AuditAction(enum.Enum):
    # Authentication
    LOGIN = "login"
    LOGOUT = "logout"
    LOGIN_FAILED = "login_failed"
    PASSWORD_CHANGED = "password_changed"
    PASSWORD_RESET = "password_reset"
    MFA_ENABLED = "mfa_enabled"
    MFA_DISABLED = "mfa_disabled"
    
    # User Management
    USER_CREATED = "user_created"
    USER_UPDATED = "user_updated"
    USER_DELETED = "user_deleted"
    USER_ROLE_CHANGED = "user_role_changed"
    
    # Company Management
    COMPANY_CREATED = "company_created"
    COMPANY_UPDATED = "company_updated"
    COMPANY_DELETED = "company_deleted"
    
    # Subscription Management
    SUBSCRIPTION_CREATED = "subscription_created"
    SUBSCRIPTION_UPDATED = "subscription_updated"
    SUBSCRIPTION_CANCELLED = "subscription_cancelled"
    PAYMENT_SUCCESS = "payment_success"
    PAYMENT_FAILED = "payment_failed"
    
    # Job Management
    JOB_CREATED = "job_created"
    JOB_UPDATED = "job_updated"
    JOB_DELETED = "job_deleted"
    JOB_PUBLISHED = "job_published"
    JOB_CLOSED = "job_closed"
    
    # Candidate Management
    CANDIDATE_APPLIED = "candidate_applied"
    CANDIDATE_UPDATED = "candidate_updated"
    CANDIDATE_STATUS_CHANGED = "candidate_status_changed"
    
    # Assessment
    ASSESSMENT_STARTED = "assessment_started"
    ASSESSMENT_COMPLETED = "assessment_completed"
    ASSESSMENT_EXPIRED = "assessment_expired"
    
    # File Management
    FILE_UPLOADED = "file_uploaded"
    FILE_DOWNLOADED = "file_downloaded"
    FILE_DELETED = "file_deleted"
    
    # Security Events
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    UNAUTHORIZED_ACCESS = "unauthorized_access"
    DATA_EXPORT = "data_export"
    
    # System Events
    SYSTEM_BACKUP = "system_backup"
    SYSTEM_MAINTENANCE = "system_maintenance"
    API_ACCESS = "api_access"


class AuditSeverity(enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AuditLog(Base):
    """
    Comprehensive audit logging for security and compliance
    Tracks all significant system activities
    """
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    
    # Event Details
    action = Column(SQLEnum(AuditAction), nullable=False, index=True)
    severity = Column(SQLEnum(AuditSeverity), default=AuditSeverity.LOW, index=True)
    description = Column(Text)
    
    # Actor Information
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    user_email = Column(String(255))  # Denormalized for easier querying
    user_role = Column(String(50))
    
    # Tenant Information (Multi-tenant)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=True, index=True)
    
    # Target Entity
    entity_type = Column(String(100))  # e.g., "user", "job", "candidate"
    entity_id = Column(Integer)
    entity_name = Column(String(255))  # Denormalized entity identifier
    
    # Request Context
    ip_address = Column(String(45), index=True)
    user_agent = Column(Text)
    request_method = Column(String(10))
    request_path = Column(String(500))
    session_id = Column(String(255))
    
    # Additional Data
    metadata = Column(JSON)  # Additional structured data
    changes = Column(JSON)  # Before/after changes for updates
    
    # Success/Failure
    success = Column(Boolean, default=True, index=True)
    error_message = Column(Text)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Relationships
    user = relationship("User")
    company = relationship("Company")
    
    def __repr__(self):
        return f"<AuditLog {self.action.value} by {self.user_email}>"
    
    @classmethod
    def log_event(cls, session, action: AuditAction, user_id=None, company_id=None, 
                  description=None, entity_type=None, entity_id=None, entity_name=None,
                  ip_address=None, user_agent=None, request_method=None, request_path=None,
                  session_id=None, metadata=None, changes=None, success=True, 
                  error_message=None, severity=AuditSeverity.LOW):
        """
        Convenience method to create audit log entries
        """
        # Get user details if user_id provided
        user_email = None
        user_role = None
        if user_id:
            user = session.query(User).filter(User.id == user_id).first()
            if user:
                user_email = user.email
                user_role = user.role.value if user.role else None
        
        audit_log = cls(
            action=action,
            severity=severity,
            description=description,
            user_id=user_id,
            user_email=user_email,
            user_role=user_role,
            company_id=company_id,
            entity_type=entity_type,
            entity_id=entity_id,
            entity_name=entity_name,
            ip_address=ip_address,
            user_agent=user_agent,
            request_method=request_method,
            request_path=request_path,
            session_id=session_id,
            metadata=metadata,
            changes=changes,
            success=success,
            error_message=error_message
        )
        
        session.add(audit_log)
        return audit_log
    
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            "id": self.id,
            "action": self.action.value,
            "severity": self.severity.value,
            "description": self.description,
            "user_id": self.user_id,
            "user_email": self.user_email,
            "user_role": self.user_role,
            "company_id": self.company_id,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "entity_name": self.entity_name,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "request_method": self.request_method,
            "request_path": self.request_path,
            "session_id": self.session_id,
            "metadata": self.metadata,
            "changes": self.changes,
            "success": self.success,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat(),
        }