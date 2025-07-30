"""
Tests for authentication system and JWT token management.
"""
import json
from django.test import TestCase, Client
from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from apps.authentication.models import User
from apps.authentication.serializers import UserRegistrationSerializer, UserProfileSerializer


class AuthenticationModelTests(TestCase):
    """Test cases for User model."""
    
    def setUp(self):
        """Set up test data."""
        self.user_data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'testpass123',
            'display_name': 'Test User',
            'dietary_preferences': {
                'allergies': ['nuts'],
                'diet_type': 'vegetarian',
                'calorie_target': 2000
            }
        }
    
    def test_create_user(self):
        """Test creating a user."""
        user = User.objects.create_user(
            username=self.user_data['username'],
            email=self.user_data['email'],
            password=self.user_data['password'],
            display_name=self.user_data['display_name'],
            dietary_preferences=self.user_data['dietary_preferences']
        )
        
        self.assertEqual(user.username, self.user_data['username'])
        self.assertEqual(user.email, self.user_data['email'])
        self.assertEqual(user.display_name, self.user_data['display_name'])
        self.assertEqual(user.dietary_preferences, self.user_data['dietary_preferences'])
        self.assertTrue(user.check_password(self.user_data['password']))
        self.assertIsNotNone(user.id)
        self.assertIsNotNone(user.created_at)
        self.assertIsNotNone(user.updated_at)
    
    def test_user_string_representation(self):
        """Test user string representation."""
        user = User.objects.create_user(
            username=self.user_data['username'],
            email=self.user_data['email']
        )
        self.assertEqual(str(user), self.user_data['username'])
    
    def test_user_password_hashing(self):
        """Test that passwords are properly hashed."""
        user = User.objects.create_user(
            username=self.user_data['username'],
            email=self.user_data['email'],
            password=self.user_data['password']
        )
        
        # Password should be hashed, not stored in plain text
        self.assertNotEqual(user.password_hash, self.user_data['password'])
        self.assertTrue(user.check_password(self.user_data['password']))
        self.assertFalse(user.check_password('wrongpassword'))


