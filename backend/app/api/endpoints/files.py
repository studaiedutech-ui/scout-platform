"""
File Upload API Endpoints
Handles document uploads for resumes, portfolios, etc.
"""

import os
import hashlib
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File as FastAPIFile, Form
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel
from datetime import datetime

from app.core.database import get_db
from app.core.security import get_current_active_user
from app.core.tenant import get_current_tenant_user, get_current_company, check_subscription_limits
from app.models.user import User
from app.models.file import File, FileType, FileStatus
from app.models.candidate import Candidate
from app.models.job import Job
from app.models.assessment import Assessment

router = APIRouter()


# Pydantic Models
class FileResponse(BaseModel):
    id: int
    filename: str
    original_filename: str
    file_type: str
    file_size: int
    file_size_mb: float
    mime_type: Optional[str]
    is_public: bool
    status: str
    created_at: str
    public_url: Optional[str]

    class Config:
        from_attributes = True


class FileUploadResponse(BaseModel):
    file: FileResponse
    message: str


# Configuration
UPLOAD_DIR = "uploads"
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_EXTENSIONS = {
    'resume': ['.pdf', '.doc', '.docx', '.txt'],
    'portfolio': ['.pdf', '.doc', '.docx', '.zip', '.png', '.jpg', '.jpeg'],
    'cover_letter': ['.pdf', '.doc', '.docx', '.txt'],
    'assessment_upload': ['.pdf', '.doc', '.docx', '.txt', '.zip', '.png', '.jpg', '.jpeg'],
    'company_logo': ['.png', '.jpg', '.jpeg', '.svg'],
    'user_avatar': ['.png', '.jpg', '.jpeg']
}

ALLOWED_MIME_TYPES = {
    'application/pdf',
    'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'text/plain',
    'image/png',
    'image/jpeg',
    'image/jpg',
    'image/svg+xml',
    'application/zip'
}


def get_file_hash(content: bytes) -> str:
    """Generate SHA-256 hash of file content"""
    return hashlib.sha256(content).hexdigest()


def validate_file(file: UploadFile, file_type: str) -> None:
    """Validate uploaded file"""
    # Check file size
    if hasattr(file, 'size') and file.size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File size exceeds maximum allowed size of {MAX_FILE_SIZE / (1024*1024):.1f}MB"
        )
    
    # Check file extension
    if file.filename:
        file_ext = os.path.splitext(file.filename.lower())[1]
        allowed_exts = ALLOWED_EXTENSIONS.get(file_type, [])
        if allowed_exts and file_ext not in allowed_exts:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File type not allowed. Allowed types: {', '.join(allowed_exts)}"
            )
    
    # Check MIME type
    if file.content_type and file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"MIME type not allowed: {file.content_type}"
        )


def save_file(file_content: bytes, filename: str, file_type: str, company_id: int) -> str:
    """Save file to storage and return storage path"""
    # Create upload directory structure
    company_dir = os.path.join(UPLOAD_DIR, str(company_id), file_type)
    os.makedirs(company_dir, exist_ok=True)
    
    # Generate unique filename
    file_hash = get_file_hash(file_content)
    file_ext = os.path.splitext(filename)[1]
    unique_filename = f"{file_hash}{file_ext}"
    
    file_path = os.path.join(company_dir, unique_filename)
    
    # Save file
    with open(file_path, 'wb') as f:
        f.write(file_content)
    
    return file_path


@router.post("/upload", response_model=FileUploadResponse)
async def upload_file(
    file: UploadFile = FastAPIFile(...),
    file_type: str = Form(...),
    description: Optional[str] = Form(None),
    candidate_id: Optional[int] = Form(None),
    job_id: Optional[int] = Form(None),
    assessment_id: Optional[int] = Form(None),
    is_public: bool = Form(False),
    current_user: User = Depends(get_current_tenant_user),
    db: Session = Depends(get_db)
):
    """
    Upload a file (resume, portfolio, etc.)
    """
    company = get_current_company()
    
    # Validate file type
    try:
        file_type_enum = FileType(file_type)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file type"
        )
    
    # Check subscription limits for storage
    current_storage = db.query(
        func.sum(File.file_size)
    ).filter(
        File.company_id == company.id,
        File.status == FileStatus.ACTIVE
    ).scalar() or 0
    
    current_storage_gb = current_storage / (1024 * 1024 * 1024)
    check_subscription_limits("storage", current_storage_gb)
    
    # Validate file
    validate_file(file, file_type)
    
    # Read file content
    file_content = await file.read()
    actual_size = len(file_content)
    
    # Additional size check
    if actual_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File size exceeds maximum allowed size of {MAX_FILE_SIZE / (1024*1024):.1f}MB"
        )
    
    # Save file to storage
    storage_path = save_file(file_content, file.filename, file_type, company.id)
    
    # Create file record
    file_hash = get_file_hash(file_content)
    
    # Generate unique filename for storage
    file_ext = os.path.splitext(file.filename)[1]
    stored_filename = f"{file_hash}{file_ext}"
    
    db_file = File(
        filename=stored_filename,
        original_filename=file.filename,
        file_hash=file_hash,
        file_type=file_type_enum,
        mime_type=file.content_type,
        file_size=actual_size,
        storage_path=storage_path,
        storage_provider="local",
        company_id=company.id,
        uploaded_by=current_user.id,
        candidate_id=candidate_id,
        job_id=job_id,
        assessment_id=assessment_id,
        status=FileStatus.ACTIVE,
        is_public=is_public,
        description=description
    )
    
    db.add(db_file)
    db.commit()
    db.refresh(db_file)
    
    # Generate public URL if file is public
    public_url = None
    if is_public:
        public_url = f"/api/files/{db_file.id}/download"
    
    file_response = FileResponse(
        id=db_file.id,
        filename=db_file.filename,
        original_filename=db_file.original_filename,
        file_type=db_file.file_type.value,
        file_size=db_file.file_size,
        file_size_mb=db_file.file_size_mb,
        mime_type=db_file.mime_type,
        is_public=db_file.is_public,
        status=db_file.status.value,
        created_at=db_file.created_at.isoformat(),
        public_url=public_url
    )
    
    return FileUploadResponse(
        file=file_response,
        message="File uploaded successfully"
    )


