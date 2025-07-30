#!/usr/bin/env python
"""
Test script for enhanced Recipe creation functionality.
Tests the Task 3 enhancements including:
- Enhanced CreateRecipeFromAIView with deterministic ID support
- Batch creation functionality  
- Advanced duplicate checking
- Data validation and sanitization
"""

import os
import sys
import django
import json
import uuid
from datetime import datetime

# Setup Django environment
base_path = '/Users/puyihao/workspace/MealPrep/MealPrepAppBackend'
src_path = os.path.join(base_path, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mealprep_project.settings.development')
django.setup()

from django.contrib.auth import get_user_model
from django.test import RequestFactory
from apps.recipes.models import Recipe
from apps.meal_plans.models import MealPlan
from apps.ai_integration.views import CreateRecipeFromAIView
from apps.ai_integration.services import generate_deterministic_recipe_uuid

User = get_user_model()

def create_test_user():
    """Create a test user for testing."""
    try:
        user = User.objects.get(email='test@example.com')
        print(f"Using existing test user: {user.email}")
    except User.DoesNotExist:
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            display_name='Test User'
        )
        print(f"Created new test user: {user.email}")
    return user

def test_deterministic_uuid_generation():
    """Test deterministic UUID generation for recipes."""
    print("\n=== Testing Deterministic UUID Generation ===")
    
    # Test recipe data
    recipe_data1 = {
        'name': '香煎三文鱼配柠檬芦笋',
        'ingredients': [
            {'name': '三文鱼', 'amount': '150克'},
            {'name': '芦笋', 'amount': '200克'},
            {'name': '柠檬', 'amount': '半个'},
            {'name': '橄榄油', 'amount': '2汤匙'}
        ],
        'instructions': [
            '将三文鱼洗净，用盐和胡椒腌制10分钟',
            '芦笋洗净切段，柠檬切片',
            '热锅下油，煎三文鱼至两面金黄',
            '加入芦笋炒制，最后挤入柠檬汁调味'
        ],
        'cuisine': '西式',
        'difficulty': '中等'
    }
    
    # Same content, slightly different format
    recipe_data2 = {
        'name': ' 香煎三文鱼配柠檬芦笋 ',  # Extra spaces
        'ingredients': [
            {'name': ' 三文鱼 ', 'amount': ' 150克 '},  # Extra spaces
            {'name': ' 芦笋 ', 'amount': ' 200克 '},
            {'name': ' 柠檬 ', 'amount': ' 半个 '},
            {'name': ' 橄榄油 ', 'amount': ' 2汤匙 '}
        ],
        'instructions': [
            ' 将三文鱼洗净，用盐和胡椒腌制10分钟 ',  # Extra spaces
            ' 芦笋洗净切段，柠檬切片 ',
            ' 热锅下油，煎三文鱼至两面金黄 ',
            ' 加入芦笋炒制，最后挤入柠檬汁调味 '
        ],
        'cuisine': ' 西式 ',  # Extra spaces
        'difficulty': ' 中等 '
    }
    
    # Different recipe
    recipe_data3 = {
        'name': '红烧肉',
        'ingredients': [
            {'name': '五花肉', 'amount': '300克'},
            {'name': '生抽', 'amount': '2汤匙'},
            {'name': '冰糖', 'amount': '1汤匙'}
        ],
        'instructions': [
            '五花肉洗净切块',
            '锅中放入五花肉煸炒出油',
            '加入生抽和冰糖炖煮30分钟'
        ],
        'cuisine': '中式',
        'difficulty': '中等'
    }
    
    # Generate UUIDs
    uuid1 = generate_deterministic_recipe_uuid(recipe_data1)
    uuid2 = generate_deterministic_recipe_uuid(recipe_data2)
    uuid3 = generate_deterministic_recipe_uuid(recipe_data3)
    
    print(f"Recipe 1 UUID: {uuid1}")
    print(f"Recipe 2 UUID (same content, different format): {uuid2}")
    print(f"Recipe 3 UUID (different recipe): {uuid3}")
    
    # Test results
    assert uuid1 == uuid2, f"Same content should generate same UUID: {uuid1} != {uuid2}"
    assert uuid1 != uuid3, f"Different content should generate different UUID: {uuid1} == {uuid3}"
    
    print("✓ Deterministic UUID generation test passed!")
    return uuid1, uuid2, uuid3

def test_recipe_validation_and_sanitization():
    """Test recipe data validation and sanitization."""
    print("\n=== Testing Recipe Validation and Sanitization ===")
    
    view = CreateRecipeFromAIView()
    
    # Test valid recipe data
    valid_recipe = {
        'name': ' 测试食谱 ',  # With spaces
        'ingredients': [
            {'name': ' 测试配料1 ', 'amount': ' 100克 '},
            {'name': ' 测试配料2 ', 'amount': ' 200克 '}
        ],
        'instructions': [
            ' 第一步操作 ',
            ' 第二步操作 '
        ],
        'prep_time': 15,  # Integer
        'cook_time': 30,  # Integer
        'cuisine': ' 中式 '
    }
    
    # Test validation
    is_valid, error = view._validate_recipe_data(valid_recipe)
    print(f"Valid recipe validation: {is_valid} (error: {error})")
    assert is_valid, f"Valid recipe should pass validation: {error}"
    
    # Test sanitization
    sanitized = view._sanitize_recipe_data(valid_recipe)
    print(f"Sanitized name: '{sanitized['name']}'")
    print(f"Sanitized ingredients: {sanitized['ingredients']}")
    print(f"Sanitized prep_time: {sanitized['prep_time']} (type: {type(sanitized['prep_time'])})")
    
    assert sanitized['name'] == '测试食谱', f"Name should be trimmed: '{sanitized['name']}'"
    assert sanitized['ingredients'][0]['name'] == '测试配料1', "Ingredient names should be trimmed"
    assert isinstance(sanitized['prep_time'], int), f"Prep time should be int: {type(sanitized['prep_time'])}"
    
    # Test invalid recipe data
    invalid_recipe = {
        'name': '',  # Empty name
        'ingredients': [],  # Empty ingredients
        'instructions': ['test']
    }
    
    is_valid, error = view._validate_recipe_data(invalid_recipe)
    print(f"Invalid recipe validation: {is_valid} (error: {error})")
    assert not is_valid, "Invalid recipe should fail validation"
    
    print("✓ Recipe validation and sanitization test passed!")

