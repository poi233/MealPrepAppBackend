#!/usr/bin/env python3
"""
Test script to verify AI meal plan generation optimization.
This script tests the new two-step process:
1. Generate simplified meal plan with recipe names only
2. Generate detailed recipes for each name
"""

import os
import sys
import django
from datetime import date

# Add the project root to Python path
sys.path.insert(0, '/Users/puyihao/workspace/MealPrep/MealPrepAppBackend/src')

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.ai_integration.services import AIService, MealPlanRequest
from django.contrib.auth import get_user_model

async def test_optimized_meal_plan():
    """Test the optimized meal plan generation."""
    print("🧪 Testing optimized AI meal plan generation...")
    
    # Create AI service instance
    ai_service = AIService()
    
    # Get or create a test user
    User = get_user_model()
    user, created = User.objects.get_or_create(
        username='test_user',
        defaults={'email': 'test@example.com'}
    )
    
    # Create a meal plan request
    request = MealPlanRequest(
        plan_description="健康的一周素食菜单，包含丰富的蛋白质和维生素",
        dietary_preferences={'dietType': 'vegetarian'},
        allergies=['坚果'],
        calorie_target=1800,
        week_start_date=date.today()
    )
    
    print(f"📝 Request: {request.plan_description}")
    print(f"🥗 Diet type: {request.dietary_preferences}")
    print(f"⚠️  Allergies: {request.allergies}")
    print(f"🎯 Calorie target: {request.calorie_target}")
    
    try:
        # Test the optimized meal plan generation
        result = await ai_service.generate_meal_plan(request, user)
        
        if result.get('success'):
            meal_plan = result['meal_plan']
            daily_meals = meal_plan['daily_meals']
            
            print(f"✅ Successfully generated meal plan!")
            print(f"📅 Week start: {meal_plan['week_start_date']}")
            print(f"📊 Total days: {len(daily_meals)}")
            
            # Check each day
            for i, day_data in enumerate(daily_meals):
                day_name = day_data['day']
                print(f"\n📆 {day_name}:")
                
                for meal_type in ['breakfast', 'lunch', 'dinner']:
                    recipes = day_data.get(meal_type, [])
                    print(f"  🍽️  {meal_type.title()}: {len(recipes)} recipe(s)")
                    
                    for recipe in recipes:
                        print(f"    - {recipe['name']} ({recipe['cuisine']})")
                        print(f"      ⏱️  Prep: {recipe['prep_time']}min, Cook: {recipe['cook_time']}min")
                        print(f"      🔧 Difficulty: {recipe['difficulty']}")
                        print(f"      🍳 Ingredients: {len(recipe['ingredients'])} items")
                        print(f"      📝 Instructions: {len(recipe['instructions'])} steps")
                        if recipe.get('image_url'):
                            print(f"      🖼️  Image: Available")
                        
                        # Show a few ingredients
                        if recipe['ingredients'][:2]:
                            print(f"      🥕 Sample ingredients: {', '.join([f\"{ing['name']} ({ing['amount']})\" for ing in recipe['ingredients'][:2]])}")
            
            print(f"\n🎉 Test completed successfully!")
            print(f"📈 Total recipes generated: {sum(len(day_data.get(meal_type, [])) for day_data in daily_meals for meal_type in ['breakfast', 'lunch', 'dinner'])}")
            
        else:
            print(f"❌ Failed to generate meal plan: {result.get('error')}")
            
    except Exception as e:
        print(f"💥 Error during testing: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_optimized_meal_plan())