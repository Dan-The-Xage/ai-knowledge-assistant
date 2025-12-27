from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel

from app.core.database import get_db
from app.core.rbac import (
    get_current_user, 
    require_manage_projects, 
    check_project_access,
    is_super_admin,
    is_admin,
    get_accessible_project_ids
)
from app.models.user import User, user_projects
from app.models.project import Project
from app.services.audit_service import audit_log

router = APIRouter(redirect_slashes=False)

class ProjectCreateRequest(BaseModel):
    name: str
    description: Optional[str] = None
    is_private: bool = False
    member_ids: Optional[List[int]] = None


class ProjectUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_private: Optional[bool] = None


class ProjectResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    is_active: bool
    is_private: bool
    created_by: str
    created_at: str
    member_count: int
    document_count: int


class ProjectMemberResponse(BaseModel):
    user_id: int
    email: str
    full_name: str
    role_in_project: str
    joined_at: str


router = APIRouter(redirect_slashes=False)

@router.post("/", response_model=ProjectResponse)
async def create_project(
    request: ProjectCreateRequest,
    current_user: User = Depends(require_manage_projects),
    db: Session = Depends(get_db)
):
    """Create a new project."""
    # Check if project name already exists
    existing_project = db.query(Project).filter(
        Project.name == request.name,
        Project.created_by_id == current_user.id
    ).first()

    if existing_project:
        raise HTTPException(
            status_code=400,
            detail="Project with this name already exists"
        )

    project = Project(
        name=request.name,
        description=request.description,
        is_private=request.is_private,
        created_by_id=current_user.id
    )

    db.add(project)
    db.commit()
    db.refresh(project)

    # Add creator as project admin
    from app.models.user import user_projects
    stmt = user_projects.insert().values(
        user_id=current_user.id,
        project_id=project.id,
        role_in_project="admin"
    )
    db.execute(stmt)

    # Add additional members if provided (only for super admin/admin)
    if request.member_ids and (is_super_admin(current_user) or is_admin(current_user)):
        for member_id in request.member_ids:
            if member_id != current_user.id:  # Don't add creator twice
                # Check if user exists
                member = db.query(User).filter(User.id == member_id).first()
                if member:
                    stmt = user_projects.insert().values(
                        user_id=member_id,
                        project_id=project.id,
                        role_in_project="member"
                    )
                    db.execute(stmt)

    db.commit()

    # Audit log
    await audit_log(
        db=db,
        user_id=current_user.id,
        action="create",
        resource_type="project",
        resource_id=project.id,
        description=f"Created project '{request.name}'",
        success="success"
    )

    return await _get_project_response(project, db)


