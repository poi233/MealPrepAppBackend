#!/usr/bin/env python
"""
Test script for AI meal plan analysis functionality.
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

from apps.ai_integration.services import AIService


async def test_meal_plan_analysis():
    """Test the meal plan analysis functionality."""
    print("Testing AI Meal Plan Analysis...")
    
    # Create AI service instance
    ai_service = AIService()
    
    # Create a mock meal plan object
    class MockRecipe:
        def __init__(self, name, ingredients, instructions):
            self.name = name
            self.ingredients = ingredients
            self.instructions = instructions
    
    class MockMealPlanItem:
        def __init__(self, recipe, day_of_week, meal_type):
            self.recipe = recipe
            self.day_of_week = day_of_week
            self.meal_type = meal_type
    
    class MockMealPlan:
        def __init__(self):
            self.id = "test-meal-plan-123"
            # Create some mock meal plan items
            recipes = [
                MockRecipe("燕麦粥", ["燕麦片", "牛奶", "香蕉"], "煮燕麦粥的步骤"),
                MockRecipe("蔬菜沙拉", ["生菜", "番茄", "黄瓜"], "制作沙拉的步骤"),
                MockRecipe("烤鸡胸肉", ["鸡胸肉", "橄榄油", "香料"], "烤鸡胸肉的步骤"),
                MockRecipe("素食炒面", ["面条", "蔬菜", "豆腐"], "炒面的步骤"),
            ]
            
            self.mock_items = [
                MockMealPlanItem(recipes[0], 0, "breakfast"),  # Monday breakfast
                MockMealPlanItem(recipes[1], 0, "lunch"),      # Monday lunch
                MockMealPlanItem(recipes[2], 0, "dinner"),     # Monday dinner
                MockMealPlanItem(recipes[3], 1, "lunch"),      # Tuesday lunch
            ]
        
        @property
        def items(self):
            class MockManager:
                def __init__(self, items):
                    self.mock_items = items
                
                def all(self):
                    return self.mock_items
                
                def count(self):
                    return len(self.mock_items)
            
            return MockManager(self.mock_items)
    
    meal_plan = MockMealPlan()
    plan_description = "我想要一个健康均衡的膳食计划，包含蛋白质和蔬菜"
    
    try:
        print("\nTesting meal plan analysis...")
        result = await ai_service.analyze_meal_plan(meal_plan, plan_description, 'full')
        
        if result['success']:
            print("✅ Meal plan analysis successful!")
            analysis = result['analysis']
            print(f"   Meal plan ID: {analysis['meal_plan_id']}")
            print(f"   Total recipes: {analysis['total_recipes']}")
            print(f"   Analysis type: {analysis['analysis_type']}")
            print(f"   Analysis text length: {len(analysis['analysis_text'])} characters")
            print(f"   Analysis preview: {analysis['analysis_text'][:200]}...")
        else:
            print(f"❌ Meal plan analysis failed: {result['error']}")
        
        print("\n✅ AI meal plan analysis test completed successfully!")
        
    except Exception as e:
        print(f"❌ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_meal_plan_analysis())