# 🚀 AI Knowledge Assistant - Deployment Guide

This guide covers deploying the AI Knowledge Assistant platform as a hosted web application.

## 🏗️ Architecture Overview

The application consists of:
- **Frontend**: Next.js React application (Port 3000)
- **Backend**: FastAPI Python application (Port 8000)
- **Database**: PostgreSQL or SQLite
- **Vector Database**: ChromaDB for document embeddings
- **AI Models**: Local LLM and embedding models

## 📋 Prerequisites

### Local Development
- Python 3.9+
- Node.js 18+
- PostgreSQL (optional, SQLite works for demos)
- 8GB+ RAM recommended
- Docker & Docker Compose (for containerized deployment)

### Production Hosting
- VPS/Cloud instance (AWS EC2, DigitalOcean, etc.)
- Domain name (optional)
- SSL certificate (Let's Encrypt recommended)

## 🚀 Quick Start with Docker

### 1. Clone and Setup
```bash
git clone <repository-url>
cd ai-knowledge-assistant
```

### 2. Environment Configuration

Create `.env` file in backend directory:
```env
# Database
DATABASE_URL=postgresql://user:password@db:5432/knowledge_db

# Security - CHANGE THESE IN PRODUCTION!
SECRET_KEY=your-super-secret-key-change-this-in-production
ACCESS_TOKEN_EXPIRE_MINUTES=30

# AI Configuration
LLM_MODEL_NAME=microsoft/DialoGPT-small
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
CHUNK_SIZE=1000
CHUNK_OVERLAP=200
MAX_RETRIEVAL_DOCS=5

# File Upload
MAX_FILE_SIZE=104857600

# Vector Database
CHROMA_HOST=localhost
CHROMA_PORT=8000
```

### 3. Launch with Docker Compose
```bash
docker-compose up -d
```

### 4. Access the Application
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

## 🛠️ Manual Installation

### Backend Setup
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Database Setup
```bash
# PostgreSQL
createdb knowledge_assistant_db
psql -d knowledge_assistant_db -c "CREATE USER assistant_user WITH PASSWORD 'secure_password';"
psql -d knowledge_assistant_db -c "GRANT ALL PRIVILEGES ON DATABASE knowledge_assistant_db TO assistant_user;"

# Or use SQLite (simpler for development)
# DATABASE_URL=sqlite:///./knowledge_assistant.db
```

### Frontend Setup
```bash
cd frontend
npm install
npm run build
npm start
```

## 🌐 Production Deployment

### Option 1: VPS with Docker

#### 1. Server Setup
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

#### 2. Deploy Application
```bash
# Clone repository
git clone <your-repo-url> knowledge-assistant
cd knowledge-assistant

# Update environment variables
nano backend/.env

# Launch application
docker-compose -f docker-compose.prod.yml up -d
```

### Option 2: Cloud Platforms

#### Heroku Deployment
```bash
# Backend
heroku create knowledge-assistant-backend
heroku addons:create heroku-postgresql:hobby-dev
heroku config:set SECRET_KEY=your-secret-key
git push heroku main

# Frontend
heroku create knowledge-assistant-frontend
npm install -g heroku
heroku buildpacks:set heroku/nodejs
git push heroku main
```

#### Railway
```bash
# Install Railway CLI
npm install -g @railway/cli

# Deploy
railway login
railway init
railway up
```

#### Vercel + Railway
- **Frontend**: Deploy to Vercel
- **Backend**: Deploy to Railway
- **Database**: Railway PostgreSQL

#### Pxxl.app (Recommended)
Pxxl.app provides a streamlined deployment experience with built-in database and scaling support.

##### Prerequisites
```bash
# Install Pxxl CLI
npm install -g @pxxl/cli

# Login to Pxxl.app
pxxl login
```

##### Quick Deploy
```bash
# Clone and setup
git clone <your-repo-url> knowledge-assistant
cd knowledge-assistant

# Copy environment template
cp pxxl.env.example .env

# Edit environment variables (see configuration section below)
nano .env

# Deploy
./deploy-pxxl.bat  # Windows
# or
./deploy-pxxl.sh   # Linux/Mac
```

##### Manual Deploy
```bash
# Deploy directly
pxxl deploy

# Check deployment status
pxxl logs

# Get your app URL
pxxl domains
```

##### Pxxl.app Configuration
Update your `pxxl.env.example` file with:

```env
# Database - Provided by Pxxl.app
DATABASE_URL=postgresql://user:password@host:5432/dbname

# Security
SECRET_KEY=your-256-bit-secret-key

# Frontend
NEXT_PUBLIC_API_URL=https://your-app-name.pxxl.app/api/v1

# AI Models (keep lightweight for Pxxl.app)
LLM_MODEL_NAME=microsoft/DialoGPT-small
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
```

##### Pxxl.app Features
- ✅ Automatic SSL certificates
- ✅ Built-in PostgreSQL database
- ✅ Redis caching support
- ✅ Horizontal scaling
- ✅ Custom domains
- ✅ Environment management
- ✅ Real-time logs and monitoring

## 🔧 Configuration

### Environment Variables

#### Backend (.env)
```env
# Application
APP_NAME=AI Knowledge Assistant
VERSION=1.0.0
DEBUG=false

# Security
SECRET_KEY=your-256-bit-secret-key
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Database
DATABASE_URL=postgresql://user:password@host:port/database

# AI Models
LLM_MODEL_NAME=mistralai/Mistral-7B-Instruct-v0.1
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
CHUNK_SIZE=1000
CHUNK_OVERLAP=200
MAX_RETRIEVAL_DOCS=5

# File Storage
MAX_FILE_SIZE=104857600
UPLOAD_DIR=./uploads

# Vector Database
CHROMA_HOST=localhost
CHROMA_PORT=8000
```

#### Frontend (.env.local)
```env
NEXT_PUBLIC_API_URL=https://your-backend-domain.com/api/v1
NEXT_PUBLIC_APP_NAME=AI Knowledge Assistant
```

### AI Model Selection

#### Small/Fast Models (Development)
```env
LLM_MODEL_NAME=microsoft/DialoGPT-small
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
```

#### Production Models (Better Quality)
```env
LLM_MODEL_NAME=mistralai/Mistral-7B-Instruct-v0.1
EMBEDDING_MODEL=sentence-transformers/all-mpnet-base-v2
```

## 🔒 Security Setup

### SSL/TLS Configuration
```bash
# Using Let's Encrypt
sudo apt install certbot
sudo certbot --nginx -d yourdomain.com

# Or with Docker
# Add to docker-compose.yml
environment:
  - HTTPS=true
  - SSL_CRT_PATH=/path/to/cert.pem
  - SSL_KEY_PATH=/path/to/key.pem
```

### Firewall Setup
```bash
# UFW (Ubuntu)
sudo ufw allow 80
sudo ufw allow 443
sudo ufw allow 22
sudo ufw enable

# Or iptables
sudo iptables -A INPUT -p tcp --dport 80 -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 443 -j ACCEPT
```

## 📊 Monitoring & Maintenance

### Health Checks
```bash
# Application health
curl https://yourdomain.com/api/v1/health

# Database connectivity
docker-compose exec backend python -c "from app.core.database import get_db; next(get_db()).execute('SELECT 1')"
```

### Logs
```bash
# View application logs
docker-compose logs -f backend
docker-compose logs -f frontend

# Database logs
docker-compose logs -f db
```

### Backups
```bash
# Database backup
docker-compose exec db pg_dump -U user knowledge_db > backup.sql

# File backup
tar -czf uploads_backup.tar.gz uploads/
tar -czf chroma_backup.tar.gz chroma_db/
```

## 🚀 Scaling

### Horizontal Scaling
```yaml
# docker-compose.scale.yml
version: '3.8'
services:
  backend:
    scale: 3
    depends_on:
      - redis
  redis:
    image: redis:alpine
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
```

### Performance Optimization
```env
# Backend
WORKERS=4
MAX_REQUESTS=1000
MAX_REQUESTS_JITTER=50

# AI Models
USE_GPU=true
MODEL_CACHE_DIR=/app/models
BATCH_SIZE=8
```

## 🐛 Troubleshooting

### Common Issues

#### Backend won't start
```bash
# Check logs
docker-compose logs backend

# Check dependencies
docker-compose exec backend pip list

# Check database connection
docker-compose exec backend python -c "from app.core.database import engine; engine.connect()"
```

#### Frontend build fails
```bash
# Clear cache
rm -rf node_modules .next
npm install
npm run build
```

#### AI models not loading
```bash
# Check available memory
free -h

# Check GPU (if available)
nvidia-smi

# Use smaller models
LLM_MODEL_NAME=microsoft/DialoGPT-small
```

#### Database connection issues
```bash
# Test connection
psql -h localhost -U user -d knowledge_db

# Check Docker network
docker-compose exec db psql -U user -d knowledge_db -c "SELECT version();"
```

## 📈 Performance Tuning

### Memory Optimization
```python
# In config.py
MAX_WORKERS = multiprocessing.cpu_count()
MEMORY_LIMIT = "4GB"
MODEL_QUANTIZATION = "8bit"  # For smaller model footprint
```

### Caching
```python
# Redis for session storage and caching
REDIS_URL=redis://redis:6379/0

# Model caching
TRANSFORMERS_CACHE=/app/models/cache
```

### CDN Integration
```javascript
// For static assets
// next.config.js
module.exports = {
  images: {
    loader: 'cloudinary',
    path: 'https://your-cdn.com',
  },
}
```

## 🔄 Updates & Maintenance

### Application Updates
```bash
# Pull latest changes
git pull origin main

# Update containers
docker-compose build --no-cache
docker-compose up -d

# Database migrations
docker-compose exec backend alembic upgrade head
```

### Model Updates
```bash
# Update AI models
docker-compose exec backend python -c "
from app.services.ai_service import ai_service
ai_service._initialize_model()
"
```

---

🎉 **Your AI Knowledge Assistant is now ready for production deployment!**

For additional support, check the [README.md](README.md) or create an issue in the repository.
