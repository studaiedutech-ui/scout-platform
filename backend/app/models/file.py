"""
File Management Model for Document Storage
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Text, Enum as SQLEnum, BigInteger
from sqlalchemy.orm import relationship
import enum

from app.core.database import Base


class FileType(enum.Enum):
    RESUME = "resume"
    COVER_LETTER = "cover_letter"
    PORTFOLIO = "portfolio"
    ASSESSMENT_UPLOAD = "assessment_upload"
    COMPANY_LOGO = "company_logo"
    USER_AVATAR = "user_avatar"
    OTHER = "other"


class FileStatus(enum.Enum):
    UPLOADING = "uploading"
    ACTIVE = "active"
    DELETED = "deleted"
    VIRUS_DETECTED = "virus_detected"
    PROCESSING = "processing"


class File(Base):
    """
    File storage model for document management
    Supports multi-tenant file isolation
    """
    __tablename__ = "files"

    id = Column(Integer, primary_key=True, index=True)
    
    # File Identification
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    file_hash = Column(String(64), index=True)  # SHA-256 hash for deduplication
    
    # File Details
    file_type = Column(SQLEnum(FileType), nullable=False, index=True)
    mime_type = Column(String(100))
    file_size = Column(BigInteger)  # Size in bytes
    
    # Storage
    storage_path = Column(String(500), nullable=False)  # Path in storage system
    storage_provider = Column(String(50), default="azure_blob")  # azure_blob, s3, local
    public_url = Column(String(500))  # Public access URL if applicable
    
    # Access Control (Multi-tenant)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=True, index=True)
    uploaded_by = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # Associated Entities
    candidate_id = Column(Integer, ForeignKey("candidates.id"), nullable=True, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=True, index=True)
    assessment_id = Column(Integer, ForeignKey("assessments.id"), nullable=True, index=True)
    
    # Status and Security
    status = Column(SQLEnum(FileStatus), default=FileStatus.UPLOADING, index=True)
    is_public = Column(Boolean, default=False)
    virus_scan_status = Column(String(50))  # clean, infected, pending
    virus_scan_at = Column(DateTime)
    
    # Metadata
    metadata = Column(Text)  # JSON string for additional metadata
    description = Column(Text)
    tags = Column(String(500))  # Comma-separated tags
    
    # Expiration (for temporary files)
    expires_at = Column(DateTime)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = Column(DateTime)
    
    # Relationships
    company = relationship("Company")
    uploaded_by_user = relationship("User")
    candidate = relationship("Candidate")
    job = relationship("Job")
    assessment = relationship("Assessment")
    
    def __repr__(self):
        return f"<File {self.filename}>"
    
    @property
    def is_active(self):
        """Check if file is active and accessible"""
        return self.status == FileStatus.ACTIVE and not self.deleted_at
    
    @property
    def is_expired(self):
        """Check if file has expired"""
        if not self.expires_at:
            return False
        return datetime.utcnow() > self.expires_at
    
    @property
    def file_size_mb(self):
        """Get file size in MB"""
        if not self.file_size:
            return 0
        return round(self.file_size / (1024 * 1024), 2)
    
    @property
    def is_image(self):
        """Check if file is an image"""
        image_types = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
        return self.mime_type in image_types
    
    @property
    def is_document(self):
        """Check if file is a document"""
        doc_types = [
            'application/pdf',
            'application/msword',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'text/plain'
        ]
        return self.mime_type in doc_types
    
    def generate_public_url(self, base_url=""):
        """Generate public access URL"""
        if self.is_public and self.public_url:
            return self.public_url
        return f"{base_url}/api/files/{self.id}/download"
    
    def to_dict(self, include_sensitive=False):
        """Convert to dictionary for API responses"""
        data = {
            "id": self.id,
            "filename": self.filename,
            "original_filename": self.original_filename,
            "file_type": self.file_type.value,
            "mime_type": self.mime_type,
            "file_size": self.file_size,
            "file_size_mb": self.file_size_mb,
            "is_image": self.is_image,
            "is_document": self.is_document,
            "status": self.status.value,
            "is_public": self.is_public,
            "description": self.description,
            "tags": self.tags.split(',') if self.tags else [],
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "is_active": self.is_active,
            "is_expired": self.is_expired,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
        
        if include_sensitive:
            data.update({
                "file_hash": self.file_hash,
                "storage_path": self.storage_path,
                "storage_provider": self.storage_provider,
                "public_url": self.public_url,
                "company_id": self.company_id,
                "uploaded_by": self.uploaded_by,
                "candidate_id": self.candidate_id,
                "job_id": self.job_id,
                "assessment_id": self.assessment_id,
                "virus_scan_status": self.virus_scan_status,
                "virus_scan_at": self.virus_scan_at.isoformat() if self.virus_scan_at else None,
                "metadata": self.metadata,
                "deleted_at": self.deleted_at.isoformat() if self.deleted_at else None,
            })
            
        return data