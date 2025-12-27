"""
Role-Based Access Control (RBAC) Module.

Implements the E-PRD RBAC requirements:
- Four user personas: Super Admin, Admin, User, Guest
- Three access scopes: Organization, Project, Personal
- Four enforcement layers: API validation, Vector filtering, Context construction, Response generation
- Deletion rules based on role
"""

from typing import List, Optional, Set
from enum import Enum
from functools import wraps
from fastapi import HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.user import User, Role
import json
import logging

logger = logging.getLogger(__name__)

# Security scheme
security = HTTPBearer(auto_error=False)


class AccessScope(str, Enum):
    """Document access scopes as per E-PRD."""
    ORGANIZATION = "organization"  # All users in organization can access
    PROJECT = "project"           # Only project members can access
    PERSONAL = "personal"         # Only the owner can access


class UserRole(str, Enum):
    """User roles as per E-PRD personas."""
    SUPER_ADMIN = "super_admin"   # Platform owner - full access
    ADMIN = "admin"               # Project admin - manages projects and teams
    USER = "user"                 # Standard user - uploads, queries, personal workspace
    GUEST = "guest"               # Read-only access, limited querying


# Define permissions for each role
ROLE_PERMISSIONS = {
    UserRole.SUPER_ADMIN: {
        "all",                    # Super admin has all permissions
    },
    UserRole.ADMIN: {
        "manage_users",           # Can manage users within their projects
        "manage_projects",        # Can create/edit/delete projects
        "manage_documents",       # Can manage all project documents
        "upload_documents",
        "delete_project_documents",
        "chat",
        "view_all",
        "view_analytics",
        "view_audit",
        "admin_access",
    },
    UserRole.USER: {
        "upload_documents",       # Can upload documents
        "delete_own_documents",   # Can delete own documents only
        "chat",                   # Can use AI chat
        "view_assigned",          # Can view assigned projects
        "manage_personal",        # Can manage personal workspace
    },
    UserRole.GUEST: {
        "chat_limited",           # Limited querying
        "view_assigned",          # Read-only access to assigned projects
    },
}


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """Get current authenticated user from JWT token."""
    from app.core.security import verify_token
    
    if not credentials:
        raise HTTPException(
            status_code=401,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    token = credentials.credentials
    user_id = verify_token(token)
    
    if not user_id:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user:
        raise HTTPException(
            status_code=401,
            detail="User not found"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=401,
            detail="User account is disabled"
        )
    
    return user


def get_user_role(user: User) -> UserRole:
    """Get the UserRole enum for a user."""
    if not user.role:
        return UserRole.GUEST
    
    role_name = user.role.name.lower()
    try:
        return UserRole(role_name)
    except ValueError:
        return UserRole.USER


def get_user_permissions(user: User) -> Set[str]:
    """Get all permissions for a user based on their role."""
    role = get_user_role(user)
    return ROLE_PERMISSIONS.get(role, set())


def has_permission(user: User, permission: str) -> bool:
    """Check if user has a specific permission."""
    permissions = get_user_permissions(user)
    
    # "all" permission grants everything
    if "all" in permissions:
        return True
    
    return permission in permissions


def is_super_admin(user: User) -> bool:
    """Check if user is a super admin."""
    return get_user_role(user) == UserRole.SUPER_ADMIN


def is_admin(user: User) -> bool:
    """Check if user is an admin or super admin."""
    role = get_user_role(user)
    return role in [UserRole.SUPER_ADMIN, UserRole.ADMIN]


class PermissionChecker:
    """RBAC Permission checker dependency."""

    def __init__(self, required_permissions: List[str]):
        self.required_permissions = required_permissions

    async def __call__(
        self,
        request: Request,
        credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
        db: Session = Depends(get_db)
    ) -> User:
        user = await get_current_user(request, credentials, db)
        
        # Check if user has any of the required permissions
        user_permissions = get_user_permissions(user)
        
        # Super admin bypass
        if "all" in user_permissions:
            return user
        
        # Check if user has at least one required permission
        if not any(perm in user_permissions for perm in self.required_permissions):
            raise HTTPException(
                status_code=403,
                detail="Not enough permissions"
            )
        
        return user


# ===========================================
# PROJECT ACCESS CONTROL
# ===========================================

def check_project_access(
    project_id: int,
    user: User,
    db: Session,
    require_admin: bool = False
) -> bool:
    """
    Check if user has access to a specific project.
    
    Args:
        project_id: The project ID to check
        user: The user requesting access
        db: Database session
        require_admin: If True, requires admin-level access to the project
        
    Returns:
        True if user has access, False otherwise
    """
    from app.models.project import Project
    from app.models.user import user_projects

    # Super admin has access to everything
    if is_super_admin(user):
        return True
    
    # Admin has access to all projects
    if is_admin(user) and not require_admin:
        return True

    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        return False
    
    # Project creator has admin access
    if project.created_by_id == user.id:
        return True
    
    # Check if user is assigned to the project
    if user in project.users:
        if require_admin:
            # Check if user is project admin (has admin role in project)
            from sqlalchemy import select
            stmt = select(user_projects.c.role_in_project).where(
                user_projects.c.user_id == user.id,
                user_projects.c.project_id == project_id
            )
            result = db.execute(stmt).first()
            if result and result[0] == "admin":
                return True
            return False
        return True
    
    # Check if project is public (not private)
    if not project.is_private:
        return not require_admin  # Public projects allow viewing but not admin actions
    
    return False


def get_accessible_project_ids(user: User, db: Session) -> List[int]:
    """
    Get list of project IDs the user can access.
    
    Returns:
        List of accessible project IDs
    """
    from app.models.project import Project
    
    # Super admin and admin can access all projects
    if is_super_admin(user) or is_admin(user):
        return [p.id for p in db.query(Project.id).filter(Project.is_active == True).all()]
    
    # Get user's assigned projects
    project_ids = []
    
    # Projects user is member of
    for project in user.projects:
        if project.is_active:
            project_ids.append(project.id)
    
    # Projects user created
    created_projects = db.query(Project.id).filter(
        Project.created_by_id == user.id,
        Project.is_active == True
    ).all()
    project_ids.extend([p.id for p in created_projects])
    
    # Public projects
    public_projects = db.query(Project.id).filter(
        Project.is_private == False,
        Project.is_active == True
    ).all()
    project_ids.extend([p.id for p in public_projects])
    
    return list(set(project_ids))


# ===========================================
# DOCUMENT ACCESS CONTROL
# ===========================================

def check_document_access(
    document_id: int,
    user: User,
    db: Session,
    action: str = "view"  # view, edit, delete
) -> bool:
    """
    Check if user has access to a specific document.
    
    Access is determined by:
    1. Document's access_scope (organization/project/personal)
    2. User's role
    3. Project membership
    4. Document ownership
    
    Args:
        document_id: The document ID
        user: The user requesting access
        db: Database session
        action: The action being performed (view, edit, delete)
    """
    from app.models.document import Document

    # Super admin has access to everything
    if is_super_admin(user):
        return True

    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        return False
    
    # Get document's access scope
    access_scope = getattr(document, 'access_scope', AccessScope.PROJECT.value)
    
    # Document owner always has full access
    if document.uploaded_by_id == user.id:
        return True
    
    # Admin can access all except personal documents
    if is_admin(user) and access_scope != AccessScope.PERSONAL.value:
        return True
    
    # Check based on access scope
    if access_scope == AccessScope.ORGANIZATION.value:
        # Organization-wide documents are accessible to all authenticated users
        return action in ["view"]  # Only view for non-owners
    
    elif access_scope == AccessScope.PROJECT.value:
        # Project-scoped documents require project membership
        if not check_project_access(document.project_id, user, db):
            return False
        
        # Project admins can edit/delete project documents
        if action in ["edit", "delete"]:
            return check_project_access(document.project_id, user, db, require_admin=True)
        return True
    
    elif access_scope == AccessScope.PERSONAL.value:
        # Personal documents only accessible by owner
        return document.uploaded_by_id == user.id
    
    return False


def can_delete_document(document_id: int, user: User, db: Session) -> bool:
    """
    Check if user can delete a document.
    
    Deletion Rules (from E-PRD):
    - Super Admin: Can delete all
    - Project Admin: Can delete project files
    - User: Can delete own files only
    """
    from app.models.document import Document
    
    # Super admin can delete anything
    if is_super_admin(user):
        return True
    
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        return False
    
    # User can always delete their own documents
    if document.uploaded_by_id == user.id:
        return True
    
    # Admin/Project Admin can delete project documents
    if is_admin(user):
        return True
    
    # Check if user is project admin for this document's project
    if check_project_access(document.project_id, user, db, require_admin=True):
        return True
    
    return False


def get_document_filter_for_user(user: User, db: Session, project_id: Optional[int] = None) -> dict:
    """
    Get filter criteria for documents based on user's access.
    
    Used for vector search filtering.
    
    Returns:
        Dict with filter criteria for Qdrant
    """
    filters = {}
    
    # Super admin sees all
    if is_super_admin(user):
        if project_id:
            filters["project_id"] = project_id
        return filters
    
    # Admin sees all except personal documents of others
    if is_admin(user):
        if project_id:
            filters["project_id"] = project_id
        # Exclude personal documents not owned by user
        filters["exclude_personal_not_owned"] = user.id
        return filters
    
    # Regular users - get accessible projects
    accessible_projects = get_accessible_project_ids(user, db)
    
    if project_id:
        # Verify user has access to requested project
        if project_id not in accessible_projects:
            raise HTTPException(status_code=403, detail="No access to this project")
        filters["project_id"] = project_id
    else:
        filters["project_ids"] = accessible_projects
    
    # User can see their own documents + project documents with appropriate scope
    filters["user_id"] = user.id
    filters["access_scope_filter"] = True
    
    return filters


# ===========================================
# CONVERSATION ACCESS CONTROL
# ===========================================

def check_conversation_access(
    conversation_id: int,
    user: User,
    db: Session
) -> bool:
    """Check if user has access to a conversation."""
    from app.models.conversation import Conversation
    
    # Super admin has access to all
    if is_super_admin(user):
        return True
    
    conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not conversation:
        return False
    
    # User owns the conversation
    if conversation.user_id == user.id:
        return True
    
    # Admin can view all conversations
    if is_admin(user):
        return True
    
    return False


# ===========================================
# PERMISSION CHECKER INSTANCES
# ===========================================

# User management - requires manage_users permission
require_manage_users = PermissionChecker(["manage_users"])

# Project management - requires manage_projects permission
require_manage_projects = PermissionChecker(["manage_projects"])

# Document upload - requires upload_documents permission
require_upload_documents = PermissionChecker(["upload_documents"])

# Chat access - requires chat or chat_limited permission
require_chat_access = PermissionChecker(["chat", "chat_limited"])

# Admin panel access
require_admin_access = PermissionChecker(["admin_access", "view_analytics"])

# View audit logs
require_audit_access = PermissionChecker(["view_audit"])


# ===========================================
# UTILITY FUNCTIONS
# ===========================================

def get_rbac_context(user: User, db: Session, project_id: Optional[int] = None) -> dict:
    """
    Get complete RBAC context for a user.
    
    Used for embedding RBAC info in API responses and vector queries.
    """
    role = get_user_role(user)
    permissions = get_user_permissions(user)
    accessible_projects = get_accessible_project_ids(user, db)
    
    return {
        "user_id": user.id,
        "role": role.value,
        "permissions": list(permissions),
        "accessible_project_ids": accessible_projects,
        "is_super_admin": is_super_admin(user),
        "is_admin": is_admin(user),
        "current_project_id": project_id,
        "has_project_access": project_id in accessible_projects if project_id else None
    }
