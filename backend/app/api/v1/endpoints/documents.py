"""
Document API Endpoints with RBAC.

Implements E-PRD RBAC requirements:
- Access scopes: organization, project, personal
- Deletion rules based on role
- Pre-retrieval RBAC filtering
"""

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, BackgroundTasks, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
import os
from pathlib import Path
from pydantic import BaseModel
from enum import Enum

from app.core.database import get_db
from app.core.rbac import (
    get_current_user, 
    require_upload_documents, 
    check_project_access, 
    check_document_access,
    can_delete_document,
    get_accessible_project_ids,
    is_super_admin,
    is_admin,
    AccessScope
)
from app.models.user import User
from app.models.document import Document
from app.models.project import Project
from app.services.document_service import document_processor
from app.services.vector_service import vector_service
from app.services.audit_service import audit_log
from app.core.config import settings

router = APIRouter()


class AccessScopeEnum(str, Enum):
    """Document access scope options."""
    ORGANIZATION = "organization"  # All authenticated users
    PROJECT = "project"            # Project members only
    PERSONAL = "personal"          # Owner only


class DocumentResponse(BaseModel):
    id: int
    filename: str
    file_size: int
    mime_type: str
    processing_status: str
    project_id: int
    uploaded_by: str
    created_at: str
    word_count: Optional[int]
    page_count: Optional[int]
    access_scope: str = "project"


class DocumentUploadResponse(BaseModel):
    document: DocumentResponse
    message: str


class DocumentListResponse(BaseModel):
    documents: List[DocumentResponse]
    total: int
    page: int
    per_page: int


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    project_id: int = Query(..., description="Project ID to upload to"),
    title: Optional[str] = Query(None, description="Document title"),
    description: Optional[str] = Query(None, description="Document description"),
    access_scope: AccessScopeEnum = Query(
        AccessScopeEnum.PROJECT, 
        description="Access scope: organization (all users), project (project members), personal (owner only)"
    ),
    current_user: User = Depends(require_upload_documents),
    db: Session = Depends(get_db)
):
    """
    Upload a document to a project.
    
    Access Scope determines who can access the document:
    - organization: All authenticated users in the system
    - project: Only members of the project
    - personal: Only the document owner
    """
    try:
        # Validate file size
        file_content = await file.read()
        if len(file_content) > settings.MAX_FILE_SIZE:
            raise HTTPException(
                status_code=413,
                detail=f"File too large. Maximum size: {settings.MAX_FILE_SIZE} bytes"
            )

        # Validate file extension
        file_ext = Path(file.filename).suffix.lower()
        if file_ext not in settings.ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"File type not allowed. Allowed: {', '.join(settings.ALLOWED_EXTENSIONS)}"
            )

        # Check project access
        if not check_project_access(project_id, current_user, db):
            raise HTTPException(
                status_code=403,
                detail="No access to this project"
            )

        # Process document
        processing_result = document_processor.process_document(
            file_content=file_content,
            filename=file.filename,
            mime_type=file.content_type
        )

        if not processing_result["success"]:
            raise HTTPException(
                status_code=500,
                detail=f"Document processing failed: {processing_result.get('error')}"
            )

        # Check if document with same hash already exists
        existing_doc = db.query(Document).filter(
            Document.file_hash == processing_result["file_hash"]
        ).first()
        
        if existing_doc:
            raise HTTPException(
                status_code=409,
                detail=f"This document has already been uploaded (as '{existing_doc.filename}' in project {existing_doc.project_id}). Delete the existing document first if you want to re-upload."
            )

        # Save document to database with access scope
        document = Document(
            filename=file.filename,
            original_filename=file.filename,
            file_path="",  # Will be set after saving
            file_size=len(file_content),
            mime_type=file.content_type,
            file_hash=processing_result["file_hash"],
            access_scope=access_scope.value,  # RBAC access scope
            extracted_text=processing_result["extracted_text"],
            page_count=processing_result["metadata"].get("pages", 1),
            word_count=processing_result["metadata"].get("word_count"),
            title=title or file.filename,
            description=description,
            tags=[],
            doc_metadata=processing_result["metadata"],
            is_excel=file_ext in ['.xlsx', '.xls'],
            sheet_names=processing_result["metadata"].get("sheets", []),
            processing_status="processing",
            project_id=project_id,
            uploaded_by_id=current_user.id
        )

        db.add(document)
        db.commit()
        db.refresh(document)

        # Save file to disk
        file_path = document_processor.save_document_file(
            file_content=file_content,
            filename=file.filename,
            document_id=document.id
        )

        # Update file path
        document.file_path = file_path
        db.commit()

        # Process chunks in background with RBAC metadata
        # Note: Don't pass db session to background task - it creates its own
        background_tasks.add_task(
            process_document_chunks,
            document.id,
            processing_result["chunks"],
            project_id,
            current_user.id,
            access_scope.value
        )

        # Audit log
        await audit_log(
            db=db,
            user_id=current_user.id,
            action="upload",
            resource_type="document",
            resource_id=document.id,
            description=f"Uploaded document {file.filename} to project {project_id} with scope {access_scope.value}",
            success="success"
        )

        return DocumentUploadResponse(
            document=DocumentResponse(
                id=document.id,
                filename=document.filename,
                file_size=document.file_size,
                mime_type=document.mime_type,
                processing_status=document.processing_status,
                project_id=document.project_id,
                uploaded_by=current_user.full_name,
                created_at=document.created_at.isoformat(),
                word_count=document.word_count,
                page_count=document.page_count,
                access_scope=document.access_scope
            ),
            message="Document uploaded successfully. Processing in background."
        )

    except HTTPException:
        raise
    except Exception as e:
        # Rollback any pending transaction before logging
        db.rollback()
        try:
            await audit_log(
                db=db,
                user_id=current_user.id,
                action="upload",
                resource_type="document",
                description=f"Failed to upload {file.filename}",
                success="failure",
                error_message=str(e)[:500]
            )
        except Exception:
            pass  # Don't fail if audit log fails
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


