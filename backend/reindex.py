import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.database import SessionLocal
from app.models.document import Document
from app.services.vector_service import vector_service
from app.services.document_service import document_processor

db = SessionLocal()
docs = db.query(Document).all()
print(f"Found {len(docs)} documents to re-index")

for doc in docs:
    print(f"Processing: {doc.filename}")
    if os.path.exists(doc.file_path):
        with open(doc.file_path, "rb") as f:
            content = f.read()
        result = document_processor.process_document(content, doc.filename, doc.mime_type)
        if result["success"]:
            chunks = result["chunks"]
            success = vector_service.add_document_chunks(
                document_id=doc.id,
                chunks=chunks,
                project_id=doc.project_id,
                user_id=doc.uploaded_by_id
            )
            print(f"  Added {len(chunks)} chunks: {'OK' if success else 'FAILED'}")
        else:
            print(f"  Processing failed: {result.get('error')}")
    else:
        print(f"  File not found: {doc.file_path}")

db.close()
stats = vector_service.get_status()
print(f"\nVector DB: {stats.get('collection_stats', {}).get('total_chunks', 0)} total chunks")

