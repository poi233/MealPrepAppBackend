# MealPrepAppBackend

Django REST API backend for the MealPrepAI application, providing unified API endpoints for both web and mobile clients.

## Features

- **Authentication**: JWT-based authentication with user management
- **Recipe Management**: CRUD operations for recipes with AI-generated details
- **Meal Planning**: Weekly meal plan creation and management
- **Favorites System**: User recipe favorites with personal ratings and notes
- **AI Integration**: Google Gemini integration for meal plan and recipe generation
- **API Documentation**: Comprehensive REST API with proper error handling

## Tech Stack

- **Framework**: Django 4.2 LTS + Django REST Framework
- **Database**: PostgreSQL (Vercel Postgres/Neon)
- **Authentication**: JWT with SimpleJWT
- **AI**: Google Gemini 2.0 Flash
- **Deployment**: Docker + Gunicorn

## Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL
- Google AI API Key

### Installation

1. **Clone and setup**:
   ```bash
   cd MealPrepAppBackend
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Environment Configuration**:
   Copy `.env.example` to `.env` and configure:
   ```bash
   cp .env.example .env
   # Edit .env with your database and API keys
   ```

3. **Database Setup**:
   ```bash
   python manage.py migrate
   python manage.py createsuperuser
   ```

4. **Run Development Server**:
   ```bash
   python manage.py runserver
   ```

The API will be available at `http://localhost:8000/`

### Docker Setup

1. **Build and run with Docker Compose**:
   ```bash
   docker-compose up --build
   ```

2. **Run migrations in container**:
   ```bash
   docker-compose exec web python manage.py migrate
   docker-compose exec web python manage.py createsuperuser
   ```

## API Endpoints

### Authentication
- `POST /api/auth/register/` - User registration
- `POST /api/auth/login/` - User login
- `POST /api/auth/logout/` - User logout
- `GET /api/auth/me/` - Get current user profile
- `PUT /api/auth/profile/` - Update user profile
- `POST /api/auth/change-password/` - Change password

### Recipes
- `GET /api/recipes/` - List recipes (with filtering)
- `POST /api/recipes/` - Create recipe
- `GET /api/recipes/{id}/` - Get recipe details
- `PUT /api/recipes/{id}/` - Update recipe
- `DELETE /api/recipes/{id}/` - Delete recipe

### Meal Plans
- `GET /api/meal-plans/` - List user's meal plans
- `POST /api/meal-plans/` - Create meal plan
- `GET /api/meal-plans/{id}/` - Get meal plan details
- `PUT /api/meal-plans/{id}/` - Update meal plan
- `DELETE /api/meal-plans/{id}/` - Delete meal plan

### Favorites
- `GET /api/favorites/` - List user's favorites
- `POST /api/favorites/{recipe_id}/` - Add to favorites
- `DELETE /api/favorites/{recipe_id}/` - Remove from favorites

### AI Integration
- `POST /api/ai/generate-meal-plan/` - Generate weekly meal plan
- `POST /api/ai/generate-recipe-details/` - Generate recipe details
- `POST /api/ai/analyze-meal-plan/` - Analyze meal plan nutrition

## Development

### Project Structure
```
MealPrepAppBackend/
├── manage.py
├── requirements.txt
├── src/
│   ├── apps/
│   │   ├── authentication/
│   │   ├── recipes/
│   │   ├── meal_plans/
│   │   ├── favorites/
│   │   └── ai_integration/
│   ├── mealprep_project/
│   │   ├── settings/
│   │   │   ├── base.py
│   │   │   ├── development.py
│   │   │   └── production.py
│   │   ├── urls.py
│   │   ├── wsgi.py
│   │   └── asgi.py
│   └── common/
│       ├── exceptions.py
│       ├── permissions.py
│       └── pagination.py
├── test/
│   ├── test_serializers.py
│   └── test_validation_compatibility.py
├── static/, media/, templates/, logs/
└── venv/
```

### Running Tests
```bash
# Run custom serializer tests
python test/test_serializers.py

# Run validation compatibility tests
python test/test_validation_compatibility.py

# Run Django tests (when available)
python manage.py test

# Run with coverage
coverage run --source='.' manage.py test
coverage report
```

### Environment Settings

- **Development**: `mealprep_project.settings.development`
- **Production**: `mealprep_project.settings.production`

Set `DJANGO_SETTINGS_MODULE` environment variable accordingly.

## Deployment

### Production Checklist

1. Set `DEBUG=False`
2. Configure `ALLOWED_HOSTS`
3. Set secure `SECRET_KEY`
4. Configure production database
5. Set up Redis for caching
6. Configure email backend
7. Set up SSL/HTTPS
8. Configure static files serving

### Docker Production

```bash
docker build -t mealprep-backend .
docker run -p 8000:8000 --env-file .env mealprep-backend
```

## Contributing

1. Follow Django coding standards
2. Write tests for new features
3. Update API documentation
4. Ensure all tests pass before submitting PR

## License

This project is part of the MealPrepAI application.