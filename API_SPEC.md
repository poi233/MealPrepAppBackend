# MealPrepAI Backend API Specification

## Overview

This document provides a comprehensive specification for all API endpoints available in the MealPrepAI Django backend. All endpoints require JWT authentication unless otherwise specified.

## Base URL
- Development: `http://localhost:8000`
- Production: `https://your-domain.com`

## Authentication

All API endpoints (except health checks) require JWT authentication. Include the JWT token in the Authorization header:

```
Authorization: Bearer <your_jwt_token>
```

## Health Check Endpoints

### Health Check
- **Endpoint:** `GET /health/`
- **Authentication:** Not required
- **Description:** Basic health check for the application
- **Response:** `200 OK` with health status

### Readiness Check
- **Endpoint:** `GET /ready/`
- **Authentication:** Not required
- **Description:** Readiness check for deployment health monitoring
- **Response:** `200 OK` when application is ready

---

## Authentication Endpoints (`/api/auth/`)

### User Registration
- **Endpoint:** `POST /api/auth/register/`
- **Authentication:** Not required
- **Description:** Register a new user account

**Request Body:**
```json
{
  "username": "johndoe",
  "email": "john@example.com",
  "password": "securepassword123",
  "password_confirm": "securepassword123",
  "display_name": "John Doe",
  "dietary_preferences": {
    "allergies": ["nuts", "shellfish"],
    "diet_type": "vegetarian",
    "dislikes": ["mushrooms"],
    "calorie_target": 2000
  }
}
```

**Success Response (201 Created):**
```json
{
  "user": {
    "id": "uuid-string",
    "username": "johndoe",
    "email": "john@example.com",
    "display_name": "John Doe",
    "dietary_preferences": {
      "allergies": ["nuts", "shellfish"],
      "diet_type": "vegetarian",
      "dislikes": ["mushrooms"],
      "calorie_target": 2000
    },
    "created_at": "2025-07-23T10:00:00Z",
    "updated_at": "2025-07-23T10:00:00Z"
  },
  "access": "jwt-access-token",
  "refresh": "jwt-refresh-token"
}
```

**Validation Rules:**
- `username`: 3-50 characters, unique (case-insensitive)
- `email`: Valid email format, unique
- `password`: Django password validation rules
- `dietary_preferences.allergies`: Max 20 items, 100 chars each
- `dietary_preferences.calorie_target`: 800-5000

### User Login
- **Endpoint:** `POST /api/auth/login/`
- **Authentication:** Not required
- **Description:** Authenticate user and get JWT tokens

**Request Body:**
```json
{
  "username": "johndoe",
  "password": "securepassword123"
}
```

**Success Response (200 OK):**
```json
{
  "user": {
    "id": "uuid-string",
    "username": "johndoe",
    "email": "john@example.com",
    "display_name": "John Doe",
    "dietary_preferences": {
      "allergies": ["nuts"],
      "diet_type": "vegetarian",
      "dislikes": ["mushrooms"],
      "calorie_target": 2000
    }
  },
  "access": "jwt-access-token",
  "refresh": "jwt-refresh-token"
}
```

### User Logout
- **Endpoint:** `POST /api/auth/logout/`
- **Authentication:** Required
- **Description:** Logout user and invalidate tokens

**Request Body:**
```json
{
  "refresh": "jwt-refresh-token"
}
```

**Success Response (200 OK):**
```json
{
  "message": "Successfully logged out"
}
```

### Get Current User Profile
- **Endpoint:** `GET /api/auth/me/`
- **Authentication:** Required
- **Description:** Get current authenticated user's profile

**Success Response (200 OK):**
```json
{
  "id": "uuid-string",
  "username": "johndoe",
  "email": "john@example.com",
  "display_name": "John Doe",
  "dietary_preferences": {
    "allergies": ["nuts"],
    "diet_type": "vegetarian",
    "dislikes": ["mushrooms"],
    "calorie_target": 2000
  },
  "created_at": "2025-07-23T10:00:00Z",
  "updated_at": "2025-07-23T10:00:00Z"
}
```

