"""
Test cases for favorites API endpoints.
"""
import uuid
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

from apps.recipes.models import Recipe
from apps.favorites.models import Favorite, Collection, CollectionRecipe

User = get_user_model()


class FavoritesAPITestCase(TestCase):
    """Test case for favorites API endpoints."""

    def setUp(self):
        """Set up test data."""
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

        # Create test recipes
        self.recipe1 = Recipe.objects.create(
            name='Test Recipe 1',
            description='A test recipe',
            ingredients=[
                {'name': 'Ingredient 1', 'amount': '1 cup'},
                {'name': 'Ingredient 2', 'amount': '2 tbsp'}
            ],
            instructions='Test instructions',
            cuisine='Italian',
            meal_type='dinner',
            prep_time=15,
            cook_time=30,
            difficulty='medium',
            created_by_user=self.user1
        )
        
        self.recipe2 = Recipe.objects.create(
            name='Test Recipe 2',
            description='Another test recipe',
            ingredients=[
                {'name': 'Ingredient 3', 'amount': '2 cups'},
                {'name': 'Ingredient 4', 'amount': '1 tsp'}
            ],
            instructions='More test instructions',
            cuisine='Mexican',
            meal_type='lunch',
            prep_time=10,
            cook_time=20,
            difficulty='easy',
            created_by_user=self.user2
        )

        # Set up API client
        self.client = APIClient()

    def get_jwt_token(self, user):
        """Get JWT token for user authentication."""
        refresh = RefreshToken.for_user(user)
        return str(refresh.access_token)

    def authenticate_user(self, user):
        """Authenticate user with JWT token."""
        token = self.get_jwt_token(user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

    def test_list_favorites_empty(self):
        """Test listing favorites when user has none."""
        self.authenticate_user(self.user1)
        
        url = reverse('favorite-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 0)
        self.assertEqual(len(response.data['results']), 0)

    def test_add_recipe_to_favorites(self):
        """Test adding a recipe to favorites."""
        self.authenticate_user(self.user1)
        
        url = reverse('favorite_by_recipe', kwargs={'recipe_id': self.recipe1.id})
        data = {
            'personal_rating': 5,
            'personal_notes': 'This is my favorite recipe!'
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['recipe']['id'], str(self.recipe1.id))
        self.assertEqual(response.data['personal_rating'], 5)
        self.assertEqual(response.data['personal_notes'], 'This is my favorite recipe!')
        
        # Verify favorite was created in database
        favorite = Favorite.objects.get(user=self.user1, recipe=self.recipe1)
        self.assertEqual(favorite.personal_rating, 5)
        self.assertEqual(favorite.personal_notes, 'This is my favorite recipe!')

    def test_add_recipe_to_favorites_minimal_data(self):
        """Test adding a recipe to favorites with minimal data."""
        self.authenticate_user(self.user1)
        
        url = reverse('favorite_by_recipe', kwargs={'recipe_id': self.recipe1.id})
        data = {}
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['recipe']['id'], str(self.recipe1.id))
        self.assertIsNone(response.data['personal_rating'])
        self.assertEqual(response.data['personal_notes'], '')

    def test_add_nonexistent_recipe_to_favorites(self):
        """Test adding a non-existent recipe to favorites."""
        self.authenticate_user(self.user1)
        
        fake_recipe_id = uuid.uuid4()
        url = reverse('favorite_by_recipe', kwargs={'recipe_id': fake_recipe_id})
        
        response = self.client.post(url, {}, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn('Recipe not found', response.data['error'])

    def test_add_duplicate_favorite(self):
        """Test adding the same recipe to favorites twice."""
        self.authenticate_user(self.user1)
        
        # Add recipe to favorites first time
        Favorite.objects.create(
            user=self.user1,
            recipe=self.recipe1,
            personal_rating=4
        )
        
        url = reverse('favorite_by_recipe', kwargs={'recipe_id': self.recipe1.id})
        data = {'personal_rating': 5}
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('already in favorites', response.data['error'])

    def test_list_favorites_with_data(self):
        """Test listing favorites when user has some."""
        self.authenticate_user(self.user1)
        
        # Create some favorites
        Favorite.objects.create(
            user=self.user1,
            recipe=self.recipe1,
            personal_rating=5,
            personal_notes='Great recipe!'
        )
        Favorite.objects.create(
            user=self.user1,
            recipe=self.recipe2,
            personal_rating=4
        )
        
        url = reverse('favorite-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(len(response.data['results']), 2)
        
        # Check that recipe details are included
        favorite_data = response.data['results'][0]
        self.assertIn('recipe', favorite_data)
        self.assertIn('name', favorite_data['recipe'])
        self.assertIn('personal_rating', favorite_data)

    def test_list_favorites_filtering_by_rating(self):
        """Test filtering favorites by personal rating."""
        self.authenticate_user(self.user1)
        
        # Create favorites with different ratings
        Favorite.objects.create(
            user=self.user1,
            recipe=self.recipe1,
            personal_rating=5
        )
        Favorite.objects.create(
            user=self.user1,
            recipe=self.recipe2,
            personal_rating=3
        )
        
        url = reverse('favorite-list')
        response = self.client.get(url, {'personal_rating__gte': 4})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['personal_rating'], 5)

    def test_search_favorites(self):
        """Test searching favorites by recipe name."""
        self.authenticate_user(self.user1)
        
        # Create favorites
        Favorite.objects.create(user=self.user1, recipe=self.recipe1)
        Favorite.objects.create(user=self.user1, recipe=self.recipe2)
        
        url = reverse('favorite-list')
        response = self.client.get(url, {'search': 'Test Recipe 1'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['recipe']['name'], 'Test Recipe 1')

    def test_remove_recipe_from_favorites(self):
        """Test removing a recipe from favorites."""
        self.authenticate_user(self.user1)
        
        # Add recipe to favorites first
        favorite = Favorite.objects.create(
            user=self.user1,
            recipe=self.recipe1,
            personal_rating=5
        )
        
        url = reverse('favorite_by_recipe', kwargs={'recipe_id': self.recipe1.id})
        response = self.client.delete(url)
        
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertIn('removed from favorites', response.data['message'])
        
        # Verify favorite was deleted from database
        self.assertFalse(
            Favorite.objects.filter(user=self.user1, recipe=self.recipe1).exists()
        )

    def test_remove_nonexistent_favorite(self):
        """Test removing a recipe that's not in favorites."""
        self.authenticate_user(self.user1)
        
        url = reverse('favorite_by_recipe', kwargs={'recipe_id': self.recipe1.id})
        response = self.client.delete(url)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn('not in favorites', response.data['error'])

    def test_check_favorite_status(self):
        """Test checking if a recipe is in favorites."""
        self.authenticate_user(self.user1)
        
        # Add recipe to favorites
        favorite = Favorite.objects.create(
            user=self.user1,
            recipe=self.recipe1,
            personal_rating=4
        )
        
        url = reverse('favorite_by_recipe', kwargs={'recipe_id': self.recipe1.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['recipe']['id'], str(self.recipe1.id))
        self.assertEqual(response.data['personal_rating'], 4)

    def test_check_non_favorite_status(self):
        """Test checking status of a recipe not in favorites."""
        self.authenticate_user(self.user1)
        
        url = reverse('favorite_by_recipe', kwargs={'recipe_id': self.recipe1.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['is_favorite'], False)

    def test_update_favorite_rating_and_notes(self):
        """Test updating favorite rating and notes."""
        self.authenticate_user(self.user1)
        
        # Create favorite
        favorite = Favorite.objects.create(
            user=self.user1,
            recipe=self.recipe1,
            personal_rating=3,
            personal_notes='Original notes'
        )
        
        url = reverse('favorite-detail', kwargs={'pk': favorite.pk})
        data = {
            'personal_rating': 5,
            'personal_notes': 'Updated notes - this is amazing!'
        }
        
        response = self.client.put(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['personal_rating'], 5)
        self.assertEqual(response.data['personal_notes'], 'Updated notes - this is amazing!')
        
        # Verify changes in database
        favorite.refresh_from_db()
        self.assertEqual(favorite.personal_rating, 5)
        self.assertEqual(favorite.personal_notes, 'Updated notes - this is amazing!')

    def test_favorites_user_isolation(self):
        """Test that users can only see their own favorites."""
        # User 1 adds recipe to favorites
        self.authenticate_user(self.user1)
        Favorite.objects.create(user=self.user1, recipe=self.recipe1)
        
        # User 2 should not see user 1's favorites
        self.authenticate_user(self.user2)
        url = reverse('favorite-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 0)

    def test_unauthenticated_access_denied(self):
        """Test that unauthenticated users cannot access favorites."""
        self.client.credentials()  # Remove authentication
        
        url = reverse('favorite-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_invalid_rating_validation(self):
        """Test validation of invalid personal ratings."""
        self.authenticate_user(self.user1)
        
        url = reverse('favorite_by_recipe', kwargs={'recipe_id': self.recipe1.id})
        
        # Test rating too low
        response = self.client.post(url, {'personal_rating': 0}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        # Test rating too high
        response = self.client.post(url, {'personal_rating': 6}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_personal_notes_truncation(self):
        """Test that personal notes are properly truncated."""
        self.authenticate_user(self.user1)
        
        # Create very long notes
        long_notes = 'A' * 1500  # Longer than 1000 character limit
        
        url = reverse('favorite_by_recipe', kwargs={'recipe_id': self.recipe1.id})
        data = {'personal_notes': long_notes}
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        # Notes should be truncated to 1000 characters
        self.assertEqual(len(response.data['personal_notes']), 1000)


class CollectionsAPITestCase(TestCase):
    """Test case for collections API endpoints."""

    def setUp(self):
        """Set up test data."""
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

        # Create test recipes
        self.recipe1 = Recipe.objects.create(
            name='Test Recipe 1',
            description='A test recipe',
            ingredients=[{'name': 'Ingredient 1', 'amount': '1 cup'}],
            instructions='Test instructions',
            cuisine='Italian',
            meal_type='dinner',
            prep_time=15,
            cook_time=30,
            difficulty='medium',
            created_by_user=self.user
        )
        
        self.recipe2 = Recipe.objects.create(
            name='Test Recipe 2',
            description='Another test recipe',
            ingredients=[{'name': 'Ingredient 2', 'amount': '2 cups'}],
            instructions='More test instructions',
            cuisine='Mexican',
            meal_type='lunch',
            prep_time=10,
            cook_time=20,
            difficulty='easy',
            created_by_user=self.user
        )

        # Set up API client
        self.client = APIClient()

    def get_jwt_token(self, user):
        """Get JWT token for user authentication."""
        refresh = RefreshToken.for_user(user)
        return str(refresh.access_token)

    def authenticate_user(self, user):
        """Authenticate user with JWT token."""
        token = self.get_jwt_token(user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

    def test_create_collection(self):
        """Test creating a new collection."""
        self.authenticate_user(self.user)
        
        url = reverse('collection-list')
        data = {
            'name': 'My Favorite Dinners',
            'description': 'Collection of my favorite dinner recipes',
            'color': '#FF5722',
            'icon': 'dinner',
            'is_public': False,
            'recipe_ids': [str(self.recipe1.id), str(self.recipe2.id)]
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], 'My Favorite Dinners')
        self.assertEqual(response.data['description'], 'Collection of my favorite dinner recipes')
        self.assertEqual(response.data['color'], '#FF5722')
        self.assertEqual(response.data['icon'], 'dinner')
        self.assertEqual(response.data['is_public'], False)
        self.assertEqual(len(response.data['recipes']), 2)
        
        # Verify collection was created in database
        collection = Collection.objects.get(name='My Favorite Dinners')
        self.assertEqual(collection.user, self.user)
        self.assertEqual(collection.recipes.count(), 2)

    def test_create_collection_minimal_data(self):
        """Test creating a collection with minimal required data."""
        self.authenticate_user(self.user)
        
        url = reverse('collection-list')
        data = {'name': 'Simple Collection'}
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], 'Simple Collection')
        self.assertEqual(response.data['color'], '#4DB6AC')  # Default color
        self.assertEqual(response.data['icon'], 'heart')  # Default icon
        self.assertEqual(response.data['is_public'], False)  # Default value

    def test_list_collections(self):
        """Test listing user's collections."""
        self.authenticate_user(self.user)
        
        # Create test collections
        collection1 = Collection.objects.create(
            user=self.user,
            name='Collection 1',
            description='First collection'
        )
        collection2 = Collection.objects.create(
            user=self.user,
            name='Collection 2',
            description='Second collection'
        )
        
        url = reverse('collection-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(len(response.data['results']), 2)

    def test_add_recipe_to_collection(self):
        """Test adding a recipe to an existing collection."""
        self.authenticate_user(self.user)
        
        # Create collection
        collection = Collection.objects.create(
            user=self.user,
            name='Test Collection'
        )
        
        url = reverse('collection-add-recipe', kwargs={'pk': collection.id})
        data = {'recipe_id': str(self.recipe1.id)}
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('added to collection', response.data['message'])
        
        # Verify recipe was added to collection
        self.assertTrue(
            CollectionRecipe.objects.filter(
                collection=collection,
                recipe=self.recipe1
            ).exists()
        )

    def test_remove_recipe_from_collection(self):
        """Test removing a recipe from a collection."""
        self.authenticate_user(self.user)
        
        # Create collection with recipe
        collection = Collection.objects.create(
            user=self.user,
            name='Test Collection'
        )
        CollectionRecipe.objects.create(
            collection=collection,
            recipe=self.recipe1
        )
        
        url = reverse('collection-remove-recipe', kwargs={
            'pk': collection.id,
            'recipe_id': self.recipe1.id
        })
        
        response = self.client.delete(url)
        
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertIn('removed from collection', response.data['message'])
        
        # Verify recipe was removed from collection
        self.assertFalse(
            CollectionRecipe.objects.filter(
                collection=collection,
                recipe=self.recipe1
            ).exists()
        )

    def test_duplicate_collection_name_validation(self):
        """Test that users cannot create collections with duplicate names."""
        self.authenticate_user(self.user)
        
        # Create first collection
        Collection.objects.create(
            user=self.user,
            name='Duplicate Name'
        )
        
        # Try to create second collection with same name
        url = reverse('collection-list')
        data = {'name': 'Duplicate Name'}
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('already have a collection', str(response.data))

    def test_collection_color_validation(self):
        """Test validation of collection color hex codes."""
        self.authenticate_user(self.user)
        
        url = reverse('collection-list')
        
        # Test invalid color format
        data = {'name': 'Test Collection', 'color': 'invalid-color'}
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('valid hex color', str(response.data))

    def test_add_nonexistent_recipe_to_collection(self):
        """Test adding a non-existent recipe to a collection."""
        self.authenticate_user(self.user)
        
        collection = Collection.objects.create(
            user=self.user,
            name='Test Collection'
        )
        
        fake_recipe_id = uuid.uuid4()
        url = reverse('collection-add-recipe', kwargs={'pk': collection.id})
        data = {'recipe_id': str(fake_recipe_id)}
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Recipe not found', str(response.data))