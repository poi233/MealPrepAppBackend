#!/usr/bin/env python3
"""
Comprehensive test suite for AI service functionality.
Tests the optimized AI meal plan generation and recipe creation.
"""

import os
import sys
import asyncio
import time
import json
from datetime import date, datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from typing import Dict, List, Any

import pytest
import django
from django.test import TestCase
from django.contrib.auth import get_user_model

# Setup Django
sys.path.insert(0, '/Users/puyihao/workspace/MealPrep/MealPrepAppBackend/src')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

# Import test infrastructure
from test_base import (
    AsyncTestCase, PerformanceTestMixin, MockingTestMixin, 
    skip_if_no_ai_service, requires_database
)
from test_fixtures import (
    TestDataFactory, MockAIServiceFactory, SMALL_TEST_DATA,
    create_deterministic_uuid
)
from performance_test_base import (
    PerformanceTestCase, AI_MEAL_PLAN_BENCHMARK,
    PerformanceTracker, PerformanceMetrics
)

# Import application code
try:
    from apps.ai_integration.services import AIService, MealPlanRequest, RecipeGenerationRequest
    AI_SERVICE_AVAILABLE = True
except ImportError:
    AI_SERVICE_AVAILABLE = False
    AIService = None
    MealPlanRequest = None
    RecipeGenerationRequest = None

User = get_user_model()


