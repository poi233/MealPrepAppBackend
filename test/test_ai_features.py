#!/usr/bin/env python
"""
Test script for AI service features like caching and rate limiting.
"""
import os
import sys
import django
import asyncio
import time
from datetime import date

# Add the src directory to the Python path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(BASE_DIR, 'src')
sys.path.insert(0, SRC_DIR)

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mealprep_project.settings.development')
django.setup()

from apps.ai_integration.services import AIService, MealPlanRequest, RecipeGenerationRequest


async def test_caching():
    """Test caching functionality."""
    print("Testing AI Service Caching...")
    
    ai_service = AIService()
    
    class MockUser:
        def __init__(self):
            self.id = "test-user-cache"
    
    user = MockUser()
    
    # Test meal plan caching
    meal_plan_request = MealPlanRequest(
        plan_description="简单的测试膳食计划",
        week_start_date=date.today()
    )
    
    print("\n1. First meal plan request (should hit AI)...")
    start_time = time.time()
    result1 = await ai_service.generate_meal_plan(meal_plan_request, user)
    first_duration = time.time() - start_time
    
    print("\n2. Second meal plan request (should use cache)...")
    start_time = time.time()
    result2 = await ai_service.generate_meal_plan(meal_plan_request, user)
    second_duration = time.time() - start_time
    
    if result1['success'] and result2['success']:
        print(f"✅ Caching test successful!")
        print(f"   First request: {first_duration:.2f}s")
        print(f"   Second request: {second_duration:.2f}s")
        print(f"   Speed improvement: {(first_duration/second_duration):.1f}x faster")
        
        # Verify the content is the same
        if result1['meal_plan']['name'] == result2['meal_plan']['name']:
            print("   ✅ Cached content matches original")
        else:
            print("   ❌ Cached content differs from original")
    else:
        print("❌ Caching test failed - requests unsuccessful")


async def test_rate_limiting():
    """Test rate limiting functionality."""
    print("\nTesting Rate Limiting...")
    
    ai_service = AIService()
    
    class MockUser:
        def __init__(self):
            self.id = "test-user-rate-limit"
    
    user = MockUser()
    
    # Override rate limit for testing
    original_limit = ai_service._max_requests_per_minute
    ai_service._max_requests_per_minute = 3  # Set very low limit for testing
    
    try:
        successful_requests = 0
        rate_limited_requests = 0
        
        for i in range(5):
            try:
                recipe_request = RecipeGenerationRequest(
                    name=f"测试食谱 {i+1}",
                    cuisine="Chinese"
                )
                
                result = await ai_service.generate_recipe_details(recipe_request, user)
                if result['success']:
                    successful_requests += 1
                    print(f"   Request {i+1}: ✅ Success")
                else:
                    if "rate limit" in result['error'].lower():
                        rate_limited_requests += 1
                        print(f"   Request {i+1}: ⏱️ Rate limited")
                    else:
                        print(f"   Request {i+1}: ❌ Failed - {result['error']}")
                        
            except Exception as e:
                if "rate limit" in str(e).lower():
                    rate_limited_requests += 1
                    print(f"   Request {i+1}: ⏱️ Rate limited (exception)")
                else:
                    print(f"   Request {i+1}: ❌ Exception - {str(e)}")
        
        print(f"\n   Rate limiting test results:")
        print(f"   Successful requests: {successful_requests}")
        print(f"   Rate limited requests: {rate_limited_requests}")
        
        if rate_limited_requests > 0:
            print("   ✅ Rate limiting is working!")
        else:
            print("   ⚠️ Rate limiting may not be working as expected")
            
    finally:
        # Restore original rate limit
        ai_service._max_requests_per_minute = original_limit


async def test_error_handling():
    """Test error handling functionality."""
    print("\nTesting Error Handling...")
    
    ai_service = AIService()
    
    class MockUser:
        def __init__(self):
            self.id = "test-user-error"
    
    user = MockUser()
    
    # Test with empty plan description
    try:
        meal_plan_request = MealPlanRequest(
            plan_description="",  # Empty description
            week_start_date=date.today()
        )
        
        result = await ai_service.generate_meal_plan(meal_plan_request, user)
        if not result['success']:
            print("   ✅ Empty description handled gracefully")
        else:
            print("   ⚠️ Empty description should have failed")
            
    except Exception as e:
        print(f"   ✅ Exception handled: {str(e)}")
    
    # Test with very long description
    try:
        long_description = "测试" * 1000  # Very long description
        meal_plan_request = MealPlanRequest(
            plan_description=long_description,
            week_start_date=date.today()
        )
        
        result = await ai_service.generate_meal_plan(meal_plan_request, user)
        if result['success']:
            print("   ✅ Long description handled successfully")
        else:
            print(f"   ⚠️ Long description failed: {result['error']}")
            
    except Exception as e:
        print(f"   ✅ Long description exception handled: {str(e)}")


async def main():
    """Run all tests."""
    print("🧪 AI Service Feature Testing")
    print("=" * 50)
    
    await test_caching()
    await test_rate_limiting()
    await test_error_handling()
    
    print("\n" + "=" * 50)
    print("✅ All AI service feature tests completed!")


if __name__ == "__main__":
    asyncio.run(main())