# Favorites API Documentation

## Overview

The Favorites API provides endpoints for managing user's favorite recipes, including personal ratings and notes. All endpoints require JWT authentication.

## Base URL

```
/api/favorites/
```

## Authentication

All endpoints require JWT authentication. Include the token in the Authorization header:

```
Authorization: Bearer <jwt_token>
```

## Endpoints

### 1. List User's Favorite Recipes

**GET** `/api/favorites/favorites/`

Lists all favorite recipes for the authenticated user with pagination, filtering, and search capabilities.

#### Query Parameters

- `search` (string): Search in recipe name, description, cuisine, or personal notes
- `personal_rating` (integer): Filter by exact personal rating (1-5)
- `personal_rating__gte` (integer): Filter by minimum personal rating
- `personal_rating__lte` (integer): Filter by maximum personal rating
- `recipe__cuisine` (string): Filter by recipe cuisine
- `recipe__difficulty` (string): Filter by recipe difficulty
- `added_at__gte` (datetime): Filter by minimum date added
- `added_at__lte` (datetime): Filter by maximum date added
- `ordering` (string): Order results by field (e.g., `-added_at`, `personal_rating`, `recipe__name`)
- `page` (integer): Page number for pagination
- `page_size` (integer): Number of results per page

#### Response

```json
{
  "count": 25,
  "next": "http://localhost:8000/api/favorites/favorites/?page=2",
  "previous": null,
  "results": [
    {
      "user_id": "123e4567-e89b-12d3-a456-426614174000",
      "recipe": {
        "id": "123e4567-e89b-12d3-a456-426614174001",
        "name": "Spaghetti Carbonara",
        "description": "Classic Italian pasta dish",
        "cuisine": "Italian",
        "meal_type": "dinner",
        "prep_time": 15,
        "cook_time": 20,
        "difficulty": "medium",
        "avg_rating": 4.5,
        "rating_count": 12,
        "image_url": "https://example.com/image.jpg",
        "tags": ["pasta", "italian", "quick"],
        "created_at": "2024-01-15T10:30:00Z",
        "updated_at": "2024-01-15T10:30:00Z"
      },
      "personal_rating": 5,
      "personal_notes": "My favorite pasta recipe!",
      "added_at": "2024-01-20T14:30:00Z"
    }
  ]
}
```

### 2. Add Recipe to Favorites

**POST** `/api/favorites/recipe/{recipe_id}/`

Adds a recipe to the user's favorites with optional personal rating and notes.

#### Path Parameters

- `recipe_id` (UUID): The ID of the recipe to add to favorites

#### Request Body

```json
{
  "personal_rating": 5,
  "personal_notes": "This is my favorite recipe!"
}
```

#### Fields

- `personal_rating` (integer, optional): Personal rating from 1 to 5 stars
- `personal_notes` (string, optional): Personal notes about the recipe (max 1000 characters)

#### Response

**Status: 201 Created**

```json
{
  "user": "testuser",
  "user_id": "123e4567-e89b-12d3-a456-426614174000",
  "recipe": {
    "id": "123e4567-e89b-12d3-a456-426614174001",
    "name": "Spaghetti Carbonara",
    "description": "Classic Italian pasta dish",
    "cuisine": "Italian",
    "meal_type": "dinner",
    "prep_time": 15,
    "cook_time": 20,
    "difficulty": "medium",
    "avg_rating": 4.5,
    "rating_count": 12,
    "image_url": "https://example.com/image.jpg",
    "tags": ["pasta", "italian", "quick"],
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-15T10:30:00Z"
  },
  "personal_rating": 5,
  "personal_notes": "This is my favorite recipe!",
  "added_at": "2024-01-20T14:30:00Z"
}
```

#### Error Responses

**Status: 400 Bad Request** - Recipe already in favorites
```json
{
  "error": "Recipe is already in favorites"
}
```

**Status: 404 Not Found** - Recipe not found
```json
{
  "error": "Recipe not found"
}
```

### 3. Remove Recipe from Favorites

**DELETE** `/api/favorites/recipe/{recipe_id}/`

Removes a recipe from the user's favorites.

#### Path Parameters

- `recipe_id` (UUID): The ID of the recipe to remove from favorites

#### Response

**Status: 204 No Content**

```json
{
  "message": "Recipe \"Spaghetti Carbonara\" has been removed from favorites"
}
```

#### Error Responses

**Status: 404 Not Found** - Recipe not in favorites
```json
{
  "error": "Recipe is not in favorites"
}
```

### 4. Check Favorite Status

**GET** `/api/favorites/recipe/{recipe_id}/`

Checks if a recipe is in the user's favorites and returns the favorite details if it exists.

#### Path Parameters

- `recipe_id` (UUID): The ID of the recipe to check

#### Response

**If recipe is in favorites:**

**Status: 200 OK**

