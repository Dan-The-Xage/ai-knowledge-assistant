from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel, EmailStr

from app.core.database import get_db
from app.core.rbac import get_current_user, require_manage_users
from app.models.user import User, Role
from app.services.audit_service import audit_log

router = APIRouter()


class UserResponse(BaseModel):
    id: int
    email: str
    full_name: str
    role: Optional[str]
    department: Optional[str]
    job_title: Optional[str]
    is_active: bool
    created_at: str


class UserUpdateRequest(BaseModel):
    full_name: Optional[str] = None
    department: Optional[str] = None
    job_title: Optional[str] = None
    role_id: Optional[int] = None
    is_active: Optional[bool] = None


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """Get current user information."""
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        role=current_user.role.name if current_user.role else None,
        department=current_user.department,
        job_title=current_user.job_title,
        is_active=current_user.is_active,
        created_at=current_user.created_at.isoformat()
    )


@router.get("/", response_model=List[UserResponse])
async def list_users(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(require_manage_users),
    db: Session = Depends(get_db)
):
    """List all users (admin only)."""
    users = db.query(User).offset(offset).limit(limit).all()
    
    return [
        UserResponse(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            role=user.role.name if user.role else None,
            department=user.department,
            job_title=user.job_title,
            is_active=user.is_active,
            created_at=user.created_at.isoformat()
        ) for user in users
    ]


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    current_user: User = Depends(require_manage_users),
    db: Session = Depends(get_db)
):
    """Get user by ID (admin only)."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role.name if user.role else None,
        department=user.department,
        job_title=user.job_title,
        is_active=user.is_active,
        created_at=user.created_at.isoformat()
    )


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    request: UserUpdateRequest,
    current_user: User = Depends(require_manage_users),
    db: Session = Depends(get_db)
):
    """Update user (admin only)."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Update fields
    if request.full_name is not None:
        user.full_name = request.full_name
    if request.department is not None:
        user.department = request.department
    if request.job_title is not None:
        user.job_title = request.job_title
    if request.role_id is not None:
        role = db.query(Role).filter(Role.id == request.role_id).first()
        if not role:
            raise HTTPException(status_code=400, detail="Invalid role ID")
        user.role_id = request.role_id
    if request.is_active is not None:
        user.is_active = request.is_active
    
    db.commit()
    db.refresh(user)
    
    # Audit log
    await audit_log(
        db=db,
        user_id=current_user.id,
        action="update",
        resource_type="user",
        resource_id=user.id,
        description=f"Updated user {user.email}",
        success="success"
    )
    
    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role.name if user.role else None,
        department=user.department,
        job_title=user.job_title,
        is_active=user.is_active,
        created_at=user.created_at.isoformat()
    )


@router.delete("/{user_id}")
async def delete_user(
    user_id: int,
    current_user: User = Depends(require_manage_users),
    db: Session = Depends(get_db)
):
    """Delete user (admin only)."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")
    
    email = user.email
    db.delete(user)
    db.commit()
    
    # Audit log
    await audit_log(
        db=db,
        user_id=current_user.id,
        action="delete",
        resource_type="user",
        resource_id=user_id,
        description=f"Deleted user {email}",
        success="success"
    )
    
    return {"message": "User deleted successfully"}