### Update User Profile
- **Endpoint:** `PUT /api/auth/profile/`
- **Authentication:** Required
- **Description:** Update current user's profile information

**Request Body:**
```json
{
  "display_name": "John Smith",
  "dietary_preferences": {
    "allergies": ["nuts", "dairy"],
    "diet_type": "vegan",
    "dislikes": ["mushrooms", "olives"],
    "calorie_target": 2200
  }
}
```

**Success Response (200 OK):**
```json
{
  "id": "uuid-string",
  "username": "johndoe",
  "email": "john@example.com",
  "display_name": "John Smith",
  "dietary_preferences": {
    "allergies": ["nuts", "dairy"],
    "diet_type": "vegan",
    "dislikes": ["mushrooms", "olives"],
    "calorie_target": 2200
  },
  "updated_at": "2025-07-23T11:00:00Z"
}
```

### Change Password
- **Endpoint:** `POST /api/auth/change-password/`
- **Authentication:** Required
- **Description:** Change user's password

**Request Body:**
```json
{
  "current_password": "oldpassword123",
  "new_password": "newpassword456",
  "new_password_confirm": "newpassword456"
}
```

**Success Response (200 OK):**
```json
{
  "message": "Password changed successfully"
}
```

---

## Recipe Endpoints (`/api/recipes/`)

### List Recipes
- **Endpoint:** `GET /api/recipes/`
- **Authentication:** Required
- **Description:** Get paginated list of recipes with filtering and search

**Query Parameters:**
- `page`: Page number (default: 1)
- `page_size`: Items per page (default: 20, max: 100)
- `search`: Search across name, description, cuisine, tags, ingredients
- `cuisine`: Filter by cuisine type
- `difficulty`: Filter by difficulty (easy, medium, hard)
- `prep_time`: Filter by prep time (minutes)
- `cook_time`: Filter by cook time (minutes)
- `total_time`: Filter by total time (prep + cook)
- `avg_rating`: Filter by minimum rating
- `tags`: Filter by tags (comma-separated)
- `meal_type`: Filter by meal type
- `my_recipes`: Show only user's recipes (true/false)

**Example Request:**
```
GET /api/recipes/?search=pasta&cuisine=Italian&difficulty=easy&page=1&page_size=10
```

**Success Response (200 OK):**
```json
{
  "links": {
    "next": "http://localhost:8000/api/recipes/?page=2",
    "previous": null
  },
  "count": 25,
  "total_pages": 3,
  "current_page": 1,
  "page_size": 10,
  "results": [
    {
      "id": "uuid-string",
      "created_by_user": "johndoe",
      "created_by_user_id": "uuid-string",
      "name": "Spaghetti Carbonara",
      "description": "Classic Italian pasta dish",
      "ingredients": [
        {
          "name": "Spaghetti",
          "amount": "400.00",
          "unit": "g",
          "notes": "Use good quality pasta"
        }
      ],
      "instructions": "1. Cook pasta...",
      "nutrition_info": {
        "calories": "520.00",
        "protein": "22.00",
        "carbs": "65.00",
        "fat": "18.00",
        "fiber": "3.00",
        "sodium": "890.00",
        "sugar": "3.00"
      },
      "cuisine": "Italian",
      "prep_time": 10,
      "cook_time": 15,
      "total_time": 25,
      "difficulty": "medium",
      "avg_rating": "4.50",
      "rating_count": 12,
      "image_url": "https://example.com/image.jpg",
      "tags": ["pasta", "italian", "quick"],
      "created_at": "2025-07-23T10:00:00Z",
      "updated_at": "2025-07-23T10:00:00Z"
    }
  ]
}
```

### Create Recipe
- **Endpoint:** `POST /api/recipes/`
- **Authentication:** Required
- **Description:** Create a new recipe

