from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks, File, UploadFile
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
import json

from app.core.database import get_db
from app.core.config import settings
from app.core.rbac import get_current_user, require_chat_access, check_project_access, get_rbac_context
from app.models.user import User
from app.models.conversation import Conversation, Message
from app.services.ai_service import ai_service
from app.services.vector_service import vector_service
from app.services.audit_service import audit_log

router = APIRouter()


class ConversationCreateRequest(BaseModel):
    title: str
    project_id: Optional[int] = None


class ConversationResponse(BaseModel):
    id: int
    title: str
    is_active: str
    project_id: Optional[int]
    user_id: int
    created_at: str
    message_count: int


class MessageRequest(BaseModel):
    content: str
    project_id: Optional[int] = None  # Override conversation project
    document_ids: Optional[List[int]] = None  # Specific documents to query


class MessageResponse(BaseModel):
    id: int
    conversation_id: int
    message_type: str
    content: str
    citations: Optional[List[Dict[str, Any]]] = None
    confidence_score: Optional[float] = None
    tokens_used: Optional[int] = None
    processing_time: Optional[float] = None
    created_at: str


class ChatResponse(BaseModel):
    conversation: ConversationResponse
    message: MessageResponse
    sources_used: List[Dict[str, Any]]


@router.post("/", response_model=ConversationResponse)
async def create_conversation(
    request: ConversationCreateRequest,
    current_user: User = Depends(require_chat_access),
    db: Session = Depends(get_db)
):
    """Create a new conversation."""
    # Validate project access if specified
    if request.project_id and not check_project_access(request.project_id, current_user, db):
        raise HTTPException(status_code=403, detail="No access to this project")

    conversation = Conversation(
        title=request.title,
        project_id=request.project_id,
        user_id=current_user.id
    )

    db.add(conversation)
    db.commit()
    db.refresh(conversation)

    # Audit log
    await audit_log(
        db=db,
        user_id=current_user.id,
        action="create",
        resource_type="conversation",
        resource_id=conversation.id,
        description=f"Created conversation '{request.title}'",
        success="success"
    )

    return ConversationResponse(
        id=conversation.id,
        title=conversation.title,
        is_active=conversation.is_active,
        project_id=conversation.project_id,
        user_id=conversation.user_id,
        created_at=conversation.created_at.isoformat(),
        message_count=0
    )


