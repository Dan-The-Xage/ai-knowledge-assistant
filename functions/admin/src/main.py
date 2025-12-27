import os
import json
from datetime import datetime
from appwrite.client import Client
from appwrite.services.databases import Databases
from appwrite.exception import AppwriteException
import jwt

# Configuration
SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'your-secret-key-change-in-production')
ALGORITHM = "HS256"

def verify_token(token: str):
    """Verify JWT token and return payload"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise Exception('Token expired')
    except jwt.JWTError:
        raise Exception('Invalid token')

def main(context):
    """Appwrite Function: Admin Operations"""

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

        database_id = os.environ.get('APPWRITE_DATABASE_ID', '')
        users_collection_id = os.environ.get('USERS_COLLECTION_ID', 'users')
        documents_collection_id = os.environ.get('DOCUMENTS_COLLECTION_ID', 'documents')
        conversations_collection_id = os.environ.get('CONVERSATIONS_COLLECTION_ID', 'conversations')

        # Authenticate user
        auth_header = req.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return context.res.json({'detail': 'Not authenticated'}, 401)

        try:
            token = auth_header.split(' ')[1]
            payload = verify_token(token)
            current_user_id = payload.get('sub')
        except Exception as e:
            return context.res.json({'detail': f'Authentication failed: {str(e)}'}, 401)

        # Get current user role
        try:
            current_user_doc = databases.get_document(
                database_id=database_id,
                collection_id=users_collection_id,
                document_id=current_user_id
            )
            current_user_role = current_user_doc.get('role', 'user')
        except AppwriteException:
            return context.res.json({'detail': 'User not found'}, 404)

        # Check admin permissions
        if current_user_role not in ['admin', 'super_admin']:
            return context.res.json({'detail': 'Admin access required'}, 403)

        if method == 'GET' and 'stats' in req.path:
            # Get system statistics
            try:
                # Count users
                users = databases.list_documents(database_id, users_collection_id)
                total_users = len(users['documents'])
                active_users = len([u for u in users['documents'] if u.get('is_active', True)])

                # Count documents
                documents = databases.list_documents(database_id, documents_collection_id)
                total_documents = len(documents['documents'])

                # Count conversations
                conversations = databases.list_documents(database_id, conversations_collection_id)
                total_conversations = len(conversations['documents'])

                # Count messages
                total_messages = 0
                for conv in conversations['documents']:
                    messages = databases.list_documents(
                        database_id,
                        'messages',
                        queries=[f"equal('conversation_id', '{conv['$id']}')"]
                    )
                    total_messages += len(messages['documents'])

                stats = {
                    "total_users": total_users,
                    "active_users": active_users,
                    "total_documents": total_documents,
                    "total_conversations": total_conversations,
                    "total_messages": total_messages,
                    "vector_db_stats": {
                        "total_chunks": total_documents,  # Simplified
                        "total_collections": 1
                    },
                    "ai_service_status": {
                        "status": "operational" if os.environ.get('HF_API_TOKEN') else "not_configured",
                        "model": "Mistral-7B-Instruct-v0.2"
                    }
                }

                return context.res.json(stats)

            except AppwriteException as e:
                return context.res.json({'detail': f'Database error: {str(e)}'}, 500)

        elif method == 'PATCH' and 'toggle-active' in req.path:
            # Toggle user active status
            user_id = body.get('user_id')
            if not user_id:
                return context.res.json({'detail': 'User ID required'}, 400)

            try:
                # Get user
                user_doc = databases.get_document(
                    database_id=database_id,
                    collection_id=users_collection_id,
                    document_id=user_id
                )

                # Prevent self-deactivation
                if user_id == current_user_id:
                    return context.res.json({'detail': 'Cannot deactivate your own account'}, 400)

                # Toggle active status
                new_active_status = not user_doc.get('is_active', True)

                # Update user
                databases.update_document(
                    database_id=database_id,
                    collection_id=users_collection_id,
                    document_id=user_id,
                    data={'is_active': new_active_status}
                )

                action = "activated" if new_active_status else "deactivated"
                return context.res.json({
                    'message': f'User {user_doc["email"]} {action} successfully'
                })

            except AppwriteException as e:
                return context.res.json({'detail': f'Database error: {str(e)}'}, 500)

        elif method == 'GET' and 'users' in req.path:
            # List all users for admin
            try:
                users = databases.list_documents(database_id, users_collection_id)

                users_list = []
                for user in users['documents']:
                    users_list.append({
                        'id': user['$id'],
                        'email': user['email'],
                        'full_name': user['full_name'],
                        'role': user['role'],
                        'department': user.get('department'),
                        'job_title': user.get('job_title'),
                        'is_active': user['is_active'],
                        'created_at': user['created_at']
                    })

                return context.res.json(users_list)

            except AppwriteException as e:
                return context.res.json({'detail': f'Database error: {str(e)}'}, 500)

        elif method == 'GET' and 'roles' in req.path:
            # Get roles with user counts
            try:
                users = databases.list_documents(database_id, users_collection_id)

                roles_count = {}
                for user in users['documents']:
                    role = user.get('role', 'user')
                    roles_count[role] = roles_count.get(role, 0) + 1

                roles_data = [
                    {
                        'id': 1,
                        'name': 'super_admin',
                        'description': 'Super Administrator',
                        'permissions': ['all'],
                        'user_count': roles_count.get('super_admin', 0)
                    },
                    {
                        'id': 2,
                        'name': 'admin',
                        'description': 'Administrator',
                        'permissions': ['manage_users', 'view_reports'],
                        'user_count': roles_count.get('admin', 0)
                    },
                    {
                        'id': 3,
                        'name': 'user',
                        'description': 'Regular User',
                        'permissions': ['upload_documents', 'chat'],
                        'user_count': roles_count.get('user', 0)
                    },
                    {
                        'id': 4,
                        'name': 'guest',
                        'description': 'Guest User',
                        'permissions': ['read_only'],
                        'user_count': roles_count.get('guest', 0)
                    }
                ]

                return context.res.json(roles_data)

            except AppwriteException as e:
                return context.res.json({'detail': f'Database error: {str(e)}'}, 500)

        return context.res.json({'detail': 'Method not allowed'}, 405)

    except Exception as e:
        return context.res.json({'detail': f'Internal server error: {str(e)}'}, 500)
