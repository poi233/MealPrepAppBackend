#!/usr/bin/env python
"""
Test script to verify Django serializer validation matches Next.js API validation patterns.
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

from apps.authentication.serializers import UserSerializer
from apps.recipes.serializers import RecipeSerializer
from apps.meal_plans.serializers import MealPlanSerializer
from apps.favorites.serializers import FavoriteSerializer, CollectionSerializer


def test_recipe_validation_compatibility():
    """Test recipe validation matches Next.js patterns."""
    print("Testing recipe validation compatibility...")
    
    # Test ingredient validation (matching Next.js patterns)
    invalid_ingredients_cases = [
        # Empty ingredients array
        [],
        # Too many ingredients
        [{'name': f'ingredient{i}', 'amount': 1, 'unit': 'cup'} for i in range(51)],
        # Invalid ingredient structure
        [{'name': '', 'amount': 1, 'unit': 'cup'}],  # Empty name
        [{'name': 'test', 'amount': -1, 'unit': 'cup'}],  # Negative amount
        [{'name': 'test', 'amount': 1, 'unit': ''}],  # Empty unit
    ]
    
    for i, ingredients in enumerate(invalid_ingredients_cases):
        data = {
            'name': 'Test Recipe',
            'ingredients': ingredients,
            'instructions': 'Test instructions',
            'prep_time': 10,
            'cook_time': 15,
            'difficulty': 'easy'
        }
        
        serializer = RecipeSerializer(data=data)
        assert not serializer.is_valid(), f"Case {i}: Should have validation errors for ingredients"
    
    # Test valid ingredients
    valid_data = {
        'name': 'Test Recipe',
        'ingredients': [
            {'name': 'Chicken breast', 'amount': 1.5, 'unit': 'lbs', 'notes': 'Boneless'},
            {'name': 'Salt', 'amount': 0.5, 'unit': 'tsp'}
        ],
        'instructions': 'Cook the chicken with salt.',
        'prep_time': 10,
        'cook_time': 15,
        'difficulty': 'easy'
    }
    
    serializer = RecipeSerializer(data=valid_data)
    assert serializer.is_valid(), f"Valid recipe should pass: {serializer.errors}"
    
    print("✓ Recipe ingredient validation compatibility verified")


def test_time_validation_compatibility():
    """Test time validation matches Next.js patterns."""
    print("Testing time validation compatibility...")
    
    # Test invalid times (matching Next.js validation)
    invalid_time_cases = [
        {'prep_time': -1, 'cook_time': 10},  # Negative prep time
        {'prep_time': 10, 'cook_time': -1},  # Negative cook time
        {'prep_time': 1500, 'cook_time': 10},  # Too long prep time (>24 hours)
        {'prep_time': 10, 'cook_time': 1500},  # Too long cook time (>24 hours)
    ]
    
    for i, times in enumerate(invalid_time_cases):
        data = {
            'name': 'Test Recipe',
            'ingredients': [{'name': 'test', 'amount': 1, 'unit': 'cup'}],
            'instructions': 'Test instructions',
            'difficulty': 'easy',
            **times
        }
        
        serializer = RecipeSerializer(data=data)
        assert not serializer.is_valid(), f"Case {i}: Should have validation errors for times"
    
    print("✓ Time validation compatibility verified")


def test_difficulty_validation_compatibility():
    """Test difficulty validation matches Next.js patterns."""
    print("Testing difficulty validation compatibility...")
    
    # Test valid difficulties
    valid_difficulties = ['easy', 'medium', 'hard']
    for difficulty in valid_difficulties:
        data = {
            'name': 'Test Recipe',
            'ingredients': [{'name': 'test', 'amount': 1, 'unit': 'cup'}],
            'instructions': 'Test instructions',
            'prep_time': 10,
            'cook_time': 15,
            'difficulty': difficulty
        }
        
        serializer = RecipeSerializer(data=data)
        assert serializer.is_valid(), f"Difficulty '{difficulty}' should be valid: {serializer.errors}"
    
    # Test invalid difficulty
    data = {
        'name': 'Test Recipe',
        'ingredients': [{'name': 'test', 'amount': 1, 'unit': 'cup'}],
        'instructions': 'Test instructions',
        'prep_time': 10,
        'cook_time': 15,
        'difficulty': 'invalid'
    }
    
    serializer = RecipeSerializer(data=data)
    assert not serializer.is_valid(), "Invalid difficulty should fail validation"
    
    print("✓ Difficulty validation compatibility verified")


def test_tags_validation_compatibility():
    """Test tags validation matches Next.js patterns."""
    print("Testing tags validation compatibility...")
    
    # Test valid tags
    valid_tags_data = {
        'name': 'Test Recipe',
        'ingredients': [{'name': 'test', 'amount': 1, 'unit': 'cup'}],
        'instructions': 'Test instructions',
        'prep_time': 10,
        'cook_time': 15,
        'difficulty': 'easy',
        'tags': ['healthy', 'quick', 'protein']
    }
    
    serializer = RecipeSerializer(data=valid_tags_data)
    assert serializer.is_valid(), f"Valid tags should pass: {serializer.errors}"
    
    # Test too many tags
    too_many_tags_data = {
        'name': 'Test Recipe',
        'ingredients': [{'name': 'test', 'amount': 1, 'unit': 'cup'}],
        'instructions': 'Test instructions',
        'prep_time': 10,
        'cook_time': 15,
        'difficulty': 'easy',
        'tags': [f'tag{i}' for i in range(21)]  # 21 tags (max is 20)
    }
    
    serializer = RecipeSerializer(data=too_many_tags_data)
    assert not serializer.is_valid(), "Too many tags should fail validation"
    
    print("✓ Tags validation compatibility verified")


def test_nutrition_validation_compatibility():
    """Test nutrition validation matches Next.js patterns."""
    print("Testing nutrition validation compatibility...")
    
    # Test valid nutrition info
    valid_nutrition_data = {
        'name': 'Test Recipe',
        'ingredients': [{'name': 'test', 'amount': 1, 'unit': 'cup'}],
        'instructions': 'Test instructions',
        'prep_time': 10,
        'cook_time': 15,
        'difficulty': 'easy',
        'nutrition_info': {
            'calories': 250.5,
            'protein': 30.2,
            'carbs': 15.0,
            'fat': 8.5,
            'fiber': 3.2,
            'sugar': 5.1,
            'sodium': 400.0
        }
    }
    
    serializer = RecipeSerializer(data=valid_nutrition_data)
    assert serializer.is_valid(), f"Valid nutrition info should pass: {serializer.errors}"
    
    # Test negative nutrition values
    negative_nutrition_data = {
        'name': 'Test Recipe',
        'ingredients': [{'name': 'test', 'amount': 1, 'unit': 'cup'}],
        'instructions': 'Test instructions',
        'prep_time': 10,
        'cook_time': 15,
        'difficulty': 'easy',
        'nutrition_info': {
            'calories': -100  # Negative calories
        }
    }
    
    serializer = RecipeSerializer(data=negative_nutrition_data)
    assert not serializer.is_valid(), "Negative nutrition values should fail validation"
    
    print("✓ Nutrition validation compatibility verified")


def test_user_validation_compatibility():
    """Test user validation matches Next.js patterns."""
    print("Testing user validation compatibility...")
    
    import uuid
    unique_id = str(uuid.uuid4())[:8]
    
    # Test valid user data
    valid_user_data = {
        'username': f'testuser_{unique_id}',
        'email': f'test_{unique_id}@example.com',
        'display_name': 'Test User',
        'dietary_preferences': {
            'allergies': ['nuts', 'dairy'],
            'diet_type': 'vegetarian',
            'dislikes': ['mushrooms'],
            'calorie_target': 2000
        }
    }
    
    serializer = UserSerializer(data=valid_user_data)
    assert serializer.is_valid(), f"Valid user data should pass: {serializer.errors}"
    
    # Test invalid username (too short)
    invalid_username_data = {
        'username': 'ab',  # Too short
        'email': f'test_short_{unique_id}@example.com'
    }
    
    serializer = UserSerializer(data=invalid_username_data)
    assert not serializer.is_valid(), "Short username should fail validation"
    assert 'username' in serializer.errors
    
    # Test invalid email
    invalid_email_data = {
        'username': f'testuser_invalid_{unique_id}',
        'email': 'invalid-email'  # Invalid format
    }
    
    serializer = UserSerializer(data=invalid_email_data)
    assert not serializer.is_valid(), "Invalid email should fail validation"
    
    print("✓ User validation compatibility verified")


def test_dietary_preferences_validation():
    """Test dietary preferences validation."""
    print("Testing dietary preferences validation...")
    
    import uuid
    unique_id = str(uuid.uuid4())[:8]
    
    # Test valid dietary preferences
    valid_prefs = {
        'allergies': ['nuts', 'shellfish'],
        'diet_type': 'vegetarian',
        'dislikes': ['mushrooms', 'olives'],
        'calorie_target': 2000
    }
    
    user_data = {
        'username': f'testuser_prefs_{unique_id}',
        'email': f'test_prefs_{unique_id}@example.com',
        'dietary_preferences': valid_prefs
    }
    
    serializer = UserSerializer(data=user_data)
    assert serializer.is_valid(), f"Valid dietary preferences should pass: {serializer.errors}"
    
    # Test invalid calorie target
    invalid_prefs = {
        'calorie_target': 500  # Too low
    }
    
    user_data = {
        'username': f'testuser_invalid_prefs_{unique_id}',
        'email': f'test_invalid_prefs_{unique_id}@example.com',
        'dietary_preferences': invalid_prefs
    }
    
    serializer = UserSerializer(data=user_data)
    assert not serializer.is_valid(), "Invalid calorie target should fail validation"
    
    print("✓ Dietary preferences validation verified")


def main():
    """Run all compatibility tests."""
    print("Running Django-Next.js validation compatibility tests...\n")
    
    try:
        test_recipe_validation_compatibility()
        test_time_validation_compatibility()
        test_difficulty_validation_compatibility()
        test_tags_validation_compatibility()
        test_nutrition_validation_compatibility()
        test_user_validation_compatibility()
        test_dietary_preferences_validation()
        
        print("\n✅ All validation compatibility tests passed!")
        print("Django serializers match Next.js API validation patterns.")
        
    except Exception as e:
        print(f"\n❌ Compatibility test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()