@echo off
REM Pxxl.app Production Deployment Script for AI Knowledge Assistant
REM Usage: deploy-pxxl.bat

echo 🚀 Deploying AI Knowledge Assistant (Production) to Pxxl.app

REM Check if pxxl CLI is installed
pxxl --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo ❌ Pxxl CLI not found. Please install it first:
    echo npm install -g @pxxl/cli
    pause
    exit /b 1
)

REM Check if we're in the project directory
if not exist "pxxl.json" (
    echo ❌ pxxl.json not found. Please run this script from the project root.
    pause
    exit /b 1
)

REM Create environment file if it doesn't exist
if not exist ".env" (
    echo 📝 Creating environment file from template...
    copy pxxl.env.example .env
    echo ⚠️  IMPORTANT: Please edit .env with your production configuration!
    echo    Required settings:
    echo    - HF_API_TOKEN: Your Hugging Face API token ^(for AI functionality^)
    echo    - SECRET_KEY: Generate a secure random key
    echo    - NEXT_PUBLIC_API_URL: Your Pxxl.app domain
    echo.
    echo Press any key after you've configured the .env file...
    pause >nul
)

REM Check for required environment variables
findstr /C:"HF_API_TOKEN=.*[^ ]" .env >nul
if %ERRORLEVEL% neq 0 (
    echo ⚠️  WARNING: HF_API_TOKEN not set. AI functionality will not work!
    echo    Get your token from: https://huggingface.co/settings/tokens
    echo.
    echo Press any key to continue anyway...
    pause >nul
)

REM Login to Pxxl.app (if not already logged in)
echo 🔐 Checking Pxxl.app authentication...
pxxl whoami >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo Please login to Pxxl.app:
    pxxl login
)

REM Deploy the application
echo 📦 Deploying production application to Pxxl.app...
pxxl deploy

REM Wait for deployment to complete
echo ⏳ Waiting for deployment to complete...
timeout /t 10 /nobreak >nul

REM Get the deployment URL
for /f "tokens=*" %%i in ('pxxl domains') do set APP_URL=%%i

echo 🎉 Deployment complete!
echo 🌐 Your production app is available at: %APP_URL%

echo.
echo 📋 Production Setup Checklist:
echo 1. ✅ Configure PostgreSQL database in Pxxl.app dashboard
echo 2. ✅ Set HF_API_TOKEN in environment variables
echo 3. ✅ Update NEXT_PUBLIC_API_URL to: %APP_URL%/api/v1
echo 4. ✅ Test AI functionality with document uploads
echo 5. ⏳ DNS propagation ^(if using custom domain^)

echo.
echo 🔧 Production Management Commands:
echo   pxxl logs --follow      - Monitor application logs
echo   pxxl env set KEY=value  - Update environment variables
echo   pxxl ps                 - Check running processes
echo   pxxl scale 2            - Scale to multiple instances
echo   pxxl restart            - Restart the application

echo.
echo 🧪 Test Your Deployment:
echo   curl %APP_URL%/api/v1/health
echo   curl %APP_URL%/api/v1/auth/roles

echo.
echo 🎯 Production Features Enabled:
echo   ✅ Real AI models ^(Mistral-7B via Hugging Face^)
echo   ✅ Production embeddings ^(BGE^)
echo   ✅ PostgreSQL database
echo   ✅ Redis caching
echo   ✅ Vector database ^(Qdrant^)
echo   ✅ Document processing pipeline
echo   ✅ Full user management
echo   ✅ Enterprise security

pause
