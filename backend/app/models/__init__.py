# Import models in the correct order to avoid circular import issues
from app.models.base import TimestampMixin
from app.models.user import user_projects, Role, User
from app.models.project import Project
from app.models.document import Document, DocumentChunk
from app.models.conversation import Conversation, Message
from app.models.audit import AuditLog

# This ensures all models are registered with SQLAlchemy
__all__ = [
    "TimestampMixin",
    "user_projects",
    "Role",
    "User", 
    "Project",
    "Document",
    "DocumentChunk",
    "Conversation",
    "Message",
    "AuditLog"
]

