# 🚀 Appwrite Deployment Guide

Complete guide for deploying the AI Knowledge Assistant to Appwrite.

## 📋 Prerequisites

- **Appwrite Account**: Sign up at [appwrite.io](https://appwrite.io)
- **Appwrite CLI**: Install the CLI tool
  ```bash
  npm install -g appwrite-cli
  ```
- **Hugging Face Account**: Get an API token from [huggingface.co](https://huggingface.co/settings/tokens)

## 🛠️ Setup Steps

### 1. Create Appwrite Project

1. Go to [cloud.appwrite.io](https://cloud.appwrite.io)
2. Click "Create Project"
3. Name it "AI Knowledge Assistant"
4. Choose your preferred region

### 2. Get Project Credentials

After creating the project, note down:
- **Project ID**: Found in Settings → General
- **API Key**: Go to Settings → API Keys → Create API Key
  - Give it a name like "AI Assistant API Key"
  - Select all permissions (or at least: Databases, Functions, Storage)

### 3. Configure Environment

Create/update your `.env` file:

```bash
# Appwrite Configuration
APPWRITE_ENDPOINT=https://cloud.appwrite.io/v1
APPWRITE_PROJECT_ID=your-project-id-here
APPWRITE_API_KEY=your-api-key-here
APPWRITE_DATABASE_ID=default  # Usually 'default'

# Hugging Face API
HF_API_TOKEN=your-huggingface-api-token-here

# JWT Secret (generate a secure random key)
JWT_SECRET_KEY=your-super-secret-jwt-key-here

# Frontend Configuration
NEXT_PUBLIC_API_URL=https://cloud.appwrite.io/v1
NEXT_PUBLIC_APPWRITE_PROJECT_ID=your-project-id-here
NEXT_PUBLIC_APP_NAME=AI Knowledge Assistant
```

### 4. Create Database Collections

In your Appwrite console:

1. Go to **Database**
2. Create collections as defined in `appwrite.json`:
   - `users` - User management
   - `documents` - Document storage
   - `conversations` - Chat conversations
   - `messages` - Chat messages

### 5. Create Storage Bucket

1. Go to **Storage**
2. Create a bucket named `documents`
3. Configure permissions and file types

### 6. Deploy Functions

```bash
# Make script executable
chmod +x deploy-appwrite.sh

# Run deployment
./deploy-appwrite.sh
```

## 🔧 Manual Function Deployment

If the automated script fails, deploy functions manually:

```bash
# Login to Appwrite
appwrite login

# Create functions
appwrite functions create --functionId "health" --name "Health Check" --runtime "python-3.11" --entrypoint "src/main.py" --path "functions/health"
appwrite functions create --functionId "auth" --name "Authentication" --runtime "python-3.11" --entrypoint "src/main.py" --path "functions/auth"
appwrite functions create --functionId "users" --name "User Management" --runtime "python-3.11" --entrypoint "src/main.py" --path "functions/users"
appwrite functions create --functionId "documents" --name "Document Management" --runtime "python-3.11" --entrypoint "src/main.py" --path "functions/documents"
appwrite functions create --functionId "conversations" --name "Conversations & Chat" --runtime "python-3.11" --entrypoint "src/main.py" --path "functions/conversations"
appwrite functions create --functionId "admin" --name "Admin Operations" --runtime "python-3.11" --entrypoint "src/main.py" --path "functions/admin"

# Deploy function code
appwrite functions createDeployment --functionId "health" --code "functions/health" --activate true
appwrite functions createDeployment --functionId "auth" --code "functions/auth" --activate true
appwrite functions createDeployment --functionId "users" --code "functions/users" --activate true
appwrite functions createDeployment --functionId "documents" --code "functions/documents" --activate true
appwrite functions createDeployment --functionId "conversations" --code "functions/conversations" --activate true
appwrite functions createDeployment --functionId "admin" --code "functions/admin" --activate true
```

## 🌐 Frontend Deployment

### Deploy to Vercel

1. **Connect Repository**:
   ```bash
   # Push to GitHub first (if not already done)
   git add .
   git commit -m "Appwrite deployment configuration"
   git push origin master
   ```

2. **Deploy on Vercel**:
   - Go to [vercel.com](https://vercel.com)
   - Import your GitHub repository
   - Configure environment variables in Vercel dashboard
   - Deploy

### Environment Variables for Vercel

```
NEXT_PUBLIC_API_URL=https://cloud.appwrite.io/v1
NEXT_PUBLIC_APPWRITE_PROJECT_ID=your-project-id
NEXT_PUBLIC_APP_NAME=AI Knowledge Assistant
```

## 🧪 Testing Your Deployment

### Test Health Check
```bash
curl -X POST "https://cloud.appwrite.io/v1/functions/health/executions" \
  -H "Content-Type: application/json" \
  -H "X-Appwrite-Project: YOUR_PROJECT_ID" \
  -d '{"data": "{}", "method": "GET", "headers": {"Content-Type": "application/json"}, "path": "/health"}'
```

### Test User Registration
```bash
curl -X POST "https://cloud.appwrite.io/v1/functions/users/executions" \
  -H "Content-Type: application/json" \
  -H "X-Appwrite-Project: YOUR_PROJECT_ID" \
  -d '{
    "data": "{\"email\":\"admin@example.com\",\"password\":\"securepassword\",\"full_name\":\"Admin User\",\"role\":\"super_admin\"}",
    "method": "POST",
    "headers": {"Content-Type": "application/json"},
    "path": "/users"
  }'
```

## 🔧 Troubleshooting

### Function Deployment Issues

1. **Check Function Logs**:
   ```bash
   appwrite functions listExecutions --functionId "health"
   ```

2. **Common Issues**:
   - **Missing Environment Variables**: Check function settings in Appwrite console
   - **Database Permissions**: Ensure API key has proper permissions
   - **Import Errors**: Check function logs for Python import issues

### Frontend Issues

1. **CORS Errors**: Configure CORS in Appwrite console under Settings → CORS
2. **API Connection**: Verify `NEXT_PUBLIC_API_URL` and project ID
3. **Authentication**: Check JWT token configuration

### AI Functionality Issues

1. **HF API Token**: Verify your Hugging Face token is valid
2. **Rate Limits**: Hugging Face has rate limits on free tier
3. **Model Availability**: Some models may have temporary downtime

## 📊 Monitoring & Maintenance

### Function Monitoring
- **Execution Logs**: Check function execution history in Appwrite console
- **Performance Metrics**: Monitor execution time and success rates
- **Error Tracking**: Review failed executions and error messages

### Database Monitoring
- **Usage Statistics**: Monitor database size and query performance
- **Backup Strategy**: Set up automated backups in Appwrite

### Cost Optimization
- **Function Execution**: Monitor function execution time and frequency
- **Storage Usage**: Track file storage and database size
- **API Usage**: Monitor external API calls (Hugging Face)

## 🚀 Production Checklist

- ✅ **Environment Variables**: All secrets properly configured
- ✅ **Database Collections**: All required collections created
- ✅ **Storage Buckets**: Document storage configured
- ✅ **Function Deployments**: All functions deployed and active
- ✅ **CORS Settings**: Frontend domains whitelisted
- ✅ **SSL/TLS**: Automatic SSL from Appwrite
- ✅ **Backup Strategy**: Database backups configured
- ✅ **Monitoring**: Error tracking and alerts set up

## 🎯 Features Available

### 🤖 AI Capabilities
- **Document Summarization**: Upload and summarize PDF/text documents
- **Intelligent Q&A**: Ask questions about your uploaded content
- **Context-Aware Responses**: AI uses document content for answers

### 👥 User Management
- **Multi-Role System**: Super Admin, Admin, User, Guest roles
- **Secure Authentication**: JWT-based authentication
- **User Lifecycle**: Create, manage, and deactivate users

### 💾 Data Management
- **Document Upload**: Support for multiple file formats
- **Conversation History**: Persistent chat conversations
- **Admin Dashboard**: System monitoring and analytics

## 📞 Support

- **Appwrite Documentation**: [docs.appwrite.io](https://docs.appwrite.io)
- **Appwrite Community**: [discord.gg/appwrite](https://discord.gg/appwrite)
- **Hugging Face Docs**: [huggingface.co/docs](https://huggingface.co/docs)

---

**Your AI Knowledge Assistant is now deployed on Appwrite! 🎉**

Access your application through the Vercel deployment URL and start uploading documents for AI-powered analysis.