@router.get("/", response_model=List[ConversationResponse])
async def list_conversations(
    project_id: Optional[int] = Query(None, description="Filter by project ID"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of conversations"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List user's conversations."""
    query = db.query(Conversation).filter(Conversation.user_id == current_user.id)

    if project_id:
        if not check_project_access(project_id, current_user, db):
            raise HTTPException(status_code=403, detail="No access to this project")
        query = query.filter(Conversation.project_id == project_id)

    conversations = query.order_by(Conversation.created_at.desc()).limit(limit).all()

    result = []
    for conv in conversations:
        message_count = db.query(Message).filter(Message.conversation_id == conv.id).count()
        result.append(ConversationResponse(
            id=conv.id,
            title=conv.title,
            is_active=conv.is_active,
            project_id=conv.project_id,
            user_id=conv.user_id,
            created_at=conv.created_at.isoformat(),
            message_count=message_count
        ))

    return result


@router.get("/{conversation_id}")
async def get_conversation(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get conversation with messages."""
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.user_id == current_user.id
    ).first()

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    messages = db.query(Message).filter(
        Message.conversation_id == conversation_id
    ).order_by(Message.created_at).all()

    return {
        "conversation": {
            "id": conversation.id,
            "title": conversation.title,
            "is_active": conversation.is_active,
            "project_id": conversation.project_id,
            "user_id": conversation.user_id,
            "created_at": conversation.created_at.isoformat()
        },
        "messages": [
            {
                "id": msg.id,
                "message_type": msg.message_type,
                "content": msg.content,
                "citations": msg.citations,
                "confidence_score": msg.confidence_score,
                "tokens_used": msg.tokens_used,
                "processing_time": msg.processing_time,
                "created_at": msg.created_at.isoformat()
            } for msg in messages
        ]
    }


@router.post("/{conversation_id}/chat", response_model=ChatResponse)
async def chat_with_assistant(
    conversation_id: int,
    request: MessageRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(require_chat_access),
    db: Session = Depends(get_db)
):
    """Send a message to the AI assistant."""
    # Get conversation
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.user_id == current_user.id
    ).first()

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Determine which project to search in
    search_project_id = request.project_id or conversation.project_id

    if search_project_id and not check_project_access(search_project_id, current_user, db):
        raise HTTPException(status_code=403, detail="No access to this project")

    # Save user message
    user_message = Message(
        conversation_id=conversation_id,
        message_type="user",
        content=request.content
    )
    db.add(user_message)
    db.commit()

    try:
        # Get conversation history for context
        recent_messages = db.query(Message).filter(
            Message.conversation_id == conversation_id
        ).order_by(Message.created_at.desc()).limit(10).all()

        conversation_history = [
            {"type": msg.message_type, "content": msg.content}
            for msg in reversed(recent_messages[1:])  # Exclude current message
        ]

        # Get RBAC context for filtering
        rbac_context = get_rbac_context(current_user, db, project_id=search_project_id)
        
        # Add super admin user ID to RBAC context for shared document access
        from app.models.user import Role
        super_admin_role = db.query(Role).filter(Role.name == "super_admin").first()
        if super_admin_role:
            super_admin_user = db.query(User).filter(User.role_id == super_admin_role.id).first()
            if super_admin_user:
                rbac_context["super_admin_user_id"] = super_admin_user.id
        
        # Search for relevant documents with RBAC filtering (E-PRD: Pre-retrieval RBAC)
        search_results = vector_service.search_similar(
            query=request.content,
            n_results=settings.MAX_RETRIEVAL_DOCS,
            project_id=search_project_id,
            user_id=current_user.id,
            rbac_context=rbac_context,
            document_ids=request.document_ids  # Filter to specific documents if provided
        )

        # Generate AI response
        ai_result = await ai_service.generate_answer(
            query=request.content,
            context_docs=search_results["results"],
            conversation_history=conversation_history,
            project_id=search_project_id
        )

        # Save AI response
        ai_message = Message(
            conversation_id=conversation_id,
            message_type="assistant",
            content=ai_result["answer"],
            citations=ai_result["citations"],
            confidence_score=ai_result["confidence_score"],
            tokens_used=ai_result.get("tokens_used"),
            processing_time=ai_result.get("processing_time"),
            model_used=ai_result.get("model_used")
        )
        db.add(ai_message)
        db.commit()
        db.refresh(ai_message)

        # Update conversation title if it's the first message
        message_count = db.query(Message).filter(
            Message.conversation_id == conversation_id,
            Message.message_type == "user"
        ).count()

        if message_count == 1 and conversation.title.startswith("New Chat"):
            # Auto-generate title from first question
            new_title = request.content[:50] + "..." if len(request.content) > 50 else request.content
            conversation.title = new_title
            db.commit()

        # Audit log
        await audit_log(
            db=db,
            user_id=current_user.id,
            action="chat",
            resource_type="conversation",
            resource_id=conversation_id,
            description=f"Chat message in conversation {conversation_id}",
            metadata={
                "query_length": len(request.content),
                "sources_found": len(search_results["results"]),
                "confidence_score": ai_result["confidence_score"]
            },
            success="success"
        )

        # Get updated message count
        total_messages = db.query(Message).filter(Message.conversation_id == conversation_id).count()

        return ChatResponse(
            conversation=ConversationResponse(
                id=conversation.id,
                title=conversation.title,
                is_active=conversation.is_active,
                project_id=conversation.project_id,
                user_id=conversation.user_id,
                created_at=conversation.created_at.isoformat(),
                message_count=total_messages
            ),
            message=MessageResponse(
                id=ai_message.id,
                conversation_id=ai_message.conversation_id,
                message_type=ai_message.message_type,
                content=ai_message.content,
                citations=ai_message.citations,
                confidence_score=ai_message.confidence_score,
                tokens_used=ai_message.tokens_used,
                processing_time=ai_message.processing_time,
                created_at=ai_message.created_at.isoformat()
            ),
            sources_used=search_results["results"]
        )

    except Exception as e:
        # Save error message
        error_message = Message(
            conversation_id=conversation_id,
            message_type="assistant",
            content="I apologize, but I encountered an error processing your question. Please try again.",
            processing_time=0.0
        )
        db.add(error_message)
        db.commit()

        await audit_log(
            db=db,
            user_id=current_user.id,
            action="chat",
            resource_type="conversation",
            resource_id=conversation_id,
            description="Chat message failed",
            success="failure",
            error_message=str(e)
        )

        raise HTTPException(status_code=500, detail=f"Chat processing failed: {str(e)}")


def _get_project_document_ids(project_id: int, db: Session) -> List[int]:
    """Get all document IDs for a project."""
    from app.models.document import Document
    docs = db.query(Document.id).filter(
        Document.project_id == project_id,
        Document.processing_status == "completed"
    ).all()
    return [doc.id for doc in docs]


@router.delete("/{conversation_id}")
async def delete_conversation(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a conversation."""
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.user_id == current_user.id
    ).first()

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Delete all messages
    db.query(Message).filter(Message.conversation_id == conversation_id).delete()

    # Delete conversation
    db.delete(conversation)
    db.commit()

    # Audit log
    await audit_log(
        db=db,
        user_id=current_user.id,
        action="delete",
        resource_type="conversation",
        resource_id=conversation_id,
        description=f"Deleted conversation '{conversation.title}'",
        success="success"
    )

    return {"message": "Conversation deleted successfully"}


@router.post("/{conversation_id}/upload-document")
async def upload_chat_document(
    conversation_id: int,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: User = Depends(require_chat_access),
    db: Session = Depends(get_db)
):
    """
    Upload a document directly in a chat conversation.
    The document will be processed and available for querying in this conversation.
    """
    from app.models.document import Document
    from app.services.document_service import DocumentProcessor
    import hashlib
    import os
    
    # Get conversation
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.user_id == current_user.id
    ).first()

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    if not file:
        raise HTTPException(status_code=400, detail="No file uploaded")

    # Validate file type
    allowed_extensions = ['.pdf', '.doc', '.docx', '.txt', '.xls', '.xlsx', '.csv']
    file_extension = os.path.splitext(file.filename)[1].lower()
    
    if file_extension not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Allowed types: {', '.join(allowed_extensions)}"
        )

    # Read file content
    content = await file.read()
    file_size = len(content)
    
    # Check file size (10MB limit for chat uploads)
    max_size = 10 * 1024 * 1024  # 10MB
    if file_size > max_size:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size is 10MB for chat uploads."
        )
    
    # Calculate file hash
    file_hash = hashlib.sha256(content).hexdigest()
    
    # Check for duplicate
    existing_doc = db.query(Document).filter(Document.file_hash == file_hash).first()
    if existing_doc:
        # Return existing document ID instead of error
        return {
            "message": "Document already exists, using existing version",
            "document_id": existing_doc.id,
            "filename": existing_doc.filename,
            "status": "existing"
        }
    
    # Generate a unique filename for storage
    import uuid
    from app.models.project import Project
    
    unique_filename = f"{uuid.uuid4().hex}_{file.filename}"
    file_path = f"uploads/chat/{unique_filename}"  # Virtual path for chat uploads
    
    # Get project_id - use conversation's project or find/create a default one
    project_id = conversation.project_id
    if not project_id:
        # Find the first project the user has access to, or use the first project
        default_project = db.query(Project).first()
        if default_project:
            project_id = default_project.id
        else:
            raise HTTPException(
                status_code=400, 
                detail="No project available. Please create a project first."
            )
    
    # Create document record (personal scope, linked to conversation)
    document = Document(
        filename=unique_filename,
        original_filename=file.filename,
        file_path=file_path,
        file_size=file_size,
        file_hash=file_hash,
        mime_type=file.content_type,
        access_scope="personal",  # Chat documents are personal
        project_id=project_id,
        uploaded_by_id=current_user.id,
        processing_status="processing"
    )
    
    db.add(document)
    db.commit()
    db.refresh(document)
    
    # Process document in background
    processor = DocumentProcessor()
    
    try:
        # Process document content
        result = processor.process_document(
            file_content=content, 
            filename=file.filename,
            mime_type=file.content_type or "application/octet-stream",
            project_id=project_id,
            user_id=current_user.id
        )
        chunks = result.get("chunks", [])
        
        if chunks:
            document.word_count = sum(c.get("token_count", 0) for c in chunks)
            document.page_count = max(c.get("page_number", 1) for c in chunks)
            db.commit()
            
            # Add RBAC metadata to chunks
            for chunk in chunks:
                chunk["project_id"] = conversation.project_id or 0
                chunk["user_id"] = current_user.id
                chunk["access_scope"] = "personal"
            
            # Index in vector database
            success = vector_service.add_document_chunks(document.id, chunks)
            
            if success:
                document.processing_status = "completed"
            else:
                document.processing_status = "failed"
                document.processing_error = "Vector indexing failed"
        else:
            document.processing_status = "failed"
            document.processing_error = "No content extracted"
            
        db.commit()
        
    except Exception as e:
        document.processing_status = "failed"
        document.processing_error = str(e)
        db.commit()
        raise HTTPException(status_code=500, detail=f"Document processing failed: {str(e)}")
    
    # Audit log
    await audit_log(
        db=db,
        user_id=current_user.id,
        action="upload",
        resource_type="chat_document",
        resource_id=document.id,
        description=f"Uploaded document '{file.filename}' in conversation {conversation_id}",
        success="success"
    )
    
    return {
        "message": "Document uploaded and processed successfully",
        "document_id": document.id,
        "filename": document.filename,
        "status": document.processing_status,
        "word_count": document.word_count,
        "page_count": document.page_count
    }
