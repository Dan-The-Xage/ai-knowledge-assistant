from app.core.database import SessionLocal
from app.models.document import Document
from app.services.vector_service import vector_service
from app.services.document_service import document_processor
import os

db = SessionLocal()

# Get the document
doc = db.query(Document).filter(Document.id == 1).first()
if not doc:
    print("No document found")
    exit(1)

print(f"Re-indexing: {doc.filename}")

# Read the file
if os.path.exists(doc.file_path):
    with open(doc.file_path, "rb") as f:
        file_content = f.read()
    
    # Re-process
    result = document_processor.process_document(file_content, doc.filename, doc.mime_type)
    
    if result["success"]:
        chunks = result["chunks"]
        print(f"Extracted {len(chunks)} chunks")
        
        # Add to vector DB
        success = vector_service.add_document_chunks(
            document_id=doc.id,
            chunks=chunks,
            project_id=doc.project_id,
            user_id=doc.uploaded_by_id
        )
        
        if success:
            print("Successfully re-indexed document!")
            # Verify
            stats = vector_service.get_status()
            total = stats.get("collection_stats", {}).get("total_chunks", 0)
            print(f"Vector DB now has: {total} chunks")
        else:
            print("Failed to add chunks to vector DB")
    else:
        print(f"Failed to process: {result.get('error')}")
else:
    print(f"File not found: {doc.file_path}")

db.close()

