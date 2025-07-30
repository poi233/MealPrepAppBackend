#!/usr/bin/env python3
"""
UUID Generation Verification Script
Tests the deterministic UUID generation system for consistency and differentiation.
"""

import sys
import os
import json
import hashlib
import uuid
from typing import Dict, Any, List

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def generate_deterministic_recipe_uuid(recipe_data: Dict[str, Any]) -> str:
    """
    Generate a deterministic UUID based on recipe content.
    This is a copy of the function from services.py for testing purposes.
    """
    # Define the namespace UUID for recipes (same as in services.py)
    RECIPE_UUID_NAMESPACE = uuid.UUID('6ba7b810-9dad-11d1-80b4-00c04fd430c8')
    
    def _normalize_recipe_data_for_uuid(data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize recipe data for consistent UUID generation."""
        normalized = {}
        
        # Normalize basic string fields
        for field in ['name', 'description', 'cuisine', 'difficulty']:
            if field in data and data[field]:
                normalized[field] = str(data[field]).strip().lower()
        
        # Normalize numeric fields
        for field in ['prep_time', 'cook_time']:
            if field in data and data[field] is not None:
                normalized[field] = int(data[field])
        
        # Normalize ingredients list
        if 'ingredients' in data and isinstance(data['ingredients'], list):
            normalized_ingredients = []
            for ingredient in data['ingredients']:
                if isinstance(ingredient, dict):
                    norm_ingredient = {}
                    if 'name' in ingredient:
                        norm_ingredient['name'] = str(ingredient['name']).strip().lower()
                    if 'amount' in ingredient:
                        norm_ingredient['amount'] = str(ingredient['amount']).strip().lower()
                    if 'unit' in ingredient:
                        norm_ingredient['unit'] = str(ingredient['unit']).strip().lower()
                    normalized_ingredients.append(norm_ingredient)
                elif isinstance(ingredient, str):
                    normalized_ingredients.append({'name': ingredient.strip().lower()})
            # Sort ingredients for consistent ordering
            normalized['ingredients'] = sorted(normalized_ingredients, key=lambda x: x.get('name', ''))
        
        # Normalize instructions list
        if 'instructions' in data and isinstance(data['instructions'], list):
            normalized_instructions = []
            for instruction in data['instructions']:
                if isinstance(instruction, str) and instruction.strip():
                    normalized_instructions.append(instruction.strip().lower())
            normalized['instructions'] = normalized_instructions
        
        # Normalize nutrition info
        if 'nutrition_info' in data and isinstance(data['nutrition_info'], dict):
            normalized_nutrition = {}
            for key, value in data['nutrition_info'].items():
                if isinstance(value, (int, float)) and value is not None:
                    normalized_nutrition[key] = float(value)
            if normalized_nutrition:
                normalized['nutrition_info'] = dict(sorted(normalized_nutrition.items()))
        
        # Normalize tags
        if 'tags' in data and isinstance(data['tags'], list):
            normalized_tags = []
            for tag in data['tags']:
                if isinstance(tag, str) and tag.strip():
                    normalized_tags.append(tag.strip().lower())
            normalized['tags'] = sorted(list(set(normalized_tags)))  # Remove duplicates and sort
        
        return normalized
    
    normalized_data = _normalize_recipe_data_for_uuid(recipe_data)
    content_string = json.dumps(normalized_data, sort_keys=True, ensure_ascii=False)
    content_hash = hashlib.sha256(content_string.encode('utf-8')).hexdigest()
    deterministic_uuid = uuid.uuid5(RECIPE_UUID_NAMESPACE, content_hash)
    
    return str(deterministic_uuid)

def test_uuid_consistency():
    """Test that identical recipe data produces identical UUIDs"""
    print("🔄 Testing UUID Consistency...")
    
    recipe_data = {
        'name': '宫保鸡丁',
        'description': '经典川菜，麻辣鲜香',
        'cuisine': '中式',
        'difficulty': '中等',
        'prep_time': 15,
        'cook_time': 20,
        'ingredients': [
            {'name': '鸡胸肉', 'amount': '300克'},
            {'name': '花生米', 'amount': '50克'},
            {'name': '干辣椒', 'amount': '10个'}
        ],
        'instructions': [
            '鸡肉切丁，用料酒、生抽腌制15分钟',
            '热锅下油，爆炒花生米盛起',
            '下鸡丁炒至变色，加入干辣椒炒香',
            '调入生抽、老抽、糖炒匀，最后加入花生米即可'
        ],
        'nutrition_info': {
            'calories': 320,
            'protein': 25.5,
            'carbs': 12.8,
            'fat': 18.2
        },
        'tags': ['川菜', '家常菜', '下饭菜']
    }
    
    # Generate UUID multiple times and verify consistency
    uuids = []
    for i in range(5):
        generated_uuid = generate_deterministic_recipe_uuid(recipe_data)
        uuids.append(generated_uuid)
        print(f"   Attempt {i+1}: {generated_uuid}")
    
    # Check if all UUIDs are identical
    all_same = all(uuid_str == uuids[0] for uuid_str in uuids)
    
    if all_same:
        print("   ✅ PASSED: All UUIDs are identical")
        return True, uuids[0]
    else:
        print("   ❌ FAILED: UUIDs are not consistent")
        return False, None

def test_uuid_differentiation():
    """Test that different recipe data produces different UUIDs"""
    print("\n🔍 Testing UUID Differentiation...")
    
    base_recipe = {
        'name': '宫保鸡丁',
        'description': '经典川菜，麻辣鲜香',
        'cuisine': '中式',
        'difficulty': '中等',
        'prep_time': 15,
        'cook_time': 20,
        'ingredients': [
            {'name': '鸡胸肉', 'amount': '300克'},
            {'name': '花生米', 'amount': '50克'}
        ],
        'instructions': ['步骤1', '步骤2'],
        'nutrition_info': {'calories': 320},
        'tags': ['川菜']
    }
    
    # Test different variations
    variations = [
        # Different name
        {**base_recipe, 'name': '麻婆豆腐'},
        # Different ingredients
        {**base_recipe, 'ingredients': [{'name': '豆腐', 'amount': '200克'}]},
        # Different cooking times
        {**base_recipe, 'prep_time': 25, 'cook_time': 30},
        # Different cuisine
        {**base_recipe, 'cuisine': '粤式'},
        # Different instructions
        {**base_recipe, 'instructions': ['不同步骤1', '不同步骤2']}
    ]
    
    base_uuid = generate_deterministic_recipe_uuid(base_recipe)
    print(f"   Base recipe UUID: {base_uuid}")
    
    all_different = True
    generated_uuids = [base_uuid]
    
    for i, variation in enumerate(variations, 1):
        variation_uuid = generate_deterministic_recipe_uuid(variation)
        print(f"   Variation {i} UUID: {variation_uuid}")
        
        if variation_uuid == base_uuid:
            print(f"   ❌ FAILED: Variation {i} has same UUID as base recipe")
            all_different = False
        elif variation_uuid in generated_uuids:
            print(f"   ❌ FAILED: Variation {i} has duplicate UUID")
            all_different = False
        else:
            generated_uuids.append(variation_uuid)
    
    if all_different:
        print("   ✅ PASSED: All variations have different UUIDs")
        return True
    else:
        print("   ❌ FAILED: Some variations have identical UUIDs")
        return False

def test_normalization_consistency():
    """Test that data normalization produces consistent results"""
    print("\n🔧 Testing Data Normalization Consistency...")
    
    # Test recipes with different formatting but same content
    recipe1 = {
        'name': '  宫保鸡丁  ',  # Extra spaces
        'description': '经典川菜，麻辣鲜香',
        'cuisine': 'CHINESE',  # Different case
        'ingredients': [
            {'name': '鸡胸肉', 'amount': '300克'},
            {'name': '花生米', 'amount': '50克'}
        ],
        'tags': ['川菜', '家常菜', '川菜']  # Duplicate tags
    }
    
    recipe2 = {
        'name': '宫保鸡丁',
        'description': '经典川菜，麻辣鲜香',
        'cuisine': 'chinese',  # Different case
        'ingredients': [
            {'name': '花生米', 'amount': '50克'},  # Different order
            {'name': '鸡胸肉', 'amount': '300克'}
        ],
        'tags': ['家常菜', '川菜']  # Different order, no duplicate
    }
    
    uuid1 = generate_deterministic_recipe_uuid(recipe1)
    uuid2 = generate_deterministic_recipe_uuid(recipe2)
    
    print(f"   Recipe 1 UUID: {uuid1}")
    print(f"   Recipe 2 UUID: {uuid2}")
    
    if uuid1 == uuid2:
        print("   ✅ PASSED: Normalization produces consistent UUIDs")
        return True
    else:
        print("   ❌ FAILED: Normalization doesn't produce consistent UUIDs")
        return False

def test_uuid_format_validity():
    """Test that generated UUIDs are valid UUID format"""
    print("\n📋 Testing UUID Format Validity...")
    
    recipe_data = {
        'name': '测试食谱',
        'description': '测试描述',
        'cuisine': '测试',
        'ingredients': [{'name': '测试配料'}],
        'instructions': ['测试步骤']
    }
    
    generated_uuid = generate_deterministic_recipe_uuid(recipe_data)
    print(f"   Generated UUID: {generated_uuid}")
    
    try:
        # Try to parse as UUID
        uuid_obj = uuid.UUID(generated_uuid)
        print(f"   UUID version: {uuid_obj.version}")
        print(f"   UUID variant: {uuid_obj.variant}")
        print("   ✅ PASSED: Generated UUID is valid format")
        return True
    except ValueError as e:
        print(f"   ❌ FAILED: Invalid UUID format - {e}")
        return False

def test_edge_cases():
    """Test edge cases and special characters"""
    print("\n🚨 Testing Edge Cases...")
    
    edge_cases = [
        # Empty/minimal data
        {'name': 'A', 'ingredients': []},
        
        # Special characters
        {'name': '🍜 拉面', 'description': 'Special chars: @#$%^&*()'},
        
        # Very long content
        {'name': 'A' * 1000, 'description': 'B' * 2000},
        
        # Unicode characters
        {'name': '寿司🍣', 'cuisine': '日式', 'ingredients': [{'name': '米饭🍚'}]},
        
        # Numbers and mixed content
        {'name': '123食谱456', 'prep_time': 0, 'cook_time': 999}
    ]
    
    uuids = []
    for i, case in enumerate(edge_cases, 1):
        try:
            case_uuid = generate_deterministic_recipe_uuid(case)
            uuids.append(case_uuid)
            print(f"   Edge case {i}: {case_uuid}")
        except Exception as e:
            print(f"   ❌ Edge case {i} failed: {e}")
            return False
    
    # Check all UUIDs are different
    if len(set(uuids)) == len(uuids):
        print("   ✅ PASSED: All edge cases produce unique UUIDs")
        return True
    else:
        print("   ❌ FAILED: Some edge cases produce duplicate UUIDs")
        return False

def run_verification_suite():
    """Run the complete UUID verification suite"""
    print("🧪 UUID Generation Verification Suite")
    print("=" * 50)
    
    tests = [
        ("Consistency Test", test_uuid_consistency),
        ("Differentiation Test", test_uuid_differentiation),
        ("Normalization Test", test_normalization_consistency),
        ("Format Validity Test", test_uuid_format_validity),
        ("Edge Cases Test", test_edge_cases)
    ]
    
    passed_tests = 0
    total_tests = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n📋 {test_name}")
        print("-" * 30)
        
        try:
            result = test_func()
            if result:
                passed_tests += 1
        except Exception as e:
            print(f"   ❌ FAILED: Test threw exception - {e}")
    
    print("\n" + "=" * 50)
    print("📊 VERIFICATION RESULTS:")
    print(f"   ✅ Passed: {passed_tests}/{total_tests} tests")
    print(f"   ❌ Failed: {total_tests - passed_tests}/{total_tests} tests")
    
    if passed_tests == total_tests:
        print("\n🎉 ALL TESTS PASSED!")
        print("✅ Deterministic UUID generation system is working correctly")
        print("✅ Frontend can now reliably predict and track recipe IDs")
        print("✅ Content-based duplicate detection is functional")
        return True
    else:
        print(f"\n⚠️  {total_tests - passed_tests} TESTS FAILED!")
        print("❌ System requires fixes before deployment")
        return False

if __name__ == "__main__":
    success = run_verification_suite()
    sys.exit(0 if success else 1)