def process_document_chunks(
    document_id: int, 
    chunks: List[Dict[str, Any]], 
    project_id: int,
    user_id: int,
    access_scope: str
):
    """
    Background task to process document chunks.
    
    Includes RBAC metadata in vector embeddings for pre-retrieval filtering.
    Creates its own database session since background tasks run after request completes.
    """
    from app.core.database import SessionLocal
    from app.models.document import DocumentChunk
    import logging
    
    logger = logging.getLogger(__name__)
    
    # Create a new database session for the background task
    db = SessionLocal()
    
    try:
        # Add RBAC metadata to each chunk for vector storage
        for chunk in chunks:
            chunk["project_id"] = project_id
            chunk["user_id"] = user_id
            chunk["access_scope"] = access_scope

        # Add chunks to vector database with RBAC metadata
        success = vector_service.add_document_chunks(document_id, chunks)

        if success:
            # Save chunks to database
            for chunk_data in chunks:
                chunk_record = DocumentChunk(
                    document_id=document_id,
                    chunk_index=chunk_data["chunk_index"],
                    content=chunk_data["content"],
                    token_count=chunk_data["token_count"],
                    page_number=chunk_data.get("page_number"),
                    section_title=chunk_data.get("section_title"),
                    embedding_id=f"doc_{document_id}_chunk_{chunk_data['chunk_index']}"
                )
                db.add(chunk_record)

            # Update document status
            document = db.query(Document).filter(Document.id == document_id).first()
            if document:
                document.processing_status = "completed"
                from datetime import datetime
                document.processing_completed_at = datetime.utcnow()

            db.commit()
            logger.info(f"Document {document_id} processing completed successfully with {len(chunks)} chunks")

        else:
            # Update document status to failed
            document = db.query(Document).filter(Document.id == document_id).first()
            if document:
                document.processing_status = "failed"
                document.processing_error = "Vector database indexing failed"
            db.commit()
            logger.error(f"Document {document_id} failed: Vector database indexing failed")

    except Exception as e:
        logger.error(f"Document {document_id} processing failed: {str(e)}")
        # Update document status to failed
        try:
            document = db.query(Document).filter(Document.id == document_id).first()
            if document:
                document.processing_status = "failed"
                document.processing_error = str(e)[:500]  # Truncate error message
            db.commit()
        except Exception as commit_error:
            logger.error(f"Failed to update document status: {commit_error}")
            db.rollback()
    finally:
        db.close()


