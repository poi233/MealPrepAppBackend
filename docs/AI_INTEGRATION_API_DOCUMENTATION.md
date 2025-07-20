# AI Integration API Documentation

This document describes the AI integration API endpoints for the MealPrepAI Django backend.

## Overview

The AI integration module provides three main endpoints that leverage Google Gemini AI to generate meal plans, recipe details, and analyze meal plans. All endpoints require authentication and provide comprehensive error handling.

## Authentication

All AI integration endpoints require JWT authentication. Include the JWT token in the Authorization header:

```
Authorization: Bearer <your_jwt_token>
```

## Endpoints

### 1. Generate Meal Plan

**Endpoint:** `POST /api/ai/generate-meal-plan/`

**Description:** Generate a 7-day meal plan using AI based on user preferences and requirements.

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
- `plan_description` (required): Description of the desired meal plan (max 2000 characters)
- `dietary_preferences` (optional): JSON object with dietary preferences
- `allergies` (optional): Array of food allergies to avoid (max 20 items)
- `dislikes` (optional): Array of foods the user dislikes (max 30 items)
- `calorie_target` (optional): Daily calorie target (1000-5000)
- `week_start_date` (optional): Start date for the meal plan (defaults to next Monday)
- `additional_requirements` (optional): Additional requirements or preferences (max 1000 characters)

**Success Response (201 Created):**
```json
{
  "name": "AI Generated Plan - 2025-07-20",
  "description": "AI-generated healthy meal plan",
  "week_start_date": "2025-07-21",
  "plan_description": "我想要一个健康的素食膳食计划，包含丰富的蛋白质和蔬菜",
  "analysis_text": "Designed for vegetarian diet. Avoids allergens: nuts, shellfish. Target: 2000 calories/day.",
  "daily_meals": [
    {
      "day": "星期一",
      "breakfast": [
        {
          "recipeName": "豆腐炒蔬菜",
          "ingredients": [
            "嫩豆腐 200克，切块",
            "胡萝卜 1根，切丁",
            "青椒 1个，切丝"
          ],
          "instructions": "1. **准备食材**: 将豆腐切块，蔬菜洗净切好。\n2. **热锅**: 平底锅刷少量油，中火加热。\n3. **炒制**: 先下豆腐块煎至两面金黄，再加入蔬菜炒制3-5分钟。\n4. **调味**: 加入生抽、盐调味即可。"
        }
      ],
      "lunch": [...],
      "dinner": [...]
    },
    // ... 6 more days
  ]
}
```

**Error Responses:**
- `400 Bad Request`: Validation errors
- `401 Unauthorized`: Authentication required
- `500 Internal Server Error`: AI service failure

### 2. Generate Recipe Details

**Endpoint:** `POST /api/ai/generate-recipe-details/`

**Description:** Generate detailed recipe information including ingredients and instructions using AI.

**Request Body:**
```json
{
  "name": "素食炒面",
  "description": "健康美味的素食炒面",
  "cuisine": "Chinese",
  "difficulty": "medium",
  "prep_time": 15,
  "cook_time": 20,
  "meal_type": "lunch",
  "dietary_restrictions": ["vegetarian"],
  "ingredients": ["面条", "蔬菜"],
  "additional_requirements": "低油少盐"
}
```

**Request Parameters:**
- `name` (required): Name of the recipe to generate (max 255 characters)
- `description` (optional): Brief description of the desired recipe (max 1000 characters)
- `cuisine` (optional): Cuisine type (max 100 characters)
- `difficulty` (optional): Difficulty level ("easy", "medium", "hard")
- `prep_time` (optional): Preparation time in minutes (1-300)
- `cook_time` (optional): Cooking time in minutes (1-480)
- `meal_type` (optional): Type of meal ("breakfast", "lunch", "dinner", "snack")
- `dietary_restrictions` (optional): Array of dietary restrictions (max 10 items)
- `ingredients` (optional): Array of specific ingredients to include (max 50 items)
- `additional_requirements` (optional): Additional requirements (max 1000 characters)

**Success Response (201 Created):**
```json
{
  "name": "素食炒面",
  "description": "健康美味的素食炒面",
  "cuisine": "Chinese",
  "difficulty": "medium",
  "prep_time": 15,
  "cook_time": 20,
  "ingredients": [
    "新鲜或干面条（推荐碱水面）200克",
    "胡萝卜 1根，切丝",
    "豆芽菜 100克",
    "青椒 1个，切丝",
    "生抽 2汤匙",
    "老抽 1茶匙",
    "植物油 2汤匙",
    "盐 适量",
    "白胡椒粉 少许"
  ],
  "instructions": "1. **准备面条**: 将面条按包装说明煮至八分熟，捞起沥干备用。\n2. **准备蔬菜**: 胡萝卜切丝，青椒切丝，豆芽菜洗净沥干。\n3. **热锅炒制**: 热锅下油，先炒胡萝卜丝1分钟，再加入青椒丝和豆芽菜炒2分钟。\n4. **下面条**: 加入煮好的面条，用铲子快速翻炒。\n5. **调味**: 加入生抽、老抽、盐和胡椒粉，炒匀至面条上色。\n6. **出锅**: 炒制1-2分钟至面条热透即可出锅。",
  "nutrition_info": {
    "calories": 350,
    "protein": "25g",
    "carbohydrates": "30g",
    "fat": "15g",
    "fiber": "5g",
    "sodium": "800mg",
    "sugar": "8g",
    "servings": 4
  },
  "tags": ["lunch", "medium", "chinese", "vegetarian"]
}
```

