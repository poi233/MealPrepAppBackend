#!/usr/bin/env python3
"""
End-to-end integration test suite for the complete meal planning workflow.
Tests the full flow from AI generation to recipe saving with all components working together.
"""

import os
import sys
import asyncio
import time
import uuid
from datetime import date, datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, List, Any

import pytest
import django
from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework import status

# Setup Django
sys.path.insert(0, '/Users/puyihao/workspace/MealPrep/MealPrepAppBackend/src')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

# Import test infrastructure
from test_base import (
    AsyncTestCase, DatabaseTestCase, PerformanceTestMixin,
    requires_database, skip_if_no_ai_service
)
from test_fixtures import (
    TestDataFactory, MockAIServiceFactory, SMALL_TEST_DATA,
    create_deterministic_uuid, ContextManagers
)
from performance_test_base import (
    PerformanceTestCase, AI_MEAL_PLAN_BENCHMARK, BATCH_SAVE_BENCHMARK,
    PerformanceTracker
)

# Import application code
try:
    from apps.recipes.models import Recipe
    from apps.ai_integration.services import AIService, MealPlanRequest
    from apps.ai_integration.views import GenerateMealPlanView, CreateRecipeFromAIView, ApplyMealPlanView
    INTEGRATION_AVAILABLE = True
except ImportError:
    INTEGRATION_AVAILABLE = False
    Recipe = None
    AIService = None

User = get_user_model()