**Request Body:**
```json
{
  "name": "Vegetable Stir Fry",
  "description": "Quick and healthy vegetable stir fry",
  "ingredients": [
    {
      "name": "Mixed vegetables",
      "amount": "2.00",
      "unit": "cups",
      "notes": "Use fresh or frozen"
    },
    {
      "name": "Soy sauce",
      "amount": "2.00",
      "unit": "tbsp",
      "notes": "Low sodium preferred"
    }
  ],
  "instructions": "1. Heat oil in wok\n2. Add vegetables\n3. Stir fry for 5 minutes\n4. Add soy sauce",
  "nutrition_info": {
    "calories": "150.00",
    "protein": "5.00",
    "carbs": "20.00",
    "fat": "6.00",
    "fiber": "4.00",
    "sodium": "800.00",
    "sugar": "8.00"
  },
  "cuisine": "Asian",
  "prep_time": 10,
  "cook_time": 8,
  "difficulty": "easy",
  "image_url": "https://example.com/stir-fry.jpg",
  "tags": ["vegetarian", "quick", "healthy"]
}
```

**Success Response (201 Created):**
```json
{
  "id": "uuid-string",
  "created_by_user": "johndoe",
  "created_by_user_id": "uuid-string",
  "name": "Vegetable Stir Fry",
  "description": "Quick and healthy vegetable stir fry",
  "ingredients": [
    {
      "name": "Mixed vegetables",
      "amount": "2.00",
      "unit": "cups",
      "notes": "Use fresh or frozen"
    }
  ],
  "instructions": "1. Heat oil in wok...",
  "nutrition_info": {
    "calories": "150.00",
    "protein": "5.00",
    "carbs": "20.00",
    "fat": "6.00"
  },
  "cuisine": "Asian",
  "prep_time": 10,
  "cook_time": 8,
  "total_time": 18,
  "difficulty": "easy",
  "avg_rating": "0.00",
  "rating_count": 0,
  "image_url": "https://example.com/stir-fry.jpg",
  "tags": ["vegetarian", "quick", "healthy"],
  "created_at": "2025-07-23T10:00:00Z",
  "updated_at": "2025-07-23T10:00:00Z"
}
```

**Validation Rules:**
- `name`: Required, max 255 characters
- `description`: Optional, max 1000 characters
- `ingredients`: 1-50 items, each with name (required), amount, unit, notes
- `instructions`: Required, max 5000 characters
- `prep_time`, `cook_time`: 0-1440 minutes
- `tags`: 0-20 items, max 50 characters each

### Get Recipe Details
- **Endpoint:** `GET /api/recipes/{id}/`
- **Authentication:** Required
- **Description:** Get detailed information for a specific recipe

**Success Response (200 OK):**
```json
{
  "id": "uuid-string",
  "created_by_user": "johndoe",
  "created_by_user_id": "uuid-string",
  "name": "Spaghetti Carbonara",
  "description": "Classic Italian pasta dish",
  "ingredients": [
    {
      "name": "Spaghetti",
      "amount": "400.00",
      "unit": "g",
      "notes": "Use good quality pasta"
    }
  ],
  "instructions": "1. Cook pasta according to package directions...",
  "nutrition_info": {
    "calories": "520.00",
    "protein": "22.00",
    "carbs": "65.00",
    "fat": "18.00"
  },
  "cuisine": "Italian",
  "prep_time": 10,
  "cook_time": 15,
  "total_time": 25,
  "difficulty": "medium",
  "avg_rating": "4.50",
  "rating_count": 12,
  "image_url": "https://example.com/image.jpg",
  "tags": ["pasta", "italian", "quick"],
  "created_at": "2025-07-23T10:00:00Z",
  "updated_at": "2025-07-23T10:00:00Z"
}
```

### Update Recipe
- **Endpoint:** `PUT /api/recipes/{id}/`
- **Authentication:** Required (only recipe creator can update)
- **Description:** Update an existing recipe

**Request Body:** Same format as Create Recipe

**Success Response (200 OK):** Same format as Get Recipe Details

