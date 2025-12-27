import os
import json
import requests
from datetime import datetime
from appwrite.client import Client
from appwrite.services.databases import Databases
from appwrite.services.storage import Storage
from appwrite.exception import AppwriteException
import jwt

# Configuration
SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'your-secret-key-change-in-production')
ALGORITHM = "HS256"
HF_API_TOKEN = os.environ.get('HF_API_TOKEN', '')

def verify_token(token: str):
    """Verify JWT token and return payload"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise Exception('Token expired')
    except jwt.JWTError:
        raise Exception('Invalid token')

def extract_text_from_file(file_data: bytes, filename: str, mime_type: str) -> str:
    """Extract text from uploaded file"""
    try:
        if mime_type == 'text/plain':
            return file_data.decode('utf-8', errors='ignore')
        elif mime_type == 'application/pdf':
            try:
                import PyPDF2
                from io import BytesIO
                pdf_reader = PyPDF2.PdfReader(BytesIO(file_data))
                text = ""
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
                return text
            except ImportError:
                return "PDF processing not available"
        elif mime_type in ['application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                          'application/msword']:
            try:
                from docx import Document
                from io import BytesIO
                doc = Document(BytesIO(file_data))
                text = ""
                for paragraph in doc.paragraphs:
                    text += paragraph.text + "\n"
                return text
            except ImportError:
                return "Word document processing not available"
        else:
            return f"Unsupported file type: {mime_type}"
    except Exception as e:
        return f"Error extracting text: {str(e)}"

def generate_embedding(text: str) -> list:
    """Generate embeddings using Hugging Face API"""
    try:
        if not HF_API_TOKEN:
            return []  # Return empty embedding if no API token

        response = requests.post(
            "https://api-inference.huggingface.co/pipeline/feature-extraction/BAAI/bge-small-en-v1.5",
            headers={"Authorization": f"Bearer {HF_API_TOKEN}"},
            json={"inputs": text[:512], "options": {"wait_for_model": True}}  # Limit text length
        )

        if response.status_code == 200:
            embedding = response.json()
            # Normalize embedding
            import numpy as np
            embedding_array = np.array(embedding)
            normalized = embedding_array / np.linalg.norm(embedding_array)
            return normalized.tolist()
        else:
            print(f"HF API error: {response.status_code}")
            return []

    except Exception as e:
        print(f"Embedding generation error: {str(e)}")
        return []

def main(context):
    """Appwrite Function: Document Management"""

    try:
        # Get request data
        req = context.req
        method = req.method
        body = json.loads(req.body) if req.body else {}

        # Initialize Appwrite client
        client = Client()
        client.set_endpoint(os.environ.get('APPWRITE_ENDPOINT', 'https://cloud.appwrite.io/v1'))
        client.set_project(os.environ.get('APPWRITE_PROJECT_ID', ''))
        client.set_key(os.environ.get('APPWRITE_API_KEY', ''))

        databases = Databases(client)
        storage = Storage(client)

        database_id = os.environ.get('APPWRITE_DATABASE_ID', '')
        documents_collection_id = os.environ.get('DOCUMENTS_COLLECTION_ID', 'documents')
        storage_bucket_id = os.environ.get('STORAGE_BUCKET_ID', 'documents')

        # Authenticate user
        auth_header = req.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return context.res.json({'detail': 'Not authenticated'}, 401)

        try:
            token = auth_header.split(' ')[1]
            payload = verify_token(token)
            current_user_id = payload.get('sub')
            current_user_email = payload.get('email')
        except Exception as e:
            return context.res.json({'detail': f'Authentication failed: {str(e)}'}, 401)

        if method == 'POST' and 'upload' in req.path:
            # Handle file upload
            try:
                # In Appwrite, files are handled through storage service
                # This is a simplified version - in production you'd handle file uploads differently

                filename = body.get('filename')
                file_data = body.get('file_data')  # Base64 encoded file data
                mime_type = body.get('mime_type')
                project_id = body.get('project_id')

                if not filename or not file_data:
                    return context.res.json({'detail': 'Missing file data'}, 400)

                # Decode base64 file data
                import base64
                file_bytes = base64.b64decode(file_data)

                # Extract text from file
                extracted_text = extract_text_from_file(file_bytes, filename, mime_type)

                # Generate embedding
                embedding = generate_embedding(extracted_text)

                # Create document record
                document_data = {
                    'filename': filename,
                    'file_path': f'/storage/{filename}',  # Placeholder path
                    'mime_type': mime_type,
                    'file_size': len(file_bytes),
                    'uploaded_by': current_user_id,
                    'uploaded_by_email': current_user_email,
                    'processing_status': 'completed',
                    'extracted_text': extracted_text[:10000],  # Limit text length
                    'embedding': json.dumps(embedding),
                    'created_at': datetime.utcnow().isoformat()
                }

                if project_id:
                    document_data['project_id'] = project_id

                # Save to database
                new_document = databases.create_document(
                    database_id=database_id,
                    collection_id=documents_collection_id,
                    document_id='unique()',
                    data=document_data
                )

                response_data = {
                    'document': {
                        'id': new_document['$id'],
                        'filename': new_document['filename'],
                        'file_size': new_document['file_size'],
                        'mime_type': new_document['mime_type'],
                        'processing_status': new_document['processing_status'],
                        'uploaded_by': new_document['uploaded_by_email'],
                        'created_at': new_document['created_at']
                    },
                    'message': 'Document uploaded and processed successfully'
                }

                return context.res.json(response_data, 201)

            except AppwriteException as e:
                return context.res.json({'detail': f'Database error: {str(e)}'}, 500)
            except Exception as e:
                return context.res.json({'detail': f'Upload failed: {str(e)}'}, 500)

        elif method == 'GET':
            # List documents
            try:
                queries = []
                project_id = body.get('project_id')

                if project_id:
                    queries.append(f"equal('project_id', '{project_id}')")

                # Only show documents uploaded by current user or shared in project
                queries.append(f"equal('uploaded_by', '{current_user_id}')")

                documents = databases.list_documents(
                    database_id=database_id,
                    collection_id=documents_collection_id,
                    queries=queries
                )

                documents_list = []
                for doc in documents['documents']:
                    documents_list.append({
                        'id': doc['$id'],
                        'filename': doc['filename'],
                        'file_size': doc['file_size'],
                        'mime_type': doc['mime_type'],
                        'processing_status': doc['processing_status'],
                        'uploaded_by': doc['uploaded_by_email'],
                        'created_at': doc['created_at']
                    })

                return context.res.json(documents_list)

            except AppwriteException as e:
                return context.res.json({'detail': f'Database error: {str(e)}'}, 500)

        return context.res.json({'detail': 'Method not allowed'}, 405)

    except Exception as e:
        return context.res.json({'detail': f'Internal server error: {str(e)}'}, 500)
