# 🚀 Pxxl.app + Supabase Deployment Guide

Complete guide for deploying the AI Knowledge Assistant with **Pxxl.app (Frontend)** and **Supabase (Backend)**.

## 📋 Architecture Overview

### **Frontend (Pxxl.app)**
- **Next.js Application** with modern UI
- **Direct AI Integration** via Hugging Face API
- **Supabase Client** for database operations
- **File Upload Handling** with Supabase Storage

### **Backend (Supabase)**
- **PostgreSQL Database** for user and document data
- **Supabase Storage** for file uploads
- **Row Level Security** policies
- **Real-time subscriptions** capabilities

### **AI Layer (Hugging Face)**
- **Mistral-7B LLM** for intelligent responses
- **BGE Embeddings** for semantic search
- **Direct API calls** from frontend
- **No server-side AI processing**

## 🛠️ Step-by-Step Setup

### **Step 1: Set Up Supabase (Backend)**

#### 1.1 Create Supabase Project
1. Go to [supabase.com](https://supabase.com)
2. Click "New Project"
3. Choose organization and region
4. Set project name: "AI Knowledge Assistant"
5. Set database password (save this!)

#### 1.2 Configure Database Schema
1. Go to **SQL Editor** in Supabase dashboard
2. Copy and run the contents of `supabase-schema.sql`
3. This creates all tables, indexes, and RLS policies

#### 1.3 Set Up Storage
1. Go to **Storage** in Supabase dashboard
2. Click "Create bucket"
3. Bucket name: `documents`
4. Make it **private** (not public)
5. Set file size limit: 10MB
6. Allowed MIME types: `pdf,doc,docx,txt,xls,xlsx`

#### 1.4 Get API Credentials
From **Settings → API** in Supabase dashboard:
- **Project URL**: `https://your-project-id.supabase.co`
- **anon/public key**: `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...`
- **service_role key**: `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...` (keep secret!)

### **Step 2: Prepare Frontend Code**

#### 2.1 Install Dependencies
```bash
cd frontend
npm install
# Supabase client should already be in package.json
```

#### 2.2 Configure Environment Variables
Create `.env.local` in the frontend directory:
```bash
# Supabase Configuration
NEXT_PUBLIC_SUPABASE_URL=https://your-project-id.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key-here

# Hugging Face API
NEXT_PUBLIC_HF_API_TOKEN=your-huggingface-api-token-here

# Application Settings
NEXT_PUBLIC_APP_NAME=AI Knowledge Assistant
NEXT_PUBLIC_MAX_FILE_SIZE=10485760
NEXT_PUBLIC_CHUNK_SIZE=1000
NEXT_PUBLIC_MAX_RETRIEVAL_DOCS=5
```

#### 2.3 Test Locally (Optional)
```bash
npm run dev
# Visit http://localhost:3000
# Test with your Supabase credentials
```

### **Step 3: Deploy Frontend to Pxxl.app**

#### 3.1 Prepare Repository
```bash
# Ensure all changes are committed
git add .
git commit -m "Deploy to Pxxl.app + Supabase architecture"
git push origin master
```

#### 3.2 Deploy to Pxxl.app
1. Go to [pxxl.app](https://pxxl.app)
2. Click "Create new app"
3. Connect your GitHub repository
4. Select repository: `Dan-The-Xage/ai-knowledge-assistant`
5. **Important**: Pxxl.app should automatically detect the `pxxl.json` configuration

#### 3.3 Configure Build Settings
Pxxl.app should automatically use:
- **Dockerfile**: `Dockerfile.pxxl-frontend`
- **Port**: 3000
- **Build Context**: Repository root

#### 3.4 Set Environment Variables in Pxxl.app Dashboard
Go to your app's **Environment** tab and add:

```
# Supabase Configuration
NEXT_PUBLIC_SUPABASE_URL=https://your-project-id.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key-here

# Hugging Face API
NEXT_PUBLIC_HF_API_TOKEN=your-huggingface-api-token-here

# Application Settings
NEXT_PUBLIC_APP_NAME=AI Knowledge Assistant
NEXT_PUBLIC_MAX_FILE_SIZE=10485760
NEXT_PUBLIC_CHUNK_SIZE=1000
NEXT_PUBLIC_MAX_RETRIEVAL_DOCS=5
```

#### 3.5 Deploy
Click **"Deploy"** and wait for completion!

## 🔧 Post-Deployment Configuration

### **Step 4: Update Domain References**

After deployment, update the Supabase URL in Pxxl.app if needed:
- Your Pxxl.app domain: `https://your-app-name.pxxl.app`
- This is used for CORS configuration in Supabase

### **Step 5: Configure Supabase CORS**

In Supabase dashboard → **Settings → API**:
- Add your Pxxl.app domain to "Site URL"
- Add `https://your-app-name.pxxl.app` to allowed origins

## 🧪 Testing Your Deployment

### **Test 1: Health Check**
```bash
curl https://your-app-name.pxxl.app/api/health
```

### **Test 2: User Registration**
1. Visit `https://your-app-name.pxxl.app`
2. Try creating a new account
3. Check Supabase Auth users to confirm

### **Test 3: Document Upload**
1. Login to the application
2. Upload a PDF or text document
3. Check Supabase Storage bucket for the file
4. Check documents table for metadata

### **Test 4: AI Chat**
1. Start a new conversation
2. Ask a question about your uploaded document
3. Verify AI responses are generated
4. Check conversations and messages tables

## 📊 Architecture Benefits

### **Scalability**
- ✅ **Frontend**: Auto-scaling on Pxxl.app
- ✅ **Backend**: Supabase handles scaling automatically
- ✅ **AI**: Hugging Face API scales with usage

### **Cost Efficiency**
- ✅ **Free Tiers**: All services have generous free tiers
- ✅ **Pay-as-you-go**: Only pay for actual usage
- ✅ **No server management**: Fully managed services

### **Developer Experience**
- ✅ **Real-time**: Supabase provides real-time subscriptions
- ✅ **Type Safety**: Full TypeScript integration
- ✅ **Security**: Built-in RLS and authentication
- ✅ **Performance**: CDN and caching included

## 🔧 Troubleshooting

### **Build Failures**
```bash
# Check Pxxl.app build logs
# Common issues:
# - Missing environment variables
# - Node.js version mismatch
# - npm install failures
```

### **Runtime Errors**
```bash
# Check browser console for JavaScript errors
# Check Pxxl.app application logs
# Verify Supabase credentials
```

### **Database Issues**
```bash
# Check Supabase dashboard for errors
# Verify RLS policies are correct
# Test database connections manually
```

### **AI Service Issues**
```bash
# Check Hugging Face API token validity
# Verify rate limits haven't been exceeded
# Test API calls directly
```

## 📋 Environment Variables Reference

### **Required Variables**
```bash
# Supabase (from Supabase dashboard)
NEXT_PUBLIC_SUPABASE_URL=https://xxx.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJhbGci...

# Hugging Face (get from huggingface.co)
NEXT_PUBLIC_HF_API_TOKEN=hf_xxxxxxxxxxxxxxxxxx
```

### **Optional Variables**
```bash
# Application customization
NEXT_PUBLIC_APP_NAME=Your App Name
NEXT_PUBLIC_MAX_FILE_SIZE=10485760
NEXT_PUBLIC_CHUNK_SIZE=1000
NEXT_PUBLIC_MAX_RETRIEVAL_DOCS=5

# Supabase service role (for admin operations)
SUPABASE_SERVICE_ROLE_KEY=eyJhbGci...
```

## 🎯 Production Checklist

- ✅ **Supabase project created** and configured
- ✅ **Database schema applied** (`supabase-schema.sql`)
- ✅ **Storage bucket created** with proper permissions
- ✅ **Pxxl.app deployment completed**
- ✅ **Environment variables configured** in both services
- ✅ **CORS settings updated** in Supabase
- ✅ **Domain references updated** if using custom domain
- ✅ **SSL certificates active** (automatic)
- ✅ **Monitoring enabled** (check dashboards)
- ✅ **Backup strategy configured** (Supabase auto-backups)

## 🚀 Scaling & Performance

### **Frontend Scaling (Pxxl.app)**
- Automatically scales based on traffic
- Multiple instances for high availability
- CDN integration for static assets

### **Backend Scaling (Supabase)**
- PostgreSQL automatically scales
- Connection pooling built-in
- Read replicas for high traffic

### **AI Scaling (Hugging Face)**
- API-based scaling
- Rate limiting handled automatically
- Multiple model sizes available

## 💰 Cost Optimization

### **Free Tier Limits**
- **Pxxl.app**: 512MB RAM, 1 instance
- **Supabase**: 500MB database, 50MB storage
- **Hugging Face**: Rate-limited free tier

### **Paid Upgrades**
- Scale instances as needed
- Upgrade database size
- Increase API rate limits

---

**🎉 Your AI Knowledge Assistant is now deployed with enterprise-grade architecture!**

The combination of **Pxxl.app (Frontend) + Supabase (Backend) + Hugging Face (AI)** provides a scalable, secure, and cost-effective solution for AI-powered document analysis.

**Access your application at: `https://your-app-name.pxxl.app`**