@pytest.mark.skipif(not INTEGRATION_AVAILABLE, reason="Integration components not available")
class TestEndToEndMealPlanningWorkflow(AsyncTestCase, DatabaseTestCase, PerformanceTestMixin):
    """Test complete meal planning workflow end-to-end."""
    
    def setUp(self):
        """Set up end-to-end test case."""
        super().setUp()
        self.performance_tracker = PerformanceTracker()
        self.ai_service = AIService() if INTEGRATION_AVAILABLE else None
    
    @requires_database
    async def test_complete_meal_plan_generation_and_save_workflow(self):
        """Test the complete workflow: Generate AI meal plan -> Save recipes -> Verify data integrity."""
        
        # Step 1: Generate AI meal plan
        request = MealPlanRequest(
            plan_description="Complete workflow test: healthy weekly meal plan",
            dietary_preferences={'dietType': 'balanced'},
            allergies=['nuts'],
            calorie_target=2000,
            week_start_date=date.today()
        )
        
        with self.measure_execution_time('complete_workflow_ai_generation'):
            ai_result = await self.ai_service.generate_meal_plan(request, self.test_user)
        
        self.assert_response_success(ai_result)
        self.assertIn('meal_plan', ai_result)
        
        meal_plan = ai_result['meal_plan']
        daily_meals = meal_plan['daily_meals']
        
        # Step 2: Extract all recipes from meal plan
        all_recipes = []
        recipe_ids = []
        
        for day_data in daily_meals:
            for meal_type in ['breakfast', 'lunch', 'dinner']:
                recipes = day_data.get(meal_type, [])
                for recipe in recipes:
                    all_recipes.append(recipe)
                    recipe_ids.append(recipe['id'])
        
        self.assertGreater(len(all_recipes), 0, "Meal plan should contain recipes")
        
        # Step 3: Save recipes individually (Scenario A: Save to Template)
        saved_individual_count = 0
        
        with self.measure_execution_time('complete_workflow_individual_saves'):
            for recipe in all_recipes[:3]:  # Test first 3 recipes
                # Check if recipe already exists
                existing_recipe = Recipe.objects.filter(
                    id=uuid.UUID(recipe['id']),
                    created_by_user=self.test_user
                ).first()
                
                if not existing_recipe:
                    saved_recipe = Recipe.objects.create(
                        id=uuid.UUID(recipe['id']),
                        name=recipe['name'],
                        description=recipe.get('description', ''),
                        cuisine=recipe['cuisine'],
                        prep_time=recipe['prep_time'],
                        cook_time=recipe['cook_time'],
                        difficulty=recipe['difficulty'],
                        ingredients=recipe['ingredients'],
                        instructions=recipe['instructions'],
                        nutrition_info=recipe.get('nutrition', {}),
                        created_by_user=self.test_user
                    )
                    saved_individual_count += 1
        
        # Step 4: Save remaining recipes in batch (Scenario B: Apply Meal Plan)
        remaining_recipes = all_recipes[3:]  # Skip already saved recipes
        saved_batch_count = 0
        
        if remaining_recipes:
            with self.measure_execution_time('complete_workflow_batch_save'):
                with django.db.transaction.atomic():
                    for recipe in remaining_recipes:
                        existing_recipe = Recipe.objects.filter(
                            id=uuid.UUID(recipe['id']),
                            created_by_user=self.test_user
                        ).first()
                        
                        if not existing_recipe:
                            Recipe.objects.create(
                                id=uuid.UUID(recipe['id']),
                                name=recipe['name'],
                                description=recipe.get('description', ''),
                                cuisine=recipe['cuisine'],
                                prep_time=recipe['prep_time'],
                                cook_time=recipe['cook_time'],
                                difficulty=recipe['difficulty'],
                                ingredients=recipe['ingredients'],
                                instructions=recipe['instructions'],
                                nutrition_info=recipe.get('nutrition', {}),
                                created_by_user=self.test_user
                            )
                            saved_batch_count += 1
        
        # Step 5: Verify data integrity and consistency
        total_saved = saved_individual_count + saved_batch_count
        self.assertGreaterEqual(total_saved, 1, "At least one recipe should be saved")
        
        # Verify all saved recipes in database
        saved_recipe_ids = list(Recipe.objects.filter(
            created_by_user=self.test_user
        ).values_list('id', flat=True))
        
        self.assertEqual(len(saved_recipe_ids), total_saved)
        
        # Step 6: Verify UUID determinism
        for recipe in all_recipes[:5]:  # Test first 5 recipes
            expected_uuid = create_deterministic_uuid(recipe['name'])
            self.assertEqual(recipe['id'], expected_uuid, 
                f"Recipe '{recipe['name']}' should have deterministic UUID")
        
        # Step 7: Verify data completeness
        for recipe_id in saved_recipe_ids:
            saved_recipe = Recipe.objects.get(id=recipe_id)
            
            # Basic validation
            self.assertIsNotNone(saved_recipe.name)
            self.assertIsNotNone(saved_recipe.cuisine)
            self.assertIsInstance(saved_recipe.ingredients, list)
            self.assertGreater(len(saved_recipe.ingredients), 0)
            self.assertIsInstance(saved_recipe.instructions, list)
            self.assertGreater(len(saved_recipe.instructions), 0)
            self.assertEqual(saved_recipe.created_by_user, self.test_user)
        
        # Performance validation
        ai_generation_time = self.performance_data.get('complete_workflow_ai_generation', 0)
        individual_save_time = self.performance_data.get('complete_workflow_individual_saves', 0)
        batch_save_time = self.performance_data.get('complete_workflow_batch_save', 0)
        
        self.assertLess(ai_generation_time, 5.0, "AI generation should complete within 5 seconds")
        self.assertLess(individual_save_time, 2.0, "Individual saves should complete within 2 seconds")
        self.assertLess(batch_save_time, 2.0, "Batch save should complete within 2 seconds")
    
    @requires_database
    async def test_duplicate_handling_across_scenarios(self):
        """Test duplicate handling when recipes are saved through both scenarios."""
        
        # Generate a meal plan
        request = MealPlanRequest(
            plan_description="Duplicate handling test meal plan",
            dietary_preferences={'dietType': 'balanced'},
            week_start_date=date.today()
        )
        
        ai_result = await self.ai_service.generate_meal_plan(request, self.test_user)
        self.assert_response_success(ai_result)
        
        meal_plan = ai_result['meal_plan']
        all_recipes = []
        
        for day_data in meal_plan['daily_meals']:
            for meal_type in ['breakfast', 'lunch', 'dinner']:
                all_recipes.extend(day_data.get(meal_type, []))
        
        self.assertGreater(len(all_recipes), 3, "Need at least 4 recipes for duplicate test")
        
        # Scenario A: Save first recipe individually
        first_recipe = all_recipes[0]
        saved_recipe = Recipe.objects.create(
            id=uuid.UUID(first_recipe['id']),
            name=first_recipe['name'],
            description=first_recipe.get('description', ''),
            cuisine=first_recipe['cuisine'],
            prep_time=first_recipe['prep_time'],
            cook_time=first_recipe['cook_time'],
            difficulty=first_recipe['difficulty'],
            ingredients=first_recipe['ingredients'],
            instructions=first_recipe['instructions'],
            nutrition_info=first_recipe.get('nutrition', {}),
            created_by_user=self.test_user
        )
        
        # Scenario B: Try to save same recipe in batch (should detect duplicate)
        duplicate_recipes = [first_recipe] + all_recipes[1:3]  # Include the already saved recipe
        
        created_count = 0
        skipped_count = 0
        
        for recipe in duplicate_recipes:
            existing_recipe = Recipe.objects.filter(
                id=uuid.UUID(recipe['id']),
                created_by_user=self.test_user
            ).first()
            
            if existing_recipe:
                skipped_count += 1
            else:
                Recipe.objects.create(
                    id=uuid.UUID(recipe['id']),
                    name=recipe['name'],
                    description=recipe.get('description', ''),
                    cuisine=recipe['cuisine'],
                    prep_time=recipe['prep_time'],
                    cook_time=recipe['cook_time'],
                    difficulty=recipe['difficulty'],
                    ingredients=recipe['ingredients'],
                    instructions=recipe['instructions'],
                    nutrition_info=recipe.get('nutrition', {}),
                    created_by_user=self.test_user
                )
                created_count += 1
        
        # Verify duplicate was properly detected and skipped
        self.assertEqual(skipped_count, 1, "One duplicate should be detected")
        self.assertEqual(created_count, 2, "Two new recipes should be created")
        self.assertEqual(Recipe.objects.filter(created_by_user=self.test_user).count(), 3, 
                        "Total should be 3 unique recipes")
    
    @requires_database
    async def test_error_recovery_and_consistency(self):
        """Test error recovery and data consistency in failure scenarios."""
        
        # Test scenario: AI generation succeeds, but some recipe saves fail
        request = MealPlanRequest(
            plan_description="Error recovery test meal plan",
            dietary_preferences={'dietType': 'balanced'},
            week_start_date=date.today()
        )
        
        ai_result = await self.ai_service.generate_meal_plan(request, self.test_user)
        self.assert_response_success(ai_result)
        
        all_recipes = []
        for day_data in ai_result['meal_plan']['daily_meals']:
            for meal_type in ['breakfast', 'lunch', 'dinner']:
                all_recipes.extend(day_data.get(meal_type, []))
        
        # Simulate partial failure: save some recipes successfully, then fail
        successful_saves = 0
        failed_saves = 0
        
        for i, recipe in enumerate(all_recipes[:5]):
            try:
                if i == 3:  # Simulate failure on 4th recipe
                    # Create recipe with invalid data to trigger failure
                    Recipe.objects.create(
                        id=uuid.UUID(recipe['id']),
                        name='',  # Invalid empty name
                        cuisine=recipe['cuisine'],
                        created_by_user=self.test_user
                    )
                else:
                    Recipe.objects.create(
                        id=uuid.UUID(recipe['id']),
                        name=recipe['name'],
                        description=recipe.get('description', ''),
                        cuisine=recipe['cuisine'],
                        prep_time=recipe['prep_time'],
                        cook_time=recipe['cook_time'],
                        difficulty=recipe['difficulty'],
                        ingredients=recipe['ingredients'],
                        instructions=recipe['instructions'],
                        nutrition_info=recipe.get('nutrition', {}),
                        created_by_user=self.test_user
                    )
                    successful_saves += 1
            except Exception:
                failed_saves += 1
        
        # Verify partial success and system consistency
        self.assertGreater(successful_saves, 0, "Some recipes should save successfully")
        self.assertGreater(failed_saves, 0, "Some saves should fail as expected")
        
        # Database should be in consistent state
        saved_count = Recipe.objects.filter(created_by_user=self.test_user).count()
        self.assertEqual(saved_count, successful_saves, 
                        "Database should only contain successfully saved recipes")
    
    @requires_database 
    async def test_concurrent_workflow_execution(self):
        """Test concurrent execution of meal planning workflows."""
        
        async def run_single_workflow(workflow_id: int):
            """Run a single meal planning workflow."""
            request = MealPlanRequest(
                plan_description=f"Concurrent workflow {workflow_id}",
                dietary_preferences={'dietType': 'balanced'},
                calorie_target=2000 + (workflow_id * 100),
                week_start_date=date.today() + timedelta(weeks=workflow_id)
            )
            
            # Generate meal plan
            ai_result = await self.ai_service.generate_meal_plan(request, self.test_user)
            if not ai_result.get('success'):
                return {'success': False, 'error': ai_result.get('error')}
            
            # Extract and save recipes
            all_recipes = []
            for day_data in ai_result['meal_plan']['daily_meals']:
                for meal_type in ['breakfast', 'lunch', 'dinner']:
                    all_recipes.extend(day_data.get(meal_type, []))
            
            saved_count = 0
            for recipe in all_recipes[:2]:  # Save first 2 recipes to avoid overwhelming
                try:
                    Recipe.objects.create(
                        id=uuid.UUID(recipe['id']),
                        name=f"{recipe['name']} - Workflow {workflow_id}",  # Make unique
                        description=recipe.get('description', ''),
                        cuisine=recipe['cuisine'],
                        prep_time=recipe['prep_time'],
                        cook_time=recipe['cook_time'],
                        difficulty=recipe['difficulty'],
                        ingredients=recipe['ingredients'],
                        instructions=recipe['instructions'],
                        nutrition_info=recipe.get('nutrition', {}),
                        created_by_user=self.test_user
                    )
                    saved_count += 1
                except Exception as e:
                    # Recipe might already exist, skip
                    pass
            
            return {
                'success': True,
                'workflow_id': workflow_id,
                'recipes_generated': len(all_recipes),
                'recipes_saved': saved_count
            }
        
        # Run 3 concurrent workflows
        workflow_count = 3
        results = await self.run_async_concurrent_operations(
            lambda: run_single_workflow(len(results) + 1) 
            if len(results) < workflow_count else None,
            count=workflow_count,
            timeout=60
        )
        
        # Verify all workflows completed successfully
        self.assertEqual(len(results), workflow_count)
        
        successful_workflows = 0
        total_recipes_saved = 0
        
        for result in results:
            if result.get('success'):
                successful_workflows += 1
                total_recipes_saved += result.get('recipes_saved', 0)
        
        self.assertGreaterEqual(successful_workflows, 2, 
                               "At least 2 out of 3 workflows should succeed")
        self.assertGreater(total_recipes_saved, 0, 
                          "At least some recipes should be saved across workflows")


