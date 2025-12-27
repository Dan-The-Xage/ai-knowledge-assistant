@echo off
REM Pxxl.app Deployment Script for AI Knowledge Assistant
REM Usage: deploy-pxxl.bat

echo 🚀 Deploying AI Knowledge Assistant to Pxxl.app

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
    echo ⚠️  Please edit .env with your actual configuration before deploying!
    echo    - Update SECRET_KEY with a secure random key
    echo    - Update DATABASE_URL with your Pxxl.app PostgreSQL URL
    echo    - Update NEXT_PUBLIC_API_URL with your Pxxl.app domain
    echo.
    echo Press any key when you've updated the .env file...
    pause >nul
)

REM Login to Pxxl.app (if not already logged in)
echo 🔐 Checking Pxxl.app authentication...
pxxl whoami >nul 2>&1
if %ERRORLEVEL% neq 0 (
    pxxl login
)

REM Deploy the application
echo 📦 Deploying to Pxxl.app...
pxxl deploy

REM Get the deployment URL
echo 🎉 Deployment complete!
echo 🌐 Your app will be available at:
pxxl domains

echo.
echo 📋 Next steps:
echo 1. Configure your database in the Pxxl.app dashboard
echo 2. Update DNS settings if using a custom domain
echo 3. Monitor logs with: pxxl logs
echo 4. Check health: curl https://your-app.pxxl.app/api/v1/health

echo.
echo 🔧 Useful commands:
echo   pxxl logs              - View application logs
echo   pxxl env               - Manage environment variables
echo   pxxl scale             - Scale your application
echo   pxxl domains           - Manage domains

pause
