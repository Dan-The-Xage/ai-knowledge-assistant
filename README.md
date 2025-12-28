# AI Knowledge Assistant - Pxxl.app Frontend

**Frontend-only deployment branch for Pxxl.app**

This branch contains only the Next.js frontend application configured for deployment on Pxxl.app with Supabase backend and Hugging Face AI integration.

## 🚀 Features

- **AI Chat Assistant**: Natural language questions with contextual answers from uploaded documents
- **Document Intelligence**: Support for PDF, Word, Excel, and text files
- **Real-time AI**: Powered by Hugging Face Mistral-7B model
- **User Authentication**: Secure login with Supabase Auth
- **Document Management**: Upload, view, and manage documents
- **Responsive UI**: Modern interface built with Next.js and Tailwind CSS

## 🏗️ Architecture

### Frontend (Next.js on Pxxl.app)
- **Framework**: Next.js 14 with TypeScript
- **Styling**: Tailwind CSS
- **Deployment**: Docker on Pxxl.app
- **AI Integration**: Direct Hugging Face API calls

### Backend (Supabase)
- **Database**: PostgreSQL with Row Level Security
- **Authentication**: Supabase Auth
- **Storage**: Supabase Storage for documents
- **Real-time**: Live subscriptions

### AI Integration (Hugging Face)
- **Model**: Mistral-7B via Inference API
- **Embeddings**: BGE for document processing
- **Direct API calls** from frontend

## 🚀 Deployment

This branch is specifically configured for **Pxxl.app deployment**.

### Prerequisites
1. **Supabase Account**: Set up your database and get API keys
2. **Hugging Face Account**: Get your API token
3. **Pxxl.app Account**: Ready for deployment

### Quick Deploy
1. **Connect Repository**: Link this `pxxl-deployment` branch to Pxxl.app
2. **Auto-Detection**: Pxxl.app detects Docker configuration
3. **Set Environment Variables**:
   ```
   NEXT_PUBLIC_SUPABASE_URL=your-supabase-url
   NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
   NEXT_PUBLIC_HF_API_TOKEN=your-huggingface-token
   ```
4. **Deploy**: Click deploy and wait for completion

### Documentation
See `PXXL_SUPABASE_DEPLOYMENT.md` for detailed deployment instructions.

### 2. Backend Setup

#### Install Python Dependencies
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

#### Environment Configuration
Create `.env` file in the backend directory:
```env
# Database
DATABASE_URL=postgresql://user:password@localhost/knowledge_db

# Security
SECRET_KEY=your-super-secret-key-here-change-this
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Vector Database
CHROMA_HOST=localhost
CHROMA_PORT=8000

# AI Configuration
LLM_MODEL_NAME=mistralai/Mistral-7B-Instruct-v0.1
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
CHUNK_SIZE=1000
CHUNK_OVERLAP=200
MAX_RETRIEVAL_DOCS=5

# File Upload
MAX_FILE_SIZE=104857600  # 100MB

# Redis/Celery (optional)
REDIS_URL=redis://localhost:6379/0
```

#### Database Setup
```bash
# Create PostgreSQL database
createdb knowledge_db

# Run database migrations
alembic upgrade head
```

#### Download AI Models (Optional)
The system will automatically download models on first use, but you can pre-download them:

```bash
# Install huggingface_hub
pip install huggingface_hub

# Download models
huggingface-cli download mistralai/Mistral-7B-Instruct-v0.1
huggingface-cli download sentence-transformers/all-MiniLM-L6-v2
```

### 3. Frontend Setup

#### Install Dependencies
```bash
cd ../frontend
npm install
```

#### Environment Configuration
Create `.env.local` file in the frontend directory:
```env
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
```

### 4. Start the Application