### Delete Recipe
- **Endpoint:** `DELETE /api/recipes/{id}/`
- **Authentication:** Required (only recipe creator can delete)
- **Description:** Delete a recipe

**Success Response (204 No Content):** Empty response body

---

## Meal Plan Endpoints (`/api/meal-plans/`)

### List Meal Plans
- **Endpoint:** `GET /api/meal-plans/`
- **Authentication:** Required
- **Description:** Get user's meal plans with pagination

**Query Parameters:**
- `page`: Page number (default: 1)
- `page_size`: Items per page (default: 20)

**Success Response (200 OK):**
```json
{
  "links": {
    "next": "http://localhost:8000/api/meal-plans/?page=2",
    "previous": null
  },
  "count": 5,
  "total_pages": 1,
  "current_page": 1,
  "page_size": 20,
  "results": [
    {
      "id": "uuid-string",
      "user_id": "uuid-string",
      "name": "Week of July 21",
      "description": "Healthy meal plan for the week",
      "week_start_date": "2025-07-21",
      "is_active": true,
      "plan_description": "Vegetarian meal plan with high protein",
      "analysis_text": "Well-balanced nutrition...",
      "items": [
        {
          "id": 1,
          "meal_plan": "uuid-string",
          "recipe": {
            "id": "recipe-uuid",
            "name": "Breakfast Oatmeal",
            "description": "Healthy oatmeal with fruits"
          },
          "recipe_id": "recipe-uuid",
          "day_of_week": 0,
          "meal_type": "breakfast",
          "added_at": "2025-07-23T10:00:00Z"
        }
      ],
      "items_count": 15,
      "created_at": "2025-07-23T10:00:00Z",
      "updated_at": "2025-07-23T10:00:00Z"
    }
  ]
}
```

### Create Meal Plan
- **Endpoint:** `POST /api/meal-plans/`
- **Authentication:** Required
- **Description:** Create a new meal plan

**Request Body:**
```json
{
  "name": "Week of July 28",
  "description": "Summer meal plan",
  "items": [
    {
      "recipe_id": "recipe-uuid",
      "day_of_week": 0,
      "meal_type": "breakfast",
      "serving_size": 1.0
    }
  ]
}
```

**Field Requirements:**
- `name`: Required, max 255 characters
- `description`: Optional, max 1000 characters  
- `week_start_date`: **Optional and deprecated** - If not provided, system uses current week
- `items`: Optional array of meal plan items

**Note:** The `week_start_date` field is deprecated and should not be used in new implementations. The backend will automatically assign the current week if not provided.

**Success Response (201 Created):**
```json
{
  "id": "uuid-string",
  "user_id": "uuid-string",
  "name": "Week of July 28",
  "description": "Summer meal plan",
  "week_start_date": "2025-07-28",
  "is_active": false,
  "plan_description": null,
  "analysis_text": null,
  "items": [
    {
      "id": 1,
      "meal_plan": "uuid-string",
      "recipe": {
        "id": "recipe-uuid",
        "name": "Recipe Name"
      },
      "recipe_id": "recipe-uuid",
      "day_of_week": 0,
      "meal_type": "breakfast",
      "added_at": "2025-07-23T10:00:00Z"
    }
  ],
  "items_count": 1,
  "created_at": "2025-07-23T10:00:00Z",
  "updated_at": "2025-07-23T10:00:00Z"
}
```

### Get Meal Plan Details
- **Endpoint:** `GET /api/meal-plans/{id}/`
- **Authentication:** Required
- **Description:** Get detailed information for a specific meal plan

**Success Response (200 OK):** Same format as Create Meal Plan response

### Update Meal Plan
- **Endpoint:** `PUT /api/meal-plans/{id}/`
- **Authentication:** Required (only meal plan owner can update)
- **Description:** Update an existing meal plan with optional complete item replacement

**Request Body:**
```json
{
  "name": "Updated Week Plan",
  "description": "Updated description",
  "is_active": true,
  "items": [
    {
      "recipe_id": "recipe-uuid",
      "day_of_week": 0,
      "meal_type": "breakfast"
    },
    {
      "recipe_id": "recipe-uuid-2",
      "day_of_week": 0,
      "meal_type": "lunch"
    }
  ]
}
```

