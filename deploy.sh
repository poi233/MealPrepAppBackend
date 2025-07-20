#!/bin/bash

echo "🚀 Deploying MealPrepAI Backend to Vercel..."

# Check if vercel CLI is installed
if ! command -v vercel &> /dev/null; then
    echo "❌ Vercel CLI not found. Installing..."
    npm install -g vercel
fi

# Deploy to Vercel
echo "📦 Starting deployment..."
vercel --prod

echo "✅ Deployment completed!"
echo ""
echo "📋 Next steps:"
echo "1. Configure environment variables in Vercel dashboard"
echo "2. Run database migrations"
echo "3. Test your API endpoints"
echo ""
echo "📖 See VERCEL_DEPLOYMENT.md for detailed instructions"