@pytest.mark.skipif(not INTEGRATION_AVAILABLE, reason="Integration components not available")
class TestEndToEndAPIIntegration(APITestCase, PerformanceTestMixin):
    """Test end-to-end integration through API endpoints."""
    
    def setUp(self):
        """Set up API integration test case."""
        super().setUp()
        self.client = APIClient()
        self.test_user = User.objects.create_user(
            username='apitest',
            email='apitest@example.com',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.test_user)
    
    def test_full_api_workflow_generate_and_apply(self):
        """Test full API workflow: Generate meal plan -> Apply meal plan with saves."""
        
        # Step 1: Generate meal plan via API
        generate_url = reverse('generate_meal_plan')
        generate_data = {
            'plan_description': 'API integration test meal plan',
            'dietary_preferences': {'dietType': 'balanced'},
            'allergies': ['shellfish'],
            'calorie_target': 2000,
            'week_start_date': str(date.today())
        }
        
        with self.measure_execution_time('api_generate_meal_plan'):
            generate_response = self.client.post(generate_url, generate_data, format='json')
        
        self.assertEqual(generate_response.status_code, status.HTTP_200_OK)
        
        generate_result = generate_response.json()
        self.assertTrue(generate_result.get('success'))
        self.assertIn('meal_plan', generate_result)
        
        # Step 2: Apply meal plan with recipe saves
        apply_url = reverse('apply_meal_plan')
        apply_data = {
            'meal_plan': generate_result['meal_plan'],
            'save_recipes': True,
            'skip_duplicates': True
        }
        
        with self.measure_execution_time('api_apply_meal_plan'):
            apply_response = self.client.post(apply_url, apply_data, format='json')
        
        self.assertEqual(apply_response.status_code, status.HTTP_200_OK)
        
        apply_result = apply_response.json()
        self.assertTrue(apply_result.get('success'))
        self.assertIn('saved_recipes', apply_result)
        
        # Step 3: Verify recipes were saved
        saved_recipes = apply_result['saved_recipes']
        self.assertGreater(len(saved_recipes), 0, "Some recipes should be saved")
        
        # Verify in database
        for saved_recipe in saved_recipes:
            if saved_recipe['status'] in ['created', 'already_exists']:
                recipe = Recipe.objects.get(id=saved_recipe['recipe_id'])
                self.assertEqual(recipe.created_by_user, self.test_user)
        
        # Performance validation
        generate_time = self.performance_data.get('api_generate_meal_plan', 0)
        apply_time = self.performance_data.get('api_apply_meal_plan', 0)
        
        self.assertLess(generate_time, 10.0, "API generation should complete within 10 seconds")
        self.assertLess(apply_time, 5.0, "API apply should complete within 5 seconds")
    
    def test_individual_recipe_save_api_workflow(self):
        """Test individual recipe save workflow through API."""
        
        # First generate a meal plan to get recipe data
        generate_url = reverse('generate_meal_plan')
        generate_data = {
            'plan_description': 'Individual save test meal plan',
            'dietary_preferences': {'dietType': 'vegetarian'},
            'week_start_date': str(date.today())
        }
        
        generate_response = self.client.post(generate_url, generate_data, format='json')
        self.assertEqual(generate_response.status_code, status.HTTP_200_OK)
        
        generate_result = generate_response.json()
        meal_plan = generate_result['meal_plan']
        
        # Extract first recipe
        first_recipe = None
        for day_data in meal_plan['daily_meals']:
            for meal_type in ['breakfast', 'lunch', 'dinner']:
                recipes = day_data.get(meal_type, [])
                if recipes:
                    first_recipe = recipes[0]
                    break
            if first_recipe:
                break
        
        self.assertIsNotNone(first_recipe, "Should have at least one recipe")
        
        # Save individual recipe via API
        save_url = reverse('create_recipe_from_ai')
        save_data = {
            'ai_recipe_data': first_recipe,
            'save_to_account': True
        }
        
        with self.measure_execution_time('api_individual_recipe_save'):
            save_response = self.client.post(save_url, save_data, format='json')
        
        self.assertEqual(save_response.status_code, status.HTTP_201_CREATED)
        
        save_result = save_response.json()
        self.assertTrue(save_result.get('success'))
        self.assertEqual(save_result.get('status'), 'created')
        self.assertIn('recipe_id', save_result)
        
        # Verify recipe was saved
        recipe_id = save_result['recipe_id']
        recipe = Recipe.objects.get(id=recipe_id)
        self.assertEqual(recipe.name, first_recipe['name'])
        self.assertEqual(recipe.created_by_user, self.test_user)
        
        # Test duplicate detection - save same recipe again
        duplicate_response = self.client.post(save_url, save_data, format='json')
        self.assertEqual(duplicate_response.status_code, status.HTTP_200_OK)
        
        duplicate_result = duplicate_response.json()
        self.assertTrue(duplicate_result.get('success'))
        self.assertEqual(duplicate_result.get('status'), 'already_exists')
    
    def test_api_error_handling_and_recovery(self):
        """Test API error handling and recovery mechanisms."""
        
        # Test invalid meal plan generation request
        generate_url = reverse('generate_meal_plan')
        invalid_data = {
            'plan_description': '',  # Empty description
            'calorie_target': -100   # Invalid calorie target
        }
        
        response = self.client.post(generate_url, invalid_data, format='json')
        self.assertIn(response.status_code, [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_422_UNPROCESSABLE_ENTITY
        ])
        
        # Test invalid recipe save request
        save_url = reverse('create_recipe_from_ai')
        invalid_recipe_data = {
            'ai_recipe_data': {
                'name': '',  # Invalid empty name
                'ingredients': 'invalid'  # Invalid data type
            },
            'save_to_account': True
        }
        
        response = self.client.post(save_url, invalid_recipe_data, format='json')
        self.assertIn(response.status_code, [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_422_UNPROCESSABLE_ENTITY
        ])
        
        # Verify no invalid data was saved
        invalid_recipes = Recipe.objects.filter(
            name='',
            created_by_user=self.test_user
        )
        self.assertEqual(invalid_recipes.count(), 0, "No invalid recipes should be saved")


if __name__ == '__main__':
    # Run tests
    import unittest
    unittest.main(verbosity=2)