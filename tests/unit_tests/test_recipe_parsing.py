#!/usr/bin/env python
"""
Test script for recipe JSON parsing fix.
"""
import os
import sys
import django
import asyncio

# Add the src directory to the Python path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(BASE_DIR, 'src')
sys.path.insert(0, SRC_DIR)

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mealprep_project.settings.development')
django.setup()

from apps.ai_integration.services import AIService, RecipeGenerationRequest


async def test_recipe_parsing():
    """Test recipe generation with improved JSON parsing."""
    print("Testing Recipe JSON Parsing Fix...")
    
    ai_service = AIService()
    
    class MockUser:
        def __init__(self):
            self.id = "test-user-parsing"
    
    user = MockUser()
    
    try:
        recipe_request = RecipeGenerationRequest(
            name="宫保鸡丁",
            cuisine="Chinese",
            difficulty="medium",
            meal_type="dinner"
        )
        
        print("Generating recipe details...")
        result = await ai_service.generate_recipe_details(recipe_request, user)
        
        if result['success']:
            print("✅ Recipe generation successful!")
            recipe = result['recipe']
            print(f"   Recipe name: {recipe['name']}")
            print(f"   Ingredients count: {len(recipe['ingredients'])}")
            print(f"   Instructions length: {len(recipe['instructions'])} characters")
            
            # Show first few ingredients
            print("   First 3 ingredients:")
            for i, ingredient in enumerate(recipe['ingredients'][:3]):
                print(f"     {i+1}. {ingredient}")
            
            # Show beginning of instructions
            instructions_preview = recipe['instructions'][:200] + "..." if len(recipe['instructions']) > 200 else recipe['instructions']
            print(f"   Instructions preview: {instructions_preview}")
            
        else:
            print(f"❌ Recipe generation failed: {result['error']}")
        
    except Exception as e:
        print(f"❌ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_recipe_parsing())