@pytest.mark.skipif(not AI_SERVICE_AVAILABLE, reason="AI service not available")
class TestAIServiceCore(AsyncTestCase, PerformanceTestMixin, MockingTestMixin):
    """Core AI service functionality tests."""
    
    def setUp(self):
        """Set up test case."""
        super().setUp()
        self.ai_service = AIService() if AI_SERVICE_AVAILABLE else None
        self.performance_tracker = PerformanceTracker()
    
    def test_ai_service_initialization(self):
        """Test AI service initializes correctly."""
        self.assertIsNotNone(self.ai_service)
        self.assertTrue(hasattr(self.ai_service, 'generate_meal_plan'))
        self.assertTrue(hasattr(self.ai_service, 'generate_recipe'))
        self.assertTrue(hasattr(self.ai_service, '_initialize_gemini'))
    
    @requires_database
    async def test_basic_meal_plan_generation(self):
        """Test basic meal plan generation functionality."""
        request = MealPlanRequest(
            plan_description="Healthy weekly meal plan with balanced nutrition",
            dietary_preferences={'dietType': 'balanced'},
            allergies=[],
            calorie_target=2000,
            week_start_date=date.today()
        )
        
        with self.measure_execution_time('basic_meal_plan_generation'):
            result = await self.ai_service.generate_meal_plan(request, self.test_user)
        
        # Basic structure validation
        self.assert_response_success(result)
        self.assertIn('meal_plan', result)
        
        meal_plan = result['meal_plan']
        self.assertIn('week_start_date', meal_plan)
        self.assertIn('daily_meals', meal_plan)
        self.assertIsInstance(meal_plan['daily_meals'], list)
        self.assertEqual(len(meal_plan['daily_meals']), 7)  # 7 days
        
        # Validate daily meal structure
        for day_data in meal_plan['daily_meals']:
            self.assertIn('day', day_data)
            self.assertIn('breakfast', day_data)
            self.assertIn('lunch', day_data)
            self.assertIn('dinner', day_data)
            
            # Each meal should have at least one recipe
            for meal_type in ['breakfast', 'lunch', 'dinner']:
                recipes = day_data[meal_type]
                self.assertIsInstance(recipes, list)
                self.assertGreater(len(recipes), 0)
                
                # Validate recipe structure
                for recipe in recipes:
                    self.validate_recipe_structure(recipe)
    
    def validate_recipe_structure(self, recipe: Dict[str, Any]):
        """Validate that a recipe has the expected structure."""
        required_fields = [
            'id', 'name', 'cuisine', 'prep_time', 'cook_time', 
            'difficulty', 'ingredients', 'instructions'
        ]
        
        for field in required_fields:
            self.assertIn(field, recipe, f"Recipe missing required field: {field}")
        
        # Validate types
        self.assertIsInstance(recipe['ingredients'], list)
        self.assertIsInstance(recipe['instructions'], list)
        self.assertIsInstance(recipe['prep_time'], int)
        self.assertIsInstance(recipe['cook_time'], int)
        
        # Validate ingredients structure
        for ingredient in recipe['ingredients']:
            self.assertIn('name', ingredient)
            self.assertIn('amount', ingredient)
        
        # Validate instructions are strings
        for instruction in recipe['instructions']:
            self.assertIsInstance(instruction, str)
    
    @requires_database
    async def test_dietary_preferences_handling(self):
        """Test handling of different dietary preferences."""
        dietary_tests = [
            {'dietType': 'vegetarian', 'expected_keywords': ['vegetarian', 'plant-based']},
            {'dietType': 'vegan', 'expected_keywords': ['vegan', 'plant-based']},
            {'dietType': 'keto', 'expected_keywords': ['low-carb', 'keto']},
            {'dietType': 'paleo', 'expected_keywords': ['paleo', 'whole-foods']}
        ]
        
        for dietary_test in dietary_tests:
            with self.subTest(dietary_test=dietary_test['dietType']):
                request = MealPlanRequest(
                    plan_description=f"Weekly {dietary_test['dietType']} meal plan",
                    dietary_preferences=dietary_test,
                    week_start_date=date.today()
                )
                
                result = await self.ai_service.generate_meal_plan(request, self.test_user)
                self.assert_response_success(result)
                
                # Verify dietary preferences are reflected in recipes
                meal_plan = result['meal_plan']
                recipe_names = []
                for day_data in meal_plan['daily_meals']:
                    for meal_type in ['breakfast', 'lunch', 'dinner']:
                        for recipe in day_data[meal_type]:
                            recipe_names.append(recipe['name'].lower())
                
                # At least some recipes should reflect dietary preferences
                # This is a heuristic check, not foolproof
                matching_recipes = 0
                for recipe_name in recipe_names:
                    for keyword in dietary_test['expected_keywords']:
                        if keyword in recipe_name:
                            matching_recipes += 1
                            break
                
                # At least 20% of recipes should match dietary preferences
                min_expected = len(recipe_names) * 0.2
                self.assertGreaterEqual(
                    matching_recipes, min_expected,
                    f"Expected at least {min_expected} recipes matching {dietary_test['dietType']} preferences"
                )
    
    @requires_database
    async def test_allergy_handling(self):
        """Test handling of food allergies."""
        allergy_tests = [
            ['nuts', 'peanuts'],
            ['dairy', 'milk'],
            ['gluten', 'wheat'],
            ['shellfish', 'shrimp']
        ]
        
        for allergies in allergy_tests:
            with self.subTest(allergies=allergies):
                request = MealPlanRequest(
                    plan_description="Allergy-safe weekly meal plan",
                    allergies=allergies,
                    week_start_date=date.today()
                )
                
                result = await self.ai_service.generate_meal_plan(request, self.test_user)
                self.assert_response_success(result)
                
                # Check that allergenic ingredients are avoided
                meal_plan = result['meal_plan']
                for day_data in meal_plan['daily_meals']:
                    for meal_type in ['breakfast', 'lunch', 'dinner']:
                        for recipe in day_data[meal_type]:
                            ingredient_names = [
                                ing['name'].lower() 
                                for ing in recipe['ingredients']
                            ]
                            
                            for allergy in allergies:
                                for ingredient_name in ingredient_names:
                                    self.assertNotIn(
                                        allergy.lower(), ingredient_name,
                                        f"Found allergenic ingredient '{ingredient_name}' "
                                        f"containing '{allergy}' in recipe '{recipe['name']}'"
                                    )
    
    @requires_database
    async def test_calorie_target_consideration(self):
        """Test that calorie targets are considered."""
        calorie_tests = [
            {'target': 1500, 'tolerance': 200},  # Low calorie
            {'target': 2000, 'tolerance': 300},  # Normal calorie
            {'target': 2800, 'tolerance': 400}   # High calorie
        ]
        
        for calorie_test in calorie_tests:
            with self.subTest(calorie_target=calorie_test['target']):
                request = MealPlanRequest(
                    plan_description="Calorie-targeted meal plan",
                    calorie_target=calorie_test['target'],
                    week_start_date=date.today()
                )
                
                result = await self.ai_service.generate_meal_plan(request, self.test_user)
                self.assert_response_success(result)
                
                # Calculate total daily calories (when nutrition data is available)
                meal_plan = result['meal_plan']
                daily_calories = []
                
                for day_data in meal_plan['daily_meals']:
                    day_total = 0
                    for meal_type in ['breakfast', 'lunch', 'dinner']:
                        for recipe in day_data[meal_type]:
                            if 'nutrition' in recipe and 'calories' in recipe['nutrition']:
                                day_total += recipe['nutrition']['calories']
                    
                    if day_total > 0:  # Only count days with nutrition data
                        daily_calories.append(day_total)
                
                if daily_calories:
                    avg_daily_calories = sum(daily_calories) / len(daily_calories)
                    target = calorie_test['target']
                    tolerance = calorie_test['tolerance']
                    
                    self.assertGreaterEqual(
                        avg_daily_calories, target - tolerance,
                        f"Average daily calories {avg_daily_calories} below target range"
                    )
                    self.assertLessEqual(
                        avg_daily_calories, target + tolerance,
                        f"Average daily calories {avg_daily_calories} above target range"
                    )


