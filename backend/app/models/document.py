from sqlalchemy import Column, Integer, String, Text, Float, DateTime, Boolean, func, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import TimestampMixin


class Document(Base, TimestampMixin):
    """
    Document model with RBAC access scope support.
    
    Access Scopes (from E-PRD):
    - organization: All authenticated users can access
    - project: Only project members can access
    - personal: Only the document owner can access
    """
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(500), nullable=False)
    original_filename = Column(String(500), nullable=False)
    file_path = Column(String(1000), nullable=False)
    file_size = Column(Integer, nullable=False)
    mime_type = Column(String(100), nullable=False)
    file_hash = Column(String(128), unique=True, nullable=False)  # SHA256 hash

    # RBAC Access Scope
    access_scope = Column(
        String(20), 
        default="project",
        nullable=False,
        index=True
    )  # organization, project, personal

    # Content
    extracted_text = Column(Text)
    page_count = Column(Integer, default=1)
    word_count = Column(Integer)

    # Metadata
    title = Column(String(500))
    description = Column(Text)
    tags = Column(JSON)  # List of tags
    doc_metadata = Column(JSON)  # Additional metadata (renamed from metadata)

    # Excel specific
    is_excel = Column(Boolean, default=False)
    sheet_names = Column(JSON)  # List of sheet names
    column_info = Column(JSON)  # Column information for Excel files

    # Processing status
    processing_status = Column(String(50), default="pending")  # pending, processing, completed, failed
    processing_started_at = Column(DateTime(timezone=True))
    processing_completed_at = Column(DateTime(timezone=True))
    processing_error = Column(Text)

    # Relationships
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    uploaded_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    project = relationship("Project", back_populates="documents")
    uploaded_by = relationship("User", back_populates="documents")
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    chunk_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    token_count = Column(Integer, nullable=False)

    # Vector information
    embedding_id = Column(String(100))  # ID in vector database
    embedding_model = Column(String(100))
    similarity_score = Column(Float)  # Used for retrieval ranking

    # Metadata
    page_number = Column(Integer)
    section_title = Column(String(500))
    chunk_metadata = Column(JSON)

    # Relationships
    document = relationship("Document", back_populates="chunks")
