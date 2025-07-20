# Django Serializers Documentation

This document provides comprehensive documentation for all Django REST Framework serializers implemented for the MealPrepAI backend.

## Overview

The serializers are designed to match the existing Next.js API validation patterns exactly, ensuring seamless migration from the current Next.js API routes to the Django backend.

## Authentication Serializers (`apps/authentication/serializers.py`)

### DietaryPreferencesSerializer

Handles nested dietary preferences data within user profiles.

**Fields:**
- `allergies`: List of allergy strings (max 20 items, 100 chars each)
- `diet_type`: String from predefined list (vegetarian, vegan, etc.)
- `dislikes`: List of dislike strings (max 30 items, 100 chars each)
- `calorie_target`: Integer between 800-5000

**Validation:**
- Validates diet type against allowed values
- Limits array sizes to prevent abuse
- Sanitizes string inputs

### UserSerializer

Main serializer for user data with nested dietary preferences.

**Fields:**
- `id`: UUID (read-only)
- `username`: String (3-50 chars, unique)
- `email`: Email (unique, required)
- `display_name`: String (max 100 chars)
- `dietary_preferences`: Nested DietaryPreferencesSerializer
- `password`: Write-only password field
- `created_at`, `updated_at`: Timestamps (read-only)

**Validation:**
- Username uniqueness check (case-insensitive)
- Email format and uniqueness validation
- Password strength validation using Django validators
- Dietary preferences structure validation

### UserRegistrationSerializer

Extends UserSerializer for registration with password confirmation.

**Additional Fields:**
- `password_confirm`: Must match password field

### UserProfileSerializer

User serializer without password field for profile updates.

### ChangePasswordSerializer

Handles password change operations.

**Fields:**
- `current_password`: Current password verification
- `new_password`: New password with strength validation
- `new_password_confirm`: Confirmation field

## Recipe Serializers (`apps/recipes/serializers.py`)

### IngredientSerializer

Handles individual recipe ingredients.

**Fields:**
- `name`: String (max 100 chars, required)
- `amount`: Decimal (positive, 2 decimal places)
- `unit`: String (max 20 chars, required)
- `notes`: String (max 200 chars, optional)

**Validation:**
- Text sanitization (removes HTML, scripts)
- Positive amount validation
- Required field validation

### NutritionInfoSerializer

Handles nutritional information data.

**Fields:**
- `calories`, `protein`, `carbs`, `fat`, `fiber`, `sugar`, `sodium`: All optional decimal fields (non-negative)

**Validation:**
- Non-negative value validation
- Rounds values to 2 decimal places

### RecipeSerializer

Main recipe serializer with comprehensive validation.

**Fields:**
- `id`: UUID (read-only)
- `created_by_user`: String representation (read-only)
- `created_by_user_id`: UUID (read-only)
- `name`: String (max 255 chars, required)
- `description`: String (max 1000 chars, optional)
- `ingredients`: Array of IngredientSerializer (1-50 items)
- `instructions`: Text (max 5000 chars, required)
- `nutrition_info`: Nested NutritionInfoSerializer
- `cuisine`: String (max 100 chars, optional)
- `prep_time`, `cook_time`: Integers (0-1440 minutes)
- `total_time`: Computed field (prep + cook time)
- `difficulty`: Choice field (easy, medium, hard)
- `avg_rating`, `rating_count`: Read-only fields
- `image_url`: URL field (optional)
- `tags`: Array of strings (max 20 items, 30 chars each)
- `created_at`, `updated_at`: Timestamps (read-only)

**Validation:**
- Comprehensive text sanitization
- Time range validation (max 24 hours)
- Ingredient array validation (1-50 items)
- Tags validation (max 20, unique)
- Difficulty choice validation
- Cross-field validation for total time

### RecipeListSerializer

Simplified version for list views (excludes heavy fields like ingredients).

### RecipeCreateSerializer

Enhanced validation for AI-generated recipe content.

## Meal Plan Serializers (`apps/meal_plans/serializers.py`)

### MealPlanItemSerializer

Handles individual meal plan items linking recipes to specific days/meals.

**Fields:**
- `meal_plan`: Foreign key to meal plan
- `recipe`: Nested RecipeListSerializer (read-only)
- `recipe_id`: UUID (write-only)
- `day_of_week`: Integer (0-6, Monday-Sunday)
- `meal_type`: Choice field (breakfast, lunch, dinner, snack)
- `added_at`: Timestamp (read-only)

**Validation:**
- Day of week range validation
- Meal type choice validation
- Recipe existence validation

### MealPlanSerializer

Main meal plan serializer with nested items.

**Fields:**
- `id`: UUID (read-only)
- `user`: String representation (read-only)
- `user_id`: UUID (read-only)
- `name`: String (max 255 chars, unique per user)
- `description`: String (max 1000 chars, optional)
- `week_start_date`: Date (must be Monday)
- `is_active`: Boolean
- `plan_description`: String (max 2000 chars, optional)
- `analysis_text`: String (max 5000 chars, optional)
- `items`: Array of MealPlanItemSerializer (read-only)
- `created_at`, `updated_at`: Timestamps (read-only)

