#!/bin/bash

# Pxxl.app Production Deployment Script for AI Knowledge Assistant
# Usage: ./deploy-pxxl.sh

set -e

echo "🚀 Deploying AI Knowledge Assistant Frontend to Pxxl.app"
echo "📋 Architecture: Pxxl.app (Frontend) + Supabase (Backend) + Hugging Face (AI)"

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
    echo "⚠️  IMPORTANT: Please edit .env with your production configuration!"
    echo "   Required settings:"
    echo "   - NEXT_PUBLIC_SUPABASE_URL: Your Supabase project URL"
    echo "   - NEXT_PUBLIC_SUPABASE_ANON_KEY: Your Supabase anon key"
    echo "   - NEXT_PUBLIC_HF_API_TOKEN: Your Hugging Face API token"
    echo ""
    echo "   Optional settings:"
    echo "   - SUPABASE_SERVICE_ROLE_KEY: For admin operations"
    echo ""
    read -p "Press Enter after you've configured the .env file..."
fi

# Check for required environment variables
if ! grep -q "NEXT_PUBLIC_SUPABASE_URL=.*[^[:space:]]" .env; then
    echo "⚠️  WARNING: NEXT_PUBLIC_SUPABASE_URL not set. Database will not work!"
    echo "   Get your Supabase URL from: https://supabase.com/dashboard"
    read -p "Press Enter to continue anyway..."
fi

if ! grep -q "NEXT_PUBLIC_SUPABASE_ANON_KEY=.*[^[:space:]]" .env; then
    echo "⚠️  WARNING: NEXT_PUBLIC_SUPABASE_ANON_KEY not set. Authentication will not work!"
    echo "   Get your Supabase anon key from: https://supabase.com/dashboard"
    read -p "Press Enter to continue anyway..."
fi

if ! grep -q "NEXT_PUBLIC_HF_API_TOKEN=.*[^[:space:]]" .env; then
    echo "⚠️  WARNING: NEXT_PUBLIC_HF_API_TOKEN not set. AI functionality will not work!"
    echo "   Get your token from: https://huggingface.co/settings/tokens"
    read -p "Press Enter to continue anyway..."
fi

# Login to Pxxl.app (if not already logged in)
echo "🔐 Checking Pxxl.app authentication..."
if ! pxxl whoami &> /dev/null; then
    echo "Please login to Pxxl.app:"
    pxxl login
fi

# Deploy the application
echo "📦 Deploying production application to Pxxl.app..."
pxxl deploy

# Wait for deployment to complete
echo "⏳ Waiting for deployment to complete..."
sleep 10

# Get the deployment URL
APP_URL=$(pxxl domains | head -1)
echo "🎉 Deployment complete!"
echo "🌐 Your production app is available at: $APP_URL"

echo ""
echo "📋 Deployment Setup Checklist:"
echo "1. ✅ Set up Supabase project and run supabase-schema.sql"
echo "2. ✅ Create 'documents' storage bucket in Supabase"
echo "3. ✅ Configure environment variables in Pxxl.app dashboard:"
echo "   - NEXT_PUBLIC_SUPABASE_URL"
echo "   - NEXT_PUBLIC_SUPABASE_ANON_KEY"
echo "   - NEXT_PUBLIC_HF_API_TOKEN"
echo "4. ✅ Test user registration and login"
echo "5. ✅ Test document upload and AI chat"
echo "6. ⏳ DNS propagation (if using custom domain)"

echo ""
echo "🔧 Application Management Commands:"
echo "  pxxl logs --follow      - Monitor application logs"
echo "  pxxl env set KEY=value  - Update environment variables"
echo "  pxxl ps                 - Check running processes"
echo "  pxxl scale 2            - Scale to multiple instances"
echo "  pxxl restart            - Restart the application"

echo ""
echo "🧪 Test Your Deployment:"
echo "  curl $APP_URL/api/health"
echo "  Visit $APP_URL in your browser"
echo "  Try user registration and document upload"

echo ""
echo "🎯 Architecture Features:"
echo "  ✅ Frontend: Next.js on Pxxl.app"
echo "  ✅ Backend: Supabase (PostgreSQL + Storage)"
echo "  ✅ AI: Hugging Face Inference API (Mistral-7B)"
echo "  ✅ Real-time: Supabase subscriptions"
echo "  ✅ Security: Row Level Security (RLS)"
echo "  ✅ Scalability: Auto-scaling on all services"
echo "  ✅ Cost-effective: Generous free tiers"

echo ""
echo "📖 Full documentation: PXXL_SUPABASE_DEPLOYMENT.md"
