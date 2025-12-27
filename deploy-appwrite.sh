#!/bin/bash

# Appwrite Deployment Script for AI Knowledge Assistant
# Usage: ./deploy-appwrite.sh

set -e

echo "🚀 Deploying AI Knowledge Assistant to Appwrite"

# Check if Appwrite CLI is installed
if ! command -v appwrite &> /dev/null; then
    echo "❌ Appwrite CLI not found. Please install it first:"
    echo "npm install -g appwrite-cli"
    echo "Or follow: https://appwrite.io/docs/tooling/command-line/installation"
    exit 1
fi

# Check if user is logged in
if ! appwrite account get &> /dev/null; then
    echo "🔐 Please login to Appwrite first:"
    appwrite login
fi

# Check if project exists
if [ ! -f "appwrite.json" ]; then
    echo "❌ appwrite.json not found. Please run this script from the project root."
    exit 1
fi

# Create environment file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "📝 Creating environment file from template..."
    cp pxxl.env.example .env
    echo "⚠️  IMPORTANT: Please configure the following in your .env file:"
    echo "   - HF_API_TOKEN: Your Hugging Face API token"
    echo "   - APPWRITE_PROJECT_ID: Your Appwrite project ID"
    echo "   - APPWRITE_API_KEY: Your Appwrite API key with necessary permissions"
    echo ""
    read -p "Press Enter after you've configured the .env file..."
fi

# Load environment variables
if [ -f ".env" ]; then
    export $(cat .env | xargs)
fi

# Check for required environment variables
if [ -z "$APPWRITE_PROJECT_ID" ]; then
    echo "❌ APPWRITE_PROJECT_ID not set. Please add it to your .env file."
    exit 1
fi

if [ -z "$HF_API_TOKEN" ]; then
    echo "⚠️  WARNING: HF_API_TOKEN not set. AI functionality will not work!"
    read -p "Press Enter to continue anyway..."
fi

echo "📦 Deploying Appwrite functions..."

# Deploy all functions
appwrite functions create \
    --functionId "health" \
    --name "Health Check" \
    --runtime "python-3.11" \
    --entrypoint "src/main.py" \
    --path "functions/health"

appwrite functions create \
    --functionId "auth" \
    --name "Authentication" \
    --runtime "python-3.11" \
    --entrypoint "src/main.py" \
    --path "functions/auth"

appwrite functions create \
    --functionId "users" \
    --name "User Management" \
    --runtime "python-3.11" \
    --entrypoint "src/main.py" \
    --path "functions/users"

appwrite functions create \
    --functionId "documents" \
    --name "Document Management" \
    --runtime "python-3.11" \
    --entrypoint "src/main.py" \
    --path "functions/documents"

appwrite functions create \
    --functionId "conversations" \
    --name "Conversations & Chat" \
    --runtime "python-3.11" \
    --entrypoint "src/main.py" \
    --path "functions/conversations"

appwrite functions create \
    --functionId "admin" \
    --name "Admin Operations" \
    --runtime "python-3.11" \
    --entrypoint "src/main.py" \
    --path "functions/admin"

echo "🗄️ Setting up database collections..."

# Create database collections (this would need to be done via Appwrite console or API)
echo "⚠️  IMPORTANT: Please create the following in your Appwrite console:"
echo "   1. Database collections as defined in appwrite.json"
echo "   2. Storage bucket for documents"
echo "   3. Set environment variables in each function"
echo ""

# Set environment variables for functions
echo "🔧 Configuring function environment variables..."

# Common environment variables for all functions
ENV_VARS="APPWRITE_ENDPOINT=https://cloud.appwrite.io/v1,APPWRITE_PROJECT_ID=$APPWRITE_PROJECT_ID,JWT_SECRET_KEY=$JWT_SECRET_KEY"

# Health function
appwrite functions createVariable \
    --functionId "health" \
    --key "APPWRITE_ENDPOINT" \
    --value "https://cloud.appwrite.io/v1"

appwrite functions createVariable \
    --functionId "health" \
    --key "APPWRITE_PROJECT_ID" \
    --key "APPWRITE_API_KEY" \
    --value "$APPWRITE_API_KEY"

# Auth function
appwrite functions createVariable \
    --functionId "auth" \
    --key "APPWRITE_ENDPOINT" \
    --value "https://cloud.appwrite.io/v1"

appwrite functions createVariable \
    --functionId "auth" \
    --key "APPWRITE_PROJECT_ID" \
    --value "$APPWRITE_PROJECT_ID"

appwrite functions createVariable \
    --functionId "auth" \
    --key "APPWRITE_API_KEY" \
    --value "$APPWRITE_API_KEY"

appwrite functions createVariable \
    --functionId "auth" \
    --key "JWT_SECRET_KEY" \
    --value "$JWT_SECRET_KEY"

# Users function
appwrite functions createVariable \
    --functionId "users" \
    --key "APPWRITE_ENDPOINT" \
    --value "https://cloud.appwrite.io/v1"

appwrite functions createVariable \
    --functionId "users" \
    --key "APPWRITE_PROJECT_ID" \
    --value "$APPWRITE_PROJECT_ID"

appwrite functions createVariable \
    --functionId "users" \
    --key "APPWRITE_API_KEY" \
    --value "$APPWRITE_API_KEY"

appwrite functions createVariable \
    --functionId "users" \
    --key "JWT_SECRET_KEY" \
    --value "$JWT_SECRET_KEY"

appwrite functions createVariable \
    --functionId "users" \
    --key "USERS_COLLECTION_ID" \
    --value "users"