@router.get("/", response_model=DocumentListResponse)
async def list_documents(
    project_id: Optional[int] = Query(None, description="Filter by project ID"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Search in filename/title"),
    access_scope: Optional[AccessScopeEnum] = Query(None, description="Filter by access scope"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List documents accessible to the user.
    
    RBAC filtering is applied:
    - Super Admin: See all documents
    - Admin: See all except personal documents of others
    - User: See own documents + project documents they have access to
    """
    query = db.query(Document)

    # Apply RBAC filters
    if is_super_admin(current_user):
        # Super admin sees all
        if project_id:
            query = query.filter(Document.project_id == project_id)
    
    elif is_admin(current_user):
        # Admin sees all except others' personal documents
        if project_id:
            query = query.filter(Document.project_id == project_id)
        # Exclude others' personal documents
        query = query.filter(
            (Document.access_scope != "personal") | 
            (Document.uploaded_by_id == current_user.id)
        )
    
    else:
        # Regular user - only accessible projects and respecting access scope
        accessible_projects = get_accessible_project_ids(current_user, db)
        
        if project_id:
            if project_id not in accessible_projects:
                raise HTTPException(status_code=403, detail="No access to this project")
            query = query.filter(Document.project_id == project_id)
        else:
            query = query.filter(Document.project_id.in_(accessible_projects))
        
        # Apply access scope filter
        query = query.filter(
            (Document.access_scope == "organization") |
            ((Document.access_scope == "project") & Document.project_id.in_(accessible_projects)) |
            ((Document.access_scope == "personal") & (Document.uploaded_by_id == current_user.id))
        )

    # Additional filters
    if access_scope:
        query = query.filter(Document.access_scope == access_scope.value)

    if search:
        query = query.filter(
            (Document.filename.ilike(f"%{search}%")) |
            (Document.title.ilike(f"%{search}%"))
        )

    # Pagination
    total = query.count()
    documents = query.order_by(Document.created_at.desc()).offset((page - 1) * per_page).limit(per_page).all()

    return DocumentListResponse(
        documents=[
            DocumentResponse(
                id=doc.id,
                filename=doc.filename,
                file_size=doc.file_size,
                mime_type=doc.mime_type,
                processing_status=doc.processing_status,
                project_id=doc.project_id,
                uploaded_by=doc.uploaded_by.full_name,
                created_at=doc.created_at.isoformat(),
                word_count=doc.word_count,
                page_count=doc.page_count,
                access_scope=doc.access_scope or "project"
            ) for doc in documents
        ],
        total=total,
        page=page,
        per_page=per_page
    )


@router.get("/available-for-chat")
async def get_documents_for_chat(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get documents available for chat queries.
    
    Returns:
    - Super Admin shared documents (visible to all)
    - User's own documents
    - Project documents the user has access to
    """
    from app.models.user import Role
    
    # Get super admin user ID
    super_admin_role = db.query(Role).filter(Role.name == "super_admin").first()
    super_admin_docs = []
    user_docs = []
    
    if super_admin_role:
        # Get all completed documents from super admins (shared with everyone)
        super_admin_docs = db.query(Document).join(User).filter(
            User.role_id == super_admin_role.id,
            Document.processing_status == "completed"
        ).all()
    
    # Get user's own documents
    user_docs = db.query(Document).filter(
        Document.uploaded_by_id == current_user.id,
        Document.processing_status == "completed"
    ).all()
    
    # Combine and deduplicate
    all_docs = {doc.id: doc for doc in super_admin_docs}
    for doc in user_docs:
        all_docs[doc.id] = doc
    
    return {
        "shared_documents": [
            {
                "id": doc.id,
                "filename": doc.filename,
                "title": doc.title or doc.filename,
                "uploaded_by": doc.uploaded_by.full_name,
                "is_shared": True,
                "page_count": doc.page_count,
                "word_count": doc.word_count
            } for doc in super_admin_docs
        ],
        "my_documents": [
            {
                "id": doc.id,
                "filename": doc.filename,
                "title": doc.title or doc.filename,
                "uploaded_by": doc.uploaded_by.full_name,
                "is_shared": False,
                "page_count": doc.page_count,
                "word_count": doc.word_count
            } for doc in user_docs if doc.id not in [d.id for d in super_admin_docs]
        ],
        "total": len(all_docs)
    }


@router.get("/{document_id}")
async def get_document(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get document details with RBAC check."""
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    if not check_document_access(document_id, current_user, db, action="view"):
        raise HTTPException(status_code=403, detail="No access to this document")

    return {
        "id": document.id,
        "filename": document.filename,
        "file_size": document.file_size,
        "mime_type": document.mime_type,
        "processing_status": document.processing_status,
        "project_id": document.project_id,
        "uploaded_by": document.uploaded_by.full_name,
        "uploaded_by_id": document.uploaded_by_id,
        "created_at": document.created_at.isoformat(),
        "word_count": document.word_count,
        "page_count": document.page_count,
        "title": document.title,
        "description": document.description,
        "tags": document.tags,
        "metadata": document.doc_metadata,
        "is_excel": document.is_excel,
        "sheet_names": document.sheet_names,
        "access_scope": document.access_scope or "project",
        "can_edit": document.uploaded_by_id == current_user.id or is_admin(current_user),
        "can_delete": can_delete_document(document_id, current_user, db)
    }


@router.patch("/{document_id}")
async def update_document(
    document_id: int,
    title: Optional[str] = None,
    description: Optional[str] = None,
    access_scope: Optional[AccessScopeEnum] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update document metadata.
    
    Only document owner or admin can update.
    Access scope can only be changed by the owner.
    """
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    # Check edit permission
    can_edit = document.uploaded_by_id == current_user.id or is_admin(current_user)
    if not can_edit:
        raise HTTPException(status_code=403, detail="No permission to edit this document")

    # Track changes for audit
    old_values = {}
    new_values = {}

    if title is not None:
        old_values["title"] = document.title
        document.title = title
        new_values["title"] = title

    if description is not None:
        old_values["description"] = document.description
        document.description = description
        new_values["description"] = description

    # Only owner can change access scope
    if access_scope is not None:
        if document.uploaded_by_id != current_user.id and not is_super_admin(current_user):
            raise HTTPException(
                status_code=403, 
                detail="Only the document owner can change access scope"
            )
        old_values["access_scope"] = document.access_scope
        document.access_scope = access_scope.value
        new_values["access_scope"] = access_scope.value

    db.commit()

    # Audit log
    await audit_log(
        db=db,
        user_id=current_user.id,
        action="update",
        resource_type="document",
        resource_id=document_id,
        description=f"Updated document {document.filename}",
        old_values=old_values,
        new_values=new_values,
        success="success"
    )

    return {"message": "Document updated successfully"}


@router.get("/{document_id}/download")
async def download_document(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Download document file with RBAC check."""
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    if not check_document_access(document_id, current_user, db, action="view"):
        raise HTTPException(status_code=403, detail="No access to this document")

    if not os.path.exists(document.file_path):
        raise HTTPException(status_code=404, detail="File not found on disk")

    # Audit log
    await audit_log(
        db=db,
        user_id=current_user.id,
        action="download",
        resource_type="document",
        resource_id=document.id,
        description=f"Downloaded document {document.filename}",
        success="success"
    )

    return FileResponse(
        path=document.file_path,
        filename=document.filename,
        media_type=document.mime_type
    )


@router.delete("/{document_id}")
async def delete_document(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete a document with RBAC enforcement.
    
    Deletion Rules (from E-PRD):
    - Super Admin: Can delete all documents
    - Project Admin: Can delete project files
    - User: Can delete own files only
    """
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    # Use RBAC deletion check
    if not can_delete_document(document_id, current_user, db):
        raise HTTPException(
            status_code=403, 
            detail="No permission to delete this document. Users can only delete their own documents."
        )

    # Store info for audit before deletion
    filename = document.filename
    file_path = document.file_path
    doc_project_id = document.project_id

    # Delete from vector database
    vector_service.delete_document_chunks(document_id)

    # Delete file from disk
    if os.path.exists(file_path):
        os.remove(file_path)

    # Delete from database
    db.delete(document)
    db.commit()

    # Audit log
    await audit_log(
        db=db,
        user_id=current_user.id,
        action="delete",
        resource_type="document",
        resource_id=document_id,
        description=f"Deleted document {filename}",
        old_values={
            "filename": filename, 
            "project_id": doc_project_id,
            "access_scope": document.access_scope
        },
        success="success"
    )

    return {"message": "Document deleted successfully"}
