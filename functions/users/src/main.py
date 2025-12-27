import os
import json
import hashlib
from datetime import datetime
from appwrite.client import Client
from appwrite.services.databases import Databases
from appwrite.services.users import Users
from appwrite.exception import AppwriteException
import jwt

# JWT Configuration
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

def get_password_hash(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def main(context):
    """Appwrite Function: User Management"""

    try:
        # Get request data
        req = context.req
        method = req.method
        body = json.loads(req.body) if req.body else {}
        path_parts = req.path.strip('/').split('/')

        # Initialize Appwrite client
        client = Client()
        client.set_endpoint(os.environ.get('APPWRITE_ENDPOINT', 'https://cloud.appwrite.io/v1'))
        client.set_project(os.environ.get('APPWRITE_PROJECT_ID', ''))
        client.set_key(os.environ.get('APPWRITE_API_KEY', ''))

        databases = Databases(client)
        users_service = Users(client)

        database_id = os.environ.get('APPWRITE_DATABASE_ID', '')
        users_collection_id = os.environ.get('USERS_COLLECTION_ID', 'users')

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

        # Get current user details for role checking
        try:
            current_user_doc = databases.get_document(
                database_id=database_id,
                collection_id=users_collection_id,
                document_id=current_user_id
            )
            current_user_role = current_user_doc.get('role', 'user')
        except AppwriteException:
            return context.res.json({'detail': 'User not found'}, 404)

        if method == 'POST':
            # Create new user
            if current_user_role not in ['admin', 'super_admin']:
                return context.res.json({'detail': 'Only administrators can create users'}, 403)

            email = body.get('email')
            password = body.get('password')
            full_name = body.get('full_name')
            role = body.get('role', 'user')
            department = body.get('department')
            job_title = body.get('job_title')
            is_active = body.get('is_active', True)

            if not email or not password or not full_name:
                return context.res.json({'detail': 'Missing required fields'}, 400)

            # Check if user already exists
            try:
                existing_users = databases.list_documents(
                    database_id=database_id,
                    collection_id=users_collection_id,
                    queries=[f"equal('email', '{email}')"]
                )
                if existing_users['documents']:
                    return context.res.json({'detail': 'Email already registered'}, 400)
            except AppwriteException as e:
                return context.res.json({'detail': f'Database error: {str(e)}'}, 500)

            # Admin role restrictions
            if current_user_role == 'admin' and role in ['super_admin', 'admin']:
                return context.res.json({'detail': 'Only Super Admin can create admin accounts'}, 403)

            # Create user document
            user_data = {
                'email': email,
                'full_name': full_name,
                'role': role,
                'is_active': is_active,
                'created_at': datetime.utcnow().isoformat()
            }

            if department:
                user_data['department'] = department
            if job_title:
                user_data['job_title'] = job_title

            # Hash password for storage
            user_data['hashed_password'] = get_password_hash(password)

            try:
                new_user = databases.create_document(
                    database_id=database_id,
                    collection_id=users_collection_id,
                    document_id='unique()',  # Auto-generate ID
                    data=user_data
                )

                # Return user data (exclude password)
                response_data = {
                    'id': new_user['$id'],
                    'email': new_user['email'],
                    'full_name': new_user['full_name'],
                    'role': new_user['role'],
                    'department': new_user.get('department'),
                    'job_title': new_user.get('job_title'),
                    'is_active': new_user['is_active'],
                    'is_verified': True,
                    'created_at': new_user['created_at']
                }

                return context.res.json(response_data, 201)

            except AppwriteException as e:
                return context.res.json({'detail': f'Failed to create user: {str(e)}'}, 500)

        elif method == 'GET':
            # List users
            if current_user_role not in ['admin', 'super_admin']:
                return context.res.json({'detail': 'Only administrators can list users'}, 403)

            try:
                # Build queries
                queries = []
                role_filter = body.get('role')
                is_active_filter = body.get('is_active')
                search_term = body.get('search')

                if role_filter:
                    queries.append(f"equal('role', '{role_filter}')")
                if is_active_filter is not None:
                    queries.append(f"equal('is_active', {str(is_active_filter).lower()})")
                if search_term:
                    # Appwrite doesn't support complex search, so we'll get all and filter
                    pass

                users_docs = databases.list_documents(
                    database_id=database_id,
                    collection_id=users_collection_id,
                    queries=queries
                )

                users_list = []
                for user in users_docs['documents']:
                    # Apply search filter if specified
                    if search_term:
                        search_lower = search_term.lower()
                        if (search_lower not in user.get('email', '').lower() and
                            search_lower not in user.get('full_name', '').lower()):
                            continue

                    users_list.append({
                        'id': user['$id'],
                        'email': user['email'],
                        'full_name': user['full_name'],
                        'role': user['role'],
                        'department': user.get('department'),
                        'job_title': user.get('job_title'),
                        'is_active': user['is_active'],
                        'is_verified': True,
                        'created_at': user['created_at']
                    })

                return context.res.json(users_list)

            except AppwriteException as e:
                return context.res.json({'detail': f'Database error: {str(e)}'}, 500)

        return context.res.json({'detail': 'Method not allowed'}, 405)

    except Exception as e:
        return context.res.json({'detail': f'Internal server error: {str(e)}'}, 500)
