#!/usr/bin/env python3
"""
Test base classes and utility functions for comprehensive testing.
Provides common functionality for all test suites.
"""

import os
import sys
import time
import asyncio
import logging
from unittest.mock import Mock, patch, MagicMock
from datetime import date, datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
from contextlib import contextmanager

import django
from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model
from django.db import transaction
from django.conf import settings

# Setup Django if not already done
if not settings.configured:
    sys.path.insert(0, '/Users/puyihao/workspace/MealPrep/MealPrepAppBackend/src')
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    django.setup()

# Configure logging for tests
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

User = get_user_model()


class BaseTestCase(TestCase):
    """Base test case with common functionality."""
    
    @classmethod
    def setUpClass(cls):
        """Set up test class."""
        super().setUpClass()
        cls.setup_test_logging()
    
    @classmethod
    def setup_test_logging(cls):
        """Configure test-specific logging."""
        cls.test_logger = logging.getLogger(f'test.{cls.__name__}')
        cls.test_logger.setLevel(logging.INFO)
    
    def setUp(self):
        """Set up each test."""
        super().setUp()
        self.start_time = time.perf_counter()
        self.test_user = self.create_test_user()
        self.test_logger.info(f"Starting test: {self._testMethodName}")
    
    def tearDown(self):
        """Clean up after each test."""
        end_time = time.perf_counter()
        duration = end_time - self.start_time
        self.test_logger.info(f"Test {self._testMethodName} completed in {duration:.3f}s")
        super().tearDown()
    
    def create_test_user(self, username: str = None, email: str = None) -> User:
        """Create a test user."""
        username = username or f"test_user_{int(time.time())}"
        email = email or f"{username}@test.com"
        
        user, created = User.objects.get_or_create(
            username=username,
            defaults={'email': email}
        )
        return user
    
    def assert_response_success(self, response: Dict[str, Any]):
        """Assert that API response indicates success."""
        self.assertTrue(response.get('success', False), 
                       f"Response should be successful: {response}")
    
    def assert_response_error(self, response: Dict[str, Any], expected_error: str = None):
        """Assert that API response indicates error."""
        self.assertFalse(response.get('success', True),
                        f"Response should indicate error: {response}")
        if expected_error:
            self.assertIn(expected_error, response.get('error', ''))
    
    def assert_execution_time(self, max_seconds: float):
        """Assert that test execution time is within limit."""
        duration = time.perf_counter() - self.start_time
        self.assertLessEqual(duration, max_seconds,
                           f"Test took {duration:.3f}s, expected <= {max_seconds}s")


class AsyncTestCase(BaseTestCase):
    """Base test case for async operations."""
    
    def setUp(self):
        """Set up async test case."""
        super().setUp()
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
    
    def tearDown(self):
        """Clean up async test case."""
        self.loop.close()
        super().tearDown()
    
    def run_async(self, coro):
        """Run async coroutine in test."""
        return self.loop.run_until_complete(coro)


class DatabaseTestCase(TransactionTestCase):
    """Test case with database transaction support."""
    
    def setUp(self):
        """Set up database test case."""
        super().setUp()
        self.start_time = time.perf_counter()
        self.test_user = self.create_test_user()
    
    def create_test_user(self, username: str = None, email: str = None) -> User:
        """Create a test user."""
        username = username or f"db_test_user_{int(time.time())}"
        email = email or f"{username}@test.com"
        
        user, created = User.objects.get_or_create(
            username=username,
            defaults={'email': email}
        )
        return user
    
    @contextmanager
    def assert_database_queries(self, max_queries: int):
        """Assert maximum number of database queries."""
        from django.test.utils import override_settings
        from django.db import connection
        
        with override_settings(DEBUG=True):
            initial_queries = len(connection.queries)
            yield
            final_queries = len(connection.queries)
            query_count = final_queries - initial_queries
            
            self.assertLessEqual(
                query_count, max_queries,
                f"Expected <= {max_queries} queries, but got {query_count}"
            )