**Field Requirements:**
- `name`: Optional, max 255 characters
- `description`: Optional, max 1000 characters
- `is_active`: Optional boolean
- `plan_description`: Optional, max 2000 characters
- `analysis_text`: Optional, max 5000 characters
- `items`: Optional array of meal plan items

**Special Behavior:**
- If `items` array is provided, all existing meal plan items are deleted and replaced with the new items
- If `items` is not provided or null, existing items remain unchanged
- This enables efficient template application and bulk meal plan updates
- Operation is atomic - all changes are applied together

**Success Response (200 OK):** Same format as Create Meal Plan response

### Delete Meal Plan
- **Endpoint:** `DELETE /api/meal-plans/{id}/`
- **Authentication:** Required (only meal plan owner can delete)
- **Description:** Delete a meal plan and all its items

**Success Response (204 No Content):** Empty response body

---

## Favorites Endpoints (`/api/favorites/`)

### List Favorites
- **Endpoint:** `GET /api/favorites/`
- **Authentication:** Required
- **Description:** Get user's favorite recipes with pagination

**Query Parameters:**
- `page`: Page number (default: 1)
- `page_size`: Items per page (default: 20)
- `search`: Search in recipe names and notes
- `rating`: Filter by rating (1-5)

**Success Response (200 OK):**
```json
{
  "links": {
    "next": "http://localhost:8000/api/favorites/?page=2",
    "previous": null
  },
  "count": 8,
  "total_pages": 1,
  "current_page": 1,
  "page_size": 20,
  "results": [
    {
      "id": "uuid-string",
      "recipe": {
        "id": "recipe-uuid",
        "name": "Spaghetti Carbonara",
        "description": "Classic Italian pasta dish",
        "cuisine": "Italian",
        "difficulty": "medium",
        "prep_time": 10,
        "cook_time": 15,
        "avg_rating": "4.50",
        "image_url": "https://example.com/image.jpg",
        "tags": ["pasta", "italian"]
      },
      "rating": 5,
      "notes": "My favorite pasta recipe!",
      "created_at": "2025-07-23T10:00:00Z",
      "updated_at": "2025-07-23T10:00:00Z"
    }
  ]
}
```

### Add Recipe to Favorites
- **Endpoint:** `POST /api/favorites/recipe/{recipe_id}/`
- **Authentication:** Required
- **Description:** Add a recipe to user's favorites

**Request Body:**
```json
{
  "rating": 5,
  "notes": "Absolutely delicious!"
}
```

**Success Response (201 Created):**
```json
{
  "id": "uuid-string",
  "recipe": {
    "id": "recipe-uuid",
    "name": "Recipe Name"
  },
  "rating": 5,
  "notes": "Absolutely delicious!",
  "created_at": "2025-07-23T10:00:00Z",
  "updated_at": "2025-07-23T10:00:00Z"
}
```

### Remove Recipe from Favorites
- **Endpoint:** `DELETE /api/favorites/recipe/{recipe_id}/`
- **Authentication:** Required
- **Description:** Remove a recipe from user's favorites

**Success Response (204 No Content):** Empty response body

### Check Favorite Status
- **Endpoint:** `GET /api/favorites/recipe/{recipe_id}/`
- **Authentication:** Required
- **Description:** Check if a recipe is in user's favorites

**Success Response (200 OK):**
```json
{
  "is_favorite": true,
  "rating": 5,
  "notes": "Great recipe!"
}
```

**Not Found Response (404 Not Found):**
```json
{
  "is_favorite": false
}
```

### Update Favorite
- **Endpoint:** `PUT /api/favorites/{id}/`
- **Authentication:** Required
- **Description:** Update rating and notes for a favorite recipe

**Request Body:**
```json
{
  "rating": 4,
  "notes": "Updated notes"
}
```