@router.get("/", response_model=List[FileResponse])
async def list_files(
    file_type: Optional[str] = None,
    candidate_id: Optional[int] = None,
    job_id: Optional[int] = None,
    assessment_id: Optional[int] = None,
    current_user: User = Depends(get_current_tenant_user),
    db: Session = Depends(get_db)
):
    """
    List files uploaded by the current user's company
    """
    company = get_current_company()
    
    query = db.query(File).filter(
        File.company_id == company.id,
        File.status == FileStatus.ACTIVE
    )
    
    # Apply filters
    if file_type:
        try:
            file_type_enum = FileType(file_type)
            query = query.filter(File.file_type == file_type_enum)
        except ValueError:
            pass  # Invalid file type, ignore filter
    
    if candidate_id:
        query = query.filter(File.candidate_id == candidate_id)
    
    if job_id:
        query = query.filter(File.job_id == job_id)
    
    if assessment_id:
        query = query.filter(File.assessment_id == assessment_id)
    
    files = query.order_by(File.created_at.desc()).all()
    
    result = []
    for file in files:
        public_url = None
        if file.is_public:
            public_url = f"/api/files/{file.id}/download"
        
        result.append(FileResponse(
            id=file.id,
            filename=file.filename,
            original_filename=file.original_filename,
            file_type=file.file_type.value,
            file_size=file.file_size,
            file_size_mb=file.file_size_mb,
            mime_type=file.mime_type,
            is_public=file.is_public,
            status=file.status.value,
            created_at=file.created_at.isoformat(),
            public_url=public_url
        ))
    
    return result


@router.get("/{file_id}", response_model=FileResponse)
async def get_file_details(
    file_id: int,
    current_user: User = Depends(get_current_tenant_user),
    db: Session = Depends(get_db)
):
    """
    Get details of a specific file
    """
    company = get_current_company()
    
    file = db.query(File).filter(
        File.id == file_id,
        File.company_id == company.id,
        File.status == FileStatus.ACTIVE
    ).first()
    
    if not file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )
    
    public_url = None
    if file.is_public:
        public_url = f"/api/files/{file.id}/download"
    
    return FileResponse(
        id=file.id,
        filename=file.filename,
        original_filename=file.original_filename,
        file_type=file.file_type.value,
        file_size=file.file_size,
        file_size_mb=file.file_size_mb,
        mime_type=file.mime_type,
        is_public=file.is_public,
        status=file.status.value,
        created_at=file.created_at.isoformat(),
        public_url=public_url
    )


@router.get("/{file_id}/download")
async def download_file(
    file_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Download a file
    """
    from fastapi.responses import FileResponse as FastAPIFileResponse
    
    # Get file record
    file = db.query(File).filter(
        File.id == file_id,
        File.status == FileStatus.ACTIVE
    ).first()
    
    if not file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )
    
    # Check access permissions
    if not file.is_public:
        # Only allow access if user belongs to the same company or is super admin
        if (current_user.company_id != file.company_id and 
            current_user.role.value != "super_admin"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
    
    # Check if file exists on disk
    if not os.path.exists(file.storage_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found on storage"
        )
    
    return FastAPIFileResponse(
        path=file.storage_path,
        filename=file.original_filename,
        media_type=file.mime_type
    )


@router.delete("/{file_id}")
async def delete_file(
    file_id: int,
    current_user: User = Depends(get_current_tenant_user),
    db: Session = Depends(get_db)
):
    """
    Delete a file
    """
    company = get_current_company()
    
    file = db.query(File).filter(
        File.id == file_id,
        File.company_id == company.id,
        File.status == FileStatus.ACTIVE
    ).first()
    
    if not file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )
    
    # Mark file as deleted (soft delete)
    file.status = FileStatus.DELETED
    file.deleted_at = datetime.utcnow()
    
    db.commit()
    
    # Optionally, delete physical file
    try:
        if os.path.exists(file.storage_path):
            os.remove(file.storage_path)
    except Exception as e:
        # Log error but don't fail the request
        import logging
        logging.error(f"Failed to delete physical file {file.storage_path}: {str(e)}")
    
    return {"message": "File deleted successfully"}