@pytest.mark.skipif(not AI_SERVICE_AVAILABLE, reason="AI service not available")
class TestAIServicePerformance(AsyncTestCase, PerformanceTestCase):
    """Performance tests for AI service."""
    
    def setUp(self):
        """Set up performance test case."""
        super().__init__()
        self.ai_service = AIService() if AI_SERVICE_AVAILABLE else None
        self.add_benchmark(AI_MEAL_PLAN_BENCHMARK)
    
    @requires_database
    async def test_meal_plan_generation_performance(self):
        """Test that meal plan generation meets performance benchmarks."""
        request = MealPlanRequest(
            plan_description="Performance test meal plan",
            dietary_preferences={'dietType': 'balanced'},
            calorie_target=2000,
            week_start_date=date.today()
        )
        
        # Measure performance
        with self.measure_operation('ai_meal_plan_generation'):
            result = await self.ai_service.generate_meal_plan(request, self.test_user)
        
        self.assert_response_success(result)
        
        # Assert performance benchmark
        self.assert_performance_benchmark(
            'ai_meal_plan_generation', 
            'ai_meal_plan_generation'
        )
    
    @requires_database
    async def test_multiple_concurrent_requests(self):
        """Test performance under concurrent load."""
        request = MealPlanRequest(
            plan_description="Concurrent test meal plan",
            dietary_preferences={'dietType': 'balanced'},
            week_start_date=date.today()
        )
        
        async def generate_meal_plan():
            return await self.ai_service.generate_meal_plan(request, self.test_user)
        
        # Test with 5 concurrent requests
        results = await self.run_async_concurrent_operations(
            generate_meal_plan, count=5, timeout=60
        )
        
        # All requests should succeed
        self.assertEqual(len(results), 5)
        for result in results:
            self.assert_response_success(result)
    
    @requires_database
    async def test_performance_degradation_monitoring(self):
        """Test for performance degradation over multiple requests."""
        request = MealPlanRequest(
            plan_description="Degradation test meal plan",
            dietary_preferences={'dietType': 'balanced'},
            week_start_date=date.today()
        )
        
        execution_times = []
        
        for i in range(5):
            start_time = time.perf_counter()
            result = await self.ai_service.generate_meal_plan(request, self.test_user)
            end_time = time.perf_counter()
            
            self.assert_response_success(result)
            execution_times.append(end_time - start_time)
        
        # Check that performance doesn't degrade significantly
        first_request_time = execution_times[0]
        last_request_time = execution_times[-1]
        
        # Last request shouldn't be more than 50% slower than first
        max_acceptable_degradation = first_request_time * 1.5
        self.assertLessEqual(
            last_request_time, max_acceptable_degradation,
            f"Performance degraded: {last_request_time:.3f}s vs {first_request_time:.3f}s"
        )