**Success Response (200 OK):**
```json
{
  "id": "uuid-string",
  "recipe": {
    "id": "recipe-uuid",
    "name": "Recipe Name"
  },
  "rating": 4,
  "notes": "Updated notes",
  "updated_at": "2025-07-23T11:00:00Z"
}
```

---

## AI Integration Endpoints (`/api/ai/`)

### Generate Meal Plan
- **Endpoint:** `POST /api/ai/generate-meal-plan/`
- **Authentication:** Required
- **Description:** Generate a 7-day meal plan using AI

**Request Body:**
```json
{
  "plan_description": "我想要一个健康的素食膳食计划，包含丰富的蛋白质和蔬菜",
  "dietary_preferences": {
    "dietType": "vegetarian"
  },
  "allergies": ["nuts", "shellfish"],
  "dislikes": ["mushrooms"],
  "calorie_target": 2000,
  "week_start_date": "2025-07-21",
  "additional_requirements": "低钠饮食"
}
```

**Request Parameters:**
- `plan_description`: Required, max 2000 characters
- `dietary_preferences`: Optional JSON object
- `allergies`: Optional array, max 20 items
- `dislikes`: Optional array, max 30 items
- `calorie_target`: Optional integer, 800-5000
- `week_start_date`: **Optional and deprecated** - date string (YYYY-MM-DD), system uses current week if not provided
- `additional_requirements`: Optional string, max 1000 characters

**Success Response (201 Created):**
```json
{
  "id": "uuid-string",
  "user_id": "uuid-string",
  "name": "AI Generated Meal Plan",
  "description": "Generated based on your preferences",
  "week_start_date": "2025-07-21",
  "is_active": false,
  "plan_description": "我想要一个健康的素食膳食计划...",
  "analysis_text": "This meal plan provides balanced nutrition...",
  "items": [
    {
      "id": 1,
      "recipe": {
        "id": "recipe-uuid",
        "name": "Vegetarian Breakfast Bowl",
        "description": "Nutritious breakfast with quinoa and vegetables"
      },
      "day_of_week": 0,
      "meal_type": "breakfast"
    }
  ],
  "items_count": 21,
  "created_at": "2025-07-23T10:00:00Z",
  "updated_at": "2025-07-23T10:00:00Z"
}
```

### Generate Recipe Details
- **Endpoint:** `POST /api/ai/generate-recipe-details/`
- **Authentication:** Required
- **Description:** Generate detailed recipe information using AI

**Request Body:**
```json
{
  "name": "素食炒面",
  "cuisine": "Chinese",
  "difficulty": "medium",
  "meal_type": "lunch",
  "prep_time": 15,
  "cook_time": 20,
  "dietary_restrictions": ["vegetarian"],
  "additional_requirements": "Use minimal oil"
}
```

**Request Parameters:**
- `name`: Required, max 255 characters
- `cuisine`: Optional string
- `difficulty`: Optional (easy, medium, hard)
- `meal_type`: Optional string
- `prep_time`: Optional integer, 0-1440 minutes
- `cook_time`: Optional integer, 0-1440 minutes
- `dietary_restrictions`: Optional array
- `additional_requirements`: Optional string, max 1000 characters

**Success Response (201 Created):**
```json
{
  "id": "uuid-string",
  "created_by_user": "ai_generated",
  "created_by_user_id": "system",
  "name": "素食炒面",
  "description": "Delicious vegetarian stir-fried noodles with fresh vegetables",
  "ingredients": [
    {
      "name": "Fresh noodles",
      "amount": "300.00",
      "unit": "g",
      "notes": "Use wheat noodles"
    },
    {
      "name": "Mixed vegetables",
      "amount": "2.00",
      "unit": "cups",
      "notes": "Carrots, bell peppers, cabbage"
    }
  ],
  "instructions": "1. Prepare all vegetables by washing and cutting...",
  "nutrition_info": {
    "calories": "320.00",
    "protein": "12.00",
    "carbs": "58.00",
    "fat": "6.00",
    "fiber": "4.00",
    "sodium": "800.00",
    "sugar": "8.00"
  },
  "cuisine": "Chinese",
  "prep_time": 15,
  "cook_time": 20,
  "total_time": 35,
  "difficulty": "medium",
  "avg_rating": "0.00",
  "rating_count": 0,
  "image_url": "",
  "tags": ["lunch", "medium", "chinese", "vegetarian"],
  "created_at": "2025-07-23T10:00:00Z",
  "updated_at": "2025-07-23T10:00:00Z"
}
```

