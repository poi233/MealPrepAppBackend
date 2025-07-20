#!/usr/bin/env python
"""
Test script for AI integration functionality.
"""
import os
import sys
import django
import asyncio
from datetime import date

# Add the src directory to the Python path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(BASE_DIR, 'src')
sys.path.insert(0, SRC_DIR)

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mealprep_project.settings.development')
django.setup()

from apps.ai_integration.services import AIService, MealPlanRequest, RecipeGenerationRequest


async def test_ai_service():
    """Test the AI service functionality."""
    print("Testing AI Service Integration...")
    
    # Create AI service instance
    ai_service = AIService()
    
    # Create a mock user object
    class MockUser:
        def __init__(self):
            self.id = "test-user-123"
    
    user = MockUser()
    
    try:
        # Test meal plan generation
        print("\n1. Testing meal plan generation...")
        meal_plan_request = MealPlanRequest(
            plan_description="我想要一个健康的素食膳食计划，包含丰富的蛋白质和蔬菜",
            dietary_preferences={"dietType": "vegetarian"},
            week_start_date=date.today()
        )
        
        result = await ai_service.generate_meal_plan(meal_plan_request, user)
        
        if result['success']:
            print("✅ Meal plan generation successful!")
            meal_plan = result['meal_plan']
            print(f"   Plan name: {meal_plan['name']}")
            print(f"   Daily meals count: {len(meal_plan['daily_meals'])}")
            
            # Check if we have meals for each day
            for day_meal in meal_plan['daily_meals'][:2]:  # Show first 2 days
                print(f"   {day_meal.get('day', 'Unknown day')}:")
                for meal_type in ['breakfast', 'lunch', 'dinner']:
                    meals = day_meal.get(meal_type, [])
                    print(f"     {meal_type}: {len(meals)} recipes")
                    if meals:
                        print(f"       Example: {meals[0].get('recipeName', 'No name')}")
        else:
            print(f"❌ Meal plan generation failed: {result['error']}")
        
        # Test recipe details generation
        print("\n2. Testing recipe details generation...")
        recipe_request = RecipeGenerationRequest(
            name="素食炒面",
            cuisine="Chinese",
            difficulty="medium",
            meal_type="lunch"
        )
        
        result = await ai_service.generate_recipe_details(recipe_request, user)
        
        if result['success']:
            print("✅ Recipe details generation successful!")
            recipe = result['recipe']
            print(f"   Recipe name: {recipe['name']}")
            print(f"   Ingredients count: {len(recipe['ingredients'])}")
            print(f"   Instructions length: {len(recipe['instructions'])} characters")
            if recipe['ingredients']:
                print(f"   Example ingredient: {recipe['ingredients'][0]}")
        else:
            print(f"❌ Recipe details generation failed: {result['error']}")
        
        print("\n✅ AI Service integration test completed successfully!")
        
    except Exception as e:
        print(f"❌ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_ai_service())