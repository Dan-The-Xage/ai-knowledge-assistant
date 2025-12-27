from sqlalchemy import Column, Integer, String, Boolean, DateTime, func, ForeignKey, Table
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import TimestampMixin


# Association table for user-project relationships
user_projects = Table(
    'user_projects',
    Base.metadata,
    Column('user_id', Integer, ForeignKey('users.id'), primary_key=True),
    Column('project_id', Integer, ForeignKey('projects.id'), primary_key=True),
    Column('role_in_project', String(50), default='member'),  # member, admin
    Column('assigned_at', DateTime(timezone=True), server_default=func.now())
)


class Role(Base, TimestampMixin):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False)  # super_admin, admin, user
    description = Column(String(255))
    permissions = Column(String(1000))  # JSON string of permissions

    # Relationships
    users = relationship("User", back_populates="role")


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    full_name = Column(String(255), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=False)

    # Profile
    department = Column(String(100))
    job_title = Column(String(100))
    avatar_url = Column(String(500))

    # Relationships
    role = relationship("Role", back_populates="users")
    projects = relationship("Project", secondary=user_projects, back_populates="users")
    documents = relationship("Document", back_populates="uploaded_by")
    conversations = relationship("Conversation", back_populates="user")
    audit_logs = relationship("AuditLog", back_populates="user")
