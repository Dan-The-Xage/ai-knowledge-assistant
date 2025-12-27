#!/bin/bash

# Pxxl.app Deployment Script for AI Knowledge Assistant
# Usage: ./deploy-pxxl.sh

set -e

echo "🚀 Deploying AI Knowledge Assistant to Pxxl.app"

# Check if pxxl CLI is installed
if ! command -v pxxl &> /dev/null; then
    echo "❌ Pxxl CLI not found. Please install it first:"
    echo "npm install -g @pxxl/cli"
    exit 1
fi

# Check if we're in the project directory
if [ ! -f "pxxl.json" ]; then
    echo "❌ pxxl.json not found. Please run this script from the project root."
    exit 1
fi

# Create environment file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "📝 Creating environment file from template..."
    cp pxxl.env.example .env
    echo "⚠️  Please edit .env with your actual configuration before deploying!"
    echo "   - Update SECRET_KEY with a secure random key"
    echo "   - Update DATABASE_URL with your Pxxl.app PostgreSQL URL"
    echo "   - Update NEXT_PUBLIC_API_URL with your Pxxl.app domain"
    read -p "Press Enter when you've updated the .env file..."
fi

# Login to Pxxl.app (if not already logged in)
echo "🔐 Checking Pxxl.app authentication..."
pxxl whoami &> /dev/null || pxxl login

# Deploy the application
echo "📦 Deploying to Pxxl.app..."
pxxl deploy

# Get the deployment URL
echo "🎉 Deployment complete!"
echo "🌐 Your app will be available at: $(pxxl domains)"

echo ""
echo "📋 Next steps:"
echo "1. Configure your database in the Pxxl.app dashboard"
echo "2. Update DNS settings if using a custom domain"
echo "3. Monitor logs with: pxxl logs"
echo "4. Check health: curl https://your-app.pxxl.app/api/v1/health"

echo ""
echo "🔧 Useful commands:"
echo "  pxxl logs              - View application logs"
echo "  pxxl env               - Manage environment variables"
echo "  pxxl scale             - Scale your application"
echo "  pxxl domains           - Manage domains"
