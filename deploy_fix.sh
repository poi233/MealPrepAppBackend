#!/bin/bash

echo "🔧 Deploying Redis fix to Vercel..."

# Deploy to Vercel
vercel --prod

echo "✅ Deployment completed!"
echo ""
echo "🧪 Testing the fix..."

# Wait for deployment to be ready
sleep 10

# Test the AI recipe generation endpoint
echo "Testing AI recipe generation..."
curl -X POST https://meal-prep-app-backend.vercel.app/api/ai/generate-recipe/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer test-token" \
  -d '{
    "name": "Test Recipe",
    "description": "A simple test recipe"
  }' \
  2>/dev/null | head -c 200

echo ""
echo "🎉 Fix deployment completed!"