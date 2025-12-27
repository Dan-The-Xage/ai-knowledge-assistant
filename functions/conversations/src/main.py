import os
import json
import requests
from datetime import datetime
from appwrite.client import Client
from appwrite.services.databases import Databases
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

def generate_ai_response(message: str, context_docs: list = None) -> str:
    """Generate AI response using Hugging Face API"""
    try:
        if not HF_API_TOKEN:
            return "AI service not configured. Please check API token."

        # Build context from documents if available
        context = ""
        if context_docs:
            context = "\n".join([doc.get('extracted_text', '')[:1000] for doc in context_docs[:3]])
            context = context[:2000]  # Limit context length

        # Create prompt
        if context:
            prompt = f"""<s>[INST] You are an AI assistant that helps users with their documents. Use the following context to answer the user's question accurately. If the answer isn't in the context, say so clearly.

Context from documents:
{context}

Question: {message}

Answer based only on the provided context. Be concise but helpful. [/INST]"""
        else:
            prompt = f"""<s>[INST] You are a helpful AI assistant. Answer the user's question clearly and accurately.

Question: {message} [/INST]"""

        # Call Hugging Face API
        response = requests.post(
            "https://api-inference.huggingface.co/models/mistralai/Mistral-7B-Instruct-v0.2",
            headers={"Authorization": f"Bearer {HF_API_TOKEN}"},
            json={
                "inputs": prompt,
                "parameters": {
                    "max_new_tokens": 512,
                    "temperature": 0.3,
                    "top_p": 0.95,
                    "do_sample": True
                },
                "options": {"wait_for_model": True}
            }
        )

        if response.status_code == 200:
            result = response.json()
            if isinstance(result, list) and result:
                generated_text = result[0].get('generated_text', '')
                # Remove the prompt from the response
                if '[INST]' in generated_text and '[/INST]' in generated_text:
                    # Extract only the response part
                    response_start = generated_text.find('[/INST]') + len('[/INST]')
                    ai_response = generated_text[response_start:].strip()
                else:
                    ai_response = generated_text.replace(prompt, '').strip()
                return ai_response or "I apologize, but I couldn't generate a proper response."
            else:
                return "AI service returned unexpected response format."
        else:
            print(f"HF API error: {response.status_code} - {response.text}")
            return "I'm sorry, but I'm having trouble generating a response right now. Please try again later."

    except Exception as e:
        print(f"AI response generation error: {str(e)}")
        return "I apologize, but there was an error processing your request. Please try again."

def find_relevant_documents(query: str, user_id: str, database, database_id: str, documents_collection_id: str):
    """Find relevant documents using simple text matching (since we can't do vector search easily)"""
    try:
        # Get user's documents
        documents = database.list_documents(
            database_id=database_id,
            collection_id=documents_collection_id,
            queries=[f"equal('uploaded_by', '{user_id}')"]
        )

        # Simple relevance scoring based on text matching
        relevant_docs = []
        query_lower = query.lower()

        for doc in documents['documents']:
            text = doc.get('extracted_text', '').lower()
            if query_lower in text:
                relevant_docs.append(doc)

        return relevant_docs[:3]  # Return top 3 matches

    except Exception as e:
        print(f"Document search error: {str(e)}")
        return []

