#!/usr/bin/env python3
"""
Specialized test suite for UUID deterministic generation mechanism.
Tests the consistency and reliability of UUID generation for recipes.
"""

import os
import sys
import uuid
import hashlib
from typing import Dict, List, Any

import pytest
import django
from django.test import TestCase

# Setup Django
sys.path.insert(0, '/Users/puyihao/workspace/MealPrep/MealPrepAppBackend/src')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

# Import test infrastructure
from test_base import BaseTestCase
from test_fixtures import create_deterministic_uuid, TestDataFactory

# Import application code
try:
    from apps.ai_integration.services import RECIPE_UUID_NAMESPACE
    AI_SERVICE_AVAILABLE = True
except ImportError:
    AI_SERVICE_AVAILABLE = False
    RECIPE_UUID_NAMESPACE = None


class TestUUIDDeterministicGeneration(BaseTestCase):
    """Test deterministic UUID generation for recipes."""
    
    def test_uuid_determinism(self):
        """Test that UUIDs are generated deterministically."""
        recipe_name = "Spaghetti Carbonara"
        
        # Generate UUID multiple times
        uuid1 = create_deterministic_uuid(recipe_name)
        uuid2 = create_deterministic_uuid(recipe_name)
        uuid3 = create_deterministic_uuid(recipe_name)
        
        # All should be identical
        self.assertEqual(uuid1, uuid2)
        self.assertEqual(uuid2, uuid3)
        self.assertEqual(uuid1, uuid3)
    
    def test_uuid_uniqueness(self):
        """Test that different recipe names produce different UUIDs."""
        recipe_names = [
            "Spaghetti Carbonara",
            "Chicken Parmesan", 
            "Beef Stir Fry",
            "Vegetable Curry",
            "Fish Tacos",
            "Mushroom Risotto",
            "Caesar Salad",
            "Chocolate Cake",
            "Apple Pie",
            "BBQ Ribs"
        ]
        
        uuids = [create_deterministic_uuid(name) for name in recipe_names]
        
        # All UUIDs should be unique
        self.assertEqual(len(uuids), len(set(uuids)))
        
        # Check each pair is different
        for i in range(len(uuids)):
            for j in range(i + 1, len(uuids)):
                self.assertNotEqual(uuids[i], uuids[j], 
                    f"UUID collision between '{recipe_names[i]}' and '{recipe_names[j]}'")
    
    def test_uuid_format_validation(self):
        """Test that generated UUIDs have correct format."""
        import re
        
        recipe_names = ["Test Recipe", "Another Recipe", "Third Recipe"]
        uuid_pattern = re.compile(
            r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
        )
        
        for recipe_name in recipe_names:
            with self.subTest(recipe_name=recipe_name):
                uuid_str = create_deterministic_uuid(recipe_name)
                
                # Should match UUID format
                self.assertTrue(uuid_pattern.match(uuid_str), 
                    f"Invalid UUID format: {uuid_str}")
                
                # Should be parseable as UUID
                try:
                    parsed_uuid = uuid.UUID(uuid_str)
                    self.assertEqual(str(parsed_uuid), uuid_str)
                except ValueError:
                    self.fail(f"UUID {uuid_str} is not parseable")
    
    def test_uuid_case_sensitivity(self):
        """Test UUID generation with different cases."""
        base_name = "Test Recipe"
        
        variations = [
            "Test Recipe",
            "test recipe",
            "TEST RECIPE",
            "Test RECIPE",
            "tEsT rEcIpE"
        ]
        
        uuids = [create_deterministic_uuid(name) for name in variations]
        
        # Different cases should produce different UUIDs
        unique_uuids = set(uuids)
        self.assertEqual(len(unique_uuids), len(variations), 
            "Case variations should produce different UUIDs")
    
    def test_uuid_special_characters(self):
        """Test UUID generation with special characters."""
        special_names = [
            "Recipe with spaces",
            "Recipe-with-dashes",
            "Recipe_with_underscores",
            "Recipe (with parentheses)",
            "Recipe [with brackets]",
            "Recipe {with braces}",
            "Recipe & with ampersand",
            "Recipe @ with at symbol",
            "Recipe #1 with hash",
            "Recipe 50% complete"
        ]
        
        uuids = []
        for name in special_names:
            with self.subTest(recipe_name=name):
                uuid_str = create_deterministic_uuid(name)
                uuids.append(uuid_str)
                
                # Should be valid UUID format
                try:
                    uuid.UUID(uuid_str)
                except ValueError:
                    self.fail(f"Invalid UUID generated for name: {name}")
        
        # All should be unique
        self.assertEqual(len(uuids), len(set(uuids)))
    
    def test_uuid_empty_and_none_handling(self):
        """Test UUID generation with empty or None inputs."""
        test_cases = [
            ("", "empty string"),
            ("   ", "whitespace only"),
        ]
        
        for test_input, description in test_cases:
            with self.subTest(input=description):
                uuid_str = create_deterministic_uuid(test_input)
                
                # Should still generate valid UUID
                try:
                    uuid.UUID(uuid_str)
                except ValueError:
                    self.fail(f"Invalid UUID for {description}: {uuid_str}")
    
    def test_uuid_length_variations(self):
        """Test UUID generation with various name lengths."""
        names_by_length = [
            "A",  # Single character
            "AB",  # Two characters
            "ABC",  # Three characters
            "A recipe with normal length name",  # Normal length
            "A" * 100,  # Very long name
            "A" * 1000,  # Extremely long name
        ]
        
        uuids = []
        for name in names_by_length:
            with self.subTest(name_length=len(name)):
                uuid_str = create_deterministic_uuid(name)
                uuids.append(uuid_str)
                
                # Should be valid UUID
                try:
                    uuid.UUID(uuid_str)
                except ValueError:
                    self.fail(f"Invalid UUID for name of length {len(name)}")
        
        # All should be unique
        self.assertEqual(len(uuids), len(set(uuids)))
    
    def test_uuid_unicode_handling(self):
        """Test UUID generation with Unicode characters."""
        unicode_names = [
            "Recipe with émojis 🍝",
            "中文食谱名称",
            "Recette française",
            "Рецепт на русском",
            "レシピの日本語名",
            "Recipe with ñ and ü",
            "Recipe with 数字123",
        ]
        
        uuids = []
        for name in unicode_names:
            with self.subTest(recipe_name=name):
                uuid_str = create_deterministic_uuid(name)
                uuids.append(uuid_str)
                
                # Should be valid UUID
                try:
                    uuid.UUID(uuid_str)
                except ValueError:
                    self.fail(f"Invalid UUID for Unicode name: {name}")
        
        # All should be unique
        self.assertEqual(len(uuids), len(set(uuids)))
    
    def test_uuid_collision_resistance(self):
        """Test collision resistance with similar names."""
        similar_names = [
            "Chicken Parmesan",
            "Chicken Parmesian",  # Typo
            "Chicken Parmesan ",  # Extra space
            " Chicken Parmesan",  # Leading space
            "chicken parmesan",   # Different case
            "Chicken-Parmesan",   # Dash instead of space
            "Chicken_Parmesan",   # Underscore instead of space
        ]
        
        uuids = [create_deterministic_uuid(name) for name in similar_names]
        
        # All should be unique despite similarity
        self.assertEqual(len(uuids), len(set(uuids)), 
            "Similar names should still produce unique UUIDs")
    
    @pytest.mark.skipif(not AI_SERVICE_AVAILABLE, reason="AI service not available")
    def test_uuid_namespace_consistency(self):
        """Test that UUID namespace is consistent with AI service."""
        if RECIPE_UUID_NAMESPACE is None:
            self.skipTest("Recipe UUID namespace not available")
        
        # Test that namespace is a valid UUID
        self.assertIsInstance(RECIPE_UUID_NAMESPACE, uuid.UUID)
        
        # Test that namespace is consistent
        expected_namespace = uuid.UUID('6ba7b810-9dad-11d1-80b4-00c04fd430c8')
        self.assertEqual(RECIPE_UUID_NAMESPACE, expected_namespace)
    
    def test_uuid_performance(self):
        """Test UUID generation performance."""
        recipe_names = [f"Performance Test Recipe {i}" for i in range(1000)]
        
        start_time = self.start_time
        
        for name in recipe_names:
            create_deterministic_uuid(name)
        
        # Should complete within reasonable time
        self.assert_execution_time(2.0)  # 1000 UUIDs in under 2 seconds
    
    def test_uuid_with_test_data(self):
        """Test UUID generation with test fixture data."""
        test_recipes = TestDataFactory.create_recipe_data(20)
        
        generated_uuids = []
        provided_uuids = []
        
        for recipe_data in test_recipes:
            # Generate UUID from name
            generated_uuid = create_deterministic_uuid(recipe_data['name'])
            generated_uuids.append(generated_uuid)
            
            # Use provided UUID from test data
            provided_uuids.append(recipe_data['id'])
        
        # All generated UUIDs should be unique
        self.assertEqual(len(generated_uuids), len(set(generated_uuids)))
        
        # All provided UUIDs should be unique  
        self.assertEqual(len(provided_uuids), len(set(provided_uuids)))
        
        # Generated and provided UUIDs might be different (depends on implementation)
        # But both sets should be valid


if __name__ == '__main__':
    # Run tests
    import unittest
    unittest.main(verbosity=2)