### Analyze Meal Plan
- **Endpoint:** `POST /api/ai/analyze-meal-plan/`
- **Authentication:** Required
- **Description:** Analyze an existing meal plan for nutrition and balance

**Request Body:**
```json
{
  "meal_plan_id": "uuid-string",
  "plan_description": "健康的素食膳食计划",
  "analysis_type": "full",
  "include_recommendations": true
}
```

**Request Parameters:**
- `meal_plan_id`: Required UUID string
- `plan_description`: Optional, max 2000 characters
- `analysis_type`: Optional (nutrition, variety, balance, full)
- `include_recommendations`: Optional boolean (default: true)

**Success Response (200 OK):**
```json
{
  "meal_plan_id": "uuid-string",
  "analysis_type": "full",
  "total_recipes": 15,
  "analysis_text": "This meal plan provides excellent nutritional balance with adequate protein, healthy carbohydrates, and essential vitamins. The variety of cuisines and cooking methods ensures an enjoyable eating experience throughout the week. Recommendations: Consider adding more omega-3 rich foods and reducing sodium intake in some meals.",
  "analysis_date": "2025-07-23T10:00:00Z"
}
```

---

## Error Response Format

All endpoints return errors in a consistent format:

**Validation Errors (400 Bad Request):**
```json
{
  "field_name": [
    "This field is required.",
    "Ensure this value has at most 255 characters."
  ],
  "non_field_errors": [
    "Cross-field validation error message"
  ]
}
```

**Authentication Errors (401 Unauthorized):**
```json
{
  "detail": "Authentication credentials were not provided."
}
```

**Permission Errors (403 Forbidden):**
```json
{
  "detail": "You do not have permission to perform this action."
}
```

**Not Found Errors (404 Not Found):**
```json
{
  "detail": "Not found."
}
```

**Server Errors (500 Internal Server Error):**
```json
{
  "detail": "A server error occurred."
}
```

---

## Data Types and Validation Rules

### Common Field Types
- **UUID**: String representation of UUID (e.g., "123e4567-e89b-12d3-a456-426614174000")
- **DateTime**: ISO 8601 format (e.g., "2025-07-23T10:00:00Z")
- **Date**: YYYY-MM-DD format (e.g., "2025-07-23")
- **Decimal**: String representation with 2 decimal places (e.g., "12.50")

### Validation Limits
- **Text Fields**: HTML sanitization applied to prevent XSS
- **Array Fields**: Size limits enforced (see individual endpoint documentation)
- **Numeric Fields**: Range validation applied
- **File Uploads**: Size and type restrictions (if applicable)

### Pagination
All list endpoints support pagination with the following response structure:
- `links.next`: URL for next page (null if last page)
- `links.previous`: URL for previous page (null if first page)
- `count`: Total number of items
- `total_pages`: Total number of pages
- `current_page`: Current page number
- `page_size`: Number of items per page
- `results`: Array of items for current page

---

## Rate Limiting

API endpoints may be subject to rate limiting. Rate limit information is included in response headers:
- `X-RateLimit-Limit`: Maximum requests per time window
- `X-RateLimit-Remaining`: Remaining requests in current window
- `X-RateLimit-Reset`: Time when rate limit resets

---

## Versioning

The API currently uses URL path versioning. All endpoints are prefixed with `/api/` and may include version numbers in future releases (e.g., `/api/v2/`).

---

## Support

For API support and questions, please refer to the project documentation or contact the development team.