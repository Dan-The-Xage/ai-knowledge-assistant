# 🚀 Koyeb Deployment Guide

Complete guide for deploying the AI Knowledge Assistant to Koyeb.

## 📋 Prerequisites

- **Koyeb Account**: Sign up at [koyeb.com](https://koyeb.com)
- **GitHub Repository**: Your code pushed to GitHub
- **Environment Variables**: API keys and configuration ready

## 🛠️ Deployment Methods

### **Method 1: Single Container (Recommended)**

#### 1. Create New App
1. Go to [app.koyeb.com](https://app.koyeb.com)
2. Click "Create App" → "GitHub"
3. Connect your GitHub account
4. Select repository: `Dan-The-Xage/ai-knowledge-assistant`

#### 2. Configure Build Settings
```
Build Type: Dockerfile
Dockerfile Path: Dockerfile.koyeb
Work Directory: /
```

#### 3. Configure Environment Variables
Add these environment variables:

```
# Database (if using external DB)
DATABASE_URL=postgresql://user:password@host:5432/dbname

# AI Configuration
HF_API_TOKEN=your-huggingface-api-token-here
LLM_MODEL_NAME=mistralai/Mistral-7B-Instruct-v0.2
EMBEDDING_MODEL=BAAI/bge-small-en-v1.5

# Security
SECRET_KEY=your-super-secret-key-here

# Appwrite (if using)
APPWRITE_PROJECT_ID=your-appwrite-project-id
APPWRITE_API_KEY=your-appwrite-api-key
```

#### 4. Configure Ports
```
Port: 3000 (Frontend)
Port: 8000 (Backend)
```

#### 5. Deploy
Click "Deploy" and wait for completion.

### **Method 2: Separate Frontend & Backend**

#### Deploy Backend First
1. Create new app with `koyeb-backend.yaml` configuration
2. Set environment variables for backend
3. Deploy and note the backend URL

#### Deploy Frontend Second
1. Create new app with `koyeb-frontend.yaml` configuration
2. Set `NEXT_PUBLIC_API_URL` to your backend URL
3. Deploy frontend

## 📋 Environment Variables

### Required Variables
```bash
# AI & ML
HF_API_TOKEN=your-huggingface-api-token-here

# Security
SECRET_KEY=your-secure-random-key-here

# Database (optional - uses SQLite by default)
DATABASE_URL=postgresql://user:password@host:5432/dbname

# Appwrite (if using Appwrite instead of local DB)
APPWRITE_PROJECT_ID=your-project-id
APPWRITE_API_KEY=your-api-key
```

### Frontend Variables
```bash
NEXT_PUBLIC_API_URL=https://your-backend-app.koyeb.app
NEXT_PUBLIC_APPWRITE_PROJECT_ID=your-project-id
NEXT_PUBLIC_APP_NAME=AI Knowledge Assistant
```

## 🔧 Configuration Files

### `koyeb.yaml` - Full Stack Deployment
Deploys both frontend and backend in one application.

### `koyeb-frontend.yaml` - Frontend Only
Deploys only the Next.js frontend application.

### `koyeb-backend.yaml` - Backend Only
Deploys only the FastAPI backend application.

### `Dockerfile.koyeb` - Container Configuration
Optimized Docker configuration for Koyeb deployment.

## 🌐 Accessing Your Application

After deployment, Koyeb will provide:
- **Frontend URL**: `https://your-app.koyeb.app`
- **Backend API**: `https://your-backend.koyeb.app`

## 🧪 Testing Deployment

### Test Health Check
```bash
curl https://your-app.koyeb.app/api/v1/health
```

### Test Frontend
```bash
curl https://your-app.koyeb.app
```

## 📊 Scaling & Performance

### Automatic Scaling
Koyeb automatically scales based on:
- CPU usage
- Memory usage
- Request volume

### Performance Optimization
- **Instances**: 1-10 automatic scaling
- **Regions**: Choose closest to users
- **Caching**: Built-in CDN for static assets

## 🔍 Monitoring & Logs

### Application Logs
```bash
# View logs in Koyeb dashboard
# Or use koyeb CLI:
koyeb services logs your-service-name
```

### Health Monitoring
- Built-in health checks
- Automatic restarts on failure
- Performance metrics dashboard

## 💰 Pricing & Resources

### Free Tier
- 512MB RAM per instance
- 1GB storage
- 100GB bandwidth
- 1 instance limit

### Paid Plans
- Scale to multiple instances
- Higher resource limits
- Advanced monitoring
- Custom domains

## 🚀 Production Checklist

- ✅ **Environment Variables**: All secrets configured
- ✅ **Database**: Connected and initialized
- ✅ **AI Services**: Hugging Face token working
- ✅ **Domains**: Custom domain configured (optional)
- ✅ **SSL**: Automatic SSL certificates
- ✅ **Monitoring**: Health checks enabled
- ✅ **Scaling**: Auto-scaling configured

## 🔧 Troubleshooting

### Build Failures
1. Check build logs in Koyeb dashboard
2. Verify Dockerfile syntax
3. Ensure all dependencies are available

### Runtime Errors
1. Check application logs
2. Verify environment variables
3. Test API endpoints individually

### Performance Issues
1. Monitor resource usage
2. Scale instances if needed
3. Optimize database queries

## 📞 Support

- **Koyeb Documentation**: [docs.koyeb.com](https://docs.koyeb.com)
- **Community Support**: [community.koyeb.com](https://community.koyeb.com)
- **Status Page**: [status.koyeb.com](https://status.koyeb.com)

---

**Your AI Knowledge Assistant is now ready for Koyeb deployment! 🎉**

Choose your preferred deployment method and deploy your production-ready AI application with ease.