def main(context):
    """Appwrite Function: Conversations Management"""

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

        database_id = os.environ.get('APPWRITE_DATABASE_ID', '')
        conversations_collection_id = os.environ.get('CONVERSATIONS_COLLECTION_ID', 'conversations')
        messages_collection_id = os.environ.get('MESSAGES_COLLECTION_ID', 'messages')
        documents_collection_id = os.environ.get('DOCUMENTS_COLLECTION_ID', 'documents')

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

        if method == 'POST' and 'chat' not in req.path:
            # Create new conversation
            title = body.get('title', f'Conversation {datetime.utcnow().strftime("%Y-%m-%d %H:%M")}')
            project_id = body.get('project_id')

            conversation_data = {
                'title': title,
                'user_id': current_user_id,
                'is_active': True,
                'created_at': datetime.utcnow().isoformat()
            }

            if project_id:
                conversation_data['project_id'] = project_id

            try:
                new_conversation = databases.create_document(
                    database_id=database_id,
                    collection_id=conversations_collection_id,
                    document_id='unique()',
                    data=conversation_data
                )

                response_data = {
                    'id': new_conversation['$id'],
                    'title': new_conversation['title'],
                    'user_id': new_conversation['user_id'],
                    'project_id': new_conversation.get('project_id'),
                    'is_active': new_conversation['is_active'],
                    'created_at': new_conversation['created_at'],
                    'message_count': 0
                }

                return context.res.json(response_data, 201)

            except AppwriteException as e:
                return context.res.json({'detail': f'Failed to create conversation: {str(e)}'}, 500)

        elif method == 'GET':
            # List conversations
            try:
                conversations = databases.list_documents(
                    database_id=database_id,
                    collection_id=conversations_collection_id,
                    queries=[f"equal('user_id', '{current_user_id}')"]
                )

                conversations_list = []
                for conv in conversations['documents']:
                    # Count messages
                    messages = databases.list_documents(
                        database_id=database_id,
                        collection_id=messages_collection_id,
                        queries=[f"equal('conversation_id', '{conv['$id']}')"]
                    )

                    conversations_list.append({
                        'id': conv['$id'],
                        'title': conv['title'],
                        'is_active': conv['is_active'],
                        'project_id': conv.get('project_id'),
                        'user_id': conv['user_id'],
                        'created_at': conv['created_at'],
                        'message_count': len(messages['documents'])
                    })

                return context.res.json(conversations_list)

            except AppwriteException as e:
                return context.res.json({'detail': f'Database error: {str(e)}'}, 500)

        elif method == 'POST' and 'chat' in req.path:
            # Handle chat message
            conversation_id = None
            for part in path_parts:
                if len(part) > 20:  # Assuming conversation ID is long
                    conversation_id = part
                    break

            if not conversation_id:
                return context.res.json({'detail': 'Conversation ID required'}, 400)

            user_message = body.get('content', '').strip()
            if not user_message:
                return context.res.json({'detail': 'Message content required'}, 400)

            try:
                # Verify conversation ownership
                conversation = databases.get_document(
                    database_id=database_id,
                    collection_id=conversations_collection_id,
                    document_id=conversation_id
                )

                if conversation['user_id'] != current_user_id:
                    return context.res.json({'detail': 'Unauthorized'}, 403)

                # Save user message
                user_message_data = {
                    'conversation_id': conversation_id,
                    'message_type': 'user',
                    'content': user_message,
                    'created_at': datetime.utcnow().isoformat()
                }

                user_msg_doc = databases.create_document(
                    database_id=database_id,
                    collection_id=messages_collection_id,
                    document_id='unique()',
                    data=user_message_data
                )

                # Find relevant documents
                relevant_docs = find_relevant_documents(
                    user_message, current_user_id, databases, database_id, documents_collection_id
                )

                # Generate AI response
                ai_response = generate_ai_response(user_message, relevant_docs)

                # Save AI message
                ai_message_data = {
                    'conversation_id': conversation_id,
                    'message_type': 'assistant',
                    'content': ai_response,
                    'created_at': datetime.utcnow().isoformat()
                }

                ai_msg_doc = databases.create_document(
                    database_id=database_id,
                    collection_id=messages_collection_id,
                    document_id='unique()',
                    data=ai_message_data
                )

                response_data = {
                    'conversation': {
                        'id': conversation['$id'],
                        'title': conversation['title']
                    },
                    'message': {
                        'id': ai_msg_doc['$id'],
                        'conversation_id': conversation_id,
                        'message_type': 'assistant',
                        'content': ai_response,
                        'created_at': ai_msg_doc['created_at']
                    },
                    'sources_used': len(relevant_docs)
                }

                return context.res.json(response_data)

            except AppwriteException as e:
                return context.res.json({'detail': f'Database error: {str(e)}'}, 500)

        return context.res.json({'detail': 'Method not allowed'}, 405)

    except Exception as e:
        return context.res.json({'detail': f'Internal server error: {str(e)}'}, 500)