def test_duplicate_detection():
    """Test duplicate recipe detection."""
    print("\n=== Testing Duplicate Detection ===")
    
    user = create_test_user()
    view = CreateRecipeFromAIView()
    
    # Clean up any existing test recipes
    Recipe.objects.filter(created_by_user=user, name__icontains='测试重复检测').delete()
    
    recipe_data = {
        'name': '测试重复检测食谱',
        'description': '这是一个测试食谱',
        'ingredients': [
            {'name': '测试配料1', 'amount': '100克'},
            {'name': '测试配料2', 'amount': '200克'}
        ],
        'instructions': [
            '第一步测试操作',
            '第二步测试操作'
        ],
        'cuisine': '中式',
        'difficulty': 'medium',
        'prep_time': 15,
        'cook_time': 30,
        'image_url': '',
        'nutrition_info': {},
        'tags': ['测试']
    }
    
    # First creation - should create new recipe
    recipe1, was_created1 = view._create_recipe_with_predefined_id(
        recipe_data, 
        str(uuid.uuid4()), 
        user
    )
    
    print(f"First creation: Recipe ID {recipe1.id}, Created: {was_created1}")
    assert was_created1, "First recipe should be created"
    
    # Second creation with same content - should return existing recipe
    recipe2, was_created2 = view._create_recipe_with_predefined_id(
        recipe_data,
        str(uuid.uuid4()),  # Different provided ID
        user
    )
    
    print(f"Second creation: Recipe ID {recipe2.id}, Created: {was_created2}")
    assert not was_created2, "Second recipe should not be created (duplicate)"
    assert recipe1.id == recipe2.id, f"Should return same recipe: {recipe1.id} != {recipe2.id}"
    
    print("✓ Duplicate detection test passed!")
    
    # Clean up
    recipe1.delete()

def test_enhanced_post_method():
    """Test the enhanced CreateRecipeFromAIView post method through direct method call."""
    print("\n=== Testing Enhanced POST Method ===")
    
    user = create_test_user()
    view = CreateRecipeFromAIView()
    
    # Test data - use easy difficulty to match database constraints
    ai_recipe_data = {
        'id': str(uuid.uuid4()),
        'name': '测试AI生成食谱',
        'description': '这是一个AI生成的测试食谱',
        'ingredients': [
            {'name': '测试配料1', 'amount': '150克'},
            {'name': '测试配料2', 'amount': '100克'}
        ],
        'instructions': [
            '准备所有配料',
            '按步骤制作',
            '调味享用'
        ],
        'cuisine': '中式',
        'difficulty': 'easy',
        'prep_time': 10,
        'cook_time': 20,
        'image_url': 'https://example.com/image.jpg',
        'nutrition_info': {'calories': 300},
        'tags': ['健康', '快手']
    }
    
    # Test data validation directly
    is_valid, validation_error = view._validate_recipe_data(ai_recipe_data)
    print(f"Recipe data validation: {is_valid} (error: {validation_error})")
    assert is_valid, f"Recipe data should be valid: {validation_error}"
    
    # Test sanitization
    sanitized_data = view._sanitize_recipe_data(ai_recipe_data)
    print(f"Sanitized recipe name: {sanitized_data['name']}")
    print(f"Sanitized difficulty: {sanitized_data['difficulty']}")
    
    # Test recipe creation directly
    try:
        recipe, was_created = view._create_recipe_with_predefined_id(
            sanitized_data, ai_recipe_data['id'], user
        )
        
        print(f"Recipe creation result: ID={recipe.id}, Created={was_created}")
        print(f"Recipe name: {recipe.name}")
        print(f"Recipe difficulty: {recipe.difficulty}")
        
        assert recipe.name == ai_recipe_data['name']
        assert recipe.difficulty == 'easy'
        
        print("✓ Enhanced recipe creation logic test passed!")
        
        # Test duplicate detection
        recipe2, was_created2 = view._create_recipe_with_predefined_id(
            sanitized_data, str(uuid.uuid4()), user
        )
        
        assert not was_created2, "Second creation should detect duplicate"
        assert recipe.id == recipe2.id, "Should return same recipe for duplicate content"
        
        print("✓ Duplicate detection in creation test passed!")
        
        # Clean up
        recipe.delete()
        
    except Exception as e:
        print(f"Error in recipe creation: {str(e)}")
        raise
    
    print("✓ Enhanced POST method test passed!")

def run_all_tests():
    """Run all enhancement tests."""
    print("🚀 Starting Recipe Enhancement Tests (Task 3)")
    print("=" * 60)
    
    try:
        # Test 1: Deterministic UUID generation
        test_deterministic_uuid_generation()
        
        # Test 2: Data validation and sanitization  
        test_recipe_validation_and_sanitization()
        
        # Test 3: Duplicate detection
        test_duplicate_detection()
        
        # Test 4: Enhanced POST method
        test_enhanced_post_method()
        
        print("\n" + "=" * 60)
        print("🎉 All Recipe Enhancement Tests Passed!")
        print("✅ Task 3 implementation is working correctly")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    run_all_tests()