#!/usr/bin/env python3
"""
Performance benchmark test suite for validating performance improvements.
Specifically validates the 4.2x AI meal plan generation performance improvement.
"""

import os
import sys
import asyncio
import time
import statistics
from datetime import date, datetime
from unittest.mock import Mock, patch
from typing import Dict, List, Any, Tuple

import pytest
import django
from django.test import TestCase
from django.contrib.auth import get_user_model

# Setup Django
sys.path.insert(0, '/Users/puyihao/workspace/MealPrep/MealPrepAppBackend/src')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

# Import test infrastructure
from test_base import AsyncTestCase, requires_database, skip_if_no_ai_service
from test_fixtures import MockAIServiceFactory, TestDataFactory
from performance_test_base import (
    PerformanceTestCase, AI_MEAL_PLAN_BENCHMARK, BATCH_SAVE_BENCHMARK,
    PerformanceTracker, LoadTestRunner, PerformanceBenchmark
)

# Import application code
try:
    from apps.ai_integration.services import AIService, MealPlanRequest
    from apps.recipes.models import Recipe
    PERFORMANCE_TEST_AVAILABLE = True
except ImportError:
    PERFORMANCE_TEST_AVAILABLE = False
    AIService = None
    Recipe = None

User = get_user_model()


@pytest.mark.skipif(not PERFORMANCE_TEST_AVAILABLE, reason="Performance test components not available")
class TestAIPerformanceImprovement(AsyncTestCase, PerformanceTestCase):
    """Test AI meal plan generation performance improvements."""
    
    def setUp(self):
        """Set up performance benchmark test case."""
        super().__init__()
        self.add_benchmark(AI_MEAL_PLAN_BENCHMARK)
        self.ai_service = AIService() if PERFORMANCE_TEST_AVAILABLE else None
        
        # Performance baselines (from previous measurements)
        self.baseline_meal_plan_time = 12.0  # seconds (original performance)
        self.target_improvement_factor = 4.2  # Expected improvement
        self.target_meal_plan_time = self.baseline_meal_plan_time / self.target_improvement_factor  # ~2.86 seconds
    
    @requires_database
    async def test_ai_meal_plan_generation_performance_improvement(self):
        """Test that AI meal plan generation meets the 4.2x improvement target."""
        
        request = MealPlanRequest(
            plan_description="Performance benchmark test: balanced weekly meal plan",
            dietary_preferences={'dietType': 'balanced'},
            allergies=[],
            calorie_target=2000,
            week_start_date=date.today()
        )
        
        # Measure multiple runs for statistical accuracy
        execution_times = []
        
        for run in range(5):  # 5 test runs
            with self.measure_operation(f'ai_meal_plan_performance_run_{run}'):
                result = await self.ai_service.generate_meal_plan(request, self.test_user)
            
            # Verify successful generation
            self.assert_response_success(result)
            self.assertIn('meal_plan', result)
            
            # Record execution time
            run_time = self.tracker.get_metrics_for_operation(f'ai_meal_plan_performance_run_{run}')
            if run_time:
                execution_times.append(run_time[-1].execution_time)
        
        # Statistical analysis
        avg_time = statistics.mean(execution_times)
        median_time = statistics.median(execution_times)
        min_time = min(execution_times)
        max_time = max(execution_times)
        stdev_time = statistics.stdev(execution_times) if len(execution_times) > 1 else 0
        
        # Performance validation
        self.assertLess(avg_time, self.target_meal_plan_time, 
            f"Average execution time {avg_time:.3f}s should be less than {self.target_meal_plan_time:.3f}s "
            f"(4.2x improvement from {self.baseline_meal_plan_time:.3f}s baseline)")
        
        self.assertLess(max_time, self.target_meal_plan_time * 1.5, 
            f"Maximum execution time {max_time:.3f}s should be within 50% of target")
        
        # Calculate actual improvement factor
        actual_improvement = self.baseline_meal_plan_time / avg_time
        self.assertGreaterEqual(actual_improvement, 3.5, 
            f"Actual improvement {actual_improvement:.1f}x should be at least 3.5x")
        
        # Report results
        print(f"\n📊 AI Meal Plan Generation Performance Results:")
        print(f"   Baseline time: {self.baseline_meal_plan_time:.3f}s")
        print(f"   Target time: {self.target_meal_plan_time:.3f}s (4.2x improvement)")
        print(f"   Average time: {avg_time:.3f}s")
        print(f"   Median time: {median_time:.3f}s")
        print(f"   Min time: {min_time:.3f}s")
        print(f"   Max time: {max_time:.3f}s")
        print(f"   Std dev: {stdev_time:.3f}s")
        print(f"   Actual improvement: {actual_improvement:.1f}x")
        print(f"   ✅ Performance target {'MET' if actual_improvement >= 4.0 else 'PARTIALLY MET'}")
    
    @requires_database
    async def test_ai_performance_under_load(self):
        """Test AI performance under concurrent load."""
        
        async def generate_meal_plan():
            """Single meal plan generation operation."""
            request = MealPlanRequest(
                plan_description="Load test meal plan",
                dietary_preferences={'dietType': 'balanced'},
                week_start_date=date.today()
            )
            
            start_time = time.perf_counter()
            result = await self.ai_service.generate_meal_plan(request, self.test_user)
            end_time = time.perf_counter()
            
            return {
                'success': result.get('success', False),
                'execution_time': end_time - start_time,
                'recipe_count': self._count_recipes_in_meal_plan(result.get('meal_plan', {}))
            }
        
        # Test with 3 concurrent requests
        concurrent_results = await self.run_async_concurrent_operations(
            generate_meal_plan, count=3, timeout=30
        )
        
        # Analyze concurrent performance
        successful_requests = [r for r in concurrent_results if r['success']]
        execution_times = [r['execution_time'] for r in successful_requests]
        
        self.assertGreaterEqual(len(successful_requests), 2, 
            "At least 2 out of 3 concurrent requests should succeed")
        
        if execution_times:
            avg_concurrent_time = statistics.mean(execution_times)
            max_concurrent_time = max(execution_times)
            
            # Performance under load should still be reasonable
            self.assertLess(avg_concurrent_time, self.target_meal_plan_time * 2, 
                f"Average concurrent time {avg_concurrent_time:.3f}s should be within 2x of target")
            
            self.assertLess(max_concurrent_time, self.target_meal_plan_time * 3, 
                f"Max concurrent time {max_concurrent_time:.3f}s should be within 3x of target")
            
            print(f"\n📊 Concurrent Load Test Results (3 requests):")
            print(f"   Successful requests: {len(successful_requests)}/3")
            print(f"   Average time: {avg_concurrent_time:.3f}s")
            print(f"   Max time: {max_concurrent_time:.3f}s")
    
    def _count_recipes_in_meal_plan(self, meal_plan: Dict[str, Any]) -> int:
        """Count total recipes in a meal plan."""
        count = 0
        for day_data in meal_plan.get('daily_meals', []):
            for meal_type in ['breakfast', 'lunch', 'dinner']:
                count += len(day_data.get(meal_type, []))
        return count
    
    @requires_database
    async def test_ai_performance_consistency(self):
        """Test that AI performance is consistent across multiple requests."""
        
        request = MealPlanRequest(
            plan_description="Consistency test meal plan",
            dietary_preferences={'dietType': 'balanced'},
            week_start_date=date.today()
        )
        
        execution_times = []
        
        # Run 10 consecutive requests
        for i in range(10):
            start_time = time.perf_counter()
            result = await self.ai_service.generate_meal_plan(request, self.test_user)
            end_time = time.perf_counter()
            
            self.assert_response_success(result)
            execution_times.append(end_time - start_time)
        
        # Analyze consistency
        avg_time = statistics.mean(execution_times)
        stdev_time = statistics.stdev(execution_times)
        coefficient_of_variation = stdev_time / avg_time
        
        # Performance should be consistent (low coefficient of variation)
        self.assertLess(coefficient_of_variation, 0.3, 
            f"Performance variation {coefficient_of_variation:.3f} should be < 0.3 for consistency")
        
        # No single request should be more than 2x the average
        max_time = max(execution_times)
        self.assertLess(max_time, avg_time * 2, 
            f"Maximum time {max_time:.3f}s should not exceed 2x average {avg_time:.3f}s")
        
        print(f"\n📊 Performance Consistency Results (10 requests):")
        print(f"   Average time: {avg_time:.3f}s")
        print(f"   Standard deviation: {stdev_time:.3f}s")
        print(f"   Coefficient of variation: {coefficient_of_variation:.3f}")
        print(f"   Min time: {min(execution_times):.3f}s")
        print(f"   Max time: {max_time:.3f}s")


