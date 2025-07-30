#!/usr/bin/env python3
"""
Test fixtures and mock data management for comprehensive testing.
Provides reusable test data and mocking utilities.
"""

import os
import sys
import json
import uuid
from datetime import date, datetime, timedelta
from typing import Dict, List, Any, Optional, Union
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from dataclasses import dataclass

import django
from django.conf import settings
from django.contrib.auth import get_user_model

# Setup Django if not already done
if not settings.configured:
    sys.path.insert(0, '/Users/puyihao/workspace/MealPrep/MealPrepAppBackend/src')
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    django.setup()

User = get_user_model()


@dataclass
class TestDataSet:
    """Container for organized test data."""
    users: List[Dict[str, Any]]
    recipes: List[Dict[str, Any]]
    meal_plans: List[Dict[str, Any]]
    ai_responses: List[Dict[str, Any]]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'users': self.users,
            'recipes': self.recipes,
            'meal_plans': self.meal_plans,
            'ai_responses': self.ai_responses
        }


class TestDataFactory:
    """Factory for creating comprehensive test data."""
    
    @staticmethod
    def create_user_data(count: int = 5) -> List[Dict[str, Any]]:
        """Create multiple test users."""
        users = []
        for i in range(count):
            users.append({
                'id': i + 1,
                'username': f'testuser{i}',
                'email': f'testuser{i}@example.com',
                'first_name': f'Test{i}',
                'last_name': 'User',
                'is_active': True,
                'date_joined': datetime.now() - timedelta(days=i),
                'profile': {
                    'dietary_preferences': {
                        'dietType': ['balanced', 'vegetarian', 'vegan', 'keto', 'paleo'][i % 5],
                        'cuisinePreferences': ['italian', 'asian', 'mexican', 'american', 'mediterranean'][i % 5]
                    },
                    'allergies': [
                        [],
                        ['nuts'],
                        ['dairy'],
                        ['gluten'],
                        ['shellfish']
                    ][i % 5],
                    'calorie_target': 1800 + (i * 200),
                    'cooking_experience': ['beginner', 'intermediate', 'advanced'][i % 3]
                }
            })
        return users
    
    @staticmethod
    def create_recipe_data(count: int = 20) -> List[Dict[str, Any]]:
        """Create multiple test recipes with consistent UUIDs."""
        recipes = []
        cuisines = ['Italian', 'Asian', 'Mexican', 'American', 'Mediterranean', 'Indian', 'French']
        difficulties = ['easy', 'medium', 'hard']
        
        for i in range(count):
            recipe_id = f'recipe-{str(uuid.uuid4())[:8]}'
            recipes.append({
                'id': recipe_id,
                'name': f'Test Recipe {i}',
                'description': f'A delicious test recipe number {i}',
                'cuisine': cuisines[i % len(cuisines)],
                'prep_time': 10 + (i % 3) * 5,
                'cook_time': 20 + (i % 4) * 10,
                'total_time': 30 + (i % 5) * 10,
                'difficulty': difficulties[i % len(difficulties)],
                'servings': 2 + (i % 4),
                'ingredients': TestDataFactory._create_ingredients(5 + (i % 5)),
                'instructions': TestDataFactory._create_instructions(4 + (i % 6)),
                'nutrition': {
                    'calories': 200 + (i * 50),
                    'protein': 15 + (i % 10),
                    'carbs': 25 + (i % 15),
                    'fat': 8 + (i % 6),
                    'fiber': 3 + (i % 5),
                    'sugar': 5 + (i % 8)
                },
                'tags': TestDataFactory._create_tags(i),
                'image_url': f'https://example.com/recipe-images/{recipe_id}.jpg',
                'created_at': datetime.now() - timedelta(days=i),
                'updated_at': datetime.now() - timedelta(hours=i)
            })
        return recipes
    
    @staticmethod
    def _create_ingredients(count: int) -> List[Dict[str, Any]]:
        """Create ingredient list for recipes."""
        base_ingredients = [
            {'name': 'Olive oil', 'amount': '2 tbsp', 'unit': 'tbsp'},
            {'name': 'Onion', 'amount': '1 medium', 'unit': 'piece'},
            {'name': 'Garlic', 'amount': '3 cloves', 'unit': 'cloves'},
            {'name': 'Tomatoes', 'amount': '2 cups', 'unit': 'cups'},
            {'name': 'Salt', 'amount': '1 tsp', 'unit': 'tsp'},
            {'name': 'Black pepper', 'amount': '1/2 tsp', 'unit': 'tsp'},
            {'name': 'Fresh herbs', 'amount': '1/4 cup', 'unit': 'cup'},
            {'name': 'Cheese', 'amount': '1/2 cup', 'unit': 'cup'},
            {'name': 'Flour', 'amount': '1 cup', 'unit': 'cup'},
            {'name': 'Butter', 'amount': '2 tbsp', 'unit': 'tbsp'}
        ]
        return base_ingredients[:count]
    
    @staticmethod
    def _create_instructions(count: int) -> List[str]:
        """Create instruction list for recipes."""
        base_instructions = [
            'Preheat oven to 375°F (190°C).',
            'Heat olive oil in a large skillet over medium heat.',
            'Add onions and cook until translucent, about 5 minutes.',
            'Add garlic and cook for another minute.',
            'Add tomatoes and season with salt and pepper.',
            'Simmer for 10-15 minutes until sauce thickens.',
            'Stir in fresh herbs and cheese.',
            'Transfer to prepared baking dish.',
            'Bake for 25-30 minutes until golden brown.',
            'Let cool for 5 minutes before serving.'
        ]
        return base_instructions[:count]
    
    @staticmethod
    def _create_tags(index: int) -> List[str]:
        """Create tags for recipes."""
        all_tags = [
            ['quick', 'easy', 'weeknight'],
            ['healthy', 'low-fat', 'high-protein'],
            ['comfort-food', 'family-friendly'],
            ['gourmet', 'special-occasion'],
            ['vegetarian', 'gluten-free'],
            ['one-pot', 'meal-prep'],
            ['spicy', 'bold-flavors'],
            ['light', 'summer', 'fresh']
        ]
        return all_tags[index % len(all_tags)]
    
    @staticmethod
    def create_meal_plan_data(count: int = 5) -> List[Dict[str, Any]]:
        """Create multiple test meal plans."""
        meal_plans = []
        for i in range(count):
            start_date = date.today() + timedelta(weeks=i)
            meal_plans.append({
                'id': f'meal-plan-{i}',
                'user_id': (i % 3) + 1,  # Cycle through first 3 users
                'week_start_date': start_date.isoformat(),
                'description': f'Test meal plan {i} - week of {start_date}',
                'daily_meals': TestDataFactory._create_daily_meals(start_date),
                'status': ['draft', 'active', 'completed'][i % 3],
                'created_at': datetime.now() - timedelta(days=i),
                'preferences': {
                    'calorie_target': 2000 + (i * 200),
                    'dietary_restrictions': [
                        [],
                        ['vegetarian'],
                        ['gluten-free'],
                        ['dairy-free'],
                        ['low-carb']
                    ][i % 5]
                }
            })
        return meal_plans
    
    @staticmethod
    def _create_daily_meals(start_date: date) -> List[Dict[str, Any]]:
        """Create daily meals for a week."""
        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        daily_meals = []
        
        for i, day in enumerate(days):
            current_date = start_date + timedelta(days=i)
            daily_meals.append({
                'day': day,
                'date': current_date.isoformat(),
                'breakfast': [
                    {
                        'id': f'recipe-breakfast-{i}',
                        'name': f'Breakfast Recipe {i}',
                        'servings': 1
                    }
                ],
                'lunch': [
                    {
                        'id': f'recipe-lunch-{i}',
                        'name': f'Lunch Recipe {i}',
                        'servings': 1
                    }
                ],
                'dinner': [
                    {
                        'id': f'recipe-dinner-{i}',
                        'name': f'Dinner Recipe {i}',
                        'servings': 2
                    }
                ],
                'snacks': []
            })
        return daily_meals
    
    @staticmethod
    def create_ai_response_data(count: int = 10) -> List[Dict[str, Any]]:
        """Create AI service response test data."""
        responses = []
        for i in range(count):
            responses.append({
                'request_id': f'ai-request-{i}',
                'success': i % 4 != 0,  # 75% success rate
                'response_time': 2.5 + (i % 5) * 0.5,
                'meal_plan' if i % 4 != 0 else 'error': {
                    'week_start_date': (date.today() + timedelta(weeks=i)).isoformat(),
                    'daily_meals': TestDataFactory._create_daily_meals(date.today() + timedelta(weeks=i))
                } if i % 4 != 0 else f'AI service error {i}',
                'metadata': {
                    'model_version': f'v1.{i % 3}',
                    'processing_time': 1.5 + (i % 3) * 0.5,
                    'tokens_used': 1000 + (i * 200)
                }
            })
        return responses


