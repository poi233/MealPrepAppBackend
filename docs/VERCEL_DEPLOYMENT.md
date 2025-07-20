# Vercel Deployment Guide

This guide will help you deploy your Django MealPrepAI backend to Vercel.

## Prerequisites

1. **Vercel Account**: Sign up at [vercel.com](https://vercel.com)
2. **Vercel CLI**: Install with `npm i -g vercel`
3. **Database**: Ensure your PostgreSQL database is accessible from the internet

## Deployment Steps

### 1. Install Vercel CLI and Login
```bash
npm i -g vercel
vercel login
```

### 2. Deploy to Vercel
From your project directory:
```bash
cd MealPrepAppBackend
vercel
```

Follow the prompts:
- Set up and deploy? **Y**
- Which scope? Choose your account
- Link to existing project? **N** (for first deployment)
- Project name: `mealprep-backend` (or your preferred name)
- Directory: `.` (current directory)

### 3. Configure Environment Variables

After deployment, add these environment variables in your Vercel dashboard:

**Required Variables:**
```
SECRET_KEY=your-django-secret-key
POSTGRES_DATABASE=your-database-name
POSTGRES_USER=your-database-user
POSTGRES_PASSWORD=your-database-password
POSTGRES_HOST=your-database-host
POSTGRES_PORT=5432
GEMINI_API_KEY=your-google-ai-api-key
```

**Optional Variables:**
```
DEBUG=False
CORS_ALLOWED_ORIGINS=https://your-frontend.vercel.app
VERCEL_URL=your-backend.vercel.app
REDIS_URL=your-redis-url (if using Redis)
```

### 4. Run Database Migrations

After setting environment variables, run migrations:
```bash
vercel env pull .env.local
python api/migrate.py
```

Or use Vercel's serverless function approach by visiting:
`https://your-app.vercel.app/api/migrate`

### 5. Test Your Deployment

Visit your Vercel URL to test:
- Health check: `https://your-app.vercel.app/health/`
- API endpoints: `https://your-app.vercel.app/api/`

## Environment Variables Setup

### Via Vercel Dashboard:
1. Go to your project dashboard
2. Click "Settings" → "Environment Variables"
3. Add each variable with appropriate values

### Via Vercel CLI:
```bash
vercel env add SECRET_KEY
vercel env add POSTGRES_DATABASE
vercel env add POSTGRES_USER
vercel env add POSTGRES_PASSWORD
vercel env add POSTGRES_HOST
vercel env add POSTGRES_PORT
vercel env add GEMINI_API_KEY
```

## Database Configuration

### Using Vercel Postgres:
```bash
vercel storage create postgres
```

### Using External Database (Neon, Supabase, etc.):
Ensure your database allows connections from Vercel's IP ranges.

## Static Files

Static files are handled by WhiteNoise middleware and will be served automatically.

## Troubleshooting

### Common Issues:

1. **Import Errors**: Ensure all dependencies are in `requirements.txt`
2. **Database Connection**: Check your database allows external connections
3. **Environment Variables**: Verify all required variables are set
4. **Static Files**: Run `python manage.py collectstatic` locally to test

### Logs:
View deployment logs in Vercel dashboard or use:
```bash
vercel logs
```

## Production Checklist

- [ ] All environment variables configured
- [ ] Database migrations run successfully
- [ ] Static files collecting properly
- [ ] CORS origins configured for your frontend
- [ ] API endpoints responding correctly
- [ ] Authentication working
- [ ] AI integration functional

## Updating Your Deployment

For future updates:
```bash
git add .
git commit -m "Update backend"
git push
```

Vercel will automatically redeploy on git push if connected to your repository.

## Custom Domain (Optional)

1. Go to your project settings in Vercel
2. Add your custom domain
3. Update DNS records as instructed
4. Update CORS_ALLOWED_ORIGINS to include your custom domain