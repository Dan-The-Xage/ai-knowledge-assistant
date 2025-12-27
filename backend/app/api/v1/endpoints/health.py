from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.core.database import get_db

router = APIRouter()


@router.get("/")
async def health_check(db: Session = Depends(get_db)):
    """Basic health check."""
    try:
        # Test database connection with a simple query
        result = db.query(1).first()
        return {
            "status": "healthy",
            "database": "connected",
            "services": {
                "api": "running",
                "database": "connected"
            }
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "database": f"error: {str(e)}",
            "services": {
                "api": "running",
                "database": "disconnected"
            }
        }


@router.get("/detailed")
async def detailed_health_check(db: Session = Depends(get_db)):
    """Detailed health check with component status."""
    health_status = {
        "status": "healthy",
        "timestamp": "2025-01-16T14:30:00Z",  # Would use datetime.utcnow() in real implementation
        "version": "1.0.0",
        "components": {}
    }

    # Database health
    try:
        result = db.query(1).first()
        health_status["components"]["database"] = {
            "status": "healthy",
            "details": "Database connection OK"
        }
    except Exception as e:
        health_status["status"] = "degraded"
        health_status["components"]["database"] = {
            "status": "unhealthy",
            "details": f"Database error: {str(e)}"
        }

    # Vector database health
    try:
        from app.services.vector_service import vector_service
        if vector_service.health_check():
            stats = vector_service.get_collection_stats()
            health_status["components"]["vector_db"] = {
                "status": "healthy",
                "details": f"ChromaDB connected - {stats.get('total_chunks', 0)} chunks stored"
            }
        else:
            health_status["status"] = "degraded"
            health_status["components"]["vector_db"] = {
                "status": "unhealthy",
                "details": "Vector database health check failed"
            }
    except Exception as e:
        health_status["status"] = "degraded"
        health_status["components"]["vector_db"] = {
            "status": "unhealthy",
            "details": f"Vector DB error: {str(e)}"
        }

    # LLM service health (placeholder)
    try:
        # TODO: Add LLM health check
        health_status["components"]["llm_service"] = {
            "status": "unknown",
            "details": "LLM service check not implemented yet"
        }
    except Exception as e:
        health_status["components"]["llm_service"] = {
            "status": "unhealthy",
            "details": f"LLM service error: {str(e)}"
        }

    return health_status
