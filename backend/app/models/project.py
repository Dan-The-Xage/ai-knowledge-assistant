from sqlalchemy import Column, Integer, String, Text, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import TimestampMixin
from app.models.user import user_projects, User


class Project(Base, TimestampMixin):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    is_active = Column(Boolean, default=True)
    is_private = Column(Boolean, default=False)  # If true, only assigned users can access

    # Creator
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Settings
    max_file_size = Column(Integer, default=104857600)  # 100MB default
    allowed_extensions = Column(String(500), default=".pdf,.docx,.xlsx,.txt")

    # Relationships
    created_by = relationship("User", backref="created_projects", foreign_keys=[created_by_id])
    users = relationship("User", secondary=user_projects, back_populates="projects")
    documents = relationship("Document", back_populates="project")
    conversations = relationship("Conversation", back_populates="project")
