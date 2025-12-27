"""
Vector Database Service using Qdrant with BGE Embeddings.

This service handles:
- Document embedding generation using BGE models
- Vector storage and retrieval with Qdrant
- RBAC-filtered semantic search
- Collection management
"""

import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
import uuid

from app.core.config import settings

logger = logging.getLogger(__name__)

# Try to import dependencies
try:
    from sentence_transformers import SentenceTransformer
    HAS_EMBEDDING_MODEL = True
except ImportError:
    HAS_EMBEDDING_MODEL = False
    logger.warning("sentence-transformers not installed - embeddings will use mock mode")

try:
    from qdrant_client import QdrantClient
    from qdrant_client.http import models as qdrant_models
    from qdrant_client.http.models import (
        Distance,
        VectorParams,
        PointStruct,
        Filter,
        FieldCondition,
        MatchValue,
        MatchAny,
        SearchParams
    )
    HAS_QDRANT = True
except ImportError:
    HAS_QDRANT = False
    logger.warning("qdrant-client not installed - vector DB will use mock mode")


class VectorService:
    """
    Vector database service using Qdrant and BGE embeddings.
    
    Features:
    - Local BGE embeddings for privacy
    - Qdrant for scalable vector storage
    - RBAC-aware filtering
    - Efficient similarity search
    """
    
    def __init__(self):
        """Initialize the vector service."""
        self._initialized = False
        self._mock_mode = False
        self._embedding_model = None
        self._qdrant_client = None
        
        # In-memory storage for mock mode
        self._mock_storage: Dict[str, Dict[str, Any]] = {}
        
        self._initialize()
    
    def _initialize(self):
        """Initialize embedding model and Qdrant client."""
        # Initialize embedding model
        if HAS_EMBEDDING_MODEL:
            try:
                logger.info(f"Loading embedding model: {settings.EMBEDDING_MODEL}")
                self._embedding_model = SentenceTransformer(settings.EMBEDDING_MODEL)
                logger.info("Embedding model loaded successfully")
            except Exception as e:
                logger.error(f"Failed to load embedding model: {e}")
                self._mock_mode = True
        else:
            self._mock_mode = True
            logger.warning("Running in mock mode - no embedding model")
        
        # Initialize Qdrant client
        if HAS_QDRANT and not self._mock_mode:
            try:
                if settings.QDRANT_USE_MEMORY:
                    # Use local persistent storage (no external server needed)
                    qdrant_path = settings.QDRANT_PATH
                    logger.info(f"Initializing Qdrant with local storage at: {qdrant_path}")
                    self._qdrant_client = QdrantClient(path=qdrant_path)
                else:
                    # Try to connect to Qdrant server
                    logger.info(f"Connecting to Qdrant at {settings.QDRANT_HOST}:{settings.QDRANT_PORT}")
                    self._qdrant_client = QdrantClient(
                        host=settings.QDRANT_HOST,
                        port=settings.QDRANT_PORT
                    )
                
                # Create collection if it doesn't exist
                self._ensure_collection_exists()
                self._initialized = True
                logger.info("Qdrant vector service initialized successfully")
                
            except Exception as e:
                logger.error(f"Failed to initialize Qdrant: {e}")
                self._mock_mode = True
                logger.warning("Falling back to mock vector storage")
        else:
            self._mock_mode = True
            logger.warning("Running in mock mode - no Qdrant client")
    
    def _ensure_collection_exists(self):
        """Create the vector collection if it doesn't exist."""
        if not self._qdrant_client:
            return
        
        collections = self._qdrant_client.get_collections().collections
        collection_names = [c.name for c in collections]
        
        if settings.QDRANT_COLLECTION_NAME not in collection_names:
            logger.info(f"Creating collection: {settings.QDRANT_COLLECTION_NAME}")
            self._qdrant_client.create_collection(
                collection_name=settings.QDRANT_COLLECTION_NAME,
                vectors_config=VectorParams(
                    size=settings.EMBEDDING_DIMENSION,
                    distance=Distance.COSINE
                )
            )
            logger.info("Collection created successfully")
    
    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for text using BGE model.
        
        Args:
            text: Text to embed
            
        Returns:
            List of embedding floats
        """
        if self._mock_mode or not self._embedding_model:
            # Generate mock embedding (deterministic based on text)
            import hashlib
            hash_obj = hashlib.md5(text.encode())
            hash_bytes = hash_obj.digest()
            # Generate embedding of correct dimension
            embedding = []
            for i in range(settings.EMBEDDING_DIMENSION):
                byte_idx = i % len(hash_bytes)
                embedding.append((hash_bytes[byte_idx] - 128) / 128.0)
            return embedding
        
        # Generate real embedding
        embedding = self._embedding_model.encode(text, normalize_embeddings=True)
        return embedding.tolist()
    
    def add_document_chunks(
        self,
        document_id: int,
        chunks: List[Dict[str, Any]],
        project_id: Optional[int] = None,
        user_id: Optional[int] = None
    ) -> bool:
        """
        Add document chunks to the vector database.
        
        Args:
            document_id: Database ID of the document
            chunks: List of chunk dictionaries with content and metadata
            project_id: Project scope for RBAC
            user_id: Owner user ID for RBAC
            
        Returns:
            Success status
        """
        if not chunks:
            return True
        
        try:
            points = []
            
            for chunk in chunks:
                chunk_id = str(uuid.uuid4())
                content = chunk.get("content", "")
                
                # Generate embedding
                embedding = self.generate_embedding(content)
                
                # Build payload with RBAC metadata
                payload = {
                    "document_id": document_id,
                    "chunk_index": chunk.get("chunk_index", 0),
                    "content": content,
                    "token_count": chunk.get("token_count", len(content.split())),
                    "page_number": chunk.get("page_number"),
                    "section_title": chunk.get("section_title"),
                    "filename": chunk.get("filename"),
                    # RBAC fields
                    "project_id": project_id,
                    "user_id": user_id,
                    "access_scope": chunk.get("access_scope", "project")  # organization, project, personal
                }
                
                if self._mock_mode:
                    # Store in mock storage
                    self._mock_storage[chunk_id] = {
                        "id": chunk_id,
                        "embedding": embedding,
                        "payload": payload
                    }
                else:
                    points.append(PointStruct(
                        id=chunk_id,
                        vector=embedding,
                        payload=payload
                    ))
            
            if not self._mock_mode and points:
                # Upsert to Qdrant
                self._qdrant_client.upsert(
                    collection_name=settings.QDRANT_COLLECTION_NAME,
                    points=points
                )
            
            logger.info(f"Added {len(chunks)} chunks for document {document_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add document chunks: {e}")
            return False
    
    def search_similar(
        self,
        query: str,
        n_results: int = 5,
        project_id: Optional[int] = None,
        user_id: Optional[int] = None,
        access_scope: str = "project",
        min_score: float = None,
        rbac_context: Optional[Dict[str, Any]] = None,
        document_ids: Optional[List[int]] = None  # Filter to specific documents
    ) -> Dict[str, Any]:
        """
        Search for similar documents with comprehensive RBAC filtering.
        
        RBAC Enforcement (from E-PRD):
        - Super Admin: Can search all documents
        - Admin: Can search all except personal documents of others
        - User: Can search own documents + project documents they have access to
        - Guest: Limited to assigned project documents only
        
        Args:
            query: Search query text
            n_results: Number of results to return
            project_id: Filter by specific project (RBAC)
            user_id: Current user ID for RBAC
            access_scope: Access scope filter (organization/project/personal)
            min_score: Minimum similarity score
            rbac_context: Full RBAC context from get_rbac_context()
            
        Returns:
            Dict with query, results, and metadata
        """
        if min_score is None:
            min_score = settings.MIN_SIMILARITY_SCORE
        
        try:
            # Generate query embedding
            query_embedding = self.generate_embedding(query)
            
            if self._mock_mode:
                return self._mock_search(query, query_embedding, n_results, project_id, user_id, min_score, rbac_context)
            
            # Build RBAC filter based on context
            filter_conditions = []
            should_conditions = []  # OR conditions for flexible access
            
            # If specific document IDs are provided, use them directly (bypasses other RBAC)
            if document_ids and len(document_ids) > 0:
                filter_conditions.append(
                    FieldCondition(
                        key="document_id",
                        match=MatchAny(any=document_ids)
                    )
                )
                # Skip other RBAC filters when specific docs are selected
                search_filter = Filter(must=filter_conditions)
            else:
                # Extract RBAC info
                is_super_admin = rbac_context.get("is_super_admin", False) if rbac_context else False
                is_admin = rbac_context.get("is_admin", False) if rbac_context else False
                accessible_projects = rbac_context.get("accessible_project_ids", []) if rbac_context else []
                super_admin_user_id = rbac_context.get("super_admin_user_id") if rbac_context else None
                
                # Super admin: no RBAC filter needed
                if is_super_admin:
                    if project_id is not None:
                        filter_conditions.append(
                            FieldCondition(key="project_id", match=MatchValue(value=project_id))
                        )
                
                # Admin: filter out personal documents of other users
                elif is_admin:
                    if project_id is not None:
                        filter_conditions.append(
                            FieldCondition(key="project_id", match=MatchValue(value=project_id))
                        )
                    # Admin can see: organization scope OR project scope OR own documents
                    should_conditions = [
                        Filter(must=[
                            FieldCondition(key="access_scope", match=MatchValue(value="organization"))
                        ]),
                        Filter(must=[
                            FieldCondition(key="access_scope", match=MatchValue(value="project"))
                        ])
                    ]
                    # Only add user filter if user_id is provided
                    if user_id is not None:
                        should_conditions.append(
                            Filter(must=[
                                FieldCondition(key="user_id", match=MatchValue(value=user_id))
                            ])
                        )
                    # Also include super admin documents
                    if super_admin_user_id is not None:
                        should_conditions.append(
                            Filter(must=[
                                FieldCondition(key="user_id", match=MatchValue(value=super_admin_user_id))
                            ])
                        )
                
                # Regular user: filter by project access + scope
                else:
                    if project_id is not None:
                        # User must have access to this project
                        if project_id not in accessible_projects:
                            logger.warning(f"User {user_id} attempted to search project {project_id} without access")
                            return {
                                "query": query,
                                "results": [],
                                "total_results": 0,
                                "error": "Access denied to this project"
                            }
                        filter_conditions.append(
                            FieldCondition(key="project_id", match=MatchValue(value=project_id))
                        )
                    elif accessible_projects:
                        # Filter to only accessible projects
                        filter_conditions.append(
                            FieldCondition(
                                key="project_id",
                                match=MatchAny(any=accessible_projects)
                            )
                        )
                    
                    # User can see: organization scope OR (project scope in their projects) OR own documents
                    should_conditions = [
                        Filter(must=[
                            FieldCondition(key="access_scope", match=MatchValue(value="organization"))
                        ]),
                        Filter(must=[
                            FieldCondition(key="access_scope", match=MatchValue(value="project"))
                        ])
                    ]
                    # Only add user filter if user_id is provided
                    if user_id is not None:
                        should_conditions.append(
                            Filter(must=[
                                FieldCondition(key="user_id", match=MatchValue(value=user_id))
                            ])
                        )
                    
                    # Also include documents uploaded by super admin (shared with everyone)
                    if super_admin_user_id is not None:
                        should_conditions.append(
                            Filter(must=[
                                FieldCondition(key="user_id", match=MatchValue(value=super_admin_user_id))
                            ])
                        )
                
                # Build final filter
                search_filter = None
                if filter_conditions or should_conditions:
                    must_conditions = filter_conditions if filter_conditions else []
                    if should_conditions:
                        search_filter = Filter(
                            must=must_conditions,
                            should=should_conditions,
                            min_should=1 if should_conditions else None
                        )
                    elif must_conditions:
                        search_filter = Filter(must=must_conditions)
            
            # Search Qdrant using query_points (newer API)
            search_result = self._qdrant_client.query_points(
                collection_name=settings.QDRANT_COLLECTION_NAME,
                query=query_embedding,
                query_filter=search_filter,
                limit=n_results,
                score_threshold=min_score,
                with_payload=True
            )
            
            # Format results
            results = []
            for hit in search_result.points:
                payload = hit.payload or {}
                results.append({
                    "content": payload.get("content", ""),
                    "metadata": {
                        "document_id": payload.get("document_id"),
                        "filename": payload.get("filename"),
                        "page_number": payload.get("page_number"),
                        "section_title": payload.get("section_title"),
                        "chunk_index": payload.get("chunk_index"),
                        "access_scope": payload.get("access_scope", "project"),
                        "project_id": payload.get("project_id")
                    },
                    "similarity_score": hit.score,
                    "document_id": payload.get("document_id"),
                    "chunk_index": payload.get("chunk_index")
                })
            
            logger.info(f"RBAC-filtered search returned {len(results)} results for user {user_id}")
            
            return {
                "query": query,
                "results": results,
                "total_results": len(results),
                "rbac_applied": True
            }
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return {
                "query": query,
                "results": [],
                "total_results": 0,
                "error": str(e)
            }
    
    def _mock_search(
        self,
        query: str,
        query_embedding: List[float],
        n_results: int,
        project_id: Optional[int],
        user_id: Optional[int],
        min_score: float,
        rbac_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Perform mock search with RBAC filtering for development/testing.
        
        Applies the same RBAC rules as the real search:
        - Super Admin: See all documents
        - Admin: See all except others' personal documents
        - User: See own documents + project documents with appropriate scope
        """
        results = []
        
        # Extract RBAC info
        is_super_admin = rbac_context.get("is_super_admin", False) if rbac_context else False
        is_admin = rbac_context.get("is_admin", False) if rbac_context else False
        accessible_projects = rbac_context.get("accessible_project_ids", []) if rbac_context else []
        
        for chunk_id, data in self._mock_storage.items():
            payload = data.get("payload", {})
            doc_project_id = payload.get("project_id")
            doc_user_id = payload.get("user_id")
            doc_access_scope = payload.get("access_scope", "project")
            
            # Apply RBAC filter
            if not is_super_admin:
                # Project filter
                if project_id is not None:
                    if doc_project_id != project_id:
                        continue
                elif not is_admin and doc_project_id not in accessible_projects:
                    continue
                
                # Access scope filter for non-admins
                if not is_admin:
                    # Can only see: organization docs, project docs in accessible projects, or own docs
                    if doc_access_scope == "personal" and doc_user_id != user_id:
                        continue
                    if doc_access_scope == "project" and doc_project_id not in accessible_projects:
                        continue
                else:
                    # Admin can't see others' personal documents
                    if doc_access_scope == "personal" and doc_user_id != user_id:
                        continue
            
            # Calculate cosine similarity
            stored_embedding = data.get("embedding", [])
            similarity = self._cosine_similarity(query_embedding, stored_embedding)
            
            if similarity >= min_score:
                results.append({
                    "content": payload.get("content", ""),
                    "metadata": {
                        "document_id": payload.get("document_id"),
                        "filename": payload.get("filename"),
                        "page_number": payload.get("page_number"),
                        "section_title": payload.get("section_title"),
                        "chunk_index": payload.get("chunk_index"),
                        "access_scope": doc_access_scope,
                        "project_id": doc_project_id
                    },
                    "similarity_score": similarity,
                    "document_id": payload.get("document_id"),
                    "chunk_index": payload.get("chunk_index")
                })
        
        # Sort by similarity and limit
        results.sort(key=lambda x: x["similarity_score"], reverse=True)
        results = results[:n_results]
        
        logger.info(f"Mock RBAC-filtered search returned {len(results)} results for user {user_id}")
        
        return {
            "query": query,
            "results": results,
            "total_results": len(results),
            "rbac_applied": True
        }
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        if len(vec1) != len(vec2):
            return 0.0
        
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = sum(a * a for a in vec1) ** 0.5
        norm2 = sum(b * b for b in vec2) ** 0.5
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)
    
    def delete_document_chunks(self, document_id: int) -> bool:
        """
        Delete all chunks for a document.
        
        Args:
            document_id: Database ID of the document
            
        Returns:
            Success status
        """
        try:
            if self._mock_mode:
                # Remove from mock storage
                to_delete = [
                    cid for cid, data in self._mock_storage.items()
                    if data.get("payload", {}).get("document_id") == document_id
                ]
                for cid in to_delete:
                    del self._mock_storage[cid]
                logger.info(f"Deleted {len(to_delete)} mock chunks for document {document_id}")
                return True
            
            # Delete from Qdrant
            self._qdrant_client.delete(
                collection_name=settings.QDRANT_COLLECTION_NAME,
                points_selector=qdrant_models.FilterSelector(
                    filter=Filter(
                        must=[
                            FieldCondition(
                                key="document_id",
                                match=MatchValue(value=document_id)
                            )
                        ]
                    )
                )
            )
            
            logger.info(f"Deleted chunks for document {document_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete document chunks: {e}")
            return False
    
    def delete_project_documents(self, project_id: int) -> bool:
        """
        Delete all documents for a project.
        
        Args:
            project_id: Project ID
            
        Returns:
            Success status
        """
        try:
            if self._mock_mode:
                to_delete = [
                    cid for cid, data in self._mock_storage.items()
                    if data.get("payload", {}).get("project_id") == project_id
                ]
                for cid in to_delete:
                    del self._mock_storage[cid]
                return True
            
            self._qdrant_client.delete(
                collection_name=settings.QDRANT_COLLECTION_NAME,
                points_selector=qdrant_models.FilterSelector(
                    filter=Filter(
                        must=[
                            FieldCondition(
                                key="project_id",
                                match=MatchValue(value=project_id)
                            )
                        ]
                    )
                )
            )
            
            logger.info(f"Deleted all documents for project {project_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete project documents: {e}")
            return False
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics about the vector collection."""
        try:
            if self._mock_mode:
                return {
                    "total_chunks": len(self._mock_storage),
                    "collection_name": "mock_collection",
                    "mock_mode": True
                }
            
            collection_info = self._qdrant_client.get_collection(
                collection_name=settings.QDRANT_COLLECTION_NAME
            )
            
            return {
                "total_chunks": collection_info.points_count,
                "collection_name": settings.QDRANT_COLLECTION_NAME,
                "vector_size": collection_info.config.params.vectors.size,
                "status": collection_info.status.value
            }
            
        except Exception as e:
            logger.error(f"Failed to get collection stats: {e}")
            return {"error": str(e)}
    
    def clear_collection(self) -> bool:
        """Clear all vectors from the collection."""
        try:
            if self._mock_mode:
                self._mock_storage.clear()
                return True
            
            # Delete and recreate collection
            self._qdrant_client.delete_collection(
                collection_name=settings.QDRANT_COLLECTION_NAME
            )
            self._ensure_collection_exists()
            
            logger.info("Collection cleared successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to clear collection: {e}")
            return False
    
    def is_ready(self) -> bool:
        """Check if vector service is ready."""
        return self._initialized or self._mock_mode
    
    def get_status(self) -> Dict[str, Any]:
        """Get detailed status of the vector service."""
        stats = self.get_collection_stats()
        return {
            "initialized": self._initialized,
            "mock_mode": self._mock_mode,
            "embedding_model": settings.EMBEDDING_MODEL,
            "collection_stats": stats
        }


# Global instance
vector_service = VectorService()
