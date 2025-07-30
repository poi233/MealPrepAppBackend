#!/usr/bin/env python
"""
Test script for AI integration error handling and response formatting.
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
        user = User.objects.get(username='testuser_ai_error')
    except User.DoesNotExist:
        user = User.objects.create_user(
            username='testuser_ai_error',
            email='testuser_ai_error@example.com',
            password='testpass123'
        )
    
    refresh = RefreshToken.for_user(user)
    return user, str(refresh.access_token)


def test_meal_plan_validation_errors():
    """Test meal plan generation validation errors."""
    print("Testing meal plan generation validation errors...")
    
    client = Client()
    user, token = create_test_user()
    
    test_cases = [
        {
            'name': 'Empty plan description',
            'data': {'plan_description': ''},
            'expected_field': 'plan_description'
        },
        {
            'name': 'Invalid calorie target (too low)',
            'data': {
                'plan_description': 'Test plan',
                'calorie_target': 500
            },
            'expected_field': 'calorie_target'
        },
        {
            'name': 'Invalid calorie target (too high)',
            'data': {
                'plan_description': 'Test plan',
                'calorie_target': 10000
            },
            'expected_field': 'calorie_target'
        },
        {
            'name': 'Past week start date',
            'data': {
                'plan_description': 'Test plan',
                'week_start_date': '2020-01-01'
            },
            'expected_field': 'week_start_date'
        },
        {
            'name': 'Too many allergies',
            'data': {
                'plan_description': 'Test plan',
                'allergies': [f'allergy_{i}' for i in range(25)]
            },
            'expected_field': 'allergies'
        }
    ]
    
    for test_case in test_cases:
        response = client.post(
            '/api/ai/generate-meal-plan/',
            data=json.dumps(test_case['data']),
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {token}'
        )
        
        if response.status_code == 400:
            response_data = response.json()
            if test_case['expected_field'] in response_data.get('details', {}):
                print(f"   ✅ {test_case['name']}: Validation error handled correctly")
            else:
                print(f"   ❌ {test_case['name']}: Expected field '{test_case['expected_field']}' not in validation errors")
        else:
            print(f"   ❌ {test_case['name']}: Expected 400 status, got {response.status_code}")


def test_recipe_validation_errors():
    """Test recipe generation validation errors."""
    print("\nTesting recipe generation validation errors...")
    
    client = Client()
    user, token = create_test_user()
    
    test_cases = [
        {
            'name': 'Empty recipe name',
            'data': {'name': ''},
            'expected_field': 'name'
        },
        {
            'name': 'Invalid prep time (too low)',
            'data': {
                'name': 'Test Recipe',
                'prep_time': 0
            },
            'expected_field': 'prep_time'
        },
        {
            'name': 'Invalid cook time (too high)',
            'data': {
                'name': 'Test Recipe',
                'cook_time': 500
            },
            'expected_field': 'cook_time'
        },
        {
            'name': 'Too many ingredients',
            'data': {
                'name': 'Test Recipe',
                'ingredients': [f'ingredient_{i}' for i in range(60)]
            },
            'expected_field': 'ingredients'
        },
        {
            'name': 'Too many dietary restrictions',
            'data': {
                'name': 'Test Recipe',
                'dietary_restrictions': [f'restriction_{i}' for i in range(15)]
            },
            'expected_field': 'dietary_restrictions'
        }
    ]
    
    for test_case in test_cases:
        response = client.post(
            '/api/ai/generate-recipe-details/',
            data=json.dumps(test_case['data']),
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {token}'
        )
        
        if response.status_code == 400:
            response_data = response.json()
            if test_case['expected_field'] in response_data.get('details', {}):
                print(f"   ✅ {test_case['name']}: Validation error handled correctly")
            else:
                print(f"   ❌ {test_case['name']}: Expected field '{test_case['expected_field']}' not in validation errors")
        else:
            print(f"   ❌ {test_case['name']}: Expected 400 status, got {response.status_code}")


def test_meal_plan_analysis_errors():
    """Test meal plan analysis validation errors."""
    print("\nTesting meal plan analysis validation errors...")
    
    client = Client()
    user, token = create_test_user()
    
    test_cases = [
        {
            'name': 'Invalid meal plan ID',
            'data': {'meal_plan_id': 'invalid-uuid'},
            'expected_status': 400
        },
        {
            'name': 'Non-existent meal plan ID',
            'data': {'meal_plan_id': '12345678-1234-1234-1234-123456789012'},
            'expected_status': 400
        }
    ]
    
    for test_case in test_cases:
        response = client.post(
            '/api/ai/analyze-meal-plan/',
            data=json.dumps(test_case['data']),
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {token}'
        )
        
        if response.status_code == test_case['expected_status']:
            print(f"   ✅ {test_case['name']}: Error handled correctly")
        else:
            print(f"   ❌ {test_case['name']}: Expected {test_case['expected_status']} status, got {response.status_code}")


def test_response_format_consistency():
    """Test that all endpoints return consistent response formats."""
    print("\nTesting response format consistency...")
    
    client = Client()
    user, token = create_test_user()
    
    # Test successful meal plan generation response format
    data = {
        'plan_description': '简单的测试膳食计划',
        'week_start_date': date.today().isoformat()
    }
    
    response = client.post(
        '/api/ai/generate-meal-plan/',
        data=json.dumps(data),
        content_type='application/json',
        HTTP_AUTHORIZATION=f'Bearer {token}'
    )
    
    if response.status_code == 201:
        response_data = response.json()
        required_fields = ['name', 'description', 'week_start_date', 'daily_meals']
        
        if all(field in response_data for field in required_fields):
            print("   ✅ Meal plan response format is consistent")
        else:
            missing_fields = [field for field in required_fields if field not in response_data]
            print(f"   ❌ Meal plan response missing fields: {missing_fields}")
    else:
        print(f"   ❌ Meal plan generation failed with status {response.status_code}")
    
    # Test successful recipe generation response format
    data = {
        'name': '测试食谱',
        'cuisine': 'Chinese'
    }
    
    response = client.post(
        '/api/ai/generate-recipe-details/',
        data=json.dumps(data),
        content_type='application/json',
        HTTP_AUTHORIZATION=f'Bearer {token}'
    )
    
    if response.status_code == 201:
        response_data = response.json()
        required_fields = ['name', 'ingredients', 'instructions', 'nutrition_info']
        
        if all(field in response_data for field in required_fields):
            print("   ✅ Recipe response format is consistent")
        else:
            missing_fields = [field for field in required_fields if field not in response_data]
            print(f"   ❌ Recipe response missing fields: {missing_fields}")
    else:
        print(f"   ❌ Recipe generation failed with status {response.status_code}")


def test_error_response_format():
    """Test that error responses have consistent format."""
    print("\nTesting error response format...")
    
    client = Client()
    user, token = create_test_user()
    
    # Test validation error format
    response = client.post(
        '/api/ai/generate-meal-plan/',
        data=json.dumps({}),  # Missing required field
        content_type='application/json',
        HTTP_AUTHORIZATION=f'Bearer {token}'
    )
    
    if response.status_code == 400:
        response_data = response.json()
        if 'error' in response_data and 'details' in response_data:
            print("   ✅ Validation error response format is consistent")
        else:
            print(f"   ❌ Validation error response format is inconsistent: {response_data}")
    else:
        print(f"   ❌ Expected 400 status for validation error, got {response.status_code}")
    
    # Test authentication error format
    response = client.post(
        '/api/ai/generate-meal-plan/',
        data=json.dumps({'plan_description': 'Test'}),
        content_type='application/json'
        # No authorization header
    )
    
    if response.status_code == 401:
        print("   ✅ Authentication error response format is consistent")
    else:
        print(f"   ❌ Expected 401 status for auth error, got {response.status_code}")


def main():
    """Run all error handling tests."""
    print("🧪 AI Integration Error Handling Testing")
    print("=" * 50)
    
    test_meal_plan_validation_errors()
    test_recipe_validation_errors()
    test_meal_plan_analysis_errors()
    test_response_format_consistency()
    test_error_response_format()
    
    print("\n" + "=" * 50)
    print("✅ All AI integration error handling tests completed!")


if __name__ == "__main__":
    main()