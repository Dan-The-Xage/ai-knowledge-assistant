# 🚀 Deploy to Pxxl.app

This guide covers deploying the AI Knowledge Assistant to [Pxxl.app](https://pxxl.app), a modern cloud platform for web applications.

## ✨ Why Pxxl.app?

- **One-click deployment** with Docker support
- **Built-in databases** (PostgreSQL, Redis)
- **Automatic scaling** and load balancing
- **SSL certificates** included
- **Custom domains** support
- **Real-time monitoring** and logs
- **Environment management** through dashboard

## 📋 Prerequisites

1. **Pxxl.app Account**: Sign up at [pxxl.app](https://pxxl.app)
2. **Pxxl CLI**: Install the command-line tool
   ```bash
   npm install -g @pxxl/cli
   ```
3. **Git**: Your code must be in a Git repository

## 🚀 Quick Start

### 1. Prepare Your Code

```bash
# Clone your repository (if not already done)
git clone <your-repo-url> knowledge-assistant
cd knowledge-assistant

# Copy environment template
cp pxxl.env.example .env
```

### 2. Configure Environment

Edit the `.env` file with your Pxxl.app settings:

```env
# Database - Get from Pxxl.app dashboard after deployment
DATABASE_URL=postgresql://user:password@host:5432/database_name

# Security - Generate a secure key
SECRET_KEY=your-super-secret-key-change-this-in-production-256-bits

# Frontend - Update with your Pxxl.app domain
NEXT_PUBLIC_API_URL=https://your-app-name.pxxl.app/api/v1

# Keep AI models lightweight for Pxxl.app
LLM_MODEL_NAME=microsoft/DialoGPT-small
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
```

### 3. Deploy

```bash
# Windows
deploy-pxxl.bat

# Linux/Mac
./deploy-pxxl.sh

# Or deploy manually
pxxl deploy
```

### 4. Access Your App

After deployment, Pxxl.app will provide a URL like:
```
https://your-app-name.pxxl.app
```

## 🔧 Configuration Files

### pxxl.json
The `pxxl.json` file defines your application configuration:

```json
{
  "name": "ai-knowledge-assistant",
  "version": "1.0.0",
  "build": {
    "dockerfile": "Dockerfile.pxxl",
    "context": "."
  },
  "services": {
    "backend": {
      "port": 8000,
      "health": "/health"
    },
    "frontend": {
      "port": 3000,
      "health": "/"
    }
  },
  "databases": {
    "postgresql": {
      "version": "15"
    }
  }
}
```

### Dockerfile.pxxl
Custom Dockerfile optimized for Pxxl.app that runs both frontend and backend services.

### supervisord.conf
Process manager configuration to run multiple services in one container.

## 📊 Database Setup

1. **After deployment**, go to your Pxxl.app dashboard
2. **Navigate to Databases** section
3. **Create a PostgreSQL database**
4. **Copy the connection URL** and update your `.env` file
5. **Redeploy** the application:
   ```bash
   pxxl deploy
   ```

## 🌐 Custom Domain

1. **Go to Domains** in Pxxl.app dashboard
2. **Add your custom domain**
3. **Update DNS records** as instructed
4. **Update environment variables**:
   ```env
   NEXT_PUBLIC_API_URL=https://your-custom-domain.com/api/v1
   ```

## 🔍 Monitoring & Debugging

### View Logs
```bash
pxxl logs
pxxl logs --follow  # Real-time logs
```

### Check Health
```bash
curl https://your-app.pxxl.app/api/v1/health
```

### Environment Variables
```bash
# View current environment
pxxl env

# Update environment variables
pxxl env set KEY=value
```

### Scale Your App
```bash
# Scale to multiple instances
pxxl scale 3

# View current scaling
pxxl ps
```

## 💰 Pricing & Resources

Pxxl.app offers generous free tiers:
- **Free Tier**: 512MB RAM, 1GB storage, 100GB bandwidth
- **Hobby**: $5/month - 1GB RAM, 10GB storage, 1TB bandwidth
- **Pro**: $25/month - 4GB RAM, 100GB storage, 10TB bandwidth

## 🆘 Troubleshooting

### Build Fails
```bash
# Check build logs
pxxl logs --build

# Common issues:
# 1. Missing dependencies in requirements.txt
# 2. Node.js version mismatch
# 3. Insufficient build resources
```

### Runtime Errors
```bash
# Check application logs
pxxl logs

# Restart application
pxxl restart
```

### Database Connection Issues
```bash
# Verify database URL in environment
pxxl env | grep DATABASE_URL

# Test database connection from app logs
pxxl logs | grep "database"
```

### Memory Issues
```bash
# Check memory usage
pxxl metrics

# Scale up if needed
pxxl scale 2
```

## 🔄 Updates & Maintenance

### Deploy Updates
```bash
# Make your changes
git add .
git commit -m "Update feature"
git push origin main

# Deploy automatically (if auto-deploy enabled)
# Or manually deploy
pxxl deploy
```

### Database Migrations
```bash
# Run migrations after deployment
pxxl run "cd /app && python -m alembic upgrade head"
```

### Backup Data
```bash
# Database backups are automatic
# Download backups from Pxxl.app dashboard
# File uploads are persisted automatically
```

## 🎯 Performance Optimization

### For Pxxl.app Deployment
1. **Use lightweight AI models** (already configured)
2. **Enable caching** with Redis
3. **Optimize images** and static assets
4. **Use CDN** for static files if needed

### Scaling Considerations
- **Horizontal scaling**: Pxxl.app handles this automatically
- **Database scaling**: Upgrade to larger database plans
- **Caching**: Use Redis for session and API caching

## 📞 Support

- **Pxxl.app Documentation**: [docs.pxxl.app](https://docs.pxxl.app)
- **Community**: [Discord/Forum link]
- **Issues**: Create GitHub issues for app-specific problems

---

🎉 **Your AI Knowledge Assistant is now live on Pxxl.app!**

Access your app at: `https://your-app-name.pxxl.app`