```json
{
  "user": "testuser",
  "user_id": "123e4567-e89b-12d3-a456-426614174000",
  "recipe": {
    "id": "123e4567-e89b-12d3-a456-426614174001",
    "name": "Spaghetti Carbonara",
    "description": "Classic Italian pasta dish",
    "cuisine": "Italian",
    "meal_type": "dinner",
    "prep_time": 15,
    "cook_time": 20,
    "difficulty": "medium",
    "avg_rating": 4.5,
    "rating_count": 12,
    "image_url": "https://example.com/image.jpg",
    "tags": ["pasta", "italian", "quick"],
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-15T10:30:00Z"
  },
  "personal_rating": 5,
  "personal_notes": "This is my favorite recipe!",
  "added_at": "2024-01-20T14:30:00Z"
}
```

**If recipe is not in favorites:**

**Status: 200 OK**

```json
{
  "is_favorite": false
}
```

### 5. Update Favorite Rating and Notes

**PUT** `/api/favorites/favorites/{favorite_id}/`

Updates the personal rating and notes for an existing favorite.

#### Path Parameters

- `favorite_id` (integer): The ID of the favorite to update

#### Request Body

```json
{
  "personal_rating": 4,
  "personal_notes": "Updated notes - still great but not perfect"
}
```

#### Fields

- `personal_rating` (integer, optional): Personal rating from 1 to 5 stars
- `personal_notes` (string, optional): Personal notes about the recipe (max 1000 characters)

#### Response

**Status: 200 OK**

```json
{
  "user": "testuser",
  "user_id": "123e4567-e89b-12d3-a456-426614174000",
  "recipe": {
    "id": "123e4567-e89b-12d3-a456-426614174001",
    "name": "Spaghetti Carbonara",
    "description": "Classic Italian pasta dish",
    "cuisine": "Italian",
    "meal_type": "dinner",
    "prep_time": 15,
    "cook_time": 20,
    "difficulty": "medium",
    "avg_rating": 4.5,
    "rating_count": 12,
    "image_url": "https://example.com/image.jpg",
    "tags": ["pasta", "italian", "quick"],
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-15T10:30:00Z"
  },
  "personal_rating": 4,
  "personal_notes": "Updated notes - still great but not perfect",
  "added_at": "2024-01-20T14:30:00Z"
}
```

## Features

### Personal Rating System
- Users can rate their favorite recipes from 1 to 5 stars
- Ratings are personal and don't affect the recipe's overall rating
- Optional field - favorites can be added without ratings

### Personal Notes
- Users can add personal notes to their favorite recipes
- Notes are limited to 1000 characters
- Useful for personal cooking tips, modifications, or memories

### Filtering and Search
- Search across recipe names, descriptions, cuisine, and personal notes
- Filter by personal rating, cuisine, difficulty, and date added
- Support for range filters (e.g., rating >= 4)

### Pagination
- All list endpoints support pagination
- Configurable page size
- Standard pagination response format

### User Isolation
- Users can only see and manage their own favorites
- Automatic user association based on JWT token
- No access to other users' favorites

### Error Handling
- Comprehensive error messages
- Proper HTTP status codes
- Validation error details

### Synchronization Logic
- Favorites are immediately synchronized across all user sessions
- Real-time updates when favorites are added/removed
- Consistent state across web and mobile applications

## Authentication Requirements

All endpoints require a valid JWT token. The token should be included in the Authorization header:

```
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...
```

Unauthenticated requests will receive a 401 Unauthorized response.

## Rate Limiting

The API implements rate limiting to prevent abuse:
- 100 requests per minute per user for read operations
- 30 requests per minute per user for write operations

## Error Codes

- `400 Bad Request`: Invalid request data or validation errors
- `401 Unauthorized`: Missing or invalid authentication token
- `403 Forbidden`: User doesn't have permission to access the resource
- `404 Not Found`: Recipe or favorite not found
- `429 Too Many Requests`: Rate limit exceeded
- `500 Internal Server Error`: Server error

## Examples

### Adding a Recipe to Favorites with cURL

```bash
curl -X POST \
  http://localhost:8000/api/favorites/recipe/123e4567-e89b-12d3-a456-426614174001/ \
  -H 'Authorization: Bearer YOUR_JWT_TOKEN' \
  -H 'Content-Type: application/json' \
  -d '{
    "personal_rating": 5,
    "personal_notes": "Amazing recipe! Added extra garlic."
  }'
```

### Searching Favorites

```bash
curl -X GET \
  'http://localhost:8000/api/favorites/favorites/?search=pasta&personal_rating__gte=4' \
  -H 'Authorization: Bearer YOUR_JWT_TOKEN'
```

### Removing a Recipe from Favorites

```bash
curl -X DELETE \
  http://localhost:8000/api/favorites/recipe/123e4567-e89b-12d3-a456-426614174001/ \
  -H 'Authorization: Bearer YOUR_JWT_TOKEN'
```