@router.get("/", response_model=List[ProjectResponse])
async def list_projects(
    include_inactive: bool = Query(False, description="Include inactive projects"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List projects accessible to the user.
    
    RBAC:
    - Super Admin/Admin: See all projects
    - User: See projects they are members of or public projects
    """
    # Get projects using RBAC helper
    if is_super_admin(current_user) or is_admin(current_user):
        query = db.query(Project)
    else:
        # Get accessible project IDs
        accessible_ids = get_accessible_project_ids(current_user, db)
        query = db.query(Project).filter(Project.id.in_(accessible_ids))

    if not include_inactive:
        query = query.filter(Project.is_active == True)

    projects = query.order_by(Project.created_at.desc()).all()

    result = []
    for project in projects:
        result.append(await _get_project_response(project, db))

    return result


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get project details."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if not check_project_access(project_id, current_user, db):
        raise HTTPException(status_code=403, detail="No access to this project")

    return await _get_project_response(project, db)


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: int,
    request: ProjectUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update project details."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Check permissions
    is_admin = current_user.role.name in ["super_admin", "admin"]
    is_project_admin = db.query(user_projects).filter(
        user_projects.c.user_id == current_user.id,
        user_projects.c.project_id == project_id,
        user_projects.c.role_in_project == "admin"
    ).first() is not None

    if not (is_admin or is_project_admin):
        raise HTTPException(status_code=403, detail="No permission to update this project")

    # Update fields
    update_data = request.dict(exclude_unset=True)
    old_values = {}

    for field, value in update_data.items():
        if hasattr(project, field):
            old_values[field] = getattr(project, field)
            setattr(project, field, value)

    db.commit()

    # Audit log
    await audit_log(
        db=db,
        user_id=current_user.id,
        action="update",
        resource_type="project",
        resource_id=project.id,
        description=f"Updated project '{project.name}'",
        old_values=old_values,
        new_values=update_data,
        success="success"
    )

    return await _get_project_response(project, db)


@router.delete("/{project_id}")
async def delete_project(
    project_id: int,
    current_user: User = Depends(require_manage_projects),
    db: Session = Depends(get_db)
):
    """
    Delete a project.
    
    RBAC (from E-PRD):
    - Super Admin: Can delete any project
    - Admin: Can delete projects they created
    - User: Cannot delete projects
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Check if user can delete this project using RBAC
    can_delete = (
        is_super_admin(current_user) or
        (is_admin(current_user) and project.created_by_id == current_user.id)
    )

    if not can_delete:
        raise HTTPException(status_code=403, detail="No permission to delete this project")

    # Soft delete - mark as inactive
    project.is_active = False
    db.commit()

    # Audit log
    await audit_log(
        db=db,
        user_id=current_user.id,
        action="delete",
        resource_type="project",
        resource_id=project.id,
        description=f"Deleted project '{project.name}'",
        old_values={"is_active": True},
        new_values={"is_active": False},
        success="success"
    )

    return {"message": "Project deleted successfully"}


@router.get("/{project_id}/members", response_model=List[ProjectMemberResponse])
async def get_project_members(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get project members."""
    if not check_project_access(project_id, current_user, db):
        raise HTTPException(status_code=403, detail="No access to this project")

    # Get project members
    members_query = db.query(
        User.id,
        User.email,
        User.full_name,
        user_projects.c.role_in_project,
        user_projects.c.assigned_at
    ).join(user_projects).filter(
        user_projects.c.project_id == project_id
    ).all()

    return [
        ProjectMemberResponse(
            user_id=member.id,
            email=member.email,
            full_name=member.full_name,
            role_in_project=member.role_in_project,
            joined_at=member.assigned_at.isoformat()
        ) for member in members_query
    ]


@router.post("/{project_id}/members/{user_id}")
async def add_project_member(
    project_id: int,
    user_id: int,
    role: str = Query("member", description="Role in project: member or admin"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Add a user to a project."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Check permissions
    is_admin = current_user.role.name in ["super_admin", "admin"]
    is_project_admin = db.query(user_projects).filter(
        user_projects.c.user_id == current_user.id,
        user_projects.c.project_id == project_id,
        user_projects.c.role_in_project == "admin"
    ).first() is not None

    if not (is_admin or is_project_admin):
        raise HTTPException(status_code=403, detail="No permission to manage project members")

    # Check if user exists
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Check if user is already a member
    existing = db.query(user_projects).filter(
        user_projects.c.user_id == user_id,
        user_projects.c.project_id == project_id
    ).first()

    if existing:
        raise HTTPException(status_code=400, detail="User is already a member of this project")

    # Validate role
    if role not in ["member", "admin"]:
        raise HTTPException(status_code=400, detail="Invalid role. Must be 'member' or 'admin'")

    # Add user to project
    stmt = user_projects.insert().values(
        user_id=user_id,
        project_id=project_id,
        role_in_project=role,
        assigned_by=current_user.id
    )
    db.execute(stmt)
    db.commit()

    # Audit log
    await audit_log(
        db=db,
        user_id=current_user.id,
        action="add_member",
        resource_type="project",
        resource_id=project_id,
        description=f"Added user {user.email} to project '{project.name}' with role '{role}'",
        success="success"
    )

    return {"message": f"User added to project with role '{role}'"}


@router.delete("/{project_id}/members/{user_id}")
async def remove_project_member(
    project_id: int,
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Remove a user from a project."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Check permissions
    is_admin = current_user.role.name in ["super_admin", "admin"]
    is_project_admin = db.query(user_projects).filter(
        user_projects.c.user_id == current_user.id,
        user_projects.c.project_id == project_id,
        user_projects.c.role_in_project == "admin"
    ).first() is not None

    if not (is_admin or is_project_admin):
        raise HTTPException(status_code=403, detail="No permission to manage project members")

    # Cannot remove yourself if you're the only admin
    if user_id == current_user.id:
        admin_count = db.query(user_projects).filter(
            user_projects.c.project_id == project_id,
            user_projects.c.role_in_project == "admin"
        ).count()
        if admin_count <= 1:
            raise HTTPException(status_code=400, detail="Cannot remove the only project admin")

    # Remove user from project
    result = db.execute(
        user_projects.delete().where(
            user_projects.c.user_id == user_id,
            user_projects.c.project_id == project_id
        )
    )

    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="User is not a member of this project")

    db.commit()

    # Audit log
    user = db.query(User).filter(User.id == user_id).first()
    await audit_log(
        db=db,
        user_id=current_user.id,
        action="remove_member",
        resource_type="project",
        resource_id=project_id,
        description=f"Removed user {user.email if user else 'unknown'} from project '{project.name}'",
        success="success"
    )

    return {"message": "User removed from project"}


async def _get_project_response(project: Project, db: Session) -> ProjectResponse:
    """Helper function to create project response with counts."""
    # Get member count
    member_count = db.query(user_projects).filter(
        user_projects.c.project_id == project.id
    ).count()

    # Get document count
    from app.models.document import Document
    document_count = db.query(Document).filter(
        Document.project_id == project.id
    ).count()

    return ProjectResponse(
        id=project.id,
        name=project.name,
        description=project.description,
        is_active=project.is_active,
        is_private=project.is_private,
        created_by=project.created_by.full_name,
        created_at=project.created_at.isoformat(),
        member_count=member_count,
        document_count=document_count
    )
