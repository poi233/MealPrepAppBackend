"""
Frontend Integration Test Scenarios for AI Integration API
Tests the two main scenarios: "Save to Template" and "Apply Meal Plan"
"""
import json
import uuid
from datetime import datetime
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from apps.meal_plans.models import MealPlan
from apps.recipes.models import Recipe
from .services import generate_deterministic_recipe_uuid


class FrontendIntegrationTestCase(TestCase):
    """Test cases for frontend integration scenarios."""
    
    def setUp(self):
        """Set up test data."""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client.force_login(self.user)
        
        # Create a test meal plan
        self.meal_plan = MealPlan.objects.create(
            user=self.user,
            name='Test Meal Plan',
            description='Test meal plan for integration testing',
            week_start_date='2025-01-27'
        )
        
        # Sample AI-generated recipe data
        self.sample_recipe_data = {
            'name': '香煎三文鱼配柠檬',
            'description': '简单美味的三文鱼料理',
            'cuisine': '西式',
            'difficulty': '简单',
            'prep_time': 15,
            'cook_time': 20,
            'ingredients': [
                {'name': '三文鱼片', 'amount': '200克'},
                {'name': '柠檬', 'amount': '1个'},
                {'name': '橄榄油', 'amount': '2汤匙'},
                {'name': '盐', 'amount': '适量'},
                {'name': '黑胡椒', 'amount': '适量'}
            ],
            'instructions': [
                '将三文鱼片用盐和黑胡椒调味',
                '平底锅加热橄榄油',
                '煎三文鱼片至两面金黄',
                '挤上新鲜柠檬汁即可'
            ],
            'nutrition_info': {
                'calories': 280,
                'protein': 25.0,
                'carbs': 2.0,
                'fat': 18.0
            },
            'tags': ['健康', '快手菜', '三文鱼'],
            'image_url': ''
        }
        
        # Generate deterministic ID for testing
        self.sample_recipe_data['id'] = generate_deterministic_recipe_uuid(self.sample_recipe_data)
    
    def test_scenario_a_save_to_template_new_recipe(self):
        """
        Test Scenario A: Save to Template - New Recipe Creation
        前端发送单个食谱的确定性ID，后端检查是否已存在，如不存在则保存
        """
        url = reverse('create_recipe_from_ai')
        data = {
            'ai_recipe_data': self.sample_recipe_data,
            'save_to_account': True
        }
        
        response = self.client.post(
            url,
            data=json.dumps(data),
            content_type='application/json'
        )
        
        # Verify response format
        self.assertEqual(response.status_code, 201)
        response_data = response.json()
        
        # Check standardized response format
        self.assertTrue(response_data['success'])
        self.assertEqual(response_data['status'], 'created')
        self.assertIn('recipe', response_data)
        self.assertIn('recipe_id', response_data)
        self.assertIn('message', response_data)
        self.assertIn('timestamp', response_data)
        
        # Verify recipe was created with correct ID
        recipe_id = response_data['recipe_id']
        self.assertEqual(recipe_id, self.sample_recipe_data['id'])
        
        # Verify recipe exists in database
        recipe = Recipe.objects.get(id=recipe_id)
        self.assertEqual(recipe.name, self.sample_recipe_data['name'])
        self.assertEqual(recipe.created_by_user, self.user)
    
    def test_scenario_a_save_to_template_existing_recipe(self):
        """
        Test Scenario A: Save to Template - Existing Recipe Detection
        测试重复食谱的正确识别和处理
        """
        # First, create the recipe
        recipe = Recipe.objects.create(
            id=uuid.UUID(self.sample_recipe_data['id']),
            created_by_user=self.user,
            name=self.sample_recipe_data['name'],
            description=self.sample_recipe_data['description'],
            ingredients=self.sample_recipe_data['ingredients'],
            instructions='\n'.join(f"{i+1}. {step}" for i, step in enumerate(self.sample_recipe_data['instructions'])),
            nutrition_info=self.sample_recipe_data['nutrition_info'],
            cuisine=self.sample_recipe_data['cuisine'],
            prep_time=self.sample_recipe_data['prep_time'],
            cook_time=self.sample_recipe_data['cook_time'],
            difficulty=self.sample_recipe_data['difficulty'],
            tags=self.sample_recipe_data['tags']
        )
        
        # Now try to save again
        url = reverse('create_recipe_from_ai')
        data = {
            'ai_recipe_data': self.sample_recipe_data,
            'save_to_account': True
        }
        
        response = self.client.post(
            url,
            data=json.dumps(data),
            content_type='application/json'
        )
        
        # Verify response indicates existing recipe
        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        
        self.assertTrue(response_data['success'])
        self.assertEqual(response_data['status'], 'already_exists')
        self.assertEqual(response_data['recipe_id'], str(recipe.id))
        self.assertIn('已存在', response_data['message'])
    
    def test_scenario_b_apply_meal_plan_batch_creation(self):
        """
        Test Scenario B: Apply Meal Plan - Batch Recipe Creation
        前端发送整个膳食计划的所有食谱，后端批量处理，支持部分成功
        """
        # Create multiple recipe variations
        recipe_variations = []
        for i in range(3):
            recipe_data = self.sample_recipe_data.copy()
            recipe_data['name'] = f"{recipe_data['name']} 变化{i+1}"
            recipe_data['id'] = generate_deterministic_recipe_uuid(recipe_data)
            
            recipe_variations.append({
                'ai_recipe_data': recipe_data,
                'meal_plan_day': i % 7,  # Distribute across different days
                'meal_plan_type': ['breakfast', 'lunch', 'dinner'][i % 3]
            })
        
        url = reverse('batch_create_recipes_from_ai')
        data = {
            'recipes': recipe_variations,
            'meal_plan_id': str(self.meal_plan.id),
            'save_to_account': True,
            'skip_duplicates': True
        }
        
        response = self.client.post(
            url,
            data=json.dumps(data),
            content_type='application/json'
        )
        
        # Verify batch response format
        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        
        # Check standardized batch response format
        self.assertTrue(response_data['success'])
        self.assertEqual(response_data['total_processed'], 3)
        self.assertEqual(response_data['successful'], 3)
        self.assertEqual(response_data['failed'], 0)
        self.assertIn('summary', response_data)
        self.assertIn('results', response_data)
        self.assertIn('processing_time', response_data)
        
        # Verify individual recipe results
        results = response_data['results']
        self.assertEqual(len(results), 3)
        
        for result in results:
            self.assertIn('recipe_id', result)
            self.assertIn('name', result)
            self.assertIn('status', result)
            self.assertEqual(result['status'], 'created')
            self.assertTrue(result.get('meal_plan_added', False))
        
        # Verify recipes were added to meal plan
        meal_plan_items = self.meal_plan.items.all()
        self.assertEqual(meal_plan_items.count(), 3)
    
    def test_scenario_b_partial_success_handling(self):
        """
        Test Scenario B: Partial Success - Some recipes succeed, others fail
        测试批量操作中部分成功的情况处理
        """
        # Create one valid recipe and one invalid recipe
        valid_recipe = {
            'ai_recipe_data': self.sample_recipe_data,
            'meal_plan_day': 0,
            'meal_plan_type': 'breakfast'
        }
        
        invalid_recipe = {
            'ai_recipe_data': {
                'name': '',  # Invalid: empty name
                'ingredients': [],  # Invalid: no ingredients
                'instructions': []  # Invalid: no instructions
            },
            'meal_plan_day': 1,
            'meal_plan_type': 'lunch'
        }
        
        url = reverse('batch_create_recipes_from_ai')
        data = {
            'recipes': [valid_recipe, invalid_recipe],
            'meal_plan_id': str(self.meal_plan.id),
            'save_to_account': True
        }
        
        response = self.client.post(
            url,
            data=json.dumps(data),
            content_type='application/json'
        )
        
        # Verify partial success response
        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        
        self.assertTrue(response_data['success'])  # Overall success even with partial failures
        self.assertEqual(response_data['total_processed'], 2)
        self.assertEqual(response_data['successful'], 1)
        self.assertEqual(response_data['failed'], 1)
        
        # Check individual results
        results = response_data['results']
        successful_result = next(r for r in results if r['status'] == 'created')
        failed_result = next(r for r in results if r['status'] == 'failed')
        
        self.assertIsNotNone(successful_result['recipe_id'])
        self.assertIsNone(failed_result['recipe_id'])
        self.assertIn('error', failed_result)
    
    def test_api_performance_requirements(self):
        """
        Test API Performance - Ensure response times meet requirements
        验证API响应时间符合<2秒的要求
        """
        import time
        
        # Test single recipe creation performance
        start_time = time.time()
        
        url = reverse('create_recipe_from_ai')
        data = {
            'ai_recipe_data': self.sample_recipe_data,
            'save_to_account': True
        }
        
        response = self.client.post(
            url,
            data=json.dumps(data),
            content_type='application/json'
        )
        
        single_recipe_time = time.time() - start_time
        
        self.assertEqual(response.status_code, 201)
        self.assertLess(single_recipe_time, 2.0, "Single recipe creation should be under 2 seconds")
        
        # Test batch creation performance (up to 10 recipes)
        batch_recipes = []
        for i in range(10):
            recipe_data = self.sample_recipe_data.copy()
            recipe_data['name'] = f"批量测试食谱 {i+1}"
            recipe_data['id'] = generate_deterministic_recipe_uuid(recipe_data)
            
            batch_recipes.append({
                'ai_recipe_data': recipe_data,
                'meal_plan_day': i % 7,
                'meal_plan_type': ['breakfast', 'lunch', 'dinner', 'snack'][i % 4]
            })
        
        start_time = time.time()
        
        url = reverse('batch_create_recipes_from_ai')
        data = {
            'recipes': batch_recipes,
            'meal_plan_id': str(self.meal_plan.id),
            'save_to_account': True
        }
        
        response = self.client.post(
            url,
            data=json.dumps(data),
            content_type='application/json'
        )
        
        batch_time = time.time() - start_time
        
        self.assertEqual(response.status_code, 200)
        self.assertLess(batch_time, 2.0, "Batch creation of 10 recipes should be under 2 seconds")
        
        # Verify performance metrics in response
        response_data = response.json()
        self.assertIn('processing_time', response_data)
        self.assertLess(response_data['processing_time'], 2.0)
    
    def test_error_handling_and_user_feedback(self):
        """
        Test Error Handling - Ensure user-friendly error messages
        测试各种错误场景的用户友好反馈
        """
        # Test invalid meal plan ID
        url = reverse('batch_create_recipes_from_ai')
        data = {
            'recipes': [{'ai_recipe_data': self.sample_recipe_data}],
            'meal_plan_id': str(uuid.uuid4()),  # Non-existent meal plan
            'save_to_account': True
        }
        
        response = self.client.post(
            url,
            data=json.dumps(data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 404)
        response_data = response.json()
        self.assertFalse(response_data['success'])
        self.assertIn('error', response_data['summary'])
        
        # Test malformed request
        url = reverse('create_recipe_from_ai')
        data = {
            'invalid_field': 'invalid_data'
        }
        
        response = self.client.post(
            url,
            data=json.dumps(data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        response_data = response.json()
        self.assertFalse(response_data['success'])
        self.assertIn('message', response_data)
        self.assertIn('errors', response_data)


class APIDocumentationTestCase(TestCase):
    """Test cases for API documentation and versioning."""
    
    def test_api_endpoint_accessibility(self):
        """Test that all documented endpoints are accessible."""
        from django.urls import reverse
        
        # Test that URL patterns are properly configured
        endpoints = [
            'generate_meal_plan',
            'create_recipe_from_ai',
            'batch_create_recipes_from_ai',
            'suggest_recipe_modifications'
        ]
        
        for endpoint_name in endpoints:
            try:
                url = reverse(endpoint_name)
                self.assertIsNotNone(url)
            except Exception as e:
                self.fail(f"Endpoint {endpoint_name} is not properly configured: {e}")
    
    def test_backward_compatibility(self):
        """Test that existing API contracts are maintained."""
        # This test ensures that changes don't break existing clients
        # In a real scenario, this would test against saved API responses
        pass


if __name__ == '__main__':
    import django
    from django.conf import settings
    from django.test.utils import get_runner
    
    django.setup()
    TestRunner = get_runner(settings)
    test_runner = TestRunner()
    failures = test_runner.run_tests(['ai_integration.integration_tests'])