@pytest.mark.skipif(not PERFORMANCE_TEST_AVAILABLE, reason="Performance test components not available")
class TestBatchSavePerformance(AsyncTestCase, PerformanceTestCase):
    """Test batch recipe save performance (20 recipes < 2 seconds)."""
    
    def setUp(self):
        """Set up batch save performance test."""
        super().__init__()
        self.add_benchmark(BATCH_SAVE_BENCHMARK)
        self.test_recipes = TestDataFactory.create_recipe_data(25)  # Extra recipes for testing
    
    @requires_database
    def test_batch_recipe_save_performance_target(self):
        """Test that 20 recipes can be saved in under 2 seconds."""
        
        batch_size = 20
        recipes_to_save = self.test_recipes[:batch_size]
        
        with self.measure_operation('batch_recipe_save_20'):
            with django.db.transaction.atomic():
                for recipe_data in recipes_to_save:
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
        
        # Verify all recipes were saved
        saved_count = Recipe.objects.filter(created_by_user=self.test_user).count()
        self.assertEqual(saved_count, batch_size)
        
        # Assert performance benchmark
        self.assert_performance_benchmark('batch_recipe_save_20', 'batch_recipe_save')
        
        # Get execution time for reporting
        metrics = self.tracker.get_metrics_for_operation('batch_recipe_save_20')
        if metrics:
            execution_time = metrics[-1].execution_time
            recipes_per_second = batch_size / execution_time
            
            print(f"\n📊 Batch Save Performance Results:")
            print(f"   Recipes saved: {batch_size}")
            print(f"   Execution time: {execution_time:.3f}s")
            print(f"   Recipes per second: {recipes_per_second:.1f}")
            print(f"   Target: < 2.0s ({'✅ MET' if execution_time < 2.0 else '❌ NOT MET'})")
    
    @requires_database
    def test_batch_save_scaling_performance(self):
        """Test batch save performance scaling with different batch sizes."""
        
        batch_sizes = [5, 10, 15, 20, 25]
        results = []
        
        for batch_size in batch_sizes:
            # Clean database for each test
            Recipe.objects.filter(created_by_user=self.test_user).delete()
            
            recipes_to_save = self.test_recipes[:batch_size]
            
            start_time = time.perf_counter()
            
            with django.db.transaction.atomic():
                for recipe_data in recipes_to_save:
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
            
            end_time = time.perf_counter()
            execution_time = end_time - start_time
            
            # Verify saves
            saved_count = Recipe.objects.filter(created_by_user=self.test_user).count()
            self.assertEqual(saved_count, batch_size)
            
            results.append({
                'batch_size': batch_size,
                'execution_time': execution_time,
                'recipes_per_second': batch_size / execution_time
            })
        
        # Analyze scaling
        print(f"\n📊 Batch Save Scaling Results:")
        for result in results:
            print(f"   {result['batch_size']:2d} recipes: {result['execution_time']:.3f}s "
                  f"({result['recipes_per_second']:.1f} recipes/sec)")
        
        # Performance should scale reasonably (not more than linear)
        time_20 = next(r['execution_time'] for r in results if r['batch_size'] == 20)
        time_10 = next(r['execution_time'] for r in results if r['batch_size'] == 10)
        
        scaling_factor = time_20 / time_10
        self.assertLess(scaling_factor, 2.5, 
            f"Scaling from 10 to 20 recipes should be < 2.5x, got {scaling_factor:.2f}x")


