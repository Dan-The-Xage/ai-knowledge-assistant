@echo off
REM AI Knowledge Assistant - Windows Startup Script

echo 🚀 Starting AI Knowledge Assistant Platform...

REM Check for Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python not found. Please install Python 3.9+
    pause
    exit /b 1
)

REM Check for Node.js
node --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Node.js not found. Please install Node.js 18+
    pause
    exit /b 1
)

REM Backend setup
echo 🔧 Setting up backend...
cd backend

if not exist "venv" (
    echo 📦 Creating Python virtual environment...
    python -m venv venv
)

echo 🔄 Activating virtual environment and installing dependencies...
call venv\Scripts\activate.bat
pip install -r requirements.txt

REM Check if .env exists
if not exist ".env" (
    echo ⚠️  .env file not found. Creating template...
    (
        echo # Database
        echo DATABASE_URL=postgresql://user:password@localhost/knowledge_db
        echo.
        echo # Security
        echo SECRET_KEY=your-super-secret-key-here-change-this-in-production
        echo ACCESS_TOKEN_EXPIRE_MINUTES=30
        echo.
        echo # Vector Database
        echo CHROMA_HOST=localhost
        echo CHROMA_PORT=8000
        echo.
        echo # AI Configuration
        echo LLM_MODEL_NAME=mistralai/Mistral-7B-Instruct-v0.1
        echo EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
        echo CHUNK_SIZE=1000
        echo CHUNK_OVERLAP=200
        echo MAX_RETRIEVAL_DOCS=5
        echo.
        echo # File Upload
        echo MAX_FILE_SIZE=104857600
    ) > .env
    echo ✅ Created .env template. Please update with your configuration.
)

REM Start backend
echo 🚀 Starting backend server...
start /B uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

REM Frontend setup
echo 🔧 Setting up frontend...
cd ../frontend

if not exist "node_modules" (
    echo 📦 Installing Node.js dependencies...
    npm install
)

REM Start frontend
echo 🚀 Starting frontend server...
start /B npm run dev

echo.
echo ✅ AI Knowledge Assistant Platform started successfully!
echo.
echo 📱 Frontend: http://localhost:3000
echo 🔌 Backend API: http://localhost:8000
echo 📚 API Documentation: http://localhost:8000/docs
echo.
echo 💡 Services are running in background
echo 💡 Close this window to stop all services

pause