# Documents function
appwrite functions createVariable \
    --functionId "documents" \
    --key "APPWRITE_ENDPOINT" \
    --value "https://cloud.appwrite.io/v1"

appwrite functions createVariable \
    --functionId "documents" \
    --key "APPWRITE_PROJECT_ID" \
    --value "$APPWRITE_PROJECT_ID"

appwrite functions createVariable \
    --functionId "documents" \
    --key "APPWRITE_API_KEY" \
    --value "$APPWRITE_API_KEY"

appwrite functions createVariable \
    --functionId "documents" \
    --key "JWT_SECRET_KEY" \
    --value "$JWT_SECRET_KEY"

appwrite functions createVariable \
    --functionId "documents" \
    --key "DOCUMENTS_COLLECTION_ID" \
    --value "documents"

appwrite functions createVariable \
    --functionId "documents" \
    --key "STORAGE_BUCKET_ID" \
    --value "documents"

appwrite functions createVariable \
    --functionId "documents" \
    --key "HF_API_TOKEN" \
    --value "$HF_API_TOKEN"

# Conversations function
appwrite functions createVariable \
    --functionId "conversations" \
    --key "APPWRITE_ENDPOINT" \
    --value "https://cloud.appwrite.io/v1"

appwrite functions createVariable \
    --functionId "conversations" \
    --key "APPWRITE_PROJECT_ID" \
    --value "$APPWRITE_PROJECT_ID"

appwrite functions createVariable \
    --functionId "conversations" \
    --key "APPWRITE_API_KEY" \
    --value "$APPWRITE_API_KEY"

appwrite functions createVariable \
    --functionId "conversations" \
    --key "JWT_SECRET_KEY" \
    --value "$JWT_SECRET_KEY"

appwrite functions createVariable \
    --functionId "conversations" \
    --key "CONVERSATIONS_COLLECTION_ID" \
    --value "conversations"

appwrite functions createVariable \
    --functionId "conversations" \
    --key "MESSAGES_COLLECTION_ID" \
    --value "messages"

appwrite functions createVariable \
    --functionId "conversations" \
    --key "DOCUMENTS_COLLECTION_ID" \
    --value "documents"

appwrite functions createVariable \
    --functionId "conversations" \
    --key "HF_API_TOKEN" \
    --value "$HF_API_TOKEN"

# Admin function
appwrite functions createVariable \
    --functionId "admin" \
    --key "APPWRITE_ENDPOINT" \
    --value "https://cloud.appwrite.io/v1"

appwrite functions createVariable \
    --functionId "admin" \
    --key "APPWRITE_PROJECT_ID" \
    --value "$APPWRITE_PROJECT_ID"

appwrite functions createVariable \
    --functionId "admin" \
    --key "APPWRITE_API_KEY" \
    --value "$APPWRITE_API_KEY"

appwrite functions createVariable \
    --functionId "admin" \
    --key "JWT_SECRET_KEY" \
    --value "$JWT_SECRET_KEY"

appwrite functions createVariable \
    --functionId "admin" \
    --key "USERS_COLLECTION_ID" \
    --value "users"

appwrite functions createVariable \
    --functionId "admin" \
    --key "DOCUMENTS_COLLECTION_ID" \
    --value "documents"

appwrite functions createVariable \
    --functionId "admin" \
    --key "CONVERSATIONS_COLLECTION_ID" \
    --value "conversations"

echo "🚀 Deploying function code..."

# Deploy function code
appwrite functions createDeployment \
    --functionId "health" \
    --entrypoint "src/main.py" \
    --code "functions/health" \
    --activate true

appwrite functions createDeployment \
    --functionId "auth" \
    --entrypoint "src/main.py" \
    --code "functions/auth" \
    --activate true

appwrite functions createDeployment \
    --functionId "users" \
    --entrypoint "src/main.py" \
    --code "functions/users" \
    --activate true

appwrite functions createDeployment \
    --functionId "documents" \
    --entrypoint "src/main.py" \
    --code "functions/documents" \
    --activate true

appwrite functions createDeployment \
    --functionId "conversations" \
    --entrypoint "src/main.py" \
    --code "functions/conversations" \
    --activate true

appwrite functions createDeployment \
    --functionId "admin" \
    --entrypoint "src/main.py" \
    --code "functions/admin" \
    --activate true

echo ""
echo "🎉 Deployment complete!"
echo ""
echo "📋 Next Steps:"
echo "1. ✅ Create database collections in Appwrite console"
echo "2. ✅ Create storage bucket for documents"
echo "3. ✅ Update frontend configuration"
echo "4. ✅ Test the deployed functions"
echo ""
echo "🔗 Function URLs:"
echo "Health: https://cloud.appwrite.io/v1/functions/health/executions"
echo "Auth: https://cloud.appwrite.io/v1/functions/auth/executions"
echo "Users: https://cloud.appwrite.io/v1/functions/users/executions"
echo "Documents: https://cloud.appwrite.io/v1/functions/documents/executions"
echo "Conversations: https://cloud.appwrite.io/v1/functions/conversations/executions"
echo "Admin: https://cloud.appwrite.io/v1/functions/admin/executions"
echo ""
echo "🧪 Test Commands:"
echo "curl -X GET 'https://cloud.appwrite.io/v1/functions/health/executions' -H 'Content-Type: application/json'"
echo ""
echo "📚 Documentation: https://appwrite.io/docs"
echo ""
echo "⚠️  Remember to:"
echo "   - Set up proper CORS settings in Appwrite"
echo "   - Configure authentication rules"
echo "   - Test all functions thoroughly"
echo "   - Monitor function execution times and costs"
