"""
Authentication API Endpoints.

No public registration - all users are created by Super Admin.
"""

from datetime import timedelta
from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
import logging

from app.core.database import get_db
from app.core.security import (
    create_access_token,
    verify_password,
    get_password_hash
)
from app.core.config import settings
from app.core.rbac import get_current_user, is_super_admin, is_admin
from app.models.user import User, Role
from app.services.audit_service import audit_log

logger = logging.getLogger(__name__)
router = APIRouter()


# ===========================================
# REQUEST/RESPONSE MODELS
# ===========================================

class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    account_type: str  # super_admin, admin, user, guest


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


class UserCreateRequest(BaseModel):
    """Request model for creating a new user (admin only)."""
    email: EmailStr
    password: str
    full_name: str
    role: str  # super_admin, admin, user, guest
    department: Optional[str] = None
    job_title: Optional[str] = None
    is_active: bool = True


class UserUpdateRequest(BaseModel):
    """Request model for updating a user."""
    full_name: Optional[str] = None
    department: Optional[str] = None
    job_title: Optional[str] = None
    is_active: Optional[bool] = None
    role: Optional[str] = None  # Only super_admin can change roles


class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str


class UserResponse(BaseModel):
    id: int
    email: str
    full_name: str
    role: str
    department: Optional[str]
    job_title: Optional[str]
    is_active: bool
    is_verified: bool
    created_at: str


class RoleResponse(BaseModel):
    id: int
    name: str
    description: str


# ===========================================
# PUBLIC ENDPOINTS
# ===========================================

@router.post("/login", response_model=TokenResponse)
async def login(
    request: LoginRequest,
    db: Session = Depends(get_db)
) -> Any:
    """
    Authenticate user and return access token.
    
    All users are created by Super Admin - no public registration.
    """
    user = db.query(User).filter(User.email == request.email).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )

    if not verify_password(request.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )

    # Verify account type (role)
    if user.role and user.role.name != request.account_type:
        # Handle case where user is super_admin but tries to login as admin or user (optional flexibility)
        # But per requirements: "if they choose the wrong account type, they would get the wrong account type message"
        # So we enforce strict matching.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Wrong account type. You are not a {request.account_type.replace('_', ' ').title()}."
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Account is disabled. Contact your administrator."
        )

    # Create access token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        subject=user.id,
        expires_delta=access_token_expires
    )

    # Log successful login
    await audit_log(
        db=db,
        user_id=user.id,
        action="login",
        resource_type="user",
        resource_id=user.id,
        description=f"User {user.email} logged in",
        success="success"
    )

    return TokenResponse(
        access_token=access_token,
        user={
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role.name if user.role else None,
            "department": user.department,
            "job_title": user.job_title,
            "is_active": user.is_active
        }
    )


@router.get("/roles", response_model=List[RoleResponse])
async def get_available_roles(
    db: Session = Depends(get_db)
) -> Any:
    """Get available user roles (for login page display)."""
    roles = db.query(Role).all()
    return [
        RoleResponse(
            id=role.id,
            name=role.name,
            description=role.description or ""
        ) for role in roles
    ]


# ===========================================
# AUTHENTICATED USER ENDPOINTS
# ===========================================

@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """Get current user's profile."""
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        role=current_user.role.name if current_user.role else "user",
        department=current_user.department,
        job_title=current_user.job_title,
        is_active=current_user.is_active,
        is_verified=current_user.is_verified,
        created_at=current_user.created_at.isoformat()
    )


@router.put("/me", response_model=UserResponse)
async def update_current_user_profile(
    request: UserUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """Update current user's profile (limited fields)."""
    # Users can only update their own name, department, job_title
    if request.full_name is not None:
        current_user.full_name = request.full_name
    if request.department is not None:
        current_user.department = request.department
    if request.job_title is not None:
        current_user.job_title = request.job_title
    
    # Role and is_active can only be changed by admins
    if request.role is not None or request.is_active is not None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot change role or active status. Contact administrator."
        )
    
    db.commit()
    db.refresh(current_user)
    
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        role=current_user.role.name if current_user.role else "user",
        department=current_user.department,
        job_title=current_user.job_title,
        is_active=current_user.is_active,
        is_verified=current_user.is_verified,
        created_at=current_user.created_at.isoformat()
    )


