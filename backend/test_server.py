#!/usr/bin/env python3
"""
Simple test server to verify the AI Knowledge Assistant platform works.
This bypasses database initialization issues for testing.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import uvicorn

app = FastAPI(
    title="AI Knowledge Assistant - Test Server",
    version="1.0.0",
    description="Test server for the AI Knowledge Assistant platform"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mock data
MOCK_DOCUMENTS = [
    {
        "id": 1,
        "filename": "company_policy.pdf",
        "file_size": 245760,
        "mime_type": "application/pdf",
        "processing_status": "completed",
        "project_id": 1,
        "uploaded_by": "admin",
        "created_at": "2024-12-16T10:00:00Z",
        "word_count": 1250,
        "page_count": 5
    },
    {
        "id": 2,
        "filename": "hr_handbook.docx",
        "file_size": 189440,
        "mime_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "processing_status": "completed",
        "project_id": 1,
        "uploaded_by": "admin",
        "created_at": "2024-12-16T11:00:00Z",
        "word_count": 2100,
        "page_count": 8
    }
]

MOCK_PROJECTS = [
    {
        "id": 1,
        "name": "HR Policies",
        "description": "Human Resources policies and procedures",
        "is_active": True,
        "is_private": False,
        "created_by": "admin",
        "created_at": "2024-12-16T09:00:00Z",
        "member_count": 3,
        "document_count": 2
    }
]

class LoginRequest(BaseModel):
    email: str
    password: str

class RegisterRequest(BaseModel):
    email: str
    password: str
    full_name: str
    department: str = None
    job_title: str = None

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict

class ChatMessageRequest(BaseModel):
    content: str
    project_id: Optional[int] = None

class ChatResponse(BaseModel):
    conversation: dict
    message: dict
    sources_used: List[dict]

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": "1.0.0-test",
        "message": "AI Knowledge Assistant test server is running"
    }

@app.post("/api/v1/auth/login")
async def login(request: LoginRequest):
    """Mock login endpoint."""
    if request.email == "admin@test.com" and request.password == "password":
        return TokenResponse(
            access_token="mock-jwt-token",
            user={
                "id": 1,
                "email": request.email,
                "full_name": "Test Admin",
                "role": "admin",
                "department": "IT",
                "job_title": "Administrator"
            }
        )
    raise HTTPException(status_code=401, detail="Invalid credentials")

@app.post("/api/v1/auth/register")
async def register(request: RegisterRequest):
    """Mock register endpoint."""
    # Accept any registration for demo purposes
    return TokenResponse(
        access_token="mock-jwt-token-new-user",
        user={
            "id": 999,
            "email": request.email,
            "full_name": request.full_name,
            "role": "user",
            "department": request.department or "General",
            "job_title": request.job_title or "User"
        }
    )

@app.get("/api/v1/projects")
async def get_projects():
    """Mock projects endpoint."""
    return MOCK_PROJECTS

@app.get("/api/v1/documents")
async def get_documents():
    """Mock documents endpoint."""
    return {"data": MOCK_DOCUMENTS, "total": len(MOCK_DOCUMENTS), "page": 1, "per_page": 20}

@app.get("/api/v1/conversations")
async def get_conversations():
    """Mock conversations endpoint."""
    return []

@app.post("/api/v1/conversations")
async def create_conversation():
    """Mock create conversation endpoint."""
    return {
        "id": 1,
        "title": "New Chat",
        "is_active": "active",
        "project_id": None,
        "user_id": 1,
        "created_at": "2024-12-16T12:00:00Z",
        "message_count": 0
    }

@app.get("/api/v1/conversations/{conversation_id}")
async def get_conversation(conversation_id: int):
    """Mock get conversation endpoint."""
    return {
        "conversation": {
            "id": conversation_id,
            "title": "New Chat",
            "is_active": "active",
            "project_id": None,
            "user_id": 1,
            "created_at": "2024-12-16T12:00:00Z"
        },
        "messages": []
    }

@app.post("/api/v1/conversations/{conversation_id}/chat")
async def chat_with_ai(conversation_id: int, request: ChatMessageRequest):
    """Mock AI chat endpoint with NLP-based responses."""
    # Simple mock AI responses based on keywords
    query_lower = request.content.lower()

    if "policy" in query_lower or "hr" in query_lower:
        response_text = "Based on the company HR policies, employees are required to submit vacation requests at least 2 weeks in advance. The policy also states that unused vacation days do not carry over to the next year."
        sources = [{
            "content": "Company Vacation Policy: Employees must submit vacation requests 2 weeks in advance...",
            "metadata": {"document_id": 1, "chunk_index": 0},
            "similarity_score": 0.85
        }]
    elif "budget" in query_lower or "finance" in query_lower:
        response_text = "According to the financial documents, the department budget for Q4 is $125,000, with $45,000 allocated for software licenses and $80,000 for hardware upgrades."
        sources = [{
            "content": "Q4 Budget Allocation: Software licenses $45K, Hardware $80K...",
            "metadata": {"document_id": 2, "chunk_index": 1},
            "similarity_score": 0.78
        }]
    else:
        response_text = f"I've searched through the available documents. While I found some relevant information about '{request.content[:30]}...', I recommend checking the specific policy documents or contacting your department head for more detailed guidance."
        sources = []

    return ChatResponse(
        conversation={
            "id": conversation_id,
            "title": "New Chat",
            "is_active": "active",
            "project_id": request.project_id,
            "user_id": 1,
            "created_at": "2024-12-16T12:00:00Z",
            "message_count": 1
        },
        message={
            "id": 1,
            "conversation_id": conversation_id,
            "message_type": "assistant",
            "content": response_text,
            "citations": [{
                "document_id": 1,
                "chunk_index": 0,
                "similarity_score": 0.85
            }] if sources else [],
            "confidence_score": 0.8,
            "tokens_used": len(response_text.split()),
            "processing_time": 0.5,
            "created_at": "2024-12-16T12:00:01Z"
        },
        sources_used=sources
    )

@app.get("/api/v1/health")
async def api_health():
    """API health endpoint."""
    return {"status": "healthy", "services": {"api": "running", "database": "mock", "vector_db": "mock", "llm_service": "nlp"}}

if __name__ == "__main__":
    print("🚀 Starting AI Knowledge Assistant Test Server...")
    print("📱 Frontend should be accessible at: http://localhost:3000")
    print("🔌 Backend API at: http://localhost:8000")
    print("📚 API Docs at: http://localhost:8000/docs")
    print("")
    print("Test login credentials:")
    print("Email: admin@test.com")
    print("Password: password")
    print("")
    uvicorn.run(app, host="0.0.0.0", port=8000)