class AuthenticationSerializerTests(TestCase):
    """Test cases for authentication serializers."""
    
    def setUp(self):
        """Set up test data."""
        self.valid_user_data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'testpass123',
            'password_confirm': 'testpass123',
            'display_name': 'Test User',
            'dietary_preferences': {
                'allergies': ['nuts'],
                'diet_type': 'vegetarian'
            }
        }
    
    def test_user_registration_serializer_valid(self):
        """Test valid user registration data."""
        serializer = UserRegistrationSerializer(data=self.valid_user_data)
        self.assertTrue(serializer.is_valid())
        
        user = serializer.save()
        self.assertEqual(user.username, self.valid_user_data['username'])
        self.assertEqual(user.email, self.valid_user_data['email'])
        self.assertTrue(user.check_password(self.valid_user_data['password']))
    
    def test_user_registration_password_mismatch(self):
        """Test password confirmation mismatch."""
        data = self.valid_user_data.copy()
        data['password_confirm'] = 'differentpassword'
        
        serializer = UserRegistrationSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('password_confirm', serializer.errors)
    
    def test_user_registration_duplicate_username(self):
        """Test duplicate username validation."""
        # Create first user
        User.objects.create_user(
            username=self.valid_user_data['username'],
            email='other@example.com',
            password='password123'
        )
        
        # Try to create second user with same username
        serializer = UserRegistrationSerializer(data=self.valid_user_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('username', serializer.errors)
    
    def test_user_registration_duplicate_email(self):
        """Test duplicate email validation."""
        # Create first user
        User.objects.create_user(
            username='otheruser',
            email=self.valid_user_data['email'],
            password='password123'
        )
        
        # Try to create second user with same email
        serializer = UserRegistrationSerializer(data=self.valid_user_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('email', serializer.errors)


class AuthenticationViewTests(APITestCase):
    """Test cases for authentication views."""
    
    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        self.user_data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'testpass123',
            'display_name': 'Test User'
        }
        
        self.user = User.objects.create_user(**self.user_data)
    
    def test_user_registration(self):
        """Test user registration endpoint."""
        registration_data = {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password': 'newpass123',
            'password_confirm': 'newpass123',
            'display_name': 'New User'
        }
        
        url = reverse('authentication:register')
        response = self.client.post(url, registration_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        self.assertIn('user', response.data)
        self.assertEqual(response.data['user']['username'], registration_data['username'])
    
    def test_user_login_with_username(self):
        """Test user login with username."""
        login_data = {
            'username': self.user_data['username'],
            'password': self.user_data['password']
        }
        
        url = reverse('authentication:login')
        response = self.client.post(url, login_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        self.assertIn('user', response.data)
        self.assertEqual(response.data['user']['username'], self.user_data['username'])
    
    def test_user_login_with_email(self):
        """Test user login with email."""
        login_data = {
            'username': self.user_data['email'],  # Using email as username
            'password': self.user_data['password']
        }
        
        url = reverse('authentication:login')
        response = self.client.post(url, login_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        self.assertIn('user', response.data)
    
    def test_user_login_invalid_credentials(self):
        """Test login with invalid credentials."""
        login_data = {
            'username': self.user_data['username'],
            'password': 'wrongpassword'
        }
        
        url = reverse('authentication:login')
        response = self.client.post(url, login_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn('error', response.data)
    
    def test_user_logout(self):
        """Test user logout."""
        # First login to get tokens
        refresh = RefreshToken.for_user(self.user)
        access_token = refresh.access_token
        
        # Set authentication
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        
        # Logout
        logout_data = {'refresh': str(refresh)}
        url = reverse('authentication:logout')
        response = self.client.post(url, logout_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('message', response.data)
    
    def test_get_user_profile(self):
        """Test getting user profile."""
        # Authenticate user
        refresh = RefreshToken.for_user(self.user)
        access_token = refresh.access_token
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        
        url = reverse('authentication:user_profile')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['username'], self.user_data['username'])
        self.assertEqual(response.data['email'], self.user_data['email'])
    
    def test_update_user_profile(self):
        """Test updating user profile."""
        # Authenticate user
        refresh = RefreshToken.for_user(self.user)
        access_token = refresh.access_token
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        
        update_data = {
            'display_name': 'Updated Name',
            'dietary_preferences': {
                'allergies': ['dairy'],
                'diet_type': 'vegan'
            }
        }
        
        url = reverse('authentication:update_profile')
        response = self.client.patch(url, update_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['display_name'], update_data['display_name'])
        self.assertEqual(response.data['dietary_preferences'], update_data['dietary_preferences'])
    
    def test_change_password(self):
        """Test changing password."""
        # Authenticate user
        refresh = RefreshToken.for_user(self.user)
        access_token = refresh.access_token
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        
        password_data = {
            'current_password': self.user_data['password'],
            'new_password': 'newpassword123',
            'new_password_confirm': 'newpassword123'
        }
        
        url = reverse('authentication:change_password')
        response = self.client.post(url, password_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('message', response.data)
        
        # Verify password was changed
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(password_data['new_password']))
    
    def test_delete_account(self):
        """Test deleting user account."""
        # Authenticate user
        refresh = RefreshToken.for_user(self.user)
        access_token = refresh.access_token
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        
        delete_data = {'password': self.user_data['password']}
        
        url = reverse('authentication:delete_account')
        response = self.client.delete(url, delete_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('message', response.data)
        
        # Verify user was deleted
        self.assertFalse(User.objects.filter(id=self.user.id).exists())
    
    def test_unauthenticated_access_to_protected_endpoints(self):
        """Test that protected endpoints require authentication."""
        protected_urls = [
            reverse('authentication:user_profile'),
            reverse('authentication:update_profile'),
            reverse('authentication:change_password'),
            reverse('authentication:delete_account'),
            reverse('authentication:logout'),
        ]
        
        for url in protected_urls:
            response = self.client.get(url)
            self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])


class JWTTokenTests(APITestCase):
    """Test cases for JWT token functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_token_generation(self):
        """Test JWT token generation."""
        refresh = RefreshToken.for_user(self.user)
        access_token = refresh.access_token
        
        self.assertIsNotNone(str(refresh))
        self.assertIsNotNone(str(access_token))
    
    def test_token_refresh(self):
        """Test token refresh endpoint."""
        refresh = RefreshToken.for_user(self.user)
        
        refresh_data = {'refresh': str(refresh)}
        url = reverse('authentication:token_refresh')
        response = self.client.post(url, refresh_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
    
    def test_invalid_token_refresh(self):
        """Test token refresh with invalid token."""
        refresh_data = {'refresh': 'invalid_token'}
        url = reverse('authentication:token_refresh')
        response = self.client.post(url, refresh_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_authenticated_request_with_valid_token(self):
        """Test making authenticated request with valid token."""
        refresh = RefreshToken.for_user(self.user)
        access_token = refresh.access_token
        
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        
        url = reverse('authentication:user_profile')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_authenticated_request_with_invalid_token(self):
        """Test making authenticated request with invalid token."""
        self.client.credentials(HTTP_AUTHORIZATION='Bearer invalid_token')
        
        url = reverse('authentication:user_profile')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)