class MockAIServiceFactory:
    """Factory for creating AI service mocks."""
    
    @staticmethod
    def create_successful_ai_service(response_time: float = 2.0) -> Mock:
        """Create a mock AI service that returns successful responses."""
        mock_service = Mock()
        
        async def mock_generate_meal_plan(request, user):
            # Simulate processing time
            import asyncio
            await asyncio.sleep(response_time / 10)  # Reduced for testing
            
            return {
                'success': True,
                'meal_plan': {
                    'week_start_date': str(request.week_start_date),
                    'daily_meals': TestDataFactory._create_daily_meals(request.week_start_date),
                    'metadata': {
                        'generation_time': response_time,
                        'recipes_generated': 21  # 3 meals * 7 days
                    }
                }
            }
        
        mock_service.generate_meal_plan = AsyncMock(side_effect=mock_generate_meal_plan)
        return mock_service
    
    @staticmethod
    def create_failing_ai_service(error_message: str = "AI service unavailable") -> Mock:
        """Create a mock AI service that returns error responses."""
        mock_service = Mock()
        
        async def mock_failing_generate_meal_plan(request, user):
            return {
                'success': False,
                'error': error_message
            }
        
        mock_service.generate_meal_plan = AsyncMock(side_effect=mock_failing_generate_meal_plan)
        return mock_service
    
    @staticmethod
    def create_slow_ai_service(delay_seconds: float = 10.0) -> Mock:
        """Create a mock AI service with simulated slow responses."""
        mock_service = Mock()
        
        async def mock_slow_generate_meal_plan(request, user):
            import asyncio
            await asyncio.sleep(delay_seconds / 100)  # Reduced for testing
            
            return {
                'success': True,
                'meal_plan': {
                    'week_start_date': str(request.week_start_date),
                    'daily_meals': TestDataFactory._create_daily_meals(request.week_start_date),
                    'metadata': {
                        'generation_time': delay_seconds,
                        'performance_warning': 'Slow response detected'
                    }
                }
            }
        
        mock_service.generate_meal_plan = AsyncMock(side_effect=mock_slow_generate_meal_plan)
        return mock_service