@router.post("/change-password")
async def change_password(
    request: PasswordChangeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """Change current user's password."""
    # Verify current password
    if not verify_password(request.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )
    
    # Update password
    current_user.hashed_password = get_password_hash(request.new_password)
    db.commit()
    
    await audit_log(
        db=db,
        user_id=current_user.id,
        action="change_password",
        resource_type="user",
        resource_id=current_user.id,
        description="User changed their password",
        success="success"
    )
    
    return {"message": "Password changed successfully"}


@router.post("/refresh-token", response_model=TokenResponse)
async def refresh_access_token(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """Refresh access token."""
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        subject=current_user.id,
        expires_delta=access_token_expires
    )

    return TokenResponse(
        access_token=access_token,
        user={
            "id": current_user.id,
            "email": current_user.email,
            "full_name": current_user.full_name,
            "role": current_user.role.name if current_user.role else None,
            "department": current_user.department,
            "job_title": current_user.job_title,
            "is_active": current_user.is_active
        }
    )


# ===========================================
# ADMIN-ONLY USER MANAGEMENT ENDPOINTS
# ===========================================

@router.post("/users", response_model=UserResponse)
async def create_user(
    request: UserCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Create a new user (Super Admin and Admin only).
    
    - Super Admin: Can create any role
    - Admin: Can create user and guest roles only
    """
    # Check permissions
    if not is_super_admin(current_user) and not is_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can create users"
        )
    
    # Admin can only create user/guest roles
    if is_admin(current_user) and not is_super_admin(current_user):
        if request.role in ["super_admin", "admin"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only Super Admin can create admin accounts"
            )
    
    # Check if email already exists
    existing_user = db.query(User).filter(User.email == request.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Get the role
    role = db.query(Role).filter(Role.name == request.role).first()
    if not role:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role: {request.role}. Valid roles: super_admin, admin, user, guest"
        )
    
    # Create user
    new_user = User(
        email=request.email,
        full_name=request.full_name,
        hashed_password=get_password_hash(request.password),
        role_id=role.id,
        department=request.department,
        job_title=request.job_title,
        is_active=request.is_active,
        is_verified=True  # Admin-created users are auto-verified
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # Audit log
    await audit_log(
        db=db,
        user_id=current_user.id,
        action="create_user",
        resource_type="user",
        resource_id=new_user.id,
        description=f"Created user {request.email} with role {request.role}",
        success="success"
    )
    
    logger.info(f"User {request.email} created by {current_user.email} with role {request.role}")
    
    return UserResponse(
        id=new_user.id,
        email=new_user.email,
        full_name=new_user.full_name,
        role=role.name,
        department=new_user.department,
        job_title=new_user.job_title,
        is_active=new_user.is_active,
        is_verified=new_user.is_verified,
        created_at=new_user.created_at.isoformat()
    )


@router.get("/users", response_model=List[UserResponse])
async def list_users(
    role: Optional[str] = Query(None, description="Filter by role"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    search: Optional[str] = Query(None, description="Search by email or name"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """List all users (Admin only)."""
    if not is_super_admin(current_user) and not is_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can list users"
        )
    
    query = db.query(User)
    
    if role:
        role_obj = db.query(Role).filter(Role.name == role).first()
        if role_obj:
            query = query.filter(User.role_id == role_obj.id)
    
    if is_active is not None:
        query = query.filter(User.is_active == is_active)
    
    if search:
        query = query.filter(
            (User.email.ilike(f"%{search}%")) |
            (User.full_name.ilike(f"%{search}%"))
        )
    
    users = query.order_by(User.created_at.desc()).all()
    
    return [
        UserResponse(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            role=user.role.name if user.role else "user",
            department=user.department,
            job_title=user.job_title,
            is_active=user.is_active,
            is_verified=user.is_verified,
            created_at=user.created_at.isoformat()
        ) for user in users
    ]


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """Get user details (Admin only)."""
    if not is_super_admin(current_user) and not is_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can view user details"
        )
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role.name if user.role else "user",
        department=user.department,
        job_title=user.job_title,
        is_active=user.is_active,
        is_verified=user.is_verified,
        created_at=user.created_at.isoformat()
    )


@router.put("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    request: UserUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """Update user (Admin only)."""
    if not is_super_admin(current_user) and not is_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can update users"
        )
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Only super admin can change roles
    if request.role is not None:
        if not is_super_admin(current_user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only Super Admin can change user roles"
            )
        role = db.query(Role).filter(Role.name == request.role).first()
        if not role:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid role: {request.role}"
            )
        user.role_id = role.id
    
    if request.full_name is not None:
        user.full_name = request.full_name
    if request.department is not None:
        user.department = request.department
    if request.job_title is not None:
        user.job_title = request.job_title
    if request.is_active is not None:
        user.is_active = request.is_active
    
    db.commit()
    db.refresh(user)
    
    await audit_log(
        db=db,
        user_id=current_user.id,
        action="update_user",
        resource_type="user",
        resource_id=user.id,
        description=f"Updated user {user.email}",
        success="success"
    )
    
    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role.name if user.role else "user",
        department=user.department,
        job_title=user.job_title,
        is_active=user.is_active,
        is_verified=user.is_verified,
        created_at=user.created_at.isoformat()
    )


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """Delete/deactivate user (Super Admin only)."""
    if not is_super_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Super Admin can delete users"
        )
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Cannot delete yourself
    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account"
        )
    
    # Soft delete - deactivate instead of hard delete
    user.is_active = False
    db.commit()
    
    await audit_log(
        db=db,
        user_id=current_user.id,
        action="delete_user",
        resource_type="user",
        resource_id=user.id,
        description=f"Deactivated user {user.email}",
        success="success"
    )
    
    return {"message": f"User {user.email} has been deactivated"}


@router.post("/users/{user_id}/reset-password")
async def reset_user_password(
    user_id: int,
    new_password: str = Query(..., min_length=8, description="New password"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """Reset a user's password (Admin only)."""
    if not is_super_admin(current_user) and not is_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can reset passwords"
        )
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Admin cannot reset super_admin password (only super_admin can)
    if user.role and user.role.name == "super_admin" and not is_super_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Super Admin can reset another Super Admin's password"
        )
    
    user.hashed_password = get_password_hash(new_password)
    db.commit()
    
    await audit_log(
        db=db,
        user_id=current_user.id,
        action="reset_password",
        resource_type="user",
        resource_id=user.id,
        description=f"Reset password for user {user.email}",
        success="success"
    )
    
    return {"message": f"Password reset for {user.email}"}