#### Backend
```bash
cd backend
source venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

#### Frontend
```bash
cd frontend
npm run dev
```

The application will be available at:
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs

## 🎯 Usage

### First Time Setup

1. **Register**: Create your admin account at `/register`
2. **Login**: Sign in with your credentials
3. **Create Project**: Set up your first knowledge project
4. **Upload Documents**: Add PDF, Word, Excel, or text files
5. **Start Chatting**: Ask questions about your documents

### Document Upload

- **Supported Formats**: PDF, DOCX, DOC, XLSX, XLS, TXT
- **Maximum Size**: 100MB per file
- **Processing**: Automatic text extraction and embedding generation
- **Organization**: Files are organized by project with access controls

### AI Chat Features

- **Natural Language**: Ask questions in plain English
- **Context Awareness**: Conversations maintain context
- **Source Citations**: Answers include document references
- **Project Scope**: Search within specific projects or globally
- **Multi-document Reasoning**: Combine information from multiple sources

### Example Queries

```
"What are our company policies on remote work?"
"Summarize the Q4 financial report"
"Who are the key contacts for the marketing department?"
"Compare the budget allocations between departments"
"Extract all email addresses from the contact list"
```

## 🔒 Security & Compliance

### Role-Based Access Control
- **Super Admin**: Full system access
- **Admin**: User and project management
- **User**: Document upload and chat access

### Data Security
- **Encryption**: Files stored securely with access controls
- **Audit Logging**: All actions tracked with timestamps
- **No External APIs**: Fully offline operation
- **Local AI Models**: No data sent to external services

### Compliance Features
- **Access Logs**: Complete audit trail
- **Data Retention**: Configurable retention policies
- **User Activity**: Detailed activity monitoring
- **Export Controls**: Data export capabilities

## 🚀 Deployment

### Production Deployment

#### Backend (Docker)
```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### Frontend (Vercel/Netlify)
```bash
npm run build
npm run start
```

### Scaling Considerations

- **Database**: Use connection pooling for high concurrency
- **Vector Search**: Implement caching for frequent queries
- **File Storage**: Use distributed storage for large deployments
- **AI Inference**: GPU acceleration for faster responses

## 🔧 Configuration

### AI Model Configuration

```python
# In backend/app/core/config.py
LLM_MODEL_NAME="microsoft/DialoGPT-medium"  # Smaller model for testing
EMBEDDING_MODEL="sentence-transformers/all-MiniLM-L6-v2"
CHUNK_SIZE=512  # Smaller chunks for faster processing
```

### Performance Tuning

```python
# Vector search optimization
MAX_RETRIEVAL_DOCS=10  # More results for better accuracy
CHUNK_OVERLAP=50  # Less overlap for efficiency

# Database optimization
DATABASE_URL="postgresql://user:password@host:port/db?sslmode=require&pool_size=20"
```

## 📊 Monitoring & Analytics

### Health Checks
- **API Health**: `/api/v1/health`
- **Detailed Status**: `/api/v1/health/detailed`
- **Database Connectivity**: Automatic monitoring
- **AI Service Status**: Model loading and inference checks

### Metrics
- **Usage Analytics**: Queries per user, documents accessed
- **AI Performance**: Response times, confidence scores
- **System Health**: CPU, memory, disk usage
- **Audit Reports**: User activity and compliance logs

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

### Development Guidelines

- **Code Style**: Black for Python, ESLint for JavaScript
- **Testing**: pytest for backend, Jest for frontend
- **Documentation**: Update README for new features
- **Security**: Run security audits before major releases

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

- **Documentation**: See `/docs` directory
- **Issues**: GitHub Issues for bug reports
- **Discussions**: GitHub Discussions for questions
- **Security**: security@example.com for security concerns

## 🎉 Acknowledgments

- **FastAPI**: High-performance async web framework
- **Next.js**: React framework for production
- **ChromaDB**: Vector database for embeddings
- **Mistral AI**: Open-source LLM models
- **Sentence Transformers**: Text embedding models

---

Built with ❤️ for organizations that value knowledge and security.