@pytest.mark.skipif(not PERFORMANCE_TEST_AVAILABLE, reason="Performance test components not available")
class TestOverallSystemPerformance(AsyncTestCase, PerformanceTestCase):
    """Test overall system performance combining AI generation and recipe saves."""
    
    def setUp(self):
        """Set up overall system performance test."""
        super().__init__()
        self.ai_service = AIService() if PERFORMANCE_TEST_AVAILABLE else None
    
    @requires_database
    async def test_end_to_end_performance_target(self):
        """Test end-to-end performance: AI generation + batch save in reasonable time."""
        
        # Step 1: Generate meal plan
        request = MealPlanRequest(
            plan_description="End-to-end performance test meal plan",
            dietary_preferences={'dietType': 'balanced'},
            calorie_target=2000,
            week_start_date=date.today()
        )
        
        with self.measure_operation('e2e_ai_generation'):
            ai_result = await self.ai_service.generate_meal_plan(request, self.test_user)
        
        self.assert_response_success(ai_result)
        
        # Step 2: Extract recipes
        all_recipes = []
        for day_data in ai_result['meal_plan']['daily_meals']:
            for meal_type in ['breakfast', 'lunch', 'dinner']:
                all_recipes.extend(day_data.get(meal_type, []))
        
        # Step 3: Save recipes
        with self.measure_operation('e2e_batch_save'):
            with django.db.transaction.atomic():
                saved_count = 0
                for recipe in all_recipes:
                    try:
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
                        saved_count += 1
                    except Exception:
                        # Skip duplicates or invalid recipes
                        pass
        
        # Performance analysis
        ai_metrics = self.tracker.get_metrics_for_operation('e2e_ai_generation')
        save_metrics = self.tracker.get_metrics_for_operation('e2e_batch_save')
        
        if ai_metrics and save_metrics:
            ai_time = ai_metrics[-1].execution_time
            save_time = save_metrics[-1].execution_time
            total_time = ai_time + save_time
            
            # Performance targets
            self.assertLess(ai_time, 5.0, f"AI generation should be < 5s, got {ai_time:.3f}s")
            self.assertLess(save_time, 3.0, f"Batch save should be < 3s, got {save_time:.3f}s")
            self.assertLess(total_time, 7.0, f"Total time should be < 7s, got {total_time:.3f}s")
            
            print(f"\n📊 End-to-End Performance Results:")
            print(f"   AI generation: {ai_time:.3f}s")
            print(f"   Batch save: {save_time:.3f}s ({saved_count} recipes)")
            print(f"   Total time: {total_time:.3f}s")
            print(f"   Target: < 7.0s total ({'✅ MET' if total_time < 7.0 else '❌ NOT MET'})")


if __name__ == '__main__':
    # Run performance benchmarks
    import unittest
    
    # Create test suite with performance tests only
    suite = unittest.TestSuite()
    
    # Add performance test classes
    for test_class in [TestAIPerformanceImprovement, TestBatchSavePerformance, TestOverallSystemPerformance]:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        suite.addTests(tests)
    
    # Run with detailed output
    runner = unittest.TextTestRunner(verbosity=2, buffer=True)
    result = runner.run(suite)
    
    # Print final summary
    print(f"\n" + "="*50)
    print(f"PERFORMANCE BENCHMARK SUMMARY")
    print(f"="*50)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")
    
    if result.failures:
        print(f"\nFAILURES:")
        for test, traceback in result.failures:
            print(f"  - {test}: {traceback.split('AssertionError: ')[-1].split('\\n')[0]}")
    
    if result.errors:
        print(f"\nERRORS:")
        for test, traceback in result.errors:
            print(f"  - {test}: {traceback.split('\\n')[-2]}")