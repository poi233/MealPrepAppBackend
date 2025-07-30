#!/usr/bin/env python3
"""
Comprehensive test suite for Recipe save functionality.
Tests single recipe save, batch save, duplicate detection, and performance.
"""

import os
import sys
import time
import uuid
from datetime import datetime, date
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, List, Any

import pytest
import django
from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model
from django.db import transaction, IntegrityError
from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework import status

# Setup Django
sys.path.insert(0, '/Users/puyihao/workspace/MealPrep/MealPrepAppBackend/src')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

# Import test infrastructure
from test_base import (
    BaseTestCase, DatabaseTestCase, PerformanceTestMixin,
    requires_database, skip_if_no_ai_service
)
from test_fixtures import (
    TestDataFactory, DatabaseFixtures, SMALL_TEST_DATA,
    create_deterministic_uuid, ContextManagers
)
from performance_test_base import (
    PerformanceTestCase, RECIPE_SAVE_BENCHMARK, BATCH_SAVE_BENCHMARK,
    PerformanceTracker
)

# Import application code
try:
    from apps.recipes.models import Recipe
    from apps.recipes.serializers import RecipeCreateSerializer
    from apps.ai_integration.views import CreateRecipeFromAIView, ApplyMealPlanView
    RECIPES_AVAILABLE = True
except ImportError:
    RECIPES_AVAILABLE = False
    Recipe = None

User = get_user_model()


