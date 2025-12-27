import os
import json
import hashlib
from datetime import datetime, timedelta
from appwrite.client import Client
from appwrite.services.databases import Databases
from appwrite.services.users import Users
from appwrite.exception import AppwriteException
import jwt

# JWT Configuration
SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'your-secret-key-change-in-production')
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 480

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return hashlib.sha256(plain_password.encode()).hexdigest() == hashed_password

def get_password_hash(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def main(context):
    """Appwrite Function: Authentication"""

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
        users_service = Users(client)

        database_id = os.environ.get('APPWRITE_DATABASE_ID', '')
        users_collection_id = os.environ.get('USERS_COLLECTION_ID', 'users')

        if method == 'POST' and 'login' in req.path:
            # Handle login
            email = body.get('email')
            password = body.get('password')
            account_type = body.get('account_type')

            if not email or not password or not account_type:
                return context.res.json({'detail': 'Missing credentials'}, 400)

            # Query user from database
            try:
                user_docs = databases.list_documents(
                    database_id=database_id,
                    collection_id=users_collection_id,
                    queries=[f"equal('email', '{email}')"]
                )

                if not user_docs['documents']:
                    return context.res.json({'detail': 'Incorrect email or password'}, 401)

                user = user_docs['documents'][0]

                # Verify password
                if not verify_password(password, user['hashed_password']):
                    return context.res.json({'detail': 'Incorrect email or password'}, 401)

                # Check if account is active
                if not user.get('is_active', True):
                    return context.res.json({'detail': 'Account is disabled'}, 400)

                # Verify role matches account type
                if user.get('role') != account_type:
                    return context.res.json({
                        'detail': f'Wrong account type. You are not a {account_type.replace("_", " ").title()}.'
                    }, 401)

                # Create access token
                access_token = create_access_token({"sub": user['$id'], "email": user['email']})

                user_data = {
                    "id": user['$id'],
                    "email": user['email'],
                    "full_name": user['full_name'],
                    "role": user['role'],
                    "department": user.get('department'),
                    "job_title": user.get('job_title'),
                    "is_active": user['is_active']
                }

                return context.res.json({
                    "access_token": access_token,
                    "token_type": "bearer",
                    "user": user_data
                })

            except AppwriteException as e:
                return context.res.json({'detail': f'Database error: {str(e)}'}, 500)

        elif method == 'GET' and 'roles' in req.path:
            # Get available roles
            roles = [
                {"id": "super_admin", "name": "super_admin", "description": "Super Administrator"},
                {"id": "admin", "name": "admin", "description": "Administrator"},
                {"id": "user", "name": "user", "description": "Regular User"},
                {"id": "guest", "name": "guest", "description": "Guest User"}
            ]
            return context.res.json(roles)

        elif method == 'GET' and 'me' in req.path:
            # Get current user profile
            auth_header = req.headers.get('Authorization', '')
            if not auth_header.startswith('Bearer '):
                return context.res.json({'detail': 'Not authenticated'}, 401)

            token = auth_header.split(' ')[1]
            try:
                payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
                user_id = payload.get('sub')

                # Get user from database
                user_doc = databases.get_document(
                    database_id=database_id,
                    collection_id=users_collection_id,
                    document_id=user_id
                )

                user_data = {
                    "id": user_doc['$id'],
                    "email": user_doc['email'],
                    "full_name": user_doc['full_name'],
                    "role": user_doc['role'],
                    "department": user_doc.get('department'),
                    "job_title": user_doc.get('job_title'),
                    "is_active": user_doc['is_active'],
                    "is_verified": True,
                    "created_at": user_doc['created_at']
                }

                return context.res.json(user_data)

            except jwt.ExpiredSignatureError:
                return context.res.json({'detail': 'Token expired'}, 401)
            except jwt.JWTError:
                return context.res.json({'detail': 'Invalid token'}, 401)
            except AppwriteException as e:
                return context.res.json({'detail': f'Database error: {str(e)}'}, 500)

        return context.res.json({'detail': 'Method not allowed'}, 405)

    except Exception as e:
        return context.res.json({'detail': f'Internal server error: {str(e)}'}, 500)
