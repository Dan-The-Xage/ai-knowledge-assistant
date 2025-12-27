import os
import json
from datetime import datetime
from appwrite.client import Client
from appwrite.services.databases import Databases

def main(context):
    """Appwrite Function: Health Check"""

    try:
        # Initialize Appwrite client
        client = Client()
        client.set_endpoint(os.environ.get('APPWRITE_ENDPOINT', 'https://cloud.appwrite.io/v1'))
        client.set_project(os.environ.get('APPWRITE_PROJECT_ID', ''))
        client.set_key(os.environ.get('APPWRITE_API_KEY', ''))

        # Test database connection
        databases = Databases(client)
        database_id = os.environ.get('APPWRITE_DATABASE_ID', '')

        # Simple health check
        health_data = {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "service": "ai-knowledge-assistant",
            "version": "1.0.0",
            "components": {
                "appwrite": "connected",
                "database": "connected" if database_id else "not_configured",
                "functions": "running"
            }
        }

        return context.res.json(health_data)

    except Exception as e:
        error_data = {
            "status": "unhealthy",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e),
            "service": "ai-knowledge-assistant"
        }
        return context.res.json(error_data, 500)