**Validation:**
- Name uniqueness per user
- Week start date must be Monday
- Date range validation (not too far in past)
- Active meal plan uniqueness per week per user

### MealPlanListSerializer

Simplified version for list views with item count.

### MealPlanCreateSerializer

Supports creating meal plans with initial items.

### AddMealPlanItemSerializer

Handles adding individual items to existing meal plans.

### MealPlanAnalysisSerializer

Handles meal plan analysis requests.

## Favorites Serializers (`apps/favorites/serializers.py`)

### FavoriteSerializer

Handles user favorite recipes with personal ratings and notes.

**Fields:**
- `user`: String representation (read-only)
- `user_id`: UUID (read-only)
- `recipe`: Nested RecipeListSerializer (read-only)
- `recipe_id`: UUID (write-only)
- `personal_rating`: Integer (1-5, optional)
- `personal_notes`: String (max 1000 chars, optional)
- `added_at`: Timestamp (read-only)

**Validation:**
- Recipe existence validation
- Rating range validation (1-5)
- Duplicate favorite prevention
- Text sanitization for notes

### FavoriteListSerializer

Simplified version for list views.

### FavoriteCreateSerializer

Handles favorite creation with upsert behavior.

### CollectionSerializer

Handles recipe collections with relationship management.

**Fields:**
- `id`: UUID (read-only)
- `user`: String representation (read-only)
- `user_id`: UUID (read-only)
- `name`: String (max 255 chars, unique per user)
- `description`: String (max 1000 chars, optional)
- `color`: Hex color code (default: #4DB6AC)
- `icon`: String (max 50 chars, default: heart)
- `is_public`: Boolean
- `recipes`: Array of RecipeListSerializer (read-only)
- `recipe_ids`: Array of UUIDs (write-only)
- `recipe_count`: Computed field
- `created_at`, `updated_at`: Timestamps (read-only)

**Validation:**
- Name uniqueness per user
- Hex color code validation
- Recipe existence validation
- Recipe limit validation (max 100)

### CollectionListSerializer

Simplified version for list views.

### CollectionCreateSerializer

Handles collection creation.

### AddRecipeToCollectionSerializer

Handles adding recipes to existing collections.

## Validation Patterns

### Text Sanitization

All text inputs are sanitized to remove:
- HTML script tags
- HTML tags in general
- JavaScript protocols
- Excessive whitespace

### Length Limits

Consistent with Next.js API:
- Usernames: 3-50 characters
- Names/titles: 255 characters max
- Descriptions: 1000 characters max
- Instructions: 5000 characters max
- Notes: 200-1000 characters depending on context

### Array Limits

- Ingredients: 1-50 items
- Tags: 0-20 items
- Allergies: 0-20 items
- Dislikes: 0-30 items
- Collection recipes: 0-100 items

### Numeric Ranges

- Time values: 0-1440 minutes (24 hours)
- Ratings: 1-5 scale
- Calorie targets: 800-5000
- Nutrition values: Non-negative

### Uniqueness Constraints

- Usernames (case-insensitive)
- Email addresses (case-insensitive)
- Meal plan names per user
- Collection names per user
- User-recipe favorites
- Meal plan items per day/meal type

## Error Response Format

All validation errors follow Django REST Framework's standard format:

```json
{
  "field_name": [
    "Error message 1",
    "Error message 2"
  ],
  "non_field_errors": [
    "Cross-field validation error"
  ]
}
```

This matches the expected error format from the Next.js API for seamless frontend integration.

## Testing

Comprehensive test suites verify:
- Individual field validation
- Cross-field validation
- Compatibility with Next.js validation patterns
- Error message consistency
- Edge case handling

Run tests with:
```bash
python test_serializers.py
python test_validation_compatibility.py
```

## Usage Examples

### Creating a Recipe

```python
from apps.recipes.serializers import RecipeSerializer

data = {
    'name': 'Grilled Chicken',
    'ingredients': [
        {'name': 'Chicken breast', 'amount': 1.5, 'unit': 'lbs'}
    ],
    'instructions': 'Grill until cooked through.',
    'prep_time': 10,
    'cook_time': 15,
    'difficulty': 'easy'
}

serializer = RecipeSerializer(data=data, context={'request': request})
if serializer.is_valid():
    recipe = serializer.save()
```

### Creating a User

```python
from apps.authentication.serializers import UserRegistrationSerializer

data = {
    'username': 'newuser',
    'email': 'user@example.com',
    'password': 'secure_password',
    'password_confirm': 'secure_password',
    'dietary_preferences': {
        'allergies': ['nuts'],
        'diet_type': 'vegetarian'
    }
}

serializer = UserRegistrationSerializer(data=data)
if serializer.is_valid():
    user = serializer.save()
```

### Creating a Meal Plan

```python
from apps.meal_plans.serializers import MealPlanSerializer

data = {
    'name': 'Week 1 Plan',
    'week_start_date': '2024-01-01',  # Must be a Monday
    'is_active': True
}

serializer = MealPlanSerializer(data=data, context={'request': request})
if serializer.is_valid():
    meal_plan = serializer.save()
```