class DatabaseFixtures:
    """Fixtures for database operations."""
    
    @staticmethod
    def create_test_users_in_db(count: int = 3) -> List[User]:
        """Create test users in the database."""
        users = []
        for i in range(count):
            user, created = User.objects.get_or_create(
                username=f'fixture_user_{i}',
                defaults={
                    'email': f'fixture_user_{i}@example.com',
                    'first_name': f'Test{i}',
                    'last_name': 'User'
                }
            )
            users.append(user)
        return users
    
    @staticmethod
    def create_test_recipes_in_db(count: int = 10) -> List[Any]:
        """Create test recipes in the database."""
        try:
            from apps.recipes.models import Recipe
            
            recipes = []
            test_recipes = TestDataFactory.create_recipe_data(count)
            
            for recipe_data in test_recipes:
                recipe, created = Recipe.objects.get_or_create(
                    name=recipe_data['name'],
                    defaults={
                        'description': recipe_data['description'],
                        'cuisine': recipe_data['cuisine'],
                        'prep_time': recipe_data['prep_time'],
                        'cook_time': recipe_data['cook_time'],
                        'difficulty': recipe_data['difficulty'],
                        'servings': recipe_data['servings'],
                        'ingredients': recipe_data['ingredients'],
                        'instructions': recipe_data['instructions'],
                        'nutrition': recipe_data['nutrition']
                    }
                )
                recipes.append(recipe)
            
            return recipes
        except ImportError:
            # Recipe model not available
            return []
    
    @staticmethod
    def cleanup_test_data():
        """Clean up test data from database."""
        # Clean up test users
        User.objects.filter(username__startswith='fixture_user_').delete()
        User.objects.filter(username__startswith='test_user_').delete()
        
        # Clean up test recipes
        try:
            from apps.recipes.models import Recipe
            Recipe.objects.filter(name__startswith='Test Recipe').delete()
        except ImportError:
            pass