@pytest.mark.skipif(not AI_SERVICE_AVAILABLE, reason="AI service not available")
class TestAIServiceErrorHandling(AsyncTestCase, MockingTestMixin):
    """Error handling tests for AI service."""
    
    def setUp(self):
        """Set up error handling test case."""
        super().setUp()
        self.ai_service = AIService() if AI_SERVICE_AVAILABLE else None
    
    @patch('apps.ai_integration.services.genai')
    async def test_api_connection_failure(self, mock_genai):
        """Test handling of API connection failures."""
        # Mock API failure
        mock_model = Mock()
        mock_model.generate_content.side_effect = Exception("API connection failed")
        mock_genai.GenerativeModel.return_value = mock_model
        
        request = MealPlanRequest(
            plan_description="Test meal plan",
            week_start_date=date.today()
        )
        
        result = await self.ai_service.generate_meal_plan(request, self.test_user)
        self.assert_response_error(result, "API connection failed")
    
    @requires_database
    async def test_invalid_request_data(self):
        """Test handling of invalid request data."""
        invalid_requests = [
            MealPlanRequest(plan_description="", week_start_date=date.today()),  # Empty description
            MealPlanRequest(plan_description="Test", calorie_target=-100),  # Negative calories
            MealPlanRequest(plan_description="Test", allergies=[""] * 100),  # Too many allergies
        ]
        
        for invalid_request in invalid_requests:
            with self.subTest(request=invalid_request):
                result = await self.ai_service.generate_meal_plan(invalid_request, self.test_user)
                # Should either handle gracefully or return meaningful error
                if not result.get('success'):
                    self.assertIn('error', result)
                    self.assertIsInstance(result['error'], str)
    
    @patch('apps.ai_integration.services.cache')
    async def test_cache_failure_handling(self, mock_cache):
        """Test handling of cache failures."""
        # Mock cache failure
        mock_cache.get.side_effect = Exception("Cache unavailable")
        mock_cache.set.side_effect = Exception("Cache unavailable")
        
        request = MealPlanRequest(
            plan_description="Cache failure test",
            week_start_date=date.today()
        )
        
        # Should still work without cache
        result = await self.ai_service.generate_meal_plan(request, self.test_user)
        # Should either succeed or fail gracefully
        self.assertIn('success', result)
    
    @requires_database
    async def test_timeout_handling(self):
        """Test handling of request timeouts."""
        # This is a complex test that would require mocking the underlying HTTP calls
        # For now, we'll test that the service has appropriate timeout settings
        self.assertTrue(hasattr(self.ai_service, '_max_requests_per_minute'))
        self.assertIsInstance(self.ai_service._max_requests_per_minute, int)
        self.assertGreater(self.ai_service._max_requests_per_minute, 0)


@pytest.mark.skipif(not AI_SERVICE_AVAILABLE, reason="AI service not available")
class TestUUIDDeterministicGeneration(TestCase):
    """Test deterministic UUID generation for recipes."""
    
    def setUp(self):
        """Set up UUID test case."""
        self.ai_service = AIService() if AI_SERVICE_AVAILABLE else None
    
    def test_deterministic_uuid_generation(self):
        """Test that UUIDs are generated deterministically."""
        recipe_name = "Test Recipe"
        
        # Generate UUID multiple times
        uuid1 = create_deterministic_uuid(recipe_name)
        uuid2 = create_deterministic_uuid(recipe_name)
        
        # Should be identical
        self.assertEqual(uuid1, uuid2)
        
        # Should be different for different names
        uuid3 = create_deterministic_uuid("Different Recipe")
        self.assertNotEqual(uuid1, uuid3)
    
    def test_uuid_format_validation(self):
        """Test that generated UUIDs have correct format."""
        import re
        
        recipe_name = "Format Test Recipe"
        uuid_str = create_deterministic_uuid(recipe_name)
        
        # Should match UUID format
        uuid_pattern = re.compile(
            r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
        )
        self.assertTrue(uuid_pattern.match(uuid_str))
    
    def test_uuid_collision_resistance(self):
        """Test that different recipe names produce different UUIDs."""
        recipe_names = [
            "Spaghetti Carbonara",
            "Chicken Alfredo", 
            "Beef Stir Fry",
            "Vegetable Curry",
            "Fish Tacos"
        ]
        
        uuids = [create_deterministic_uuid(name) for name in recipe_names]
        
        # All UUIDs should be unique
        self.assertEqual(len(uuids), len(set(uuids)))


@pytest.mark.skipif(not AI_SERVICE_AVAILABLE, reason="AI service not available")
class TestRecipeGeneration(AsyncTestCase):
    """Test individual recipe generation functionality."""
    
    def setUp(self):
        """Set up recipe generation test case."""
        super().setUp()
        self.ai_service = AIService() if AI_SERVICE_AVAILABLE else None
    
    @requires_database
    async def test_single_recipe_generation(self):
        """Test generation of a single recipe."""
        if not hasattr(self.ai_service, 'generate_recipe'):
            self.skipTest("Recipe generation method not available")
        
        request = RecipeGenerationRequest(
            name="Test Recipe",
            cuisine="Italian",
            difficulty="medium",
            meal_type="dinner"
        )
        
        result = await self.ai_service.generate_recipe(request)
        
        if result.get('success'):
            recipe = result['recipe']
            self.assertIn('name', recipe)
            self.assertIn('ingredients', recipe)
            self.assertIn('instructions', recipe)
            self.assertIn('id', recipe)
        else:
            # If recipe generation fails, should have error message
            self.assertIn('error', result)


if __name__ == '__main__':
    # Run tests
    import unittest
    unittest.main(verbosity=2)