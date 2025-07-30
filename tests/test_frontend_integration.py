#!/usr/bin/env python3
"""
Frontend Integration Test Suite for Task 4: API Interface Enhancement

This script tests the enhanced API endpoints to ensure they support the two core frontend scenarios:
- Scene A: "Save to Template" (Single recipe save)
- Scene B: "Apply Meal Plan" (Batch recipe save)

Usage:
    python test_frontend_integration.py
"""

import os
import sys
import django
import requests
import json
import uuid
from datetime import datetime
from typing import Dict, List, Any

# Setup Django environment
base_dir = '/Users/puyihao/workspace/MealPrep/MealPrepAppBackend'
sys.path.append(base_dir)
sys.path.append(os.path.join(base_dir, 'src'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mealprep_project.settings')
django.setup()

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from apps.ai_integration.services import generate_deterministic_recipe_uuid

User = get_user_model()

class FrontendIntegrationTestSuite:
    """Test suite for frontend integration scenarios."""
    
    def __init__(self):
        self.client = APIClient()
        self.test_user = None
        self.base_url = "http://127.0.0.1:8000"
        
    def setup_test_user(self):
        """Create a test user for API calls."""
        try:
            self.test_user = User.objects.create_user(
                username='frontend_test_user',
                email='test@frontend.com',
                password='testpass123'
            )
            self.client.force_authenticate(user=self.test_user)
            print("✅ Test user created and authenticated")
            return True
        except Exception as e:
            print(f"❌ Failed to create test user: {e}")
            return False
    
    def cleanup_test_user(self):
        """Clean up test user."""
        if self.test_user:
            self.test_user.delete()
            print("✅ Test user cleaned up")
    
    def generate_test_recipe_data(self, name_suffix: str = "") -> Dict[str, Any]:
        """Generate test recipe data with deterministic UUID."""
        recipe_data = {
            "name": f"测试食谱{name_suffix}",
            "description": f"这是一个测试食谱的描述{name_suffix}",
            "cuisine": "中式",
            "difficulty": "medium",
            "prep_time": 15,
            "cook_time": 30,
            "ingredients": [
                {"name": "鸡胸肉", "amount": "200克"},
                {"name": "蔬菜", "amount": "100克"}
            ],
            "instructions": [
                "步骤1：准备食材",
                "步骤2：开始烹饪",
                "步骤3：完成装盘"
            ],
            "nutrition_info": {
                "calories": 350,
                "protein": 25,
                "carbs": 10,
                "fat": 8
            },
            "image_url": "https://example.com/recipe.jpg",
            "tags": ["健康", "简单"]
        }
        
        # Generate deterministic UUID
        recipe_id = generate_deterministic_recipe_uuid(recipe_data)
        recipe_data["id"] = recipe_id
        
        return recipe_data
    
    def test_scene_a_single_recipe_save(self) -> bool:
        """Test Scene A: Save to Template (Single recipe save)."""
        print("\n🧪 Testing Scene A: Save to Template (Single recipe save)")
        
        try:
            # Generate test recipe data
            recipe_data = self.generate_test_recipe_data("_SceneA")
            
            # Prepare request payload
            payload = {
                "ai_recipe_data": recipe_data,
                "save_to_account": True
            }
            
            # Make API call
            response = self.client.post(
                '/api/ai-integration/create-recipe-from-ai/',
                data=payload,
                format='json'
            )
            
            print(f"   Status Code: {response.status_code}")
            print(f"   Response Keys: {list(response.data.keys()) if hasattr(response, 'data') else 'No data'}")
            
            # Validate response structure
            if response.status_code not in [200, 201]:
                print(f"❌ Scene A failed with status {response.status_code}")
                print(f"   Error: {response.data if hasattr(response, 'data') else response.content}")
                return False
            
            # Check new response format
            expected_fields = ['success', 'recipe', 'status', 'message', 'recipe_id', 'timestamp']
            response_data = response.data
            
            missing_fields = [field for field in expected_fields if field not in response_data]
            if missing_fields:
                print(f"❌ Scene A missing required fields: {missing_fields}")
                return False
            
            # Validate response content
            if not response_data.get('success'):
                print(f"❌ Scene A returned success=False: {response_data.get('message', 'No message')}")
                return False
            
            if response_data.get('status') not in ['created', 'already_exists']:
                print(f"❌ Scene A invalid status: {response_data.get('status')}")
                return False
            
            # Validate recipe data structure
            recipe_response = response_data.get('recipe', {})
            if not recipe_response.get('id') or not recipe_response.get('name'):
                print(f"❌ Scene A invalid recipe data structure")
                return False
            
            print(f"✅ Scene A passed!")
            print(f"   Status: {response_data.get('status')}")
            print(f"   Message: {response_data.get('message')}")
            print(f"   Recipe ID: {response_data.get('recipe_id')}")
            
            # Test the same recipe again to verify deterministic behavior
            print("   Testing deterministic behavior with same recipe...")
            response2 = self.client.post(
                '/api/ai-integration/create-recipe-from-ai/',
                data=payload,
                format='json'
            )
            
            if response2.status_code == 200 and response2.data.get('status') == 'already_exists':
                print("   ✅ Deterministic behavior confirmed - recipe already exists")
            else:
                print("   ⚠️  Deterministic behavior not as expected")
            
            return True
            
        except Exception as e:
            print(f"❌ Scene A failed with exception: {e}")
            return False
    
    def test_scene_b_batch_recipe_save(self) -> bool:
        """Test Scene B: Apply Meal Plan (Batch recipe save)."""
        print("\n🧪 Testing Scene B: Apply Meal Plan (Batch recipe save)")
        
        try:
            # Generate multiple test recipes
            recipes_data = []
            for i in range(3):
                recipe_data = self.generate_test_recipe_data(f"_SceneB_{i}")
                recipes_data.append({
                    "ai_recipe_data": recipe_data,
                    "meal_plan_day": i % 7,  # Distribute across days
                    "meal_plan_type": ["breakfast", "lunch", "dinner"][i % 3]
                })
            
            # Prepare batch request payload
            payload = {
                "recipes": recipes_data,
                "save_to_account": True,
                "skip_duplicates": True
            }
            
            # Make batch API call
            response = self.client.post(
                '/api/ai-integration/batch-create-recipes-from-ai/',
                data=payload,
                format='json'
            )
            
            print(f"   Status Code: {response.status_code}")
            print(f"   Response Keys: {list(response.data.keys()) if hasattr(response, 'data') else 'No data'}")
            
            # Validate response structure
            if response.status_code != 200:
                print(f"❌ Scene B failed with status {response.status_code}")
                print(f"   Error: {response.data if hasattr(response, 'data') else response.content}")
                return False
            
            # Check new batch response format
            expected_fields = [
                'success', 'total_processed', 'successful', 'failed', 
                'already_exists', 'summary', 'results', 'timestamp', 'processing_time'
            ]
            response_data = response.data
            
            missing_fields = [field for field in expected_fields if field not in response_data]
            if missing_fields:
                print(f"❌ Scene B missing required fields: {missing_fields}")
                return False
            
            # Validate response content
            if not response_data.get('success'):
                print(f"❌ Scene B returned success=False")
                return False
            
            # Validate batch processing statistics
            total_processed = response_data.get('total_processed', 0)
            successful = response_data.get('successful', 0)
            failed = response_data.get('failed', 0)
            
            if total_processed != len(recipes_data):
                print(f"❌ Scene B total_processed mismatch: expected {len(recipes_data)}, got {total_processed}")
                return False
            
            if successful + failed != total_processed:
                print(f"❌ Scene B count mismatch: successful({successful}) + failed({failed}) != total({total_processed})")
                return False
            
            # Validate individual results
            results = response_data.get('results', [])
            if len(results) != len(recipes_data):
                print(f"❌ Scene B results count mismatch: expected {len(recipes_data)}, got {len(results)}")
                return False
            
            # Check each result structure
            for i, result in enumerate(results):
                required_result_fields = ['recipe_id', 'name', 'status', 'error', 'meal_plan_added']
                missing_result_fields = [field for field in required_result_fields if field not in result]
                if missing_result_fields:
                    print(f"❌ Scene B result {i} missing fields: {missing_result_fields}")
                    return False
                
                if result['status'] not in ['created', 'already_exists', 'failed']:
                    print(f"❌ Scene B result {i} invalid status: {result['status']}")
                    return False
            
            print(f"✅ Scene B passed!")
            print(f"   Total Processed: {total_processed}")
            print(f"   Successful: {successful}")
            print(f"   Failed: {failed}")
            print(f"   Already Exists: {response_data.get('already_exists', 0)}")
            print(f"   Processing Time: {response_data.get('processing_time', 0):.2f}s")
            
            # Test the same batch again to verify deterministic behavior
            print("   Testing batch deterministic behavior...")
            response2 = self.client.post(
                '/api/ai-integration/batch-create-recipes-from-ai/',
                data=payload,
                format='json'
            )
            
            if (response2.status_code == 200 and 
                response2.data.get('already_exists', 0) == successful):
                print("   ✅ Batch deterministic behavior confirmed")
            else:
                print("   ⚠️  Batch deterministic behavior not as expected")
            
            return True
            
        except Exception as e:
            print(f"❌ Scene B failed with exception: {e}")
            return False
    
    def test_backward_compatibility(self) -> bool:
        """Test backward compatibility with older API formats."""
        print("\n🧪 Testing Backward Compatibility")
        
        try:
            # Test old format without deterministic UUID
            recipe_data = {
                "name": "兼容性测试食谱",
                "description": "测试向后兼容性",
                "cuisine": "中式",
                "difficulty": "easy",
                "prep_time": 10,
                "cook_time": 20,
                "ingredients": [{"name": "测试食材", "amount": "100克"}],
                "instructions": ["测试步骤"],
                "nutrition_info": {"calories": 200},
                "image_url": "",
                "tags": ["测试"]
                # Note: No 'id' field - should be auto-generated
            }
            
            payload = {
                "ai_recipe_data": recipe_data,
                "save_to_account": True
            }
            
            response = self.client.post(
                '/api/ai-integration/create-recipe-from-ai/',
                data=payload,
                format='json'
            )
            
            if response.status_code not in [200, 201]:
                print(f"❌ Backward compatibility failed: {response.status_code}")
                return False
            
            # Should still return new format but work with old input
            if not response.data.get('success'):
                print(f"❌ Backward compatibility: success=False")
                return False
            
            print("✅ Backward compatibility confirmed")
            return True
            
        except Exception as e:
            print(f"❌ Backward compatibility failed: {e}")
            return False
    
    def test_error_handling(self) -> bool:
        """Test error handling scenarios."""
        print("\n🧪 Testing Error Handling")
        
        test_cases = [
            {
                "name": "Invalid recipe data",
                "payload": {"ai_recipe_data": {"name": ""}, "save_to_account": True},
                "expected_status": 400
            },
            {
                "name": "Missing required fields",
                "payload": {"save_to_account": True},
                "expected_status": 400
            },
            {
                "name": "Invalid batch data",
                "payload": {"recipes": "not_a_list"},
                "expected_status": 400
            }
        ]
        
        all_passed = True
        
        for test_case in test_cases:
            try:
                if "recipes" in test_case["payload"]:
                    # Batch endpoint
                    response = self.client.post(
                        '/api/ai-integration/batch-create-recipes-from-ai/',
                        data=test_case["payload"],
                        format='json'
                    )
                else:
                    # Single endpoint
                    response = self.client.post(
                        '/api/ai-integration/create-recipe-from-ai/',
                        data=test_case["payload"],
                        format='json'
                    )
                
                if response.status_code == test_case["expected_status"]:
                    # Check new error format
                    if not response.data.get('success', True):  # Should be False for errors
                        print(f"   ✅ {test_case['name']}: Proper error handling")
                    else:
                        print(f"   ⚠️  {test_case['name']}: Error format issue")
                        all_passed = False
                else:
                    print(f"   ❌ {test_case['name']}: Expected {test_case['expected_status']}, got {response.status_code}")
                    all_passed = False
                    
            except Exception as e:
                print(f"   ❌ {test_case['name']}: Exception {e}")
                all_passed = False
        
        if all_passed:
            print("✅ Error handling tests passed")
        else:
            print("❌ Some error handling tests failed")
        
        return all_passed
    
    def run_all_tests(self) -> bool:
        """Run all frontend integration tests."""
        print("🚀 Starting Frontend Integration Test Suite for Task 4")
        print("=" * 60)
        
        if not self.setup_test_user():
            return False
        
        tests = [
            ("Scene A: Single Recipe Save", self.test_scene_a_single_recipe_save),
            ("Scene B: Batch Recipe Save", self.test_scene_b_batch_recipe_save),
            ("Backward Compatibility", self.test_backward_compatibility),
            ("Error Handling", self.test_error_handling)
        ]
        
        results = []
        for test_name, test_func in tests:
            try:
                result = test_func()
                results.append((test_name, result))
            except Exception as e:
                print(f"❌ {test_name} crashed: {e}")
                results.append((test_name, False))
        
        # Cleanup
        self.cleanup_test_user()
        
        # Summary
        print("\n" + "=" * 60)
        print("📋 Test Results Summary:")
        passed = sum(1 for _, result in results if result)
        total = len(results)
        
        for test_name, result in results:
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"   {status} {test_name}")
        
        print(f"\n🏆 Overall Result: {passed}/{total} tests passed")
        
        if passed == total:
            print("🎉 All frontend integration tests passed! API is ready for frontend integration.")
            return True
        else:
            print("⚠️  Some tests failed. Please review and fix issues before frontend integration.")
            return False


def main():
    """Main entry point."""
    test_suite = FrontendIntegrationTestSuite()
    success = test_suite.run_all_tests()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()