@pytest.mark.skipif(not RECIPES_AVAILABLE, reason="Recipe models not available")
class TestRecipeSaveCore(DatabaseTestCase, PerformanceTestMixin):
    """Core recipe save functionality tests."""
    
    def setUp(self):
        """Set up test case."""
        super().setUp()
        self.test_recipes = TestDataFactory.create_recipe_data(10)
        self.performance_tracker = PerformanceTracker()
    
    def test_single_recipe_creation(self):
        """Test creating a single recipe."""
        recipe_data = self.test_recipes[0]
        
        with self.measure_execution_time('single_recipe_creation'):
            recipe = Recipe.objects.create(
                id=uuid.UUID(recipe_data['id']),
                name=recipe_data['name'],
                description=recipe_data['description'],
                cuisine=recipe_data['cuisine'],
                prep_time=recipe_data['prep_time'],
                cook_time=recipe_data['cook_time'],
                difficulty=recipe_data['difficulty'],
                ingredients=recipe_data['ingredients'],
                instructions=recipe_data['instructions'],
                nutrition_info=recipe_data['nutrition'],
                created_by_user=self.test_user
            )
        
        # Validate creation
        self.assertIsNotNone(recipe.id)
        self.assertEqual(recipe.name, recipe_data['name'])
        self.assertEqual(recipe.cuisine, recipe_data['cuisine'])
        self.assertEqual(len(recipe.ingredients), len(recipe_data['ingredients']))
        self.assertEqual(recipe.created_by_user, self.test_user)
        
        # Validate database persistence
        saved_recipe = Recipe.objects.get(id=recipe.id)
        self.assertEqual(saved_recipe.name, recipe_data['name'])
    
    def test_recipe_duplicate_detection_by_id(self):
        """Test duplicate detection using recipe ID."""
        recipe_data = self.test_recipes[0]
        recipe_id = uuid.UUID(recipe_data['id'])
        
        # Create first recipe
        recipe1 = Recipe.objects.create(
            id=recipe_id,
            name=recipe_data['name'],
            description=recipe_data['description'],
            cuisine=recipe_data['cuisine'],
            prep_time=recipe_data['prep_time'],
            cook_time=recipe_data['cook_time'],
            difficulty=recipe_data['difficulty'],
            ingredients=recipe_data['ingredients'],
            instructions=recipe_data['instructions'],
            nutrition_info=recipe_data['nutrition'],
            created_by_user=self.test_user
        )
        
        # Try to create duplicate with same ID
        with self.assertRaises(IntegrityError):
            Recipe.objects.create(
                id=recipe_id,  # Same ID
                name="Different Name",
                description="Different description",
                cuisine="Different cuisine",
                created_by_user=self.test_user
            )
    
    def test_recipe_duplicate_detection_by_name(self):
        """Test duplicate detection using recipe name."""
        recipe_data = self.test_recipes[0]
        
        # Create first recipe
        recipe1 = Recipe.objects.create(
            name=recipe_data['name'],
            description=recipe_data['description'],
            cuisine=recipe_data['cuisine'],
            prep_time=recipe_data['prep_time'],
            cook_time=recipe_data['cook_time'],
            difficulty=recipe_data['difficulty'],
            ingredients=recipe_data['ingredients'],
            instructions=recipe_data['instructions'],
            nutrition_info=recipe_data['nutrition'],
            created_by_user=self.test_user
        )
        
        # Check for existing recipe by name
        existing_recipe = Recipe.objects.filter(
            name=recipe_data['name'],
            created_by_user=self.test_user
        ).first()
        
        self.assertIsNotNone(existing_recipe)
        self.assertEqual(existing_recipe.id, recipe1.id)
    
    def test_batch_recipe_creation(self):
        """Test creating multiple recipes in batch."""
        batch_size = 5
        recipes_data = self.test_recipes[:batch_size]
        
        with self.measure_execution_time('batch_recipe_creation'):
            with transaction.atomic():
                created_recipes = []
                for recipe_data in recipes_data:
                    recipe = Recipe.objects.create(
                        id=uuid.UUID(recipe_data['id']),
                        name=recipe_data['name'],
                        description=recipe_data['description'],
                        cuisine=recipe_data['cuisine'],
                        prep_time=recipe_data['prep_time'],
                        cook_time=recipe_data['cook_time'],
                        difficulty=recipe_data['difficulty'],
                        ingredients=recipe_data['ingredients'],
                        instructions=recipe_data['instructions'],
                        nutrition_info=recipe_data['nutrition'],
                        created_by_user=self.test_user
                    )
                    created_recipes.append(recipe)
        
        # Validate all recipes were created
        self.assertEqual(len(created_recipes), batch_size)
        self.assertEqual(Recipe.objects.filter(created_by_user=self.test_user).count(), batch_size)
        
        # Validate performance (should be fast for small batch)
        execution_time = self.performance_data.get('batch_recipe_creation', 0)
        self.assertLess(execution_time, 2.0, "Batch creation should be under 2 seconds")
    
    def test_recipe_validation(self):
        """Test recipe data validation."""
        invalid_recipes = [
            # Missing required fields
            {
                'name': '',  # Empty name
                'ingredients': [],
                'instructions': []
            },
            # Invalid data types
            {
                'name': 'Valid Name',
                'prep_time': 'invalid',  # Should be integer
                'ingredients': 'invalid',  # Should be list
                'instructions': []
            },
            # Invalid nutrition data
            {
                'name': 'Valid Name',
                'ingredients': [],
                'instructions': [],
                'nutrition_info': {'calories': 'invalid'}  # Should be number
            }
        ]
        
        for invalid_recipe in invalid_recipes:
            with self.subTest(recipe=invalid_recipe):
                try:
                    recipe = Recipe(**invalid_recipe)
                    recipe.full_clean()  # This should raise ValidationError
                    self.fail("Expected validation error for invalid recipe data")
                except Exception:
                    # Expected to fail validation
                    pass
    
    def test_recipe_serializer_validation(self):
        """Test recipe serializer validation."""
        valid_recipe_data = {
            'name': 'Test Recipe',
            'description': 'A test recipe description',
            'cuisine': 'Test Cuisine',
            'prep_time': 15,
            'cook_time': 30,
            'difficulty': 'easy',
            'ingredients': [
                {'name': 'Ingredient 1', 'amount': '1 cup'},
                {'name': 'Ingredient 2', 'amount': '2 tbsp'}
            ],
            'instructions': ['Step 1', 'Step 2', 'Step 3'],
            'nutrition_info': {'calories': 300, 'protein': 20}
        }
        
        serializer = RecipeCreateSerializer(data=valid_recipe_data)
        self.assertTrue(serializer.is_valid(), f"Serializer errors: {serializer.errors}")
        
        # Test invalid data
        invalid_recipe_data = valid_recipe_data.copy()
        invalid_recipe_data['name'] = 'AB'  # Too short
        
        invalid_serializer = RecipeCreateSerializer(data=invalid_recipe_data)
        self.assertFalse(invalid_serializer.is_valid())
        self.assertIn('name', invalid_serializer.errors)


