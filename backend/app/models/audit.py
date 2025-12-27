from sqlalchemy import Column, Integer, String, Text, DateTime, func, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.core.database import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Who performed the action
    user_id = Column(Integer, ForeignKey("users.id"))
    user_email = Column(String(255))  # Store email for historical purposes

    # What action was performed
    action = Column(String(100), nullable=False)  # create, read, update, delete, login, etc.
    resource_type = Column(String(50), nullable=False)  # user, document, project, conversation
    resource_id = Column(Integer)

    # Context
    ip_address = Column(String(45))  # IPv4/IPv6
    user_agent = Column(String(500))
    session_id = Column(String(100))

    # Details
    description = Column(Text)
    old_values = Column(JSON)  # For update/delete operations
    new_values = Column(JSON)  # For create/update operations
    extra_data = Column(JSON)    # Additional context (renamed from metadata)

    # Result
    success = Column(String(10), default="success")  # success, failure
    error_message = Column(Text)

    # Relationships
    user = relationship("User", back_populates="audit_logs")
