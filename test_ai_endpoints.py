#!/usr/bin/env python
"""
Test script for AI integration API endpoints.
"""
import os
import sys
import django
import json
from datetime import date

# Add the src directory to the Python path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.join(BASE_DIR, 'src')
sys.path.insert(0, SRC_DIR)

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mealprep_project.settings.development')
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()


def create_test_user():
    """Create a test user and return authentication token."""
    try:
        user = User.objects.get(username='testuser_ai')
    except User.DoesNotExist:
        user = User.objects.create_user(
            username='testuser_ai',
            email='testuser_ai@example.com',
            password='testpass123'
        )
    
    refresh = RefreshToken.for_user(user)
    return user, str(refresh.access_token)


def test_generate_meal_plan_endpoint():
    """Test the generate meal plan API endpoint."""
    print("Testing /api/ai/generate-meal-plan/ endpoint...")
    
    client = Client()
    user, token = create_test_user()
    
    # Test data
    data = {
        'plan_description': '我想要一个健康的素食膳食计划，包含丰富的蛋白质和蔬菜',
        'dietary_preferences': {'dietType': 'vegetarian'},
        'week_start_date': date.today().isoformat(),
        'calorie_target': 2000
    }
    
    # Make request with authentication
    response = client.post(
        '/api/ai/generate-meal-plan/',
        data=json.dumps(data),
        content_type='application/json',
        HTTP_AUTHORIZATION=f'Bearer {token}'
    )
    
    print(f"   Status Code: {response.status_code}")
    
    if response.status_code == 201:
        response_data = response.json()
        print("   ✅ Meal plan generation endpoint successful!")
        print(f"   Plan name: {response_data.get('name', 'N/A')}")
        print(f"   Daily meals count: {len(response_data.get('daily_meals', []))}")
        return True
    else:
        print(f"   ❌ Meal plan generation failed: {response.content.decode()}")
        return False


def test_generate_recipe_details_endpoint():
    """Test the generate recipe details API endpoint."""
    print("\nTesting /api/ai/generate-recipe-details/ endpoint...")
    
    client = Client()
    user, token = create_test_user()
    
    # Test data
    data = {
        'name': '素食炒面',
        'cuisine': 'Chinese',
        'difficulty': 'medium',
        'meal_type': 'lunch',
        'prep_time': 15,
        'cook_time': 20
    }
    
    # Make request with authentication
    response = client.post(
        '/api/ai/generate-recipe-details/',
        data=json.dumps(data),
        content_type='application/json',
        HTTP_AUTHORIZATION=f'Bearer {token}'
    )
    
    print(f"   Status Code: {response.status_code}")
    
    if response.status_code == 201:
        response_data = response.json()
        print("   ✅ Recipe details generation endpoint successful!")
        print(f"   Recipe name: {response_data.get('name', 'N/A')}")
        print(f"   Ingredients count: {len(response_data.get('ingredients', []))}")
        return True
    else:
        print(f"   ❌ Recipe details generation failed: {response.content.decode()}")
        return False


def test_analyze_meal_plan_endpoint():
    """Test the analyze meal plan API endpoint."""
    print("\nTesting /api/ai/analyze-meal-plan/ endpoint...")
    
    client = Client()
    user, token = create_test_user()
    
    # First, create a meal plan to analyze
    from apps.meal_plans.models import MealPlan, MealPlanItem
    from apps.recipes.models import Recipe
    
    # Create a test recipe
    recipe = Recipe.objects.create(
        name='Test Recipe',
        description='A test recipe for analysis',
        ingredients=['Test ingredient 1', 'Test ingredient 2'],
        instructions='Test instructions',
        created_by_user=user
    )
    
    # Create a test meal plan (or get existing one)
    import uuid
    meal_plan_name = f'Test Meal Plan {uuid.uuid4().hex[:8]}'
    meal_plan = MealPlan.objects.create(
        user=user,
        name=meal_plan_name,
        description='A test meal plan for analysis',
        week_start_date=date.today()
    )
    
    # Add recipe to meal plan
    MealPlanItem.objects.create(
        meal_plan=meal_plan,
        recipe=recipe,
        day_of_week=0,  # Monday
        meal_type='lunch'
    )
    
    # Test data
    data = {
        'meal_plan_id': str(meal_plan.id),
        'plan_description': '健康的素食膳食计划',
        'analysis_type': 'full'
    }
    
    # Make request with authentication
    response = client.post(
        '/api/ai/analyze-meal-plan/',
        data=json.dumps(data),
        content_type='application/json',
        HTTP_AUTHORIZATION=f'Bearer {token}'
    )
    
    print(f"   Status Code: {response.status_code}")
    
    if response.status_code == 200:
        response_data = response.json()
        print("   ✅ Meal plan analysis endpoint successful!")
        print(f"   Analysis type: {response_data.get('analysis_type', 'N/A')}")
        print(f"   Total recipes: {response_data.get('total_recipes', 'N/A')}")
        return True
    else:
        print(f"   ❌ Meal plan analysis failed: {response.content.decode()}")
        return False


def test_authentication_required():
    """Test that endpoints require authentication."""
    print("\nTesting authentication requirements...")
    
    client = Client()
    
    # Test without authentication
    data = {'plan_description': 'Test plan'}
    
    response = client.post(
        '/api/ai/generate-meal-plan/',
        data=json.dumps(data),
        content_type='application/json'
    )
    
    if response.status_code == 401:
        print("   ✅ Authentication required - endpoint properly protected")
        return True
    else:
        print(f"   ❌ Authentication not required - security issue! Status: {response.status_code}")
        return False


def test_validation_errors():
    """Test validation error handling."""
    print("\nTesting validation error handling...")
    
    client = Client()
    user, token = create_test_user()
    
    # Test with missing required field
    data = {}  # Missing plan_description
    
    response = client.post(
        '/api/ai/generate-meal-plan/',
        data=json.dumps(data),
        content_type='application/json',
        HTTP_AUTHORIZATION=f'Bearer {token}'
    )
    
    if response.status_code == 400:
        response_data = response.json()
        print("   ✅ Validation errors handled properly")
        print(f"   Error details: {response_data.get('details', {})}")
        return True
    else:
        print(f"   ❌ Validation not working properly. Status: {response.status_code}")
        return False


def main():
    """Run all endpoint tests."""
    print("🧪 AI Integration API Endpoint Testing")
    print("=" * 50)
    
    results = []
    
    results.append(test_generate_meal_plan_endpoint())
    results.append(test_generate_recipe_details_endpoint())
    results.append(test_analyze_meal_plan_endpoint())
    results.append(test_authentication_required())
    results.append(test_validation_errors())
    
    print("\n" + "=" * 50)
    print(f"Test Results: {sum(results)}/{len(results)} passed")
    
    if all(results):
        print("✅ All AI integration API endpoint tests passed!")
    else:
        print("❌ Some tests failed. Check the output above for details.")
    
    return all(results)


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)