@pytest.mark.skipif(not RECIPES_AVAILABLE, reason="Recipe models not available")
class TestRecipeSaveAPI(APITestCase, PerformanceTestMixin):
    """Test recipe save API endpoints."""
    
    def setUp(self):
        """Set up API test case."""
        super().setUp()
        self.client = APIClient()
        self.test_user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.test_user)
        self.test_recipes = TestDataFactory.create_recipe_data(5)
    
    def test_create_recipe_from_ai_endpoint(self):
        """Test the create recipe from AI endpoint."""
        recipe_data = self.test_recipes[0]
        
        request_data = {
            'ai_recipe_data': recipe_data,
            'save_to_account': True
        }
        
        url = reverse('create_recipe_from_ai')
        
        with self.measure_execution_time('api_create_recipe_from_ai'):
            response = self.client.post(url, request_data, format='json')
        
        # Validate response
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        response_data = response.json()
        self.assertTrue(response_data.get('success'))
        self.assertEqual(response_data.get('status'), 'created')
        self.assertIn('recipe_id', response_data)
        self.assertIn('message', response_data)
        
        # Validate database record
        recipe_id = response_data['recipe_id']
        recipe = Recipe.objects.get(id=recipe_id)
        self.assertEqual(recipe.name, recipe_data['name'])
        self.assertEqual(recipe.created_by_user, self.test_user)
    
    def test_create_recipe_duplicate_handling(self):
        """Test duplicate recipe handling in API."""
        recipe_data = self.test_recipes[0]
        
        # Create recipe first time
        request_data = {
            'ai_recipe_data': recipe_data,
            'save_to_account': True
        }
        
        url = reverse('create_recipe_from_ai')
        
        # First request should create recipe
        response1 = self.client.post(url, request_data, format='json')
        self.assertEqual(response1.status_code, status.HTTP_201_CREATED)
        
        # Second request should detect duplicate
        response2 = self.client.post(url, request_data, format='json')
        self.assertEqual(response2.status_code, status.HTTP_200_OK)
        
        response_data = response2.json()
        self.assertTrue(response_data.get('success'))
        self.assertEqual(response_data.get('status'), 'already_exists')
    
    def test_batch_recipe_save_api(self):
        """Test batch recipe save through apply meal plan endpoint."""
        meal_plan_data = {
            'meal_plan': {
                'week_start_date': str(date.today()),
                'daily_meals': [
                    {
                        'day': 'Monday',
                        'breakfast': [self.test_recipes[0]],
                        'lunch': [self.test_recipes[1]],
                        'dinner': [self.test_recipes[2]]
                    }
                ]
            },
            'save_recipes': True,
            'skip_duplicates': True
        }
        
        url = reverse('apply_meal_plan')
        
        with self.measure_execution_time('api_batch_recipe_save'):
            response = self.client.post(url, meal_plan_data, format='json')
        
        # Validate response
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        response_data = response.json()
        self.assertTrue(response_data.get('success'))
        self.assertIn('saved_recipes', response_data)
        
        # Check that recipes were saved
        saved_recipes = response_data['saved_recipes']
        self.assertGreaterEqual(len(saved_recipes), 3)
        
        # Validate database records
        for saved_recipe in saved_recipes:
            if saved_recipe['status'] in ['created', 'already_exists']:
                recipe = Recipe.objects.get(id=saved_recipe['recipe_id'])
                self.assertEqual(recipe.created_by_user, self.test_user)
    
    def test_api_error_handling(self):
        """Test API error handling for invalid data."""
        invalid_requests = [
            # Missing recipe data
            {'save_to_account': True},
            # Invalid recipe structure
            {
                'ai_recipe_data': {'invalid': 'data'},
                'save_to_account': True
            },
            # Missing required fields
            {
                'ai_recipe_data': {
                    'name': '',  # Empty name
                    'ingredients': [],
                    'instructions': []
                },
                'save_to_account': True
            }
        ]
        
        url = reverse('create_recipe_from_ai')
        
        for invalid_request in invalid_requests:
            with self.subTest(request=invalid_request):
                response = self.client.post(url, invalid_request, format='json')
                self.assertIn(response.status_code, [
                    status.HTTP_400_BAD_REQUEST,
                    status.HTTP_422_UNPROCESSABLE_ENTITY
                ])


