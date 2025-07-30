#!/usr/bin/env python
"""
Test script to verify Django serializers are working correctly.
"""
import os
import sys
import django
from django.conf import settings

# Add the src directory to Python path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(BASE_DIR, 'src')
sys.path.insert(0, SRC_DIR)

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mealprep_project.settings.development')
django.setup()

from apps.authentication.serializers import UserSerializer, DietaryPreferencesSerializer
from apps.recipes.serializers import RecipeSerializer, IngredientSerializer, NutritionInfoSerializer
from apps.meal_plans.serializers import MealPlanSerializer, MealPlanItemSerializer
from apps.favorites.serializers import FavoriteSerializer, CollectionSerializer


def test_dietary_preferences_serializer():
    """Test DietaryPreferencesSerializer."""
    print("Testing DietaryPreferencesSerializer...")
    
    data = {
        'allergies': ['nuts', 'dairy'],
        'diet_type': 'vegetarian',
        'dislikes': ['mushrooms'],
        'calorie_target': 2000
    }
    
    serializer = DietaryPreferencesSerializer(data=data)
    assert serializer.is_valid(), f"Validation errors: {serializer.errors}"
    print("✓ DietaryPreferencesSerializer validation passed")


def test_user_serializer():
    """Test UserSerializer."""
    print("Testing UserSerializer...")
    
    data = {
        'username': 'testuser',
        'email': 'test@example.com',
        'display_name': 'Test User',
        'dietary_preferences': {
            'allergies': ['nuts'],
            'diet_type': 'vegetarian'
        }
    }
    
    serializer = UserSerializer(data=data)
    assert serializer.is_valid(), f"Validation errors: {serializer.errors}"
    print("✓ UserSerializer validation passed")


def test_ingredient_serializer():
    """Test IngredientSerializer."""
    print("Testing IngredientSerializer...")
    
    data = {
        'name': 'Chicken breast',
        'amount': 1.5,
        'unit': 'lbs',
        'notes': 'Boneless, skinless'
    }
    
    serializer = IngredientSerializer(data=data)
    assert serializer.is_valid(), f"Validation errors: {serializer.errors}"
    print("✓ IngredientSerializer validation passed")


def test_nutrition_info_serializer():
    """Test NutritionInfoSerializer."""
    print("Testing NutritionInfoSerializer...")
    
    data = {
        'calories': 250.5,
        'protein': 30.2,
        'carbs': 15.0,
        'fat': 8.5
    }
    
    serializer = NutritionInfoSerializer(data=data)
    assert serializer.is_valid(), f"Validation errors: {serializer.errors}"
    print("✓ NutritionInfoSerializer validation passed")


def test_recipe_serializer():
    """Test RecipeSerializer."""
    print("Testing RecipeSerializer...")
    
    data = {
        'name': 'Grilled Chicken',
        'description': 'Simple grilled chicken breast',
        'ingredients': [
            {
                'name': 'Chicken breast',
                'amount': 1.5,
                'unit': 'lbs'
            }
        ],
        'instructions': 'Grill the chicken until cooked through.',
        'nutrition_info': {
            'calories': 250,
            'protein': 30
        },
        'cuisine': 'American',
        'prep_time': 10,
        'cook_time': 15,
        'difficulty': 'easy',
        'tags': ['healthy', 'protein']
    }
    
    serializer = RecipeSerializer(data=data)
    assert serializer.is_valid(), f"Validation errors: {serializer.errors}"
    print("✓ RecipeSerializer validation passed")


def test_validation_errors():
    """Test validation error handling."""
    print("Testing validation error handling...")
    
    # Test invalid user data
    invalid_user_data = {
        'username': 'ab',  # Too short
        'email': 'invalid-email',  # Invalid format
    }
    
    serializer = UserSerializer(data=invalid_user_data)
    assert not serializer.is_valid(), "Should have validation errors"
    assert 'username' in serializer.errors
    print("✓ User validation errors handled correctly")
    
    # Test invalid recipe data
    invalid_recipe_data = {
        'name': '',  # Empty name
        'ingredients': [],  # No ingredients
        'instructions': '',  # Empty instructions
        'prep_time': -5,  # Negative time
        'difficulty': 'invalid'  # Invalid difficulty
    }
    
    serializer = RecipeSerializer(data=invalid_recipe_data)
    assert not serializer.is_valid(), "Should have validation errors"
    assert 'name' in serializer.errors
    assert 'ingredients' in serializer.errors
    assert 'instructions' in serializer.errors
    print("✓ Recipe validation errors handled correctly")


def main():
    """Run all tests."""
    print("Running Django serializer tests...\n")
    
    try:
        test_dietary_preferences_serializer()
        test_user_serializer()
        test_ingredient_serializer()
        test_nutrition_info_serializer()
        test_recipe_serializer()
        test_validation_errors()
        
        print("\n✅ All serializer tests passed!")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()