### 3. Analyze Meal Plan

**Endpoint:** `POST /api/ai/analyze-meal-plan/`

**Description:** Analyze an existing meal plan for nutrition, variety, and balance using AI.

**Request Body:**
```json
{
  "meal_plan_id": "12345678-1234-1234-1234-123456789012",
  "plan_description": "健康的素食膳食计划",
  "analysis_type": "full",
  "include_recommendations": true
}
```

**Request Parameters:**
- `meal_plan_id` (required): UUID of the meal plan to analyze
- `plan_description` (optional): Original plan description for context (max 2000 characters)
- `analysis_type` (optional): Type of analysis ("nutrition", "variety", "balance", "full")
- `include_recommendations` (optional): Whether to include AI recommendations (default: true)

**Success Response (200 OK):**
```json
{
  "meal_plan_id": "12345678-1234-1234-1234-123456789012",
  "analysis_type": "full",
  "total_recipes": 15,
  "analysis_text": "整体来看，这个膳食计划在蛋白质摄入方面做得不错，主要来源包括豆腐、豆类和坚果。蔬菜种类丰富，包含了不同颜色的蔬菜，能够提供多样化的维生素和矿物质。\n\n该计划很好地遵循了您"素食"的偏好，所有食谱都不含肉类和海鲜。碳水化合物来源主要是全谷物和蔬菜，这有助于维持稳定的血糖水平。\n\n**建议改进：**\n* **增加钙质来源**: 建议在早餐中加入芝麻或豆浆，以补充钙质。\n* **丰富蛋白质种类**: 可以考虑加入藜麦、鹰嘴豆等高蛋白食材。\n* **注意维生素B12**: 素食者容易缺乏B12，建议适当补充或选择强化食品。",
  "analysis_date": "2025-07-20T10:30:00Z"
}
```

**Error Responses:**
- `400 Bad Request`: Validation errors or meal plan not found
- `401 Unauthorized`: Authentication required
- `404 Not Found`: Meal plan not accessible by user
- `500 Internal Server Error`: AI service failure

## Error Response Format

All error responses follow a consistent format:

**Validation Error (400):**
```json
{
  "error": "Validation failed",
  "details": {
    "plan_description": ["This field is required."],
    "calorie_target": ["Ensure this value is greater than or equal to 1000."]
  }
}
```

**Authentication Error (401):**
```json
{
  "detail": "Authentication credentials were not provided."
}
```

**Server Error (500):**
```json
{
  "error": "Failed to generate meal plan: AI service temporarily unavailable"
}
```

## Rate Limiting

The AI integration endpoints implement rate limiting to prevent abuse:
- Maximum 60 requests per minute per user
- Rate limit exceeded responses return HTTP 429 with retry information

## Caching

AI responses are cached to improve performance:
- Meal plan generation: 1 hour cache
- Recipe details generation: 2 hours cache  
- Meal plan analysis: 30 minutes cache

Cache keys are based on request parameters and user ID to ensure user-specific caching.

## Features

### 1. Request Validation
- Comprehensive input validation using Django REST Framework serializers
- Field-specific error messages
- Cross-field validation for related parameters

### 2. Error Handling
- Graceful handling of AI service failures
- Retry logic with exponential backoff
- Detailed error logging for debugging

### 3. Performance Optimization
- Response caching to reduce AI API calls
- Rate limiting to prevent abuse
- Async processing for better concurrency

### 4. Security
- JWT authentication required for all endpoints
- User-specific data access controls
- Input sanitization and validation

## Usage Examples

### Generate a Vegetarian Meal Plan

```bash
curl -X POST "http://localhost:8000/api/ai/generate-meal-plan/" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "plan_description": "我想要一个健康的素食膳食计划，包含丰富的蛋白质和蔬菜",
    "dietary_preferences": {"dietType": "vegetarian"},
    "calorie_target": 2000,
    "week_start_date": "2025-07-21"
  }'
```

### Generate Recipe Details

```bash
curl -X POST "http://localhost:8000/api/ai/generate-recipe-details/" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "素食炒面",
    "cuisine": "Chinese",
    "difficulty": "medium",
    "meal_type": "lunch"
  }'
```

### Analyze Meal Plan

```bash
curl -X POST "http://localhost:8000/api/ai/analyze-meal-plan/" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "meal_plan_id": "12345678-1234-1234-1234-123456789012",
    "analysis_type": "full"
  }'
```

## Integration Notes

### For Web Frontend (Next.js)
- Replace existing `/api/ai/*` routes with Django backend calls
- Update authentication to use Django JWT tokens
- Handle new response formats and error structures

### For iOS App
- Use the same endpoints with proper JWT authentication
- Implement offline caching for generated content
- Handle network errors gracefully with retry logic

## Monitoring and Logging

All AI integration endpoints include comprehensive logging:
- Request/response logging for debugging
- Performance metrics for optimization
- Error tracking for reliability monitoring
- AI service usage tracking for cost management