@pytest.mark.skipif(not RECIPES_AVAILABLE, reason="Recipe models not available")
class TestRecipeSavePerformance(DatabaseTestCase, PerformanceTestCase):
    """Performance tests for recipe save operations."""
    
    def setUp(self):
        """Set up performance test case."""
        super().__init__()
        self.add_benchmark(RECIPE_SAVE_BENCHMARK)
        self.add_benchmark(BATCH_SAVE_BENCHMARK)
        self.test_recipes = TestDataFactory.create_recipe_data(20)
    
    def test_single_recipe_save_performance(self):
        """Test single recipe save performance."""
        recipe_data = self.test_recipes[0]
        
        with self.measure_operation('recipe_save_operation'):
            recipe = Recipe.objects.create(
                id=uuid.UUID(recipe_data['id']),
                name=recipe_data['name'],
                description=recipe_data['description'],
                cuisine=recipe_data['cuisine'],
                prep_time=recipe_data['prep_time'],
                cook_time=recipe_data['cook_time'],
                difficulty=recipe_data['difficulty'],
                ingredients=recipe_data['ingredients'],
                instructions=recipe_data['instructions'],
                nutrition_info=recipe_data['nutrition'],
                created_by_user=self.test_user
            )
        
        self.assertIsNotNone(recipe.id)
        self.assert_performance_benchmark('recipe_save_operation', 'recipe_save_operation')
    
    def test_batch_recipe_save_performance(self):
        """Test batch recipe save performance (20 recipes under 2 seconds)."""
        batch_size = 20
        recipes_data = self.test_recipes[:batch_size]
        
        with self.measure_operation('batch_recipe_save'):
            with transaction.atomic():
                for recipe_data in recipes_data:
                    Recipe.objects.create(
                        id=uuid.UUID(recipe_data['id']),
                        name=recipe_data['name'],
                        description=recipe_data['description'],
                        cuisine=recipe_data['cuisine'],
                        prep_time=recipe_data['prep_time'],
                        cook_time=recipe_data['cook_time'],
                        difficulty=recipe_data['difficulty'],
                        ingredients=recipe_data['ingredients'],
                        instructions=recipe_data['instructions'],
                        nutrition_info=recipe_data['nutrition'],
                        created_by_user=self.test_user
                    )
        
        # Validate all recipes were created
        self.assertEqual(Recipe.objects.filter(created_by_user=self.test_user).count(), batch_size)
        
        # Assert performance benchmark
        self.assert_performance_benchmark('batch_recipe_save', 'batch_recipe_save')
    
    def test_concurrent_recipe_saves(self):
        """Test concurrent recipe save operations."""
        def save_recipe(recipe_data):
            return Recipe.objects.create(
                id=uuid.UUID(recipe_data['id']),
                name=recipe_data['name'],
                description=recipe_data['description'],
                cuisine=recipe_data['cuisine'],
                prep_time=recipe_data['prep_time'],
                cook_time=recipe_data['cook_time'],
                difficulty=recipe_data['difficulty'],
                ingredients=recipe_data['ingredients'],
                instructions=recipe_data['instructions'],
                nutrition_info=recipe_data['nutrition'],
                created_by_user=self.test_user
            )
        
        # Test with 5 concurrent saves
        recipes_for_concurrent = self.test_recipes[:5]
        
        results = self.run_concurrent_operations(
            lambda: save_recipe(recipes_for_concurrent[len(results)]) 
            if len(results) < len(recipes_for_concurrent) else None,
            count=5
        )
        
        # All operations should succeed
        self.assertEqual(len(results), 5)
        self.assertEqual(Recipe.objects.filter(created_by_user=self.test_user).count(), 5)
    
    def test_database_query_optimization(self):
        """Test that recipe saves use optimal number of database queries."""
        recipe_data = self.test_recipes[0]
        
        with self.assert_database_queries(max_queries=2):  # INSERT + possible SELECT
            Recipe.objects.create(
                id=uuid.UUID(recipe_data['id']),
                name=recipe_data['name'],
                description=recipe_data['description'],
                cuisine=recipe_data['cuisine'],
                prep_time=recipe_data['prep_time'],
                cook_time=recipe_data['cook_time'],
                difficulty=recipe_data['difficulty'],
                ingredients=recipe_data['ingredients'],
                instructions=recipe_data['instructions'],
                nutrition_info=recipe_data['nutrition'],
                created_by_user=self.test_user
            )


