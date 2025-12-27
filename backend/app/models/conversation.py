from sqlalchemy import Column, Integer, String, Text, Float, DateTime, func, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import TimestampMixin


class Conversation(Base, TimestampMixin):
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500), nullable=False)
    is_active = Column(String(10), default="active")  # active, archived

    # Context
    project_id = Column(Integer, ForeignKey("projects.id"))
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # AI Settings for this conversation
    llm_model = Column(String(100))
    temperature = Column(Float, default=0.7)
    max_tokens = Column(Integer, default=1000)

    # Relationships
    project = relationship("Project", back_populates="conversations")
    user = relationship("User", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False)
    message_type = Column(String(20), nullable=False)  # user, assistant
    content = Column(Text, nullable=False)

    # AI Response metadata
    tokens_used = Column(Integer)
    processing_time = Column(Float)  # seconds
    model_used = Column(String(100))

    # Source citations
    citations = Column(JSON)  # List of document chunks used
    confidence_score = Column(Float)

    # Timestamp
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    conversation = relationship("Conversation", back_populates="messages")
