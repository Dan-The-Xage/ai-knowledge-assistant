from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging
import traceback

from app.core.config import settings
from app.core.database import init_db, get_db, SessionLocal
from app.api.v1.api import api_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler - startup and shutdown."""
    # Startup
    logger.info("Starting AI Knowledge Assistant...")
    
    # Initialize database
    try:
        init_db()
        logger.info("Database initialized successfully")
        
        # Create default roles and super admin if they don't exist
        await create_default_roles_and_superadmin()
        
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise
    
    # Initialize AI services
    try:
        from app.services.vector_service import vector_service
        from app.services.ai_service import ai_service
        
        if vector_service.is_ready():
            logger.info("Vector service initialized successfully")
        else:
            logger.warning("Vector service running in mock mode")
            
        if ai_service.is_ready():
            logger.info("AI service initialized successfully")
        else:
            logger.warning("AI service running in basic mode")
            
    except Exception as e:
        logger.warning(f"AI services initialization warning: {e}")
    
    logger.info("AI Knowledge Assistant started successfully!")
    
    yield
    
    # Shutdown
    logger.info("Shutting down AI Knowledge Assistant...")


async def create_default_roles_and_superadmin():
    """Create default roles and super admin user if they don't exist."""
    from app.models.user import Role, User
    from app.core.security import get_password_hash
    
    logger.info("Checking for default roles...")
    db = SessionLocal()
    try:
        # Check if roles exist
        roles_count = db.query(Role).count()
        logger.info(f"Found {roles_count} existing roles")
        
        if roles_count == 0:
            logger.info("Creating default roles per E-PRD RBAC specification...")
            # Create default roles with permissions from E-PRD
            default_roles = [
                Role(
                    name="super_admin",
                    description="Platform owner with full system access",
                    permissions='["all"]'
                ),
                Role(
                    name="admin",
                    description="Project admin - manages projects, teams, and documents",
                    permissions='["manage_users", "manage_projects", "manage_documents", "upload_documents", "delete_project_documents", "chat", "view_all", "view_analytics", "view_audit", "admin_access"]'
                ),
                Role(
                    name="user",
                    description="Standard user - uploads documents, queries AI, manages personal workspace",
                    permissions='["upload_documents", "delete_own_documents", "chat", "view_assigned", "manage_personal"]'
                ),
                Role(
                    name="guest",
                    description="Read-only access with limited querying",
                    permissions='["chat_limited", "view_assigned"]'
                )
            ]
            for role in default_roles:
                db.add(role)
                logger.info(f"Adding role: {role.name}")
            db.commit()
            logger.info("Default roles created successfully")
        
        # Create default Super Admin user if doesn't exist
        super_admin_role = db.query(Role).filter(Role.name == "super_admin").first()
        if super_admin_role:
            existing_super_admin = db.query(User).filter(
                User.role_id == super_admin_role.id
            ).first()
            
            if not existing_super_admin:
                logger.info("Creating default Super Admin user...")
                super_admin = User(
                    email="superadmin@dsn.ai",
                    full_name="Super Administrator",
                    hashed_password=get_password_hash("DSN@SuperAdmin2024!"),
                    role_id=super_admin_role.id,
                    is_active=True,
                    is_verified=True,
                    department="Administration",
                    job_title="Platform Owner"
                )
                db.add(super_admin)
                db.commit()
                logger.info("=" * 50)
                logger.info("DEFAULT SUPER ADMIN ACCOUNT CREATED:")
                logger.info("Email: superadmin@dsn.ai")
                logger.info("Password: DSN@SuperAdmin2024!")
                logger.info("IMPORTANT: Change this password after first login!")
                logger.info("=" * 50)
            else:
                logger.info(f"Super Admin already exists: {existing_super_admin.email}")
        
        # List existing roles
        existing_roles = db.query(Role).all()
        role_names = [r.name for r in existing_roles]
        logger.info(f"Available roles: {role_names}")
        
    except Exception as e:
        logger.error(f"Failed to create default roles/superadmin: {e}", exc_info=True)
        db.rollback()
    finally:
        db.close()


# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description="AI Knowledge Assistant Platform - Internal secure AI-powered system with RAG",
    openapi_url="/api/v1/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security scheme
security = HTTPBearer()

# Include API router
app.include_router(api_router, prefix="/api/v1")


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle all unhandled exceptions."""
    logger.error(f"Unhandled exception: {exc}")
    logger.error(f"Request URL: {request.url}")
    logger.error(f"Traceback: {traceback.format_exc()}")
    return JSONResponse(
        status_code=500,
        content={"detail": f"Internal server error: {str(exc)}"}
    )


@app.get("/health")
async def health_check():
    """Health check endpoint with detailed service status."""
    from app.services.vector_service import vector_service
    from app.services.ai_service import ai_service
    from app.services.analytics_service import analytics_service
    
    # Get detailed status
    vector_status = vector_service.get_status()
    ai_status = ai_service.get_status()
    
    return {
        "status": "healthy",
        "version": settings.VERSION,
        "model": settings.LLM_MODEL_NAME,
        "embedding_model": settings.EMBEDDING_MODEL,
        "services": {
            "vector_db": {
                "status": "ready" if vector_service.is_ready() else "mock_mode",
                "mock_mode": vector_status.get("mock_mode", False),
                "collection_stats": vector_status.get("collection_stats", {})
            },
            "ai_service": {
                "status": "ready" if ai_service.is_ready() else "mock_mode",
                "mock_mode": ai_status.get("mock_mode", False),
                "circuit_breaker": ai_status.get("circuit_breaker_state", "unknown"),
                "cache_size": ai_status.get("cache_size", 0)
            },
            "analytics": {
                "enabled": analytics_service.is_enabled()
            },
            "database": "connected"
        }
    }


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "AI Knowledge Assistant API",
        "version": settings.VERSION,
        "docs": "/docs"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    )