class PerformanceTestMixin:
    """Mixin for performance testing functionality."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.performance_data = {}
    
    @contextmanager
    def measure_execution_time(self, operation_name: str):
        """Measure execution time for an operation."""
        start_time = time.perf_counter()
        try:
            yield
        finally:
            end_time = time.perf_counter()
            duration = end_time - start_time
            self.performance_data[operation_name] = duration
            logger.info(f"{operation_name} took {duration:.3f}s")
    
    def assert_performance_improvement(self, operation_name: str, 
                                     baseline_time: float, 
                                     improvement_factor: float):
        """Assert that operation shows performance improvement."""
        actual_time = self.performance_data.get(operation_name)
        self.assertIsNotNone(actual_time, f"No timing data for {operation_name}")
        
        expected_max_time = baseline_time / improvement_factor
        self.assertLessEqual(
            actual_time, expected_max_time,
            f"{operation_name} took {actual_time:.3f}s, expected <= {expected_max_time:.3f}s "
            f"(baseline: {baseline_time:.3f}s, improvement factor: {improvement_factor}x)"
        )
    
    def get_performance_summary(self) -> Dict[str, float]:
        """Get summary of performance measurements."""
        return self.performance_data.copy()


class MockingTestMixin:
    """Mixin for mocking functionality."""
    
    def create_ai_service_mock(self, **mock_responses) -> Mock:
        """Create a mock AI service with predefined responses."""
        mock_service = Mock()
        
        # Default responses
        default_meal_plan = {
            'success': True,
            'meal_plan': {
                'week_start_date': str(date.today()),
                'daily_meals': [
                    {
                        'day': 'Monday',
                        'breakfast': [self.create_mock_recipe('Mock Breakfast')],
                        'lunch': [self.create_mock_recipe('Mock Lunch')],
                        'dinner': [self.create_mock_recipe('Mock Dinner')]
                    }
                ]
            }
        }
        
        mock_service.generate_meal_plan.return_value = asyncio.Future()
        mock_service.generate_meal_plan.return_value.set_result(
            mock_responses.get('generate_meal_plan', default_meal_plan)
        )
        
        return mock_service
    
    def create_mock_recipe(self, name: str = "Mock Recipe") -> Dict[str, Any]:
        """Create a mock recipe data structure."""
        return {
            'id': f'mock-{name.lower().replace(" ", "-")}',
            'name': name,
            'cuisine': 'Mock Cuisine',
            'prep_time': 10,
            'cook_time': 20,
            'difficulty': 'easy',
            'ingredients': [
                {'name': 'Mock Ingredient 1', 'amount': '1 cup'},
                {'name': 'Mock Ingredient 2', 'amount': '2 tbsp'}
            ],
            'instructions': [
                'Mock instruction 1',
                'Mock instruction 2'
            ],
            'nutrition': {
                'calories': 300,
                'protein': 20,
                'carbs': 30,
                'fat': 10
            },
            'image_url': 'https://example.com/mock-image.jpg'
        }


class ConcurrencyTestMixin:
    """Mixin for concurrency testing."""
    
    def run_concurrent_operations(self, operation: Callable, 
                                 count: int, 
                                 timeout: float = 30.0) -> List[Any]:
        """Run multiple operations concurrently."""
        import concurrent.futures
        import threading
        
        results = []
        errors = []
        
        def wrapped_operation():
            try:
                return operation()
            except Exception as e:
                errors.append(e)
                return None
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=count) as executor:
            futures = [executor.submit(wrapped_operation) for _ in range(count)]
            
            try:
                for future in concurrent.futures.as_completed(futures, timeout=timeout):
                    result = future.result()
                    if result is not None:
                        results.append(result)
            except concurrent.futures.TimeoutError:
                self.fail(f"Concurrent operations timed out after {timeout}s")
        
        if errors:
            self.fail(f"Concurrent operations had {len(errors)} errors: {errors[0]}")
        
        return results
    
    async def run_async_concurrent_operations(self, async_operation: Callable,
                                            count: int,
                                            timeout: float = 30.0) -> List[Any]:
        """Run multiple async operations concurrently."""
        tasks = [asyncio.create_task(async_operation()) for _ in range(count)]
        
        try:
            results = await asyncio.wait_for(asyncio.gather(*tasks), timeout=timeout)
            return results
        except asyncio.TimeoutError:
            self.fail(f"Async concurrent operations timed out after {timeout}s")


class TestDataFactory:
    """Factory for creating test data."""
    
    @staticmethod
    def create_meal_plan_request(user: User = None, **overrides) -> Dict[str, Any]:
        """Create a meal plan request for testing."""
        from apps.ai_integration.services import MealPlanRequest
        
        defaults = {
            'plan_description': 'Healthy weekly meal plan with balanced nutrition',
            'dietary_preferences': {'dietType': 'balanced'},
            'allergies': [],
            'calorie_target': 2000,
            'week_start_date': date.today()
        }
        defaults.update(overrides)
        
        return MealPlanRequest(**defaults)
    
    @staticmethod
    def create_test_recipes(count: int = 5) -> List[Dict[str, Any]]:
        """Create multiple test recipes."""
        recipes = []
        for i in range(count):
            recipes.append({
                'id': f'test-recipe-{i}',
                'name': f'Test Recipe {i}',
                'cuisine': 'Test Cuisine',
                'prep_time': 10 + (i * 5),
                'cook_time': 20 + (i * 5),
                'difficulty': ['easy', 'medium', 'hard'][i % 3],
                'ingredients': [
                    {'name': f'Ingredient {i}-1', 'amount': '1 cup'},
                    {'name': f'Ingredient {i}-2', 'amount': '2 tbsp'}
                ],
                'instructions': [
                    f'Test instruction {i}-1',
                    f'Test instruction {i}-2'
                ],
                'nutrition': {
                    'calories': 200 + (i * 100),
                    'protein': 15 + (i * 5),
                    'carbs': 25 + (i * 5),
                    'fat': 8 + (i * 2)
                }
            })
        return recipes


# Utility functions
def skip_if_no_ai_service(test_func):
    """Decorator to skip test if AI service is not available."""
    def wrapper(*args, **kwargs):
        try:
            from apps.ai_integration.services import AIService
            return test_func(*args, **kwargs)
        except ImportError:
            import unittest
            raise unittest.SkipTest("AI service not available")
    return wrapper


def requires_database(test_func):
    """Decorator to ensure test requires database access."""
    def wrapper(self, *args, **kwargs):
        if not hasattr(self, 'test_user'):
            self.test_user = self.create_test_user()
        return test_func(self, *args, **kwargs)
    return wrapper


# Test suite discovery
def discover_test_modules():
    """Discover all test modules in the test directory."""
    import importlib
    import pkgutil
    
    test_modules = []
    test_dir = os.path.dirname(__file__)
    
    for importer, modname, ispkg in pkgutil.iter_modules([test_dir]):
        if modname.startswith('test_') and modname != 'test_base':
            try:
                module = importlib.import_module(f'test.{modname}')
                test_modules.append(module)
            except ImportError as e:
                logger.warning(f"Could not import test module {modname}: {e}")
    
    return test_modules