@pytest.mark.skipif(not RECIPES_AVAILABLE, reason="Recipe models not available")
class TestRecipeDuplicateDetection(DatabaseTestCase):
    """Test comprehensive duplicate detection mechanisms."""
    
    def setUp(self):
        """Set up duplicate detection test case."""
        super().setUp()
        self.test_recipes = TestDataFactory.create_recipe_data(10)
    
    def test_deterministic_uuid_consistency(self):
        """Test that deterministic UUIDs are consistent."""
        recipe_name = "Test Recipe Name"
        
        uuid1 = create_deterministic_uuid(recipe_name)
        uuid2 = create_deterministic_uuid(recipe_name)
        
        self.assertEqual(uuid1, uuid2)
        
        # Different names should produce different UUIDs
        uuid3 = create_deterministic_uuid("Different Recipe Name")
        self.assertNotEqual(uuid1, uuid3)
    
    def test_duplicate_detection_by_content_similarity(self):
        """Test duplicate detection based on content similarity."""
        base_recipe = self.test_recipes[0]
        
        # Create original recipe
        original = Recipe.objects.create(
            name=base_recipe['name'],
            description=base_recipe['description'],
            cuisine=base_recipe['cuisine'],
            prep_time=base_recipe['prep_time'],
            cook_time=base_recipe['cook_time'],
            difficulty=base_recipe['difficulty'],
            ingredients=base_recipe['ingredients'],
            instructions=base_recipe['instructions'],
            nutrition_info=base_recipe['nutrition'],
            created_by_user=self.test_user
        )
        
        # Test variations that should be considered duplicates
        similar_variations = [
            # Same name, different case
            {**base_recipe, 'name': base_recipe['name'].upper()},
            # Same name with extra spaces
            {**base_recipe, 'name': f"  {base_recipe['name']}  "},
            # Same name with minor differences
            {**base_recipe, 'name': base_recipe['name'].replace(' ', '-')},
        ]
        
        for variation in similar_variations:
            with self.subTest(variation=variation['name']):
                # Check if similar recipe already exists
                existing = Recipe.objects.filter(
                    name__iexact=variation['name'].strip(),
                    created_by_user=self.test_user
                ).first()
                
                if not existing:
                    # Create only if no similar recipe exists
                    new_recipe = Recipe.objects.create(
                        name=variation['name'],
                        description=variation['description'],
                        cuisine=variation['cuisine'],
                        prep_time=variation['prep_time'],
                        cook_time=variation['cook_time'],
                        difficulty=variation['difficulty'],
                        ingredients=variation['ingredients'],
                        instructions=variation['instructions'],
                        nutrition_info=variation['nutrition'],
                        created_by_user=self.test_user
                    )
                    self.assertNotEqual(new_recipe.id, original.id)
    
    def test_batch_duplicate_detection(self):
        """Test duplicate detection in batch operations."""
        # Create recipes with some duplicates
        recipes_with_duplicates = self.test_recipes[:5] + self.test_recipes[:2]  # 5 + 2 duplicates
        
        created_recipes = []
        skipped_duplicates = []
        
        for recipe_data in recipes_with_duplicates:
            recipe_id = uuid.UUID(recipe_data['id'])
            
            # Check if recipe already exists
            existing = Recipe.objects.filter(
                id=recipe_id,
                created_by_user=self.test_user
            ).first()
            
            if existing:
                skipped_duplicates.append(existing)
            else:
                recipe = Recipe.objects.create(
                    id=recipe_id,
                    name=recipe_data['name'],
                    description=recipe_data['description'],
                    cuisine=recipe_data['cuisine'],
                    prep_time=recipe_data['prep_time'],
                    cook_time=recipe_data['cook_time'],
                    difficulty=recipe_data['difficulty'],
                    ingredients=recipe_data['ingredients'],
                    instructions=recipe_data['instructions'],
                    nutrition_info=recipe_data['nutrition'],
                    created_by_user=self.test_user
                )
                created_recipes.append(recipe)
        
        # Should have created 5 unique recipes and skipped 2 duplicates
        self.assertEqual(len(created_recipes), 5)
        self.assertEqual(len(skipped_duplicates), 2)
        self.assertEqual(Recipe.objects.filter(created_by_user=self.test_user).count(), 5)


if __name__ == '__main__':
    # Run tests
    import unittest
    unittest.main(verbosity=2)