class ContextManagers:
    """Context managers for testing scenarios."""
    
    @staticmethod
    @patch('apps.ai_integration.services.AIService')
    def mock_ai_service(mock_ai_class, mock_instance=None):
        """Context manager for mocking AI service."""
        if mock_instance is None:
            mock_instance = MockAIServiceFactory.create_successful_ai_service()
        
        mock_ai_class.return_value = mock_instance
        return mock_instance
    
    @staticmethod
    def temporary_test_data():
        """Context manager for temporary test data creation and cleanup."""
        class TempDataContext:
            def __enter__(self):
                self.users = DatabaseFixtures.create_test_users_in_db()
                self.recipes = DatabaseFixtures.create_test_recipes_in_db()
                return self
            
            def __exit__(self, exc_type, exc_val, exc_tb):
                DatabaseFixtures.cleanup_test_data()
        
        return TempDataContext()


# Pre-built test data sets
SMALL_TEST_DATA = TestDataSet(
    users=TestDataFactory.create_user_data(3),
    recipes=TestDataFactory.create_recipe_data(10),
    meal_plans=TestDataFactory.create_meal_plan_data(2),
    ai_responses=TestDataFactory.create_ai_response_data(5)
)

MEDIUM_TEST_DATA = TestDataSet(
    users=TestDataFactory.create_user_data(10),
    recipes=TestDataFactory.create_recipe_data(50),
    meal_plans=TestDataFactory.create_meal_plan_data(10),
    ai_responses=TestDataFactory.create_ai_response_data(20)
)

LARGE_TEST_DATA = TestDataSet(
    users=TestDataFactory.create_user_data(100),
    recipes=TestDataFactory.create_recipe_data(500),
    meal_plans=TestDataFactory.create_meal_plan_data(100),
    ai_responses=TestDataFactory.create_ai_response_data(200)
)


# Utility functions for test data management
def save_test_data_to_file(test_data: TestDataSet, filepath: str):
    """Save test data to JSON file."""
    with open(filepath, 'w') as f:
        json.dump(test_data.to_dict(), f, indent=2, default=str)


def load_test_data_from_file(filepath: str) -> TestDataSet:
    """Load test data from JSON file."""
    with open(filepath, 'r') as f:
        data = json.load(f)
    
    return TestDataSet(
        users=data.get('users', []),
        recipes=data.get('recipes', []),
        meal_plans=data.get('meal_plans', []),
        ai_responses=data.get('ai_responses', [])
    )


def create_deterministic_uuid(seed: str) -> str:
    """Create deterministic UUID for testing."""
    import hashlib
    hash_obj = hashlib.md5(seed.encode())
    hex_dig = hash_obj.hexdigest()
    return f"{hex_dig[:8]}-{hex_dig[8:12]}-{hex_dig[12:16]}-{hex_dig[16:20]}-{hex_dig[20:32]}"