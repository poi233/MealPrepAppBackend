"""
Tests for recipe management API endpoints.
"""
import json
import uuid
from decimal import Decimal
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

from src.apps.recipes.models import Recipe

User = get_user_model()


class RecipeEndpointsTestCase(TestCase):
    """Test case for recipe management endpoints."""

    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        
        # Create test users
        self.user1 = User.objects.create_user(
            username='testuser1',
            email='test1@example.com',
            password='testpass123'
        )
        self.user2 = User.objects.create_user(
            username='testuser2',
            email='test2@example.com',
            password='testpass123'
        )
        
        # Create JWT tokens
        self.token1 = RefreshToken.for_user(self.user1).access_token
        self.token2 = RefreshToken.for_user(self.user2).access_token
        
        # Sample recipe data
        self.recipe_data = {
            'name': 'Test Recipe',
            'description': 'A delicious test recipe',
            'ingredients': [
                {
                    'name': 'Flour',
                    'amount': 2.5,
                    'unit': 'cups',
                    'notes': 'All-purpose flour'
                },
                {
                    'name': 'Sugar',
                    'amount': 1.0,
                    'unit': 'cup',
                    'notes': ''
                }
            ],
            'instructions': 'Mix ingredients and bake for 30 minutes.',
            'nutrition_info': {
                'calories': 250.0,
                'protein': 8.0,
                'carbs': 45.0,
                'fat': 5.0
            },
            'cuisine': 'American',
            'prep_time': 15,
            'cook_time': 30,
            'difficulty': 'easy',
            'tags': ['dessert', 'baking']
        }
        
        # Create test recipes
        self.recipe1 = Recipe.objects.create(
            created_by_user=self.user1,
            name='User 1 Recipe',
            description='Recipe by user 1',
            ingredients=[{'name': 'Test', 'amount': 1, 'unit': 'cup'}],
            instructions='Test instructions',
            cuisine='Italian',
            prep_time=10,
            cook_time=20,
            difficulty='medium',
            tags=['pasta', 'dinner']
        )
        
        self.recipe2 = Recipe.objects.create(
            created_by_user=self.user2,
            name='User 2 Recipe',
            description='Recipe by user 2',
            ingredients=[{'name': 'Ingredient', 'amount': 2, 'unit': 'tbsp'}],
            instructions='Different instructions',
            cuisine='Mexican',
            prep_time=5,
            cook_time=15,
            difficulty='easy',
            tags=['quick', 'lunch']
        )

    def authenticate_user(self, user_token):
        """Helper method to authenticate user."""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {user_token}')

    def test_list_recipes_unauthenticated(self):
        """Test that unauthenticated users cannot list recipes."""
        url = reverse('recipe-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_recipes_authenticated(self):
        """Test listing recipes for authenticated users."""
        self.authenticate_user(self.token1)
        url = reverse('recipe-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.data)
        self.assertIn('count', response.data)
        self.assertEqual(len(response.data['results']), 2)

    def test_list_recipes_with_pagination(self):
        """Test recipe listing with pagination."""
        self.authenticate_user(self.token1)
        url = reverse('recipe-list')
        response = self.client.get(url, {'page_size': 1})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('links', response.data)
        self.assertIn('total_pages', response.data)
        self.assertEqual(len(response.data['results']), 1)

    def test_list_recipes_with_search(self):
        """Test recipe listing with search functionality."""
        self.authenticate_user(self.token1)
        url = reverse('recipe-list')
        response = self.client.get(url, {'search': 'User 1'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['name'], 'User 1 Recipe')

    def test_list_recipes_with_filters(self):
        """Test recipe listing with various filters."""
        self.authenticate_user(self.token1)
        url = reverse('recipe-list')
        
        # Filter by cuisine
        response = self.client.get(url, {'cuisine': 'Italian'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        
        # Filter by difficulty
        response = self.client.get(url, {'difficulty': 'easy'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        
        # Filter by prep time
        response = self.client.get(url, {'prep_time__lte': 10})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)

    def test_list_my_recipes(self):
        """Test listing current user's recipes only."""
        self.authenticate_user(self.token1)
        url = reverse('recipe-my-recipes')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['name'], 'User 1 Recipe')

    def test_create_recipe_success(self):
        """Test successful recipe creation."""
        self.authenticate_user(self.token1)
        url = reverse('recipe-list')
        response = self.client.post(url, self.recipe_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], self.recipe_data['name'])
        self.assertEqual(response.data['created_by_user_id'], str(self.user1.id))
        
        # Verify recipe was created in database
        recipe = Recipe.objects.get(id=response.data['id'])
        self.assertEqual(recipe.name, self.recipe_data['name'])
        self.assertEqual(recipe.created_by_user, self.user1)

    def test_create_recipe_validation_errors(self):
        """Test recipe creation with validation errors."""
        self.authenticate_user(self.token1)
        url = reverse('recipe-list')
        
        # Missing required fields
        invalid_data = {'name': ''}
        response = self.client.post(url, invalid_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)

    def test_create_recipe_unauthenticated(self):
        """Test that unauthenticated users cannot create recipes."""
        url = reverse('recipe-list')
        response = self.client.post(url, self.recipe_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_retrieve_recipe_success(self):
        """Test successful recipe retrieval."""
        self.authenticate_user(self.token1)
        url = reverse('recipe-detail', kwargs={'pk': self.recipe1.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], str(self.recipe1.id))
        self.assertEqual(response.data['name'], self.recipe1.name)

    def test_retrieve_recipe_not_found(self):
        """Test retrieving non-existent recipe."""
        self.authenticate_user(self.token1)
        url = reverse('recipe-detail', kwargs={'pk': uuid.uuid4()})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_recipe_success(self):
        """Test successful recipe update by owner."""
        self.authenticate_user(self.token1)
        url = reverse('recipe-detail', kwargs={'pk': self.recipe1.id})
        
        update_data = self.recipe_data.copy()
        update_data['name'] = 'Updated Recipe Name'
        
        response = self.client.put(url, update_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Updated Recipe Name')
        
        # Verify update in database
        self.recipe1.refresh_from_db()
        self.assertEqual(self.recipe1.name, 'Updated Recipe Name')

    def test_partial_update_recipe_success(self):
        """Test successful partial recipe update."""
        self.authenticate_user(self.token1)
        url = reverse('recipe-detail', kwargs={'pk': self.recipe1.id})
        
        partial_data = {'name': 'Partially Updated Name'}
        response = self.client.patch(url, partial_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Partially Updated Name')

    def test_update_recipe_permission_denied(self):
        """Test that users cannot update recipes they don't own."""
        self.authenticate_user(self.token2)  # User 2 trying to update User 1's recipe
        url = reverse('recipe-detail', kwargs={'pk': self.recipe1.id})
        
        update_data = {'name': 'Unauthorized Update'}
        response = self.client.put(url, update_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_recipe_success(self):
        """Test successful recipe deletion by owner."""
        self.authenticate_user(self.token1)
        url = reverse('recipe-detail', kwargs={'pk': self.recipe1.id})
        
        response = self.client.delete(url)
        
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        
        # Verify deletion in database
        with self.assertRaises(Recipe.DoesNotExist):
            Recipe.objects.get(id=self.recipe1.id)

    def test_delete_recipe_permission_denied(self):
        """Test that users cannot delete recipes they don't own."""
        self.authenticate_user(self.token2)  # User 2 trying to delete User 1's recipe
        url = reverse('recipe-detail', kwargs={'pk': self.recipe1.id})
        
        response = self.client.delete(url)
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
        # Verify recipe still exists
        self.assertTrue(Recipe.objects.filter(id=self.recipe1.id).exists())

    def test_advanced_search_endpoint(self):
        """Test the advanced search endpoint."""
        self.authenticate_user(self.token1)
        url = reverse('recipe-search')
        
        # Search for recipes
        response = self.client.get(url, {'q': 'pasta'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        
        # Search without query parameter
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_recipe_ordering(self):
        """Test recipe ordering functionality."""
        self.authenticate_user(self.token1)
        url = reverse('recipe-list')
        
        # Order by name
        response = self.client.get(url, {'ordering': 'name'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Order by creation date (descending)
        response = self.client.get(url, {'ordering': '-created_at'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_recipe_filtering_by_tags(self):
        """Test filtering recipes by tags."""
        self.authenticate_user(self.token1)
        url = reverse('recipe-list')
        
        # Filter by single tag
        response = self.client.get(url, {'tags': 'dinner'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)

    def test_recipe_filtering_by_total_time(self):
        """Test filtering recipes by total cooking time."""
        self.authenticate_user(self.token1)
        url = reverse('recipe-list')
        
        # Filter by maximum total time
        response = self.client.get(url, {'max_total_time': 25})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)  # Only recipe2 (5+15=20 minutes)

    def test_recipe_serializer_fields(self):
        """Test that recipe serializer includes all expected fields."""
        self.authenticate_user(self.token1)
        url = reverse('recipe-detail', kwargs={'pk': self.recipe1.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        expected_fields = [
            'id', 'created_by_user', 'created_by_user_id', 'name', 'description',
            'ingredients', 'instructions', 'nutrition_info', 'cuisine',
            'prep_time', 'cook_time', 'total_time', 'difficulty', 'avg_rating',
            'rating_count', 'image_url', 'tags', 'created_at', 'updated_at'
        ]
        
        for field in expected_fields:
            self.assertIn(field, response.data)

    def test_recipe_list_serializer_excludes_heavy_fields(self):
        """Test that recipe list serializer excludes heavy fields for performance."""
        self.authenticate_user(self.token1)
        url = reverse('recipe-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Should not include ingredients and instructions in list view
        for recipe in response.data['results']:
            self.assertNotIn('ingredients', recipe)
            self.assertNotIn('instructions', recipe)
            self.assertNotIn('nutrition_info', recipe)