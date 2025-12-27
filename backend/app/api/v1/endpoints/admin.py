"""
Admin API Endpoints.

Provides administrative functionality including:
- System statistics
- Audit logs
- AI configuration
- Analytics dashboard
- User management
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, text
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from datetime import datetime, timedelta

from app.core.database import get_db
from app.core.config import settings
from app.core.rbac import get_current_user, require_admin_access
from app.models.user import User, Role
from app.models.project import Project
from app.models.document import Document
from app.models.conversation import Conversation, Message
from app.models.audit import AuditLog
from app.services.vector_service import vector_service
from app.services.ai_service import ai_service
from app.services.analytics_service import analytics_service

router = APIRouter()


class SystemStatsResponse(BaseModel):
    total_users: int
    active_users: int
    total_projects: int
    total_documents: int
    processed_documents: int
    total_conversations: int
    total_messages: int
    vector_db_stats: Dict[str, Any]
    ai_service_status: Dict[str, Any]


class AuditLogResponse(BaseModel):
    id: int
    timestamp: str
    user_id: Optional[int]
    user_email: Optional[str]
    action: str
    resource_type: str
    resource_id: Optional[int]
    description: Optional[str]
    success: str


class AIConfigResponse(BaseModel):
    model_name: str
    max_tokens: int
    temperature: float
    top_p: float
    embedding_model: str
    chunk_size: int
    max_retrieval_docs: int
    rate_limit_per_minute: int


class AIConfigUpdateRequest(BaseModel):
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    max_tokens: Optional[int] = None


@router.get("/stats", response_model=SystemStatsResponse)
async def get_system_stats(
    current_user: User = Depends(require_admin_access),
    db: Session = Depends(get_db)
):
    """Get comprehensive system statistics (admin only)."""
    total_users = db.query(User).count()
    active_users = db.query(User).filter(User.is_active == True).count()
    total_projects = db.query(Project).count()
    total_documents = db.query(Document).count()
    processed_documents = db.query(Document).filter(
        Document.processing_status == "completed"
    ).count()
    total_conversations = db.query(Conversation).count()
    total_messages = db.query(Message).count()
    
    # Get vector service stats
    vector_stats = vector_service.get_status()
    
    # Get AI service status
    ai_status = ai_service.get_status()
    
    return SystemStatsResponse(
        total_users=total_users,
        active_users=active_users,
        total_projects=total_projects,
        total_documents=total_documents,
        processed_documents=processed_documents,
        total_conversations=total_conversations,
        total_messages=total_messages,
        vector_db_stats=vector_stats.get("collection_stats", {}),
        ai_service_status=ai_status
    )


@router.get("/analytics")
async def get_analytics_dashboard(
    current_user: User = Depends(require_admin_access),
    db: Session = Depends(get_db)
):
    """Get analytics dashboard data (admin only)."""
    # Get analytics metrics
    metrics = analytics_service.get_dashboard_metrics()
    
    # Add database-level stats
    now = datetime.utcnow()
    day_ago = now - timedelta(days=1)
    week_ago = now - timedelta(days=7)
    
    # Messages per day
    messages_today = db.query(Message).filter(
        Message.created_at > day_ago
    ).count()
    
    # Active users this week
    active_conversations = db.query(Conversation.user_id).filter(
        Conversation.created_at > week_ago
    ).distinct().count()
    
    # Documents processed this week
    docs_this_week = db.query(Document).filter(
        Document.created_at > week_ago,
        Document.processing_status == "completed"
    ).count()
    
    metrics["database_stats"] = {
        "messages_today": messages_today,
        "active_users_this_week": active_conversations,
        "documents_processed_this_week": docs_this_week
    }
    
    return metrics


@router.get("/audit-logs", response_model=List[AuditLogResponse])
async def get_audit_logs(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    action: Optional[str] = Query(None, description="Filter by action type"),
    resource_type: Optional[str] = Query(None, description="Filter by resource type"),
    user_id: Optional[int] = Query(None, description="Filter by user ID"),
    success: Optional[str] = Query(None, description="Filter by success status"),
    current_user: User = Depends(require_admin_access),
    db: Session = Depends(get_db)
):
    """Get audit logs with filtering (admin only)."""
    query = db.query(AuditLog)
    
    if action:
        query = query.filter(AuditLog.action == action)
    if resource_type:
        query = query.filter(AuditLog.resource_type == resource_type)
    if user_id:
        query = query.filter(AuditLog.user_id == user_id)
    if success:
        query = query.filter(AuditLog.success == success)
    
    logs = query.order_by(AuditLog.timestamp.desc()).offset(offset).limit(limit).all()
    
    return [
        AuditLogResponse(
            id=log.id,
            timestamp=log.timestamp.isoformat(),
            user_id=log.user_id,
            user_email=log.user_email,
            action=log.action,
            resource_type=log.resource_type,
            resource_id=log.resource_id,
            description=log.description,
            success=log.success
        ) for log in logs
    ]


@router.get("/ai-config", response_model=AIConfigResponse)
async def get_ai_configuration(
    current_user: User = Depends(require_admin_access)
):
    """Get current AI configuration (admin only)."""
    return AIConfigResponse(
        model_name=settings.LLM_MODEL_NAME,
        max_tokens=settings.LLM_MAX_NEW_TOKENS,
        temperature=settings.LLM_TEMPERATURE,
        top_p=settings.LLM_TOP_P,
        embedding_model=settings.EMBEDDING_MODEL,
        chunk_size=settings.CHUNK_SIZE,
        max_retrieval_docs=settings.MAX_RETRIEVAL_DOCS,
        rate_limit_per_minute=settings.RATE_LIMIT_REQUESTS_PER_MINUTE
    )


@router.get("/roles")
async def get_roles(
    current_user: User = Depends(require_admin_access),
    db: Session = Depends(get_db)
):
    """Get all roles with user counts (admin only)."""
    roles = db.query(Role).all()
    
    result = []
    for role in roles:
        user_count = db.query(User).filter(User.role_id == role.id).count()
        result.append({
            "id": role.id,
            "name": role.name,
            "description": role.description,
            "permissions": role.permissions,
            "user_count": user_count
        })
    
    return result


@router.post("/clear-vector-db")
async def clear_vector_database(
    current_user: User = Depends(require_admin_access),
    db: Session = Depends(get_db)
):
    """
    Clear all documents from vector database (admin only).
    
    WARNING: This will remove all document embeddings and require re-processing.
    """
    success = vector_service.clear_collection()
    
    if success:
        # Update document processing status
        db.query(Document).update({
            Document.processing_status: "pending"
        })
        db.commit()
        
        return {"message": "Vector database cleared successfully. Documents need to be re-processed."}
    else:
        raise HTTPException(status_code=500, detail="Failed to clear vector database")


@router.get("/health-detailed")
async def get_detailed_health(
    current_user: User = Depends(require_admin_access),
    db: Session = Depends(get_db)
):
    """Get detailed system health information (admin only)."""
    # Database health
    try:
        db.execute(text("SELECT 1"))
        db_healthy = True
        db_error = None
    except Exception as e:
        db_healthy = False
        db_error = str(e)
    
    # Vector service health
    vector_status = vector_service.get_status()
    
    # AI service health
    ai_status = ai_service.get_status()
    
    # Analytics service status
    analytics_enabled = analytics_service.is_enabled()
    
    return {
        "database": {
            "healthy": db_healthy,
            "error": db_error
        },
        "vector_service": {
            "healthy": vector_service.is_ready(),
            "status": vector_status
        },
        "ai_service": {
            "healthy": ai_service.is_ready(),
            "status": ai_status
        },
        "analytics": {
            "enabled": analytics_enabled
        },
        "configuration": {
            "llm_model": settings.LLM_MODEL_NAME,
            "embedding_model": settings.EMBEDDING_MODEL,
            "hf_api_configured": bool(settings.HF_API_TOKEN)
        },
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/knowledge-gaps")
async def get_knowledge_gaps(
    current_user: User = Depends(require_admin_access)
):
    """
    Get knowledge gaps analysis (admin only).
    
    Shows frequently asked questions that couldn't be answered,
    indicating missing documents or knowledge areas.
    """
    metrics = analytics_service.get_dashboard_metrics()
    
    return {
        "knowledge_gaps": metrics.get("knowledge_gaps", []),
        "no_answer_rate": metrics.get("performance", {}).get("no_answer_rate", 0),
        "recommendations": [
            "Review unanswered queries and add relevant documents",
            "Consider creating FAQ documents for common questions",
            "Ensure document processing completed successfully"
        ]
    }


@router.get("/users")
async def list_all_users(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    role_id: Optional[int] = Query(None, description="Filter by role"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    current_user: User = Depends(require_admin_access),
    db: Session = Depends(get_db)
):
    """List all users with filtering (admin only)."""
    query = db.query(User)
    
    if role_id is not None:
        query = query.filter(User.role_id == role_id)
    if is_active is not None:
        query = query.filter(User.is_active == is_active)
    
    users = query.order_by(User.created_at.desc()).offset(offset).limit(limit).all()
    
    return [
        {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role.name if user.role else None,
            "department": user.department,
            "job_title": user.job_title,
            "is_active": user.is_active,
            "is_verified": user.is_verified,
            "created_at": user.created_at.isoformat() if user.created_at else None
        }
        for user in users
    ]


@router.patch("/users/{user_id}/toggle-active")
async def toggle_user_active(
    user_id: int,
    current_user: User = Depends(require_admin_access),
    db: Session = Depends(get_db)
):
    """Toggle user active status (admin only)."""
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot deactivate your own account")
    
    user.is_active = not user.is_active
    db.commit()
    
    status = "activated" if user.is_active else "deactivated"
    return {"message": f"User {user.email} {status} successfully"}


@router.patch("/users/{user_id}/role")
async def update_user_role(
    user_id: int,
    role_id: int,
    current_user: User = Depends(require_admin_access),
    db: Session = Depends(get_db)
):
    """Update user role (admin only)."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    
    user.role_id = role_id
    db.commit()
    
    return {"message": f"User {user.email} role updated to {role.name}"}
