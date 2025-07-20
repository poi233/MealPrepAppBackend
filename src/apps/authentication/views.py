"""
Authentication views for MealPrepAI Django backend.
"""
from rest_framework import status, generics
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from django.contrib.auth import authenticate
from django.db import transaction
import logging

from .models import User
from .serializers import (
    UserRegistrationSerializer, 
    UserProfileSerializer, 
    ChangePasswordSerializer,
    UserSerializer
)

logger = logging.getLogger(__name__)


class CustomTokenObtainPairView(TokenObtainPairView):
    """Custom login view that returns user data along with tokens."""
    permission_classes = [AllowAny]
    
    def post(self, request, *args, **kwargs):
        """Login user and return tokens with user data."""
        try:
            username = request.data.get('username')
            password = request.data.get('password')
            
            if not username or not password:
                return Response({
                    'error': {
                        'code': 'validation_error',
                        'message': 'Username and password are required',
                        'details': {
                            'username': ['This field is required.'] if not username else [],
                            'password': ['This field is required.'] if not password else []
                        }
                    }
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Try to find user by username or email
            user = None
            try:
                if '@' in username:
                    user = User.objects.get(email__iexact=username)
                else:
                    user = User.objects.get(username__iexact=username)
            except User.DoesNotExist:
                pass
            
            if not user or not user.check_password(password):
                return Response({
                    'error': {
                        'code': 'authentication_error',
                        'message': 'Invalid credentials',
                        'details': {'non_field_errors': ['Invalid username/email or password']}
                    }
                }, status=status.HTTP_401_UNAUTHORIZED)
            
            # Generate tokens
            refresh = RefreshToken.for_user(user)
            access_token = refresh.access_token
            
            # Serialize user data
            user_serializer = UserProfileSerializer(user)
            
            logger.info(f"User {user.username} logged in successfully")
            
            return Response({
                'access': str(access_token),
                'refresh': str(refresh),
                'user': user_serializer.data
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Login error: {str(e)}", exc_info=True)
            return Response({
                'error': {
                    'code': 'server_error',
                    'message': 'An error occurred during login',
                    'details': {}
                }
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class RegisterView(generics.CreateAPIView):
    """User registration view."""
    queryset = User.objects.all()
    serializer_class = UserRegistrationSerializer
    permission_classes = [AllowAny]
    
    @transaction.atomic
    def create(self, request, *args, **kwargs):
        """Register a new user and return tokens."""
        try:
            serializer = self.get_serializer(data=request.data)
            
            if not serializer.is_valid():
                return Response({
                    'error': {
                        'code': 'validation_error',
                        'message': 'Invalid input provided',
                        'details': serializer.errors
                    }
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Create user
            user = serializer.save()
            
            # Generate tokens
            refresh = RefreshToken.for_user(user)
            access_token = refresh.access_token
            
            # Serialize user data
            user_serializer = UserProfileSerializer(user)
            
            logger.info(f"New user registered: {user.username}")
            
            return Response({
                'access': str(access_token),
                'refresh': str(refresh),
                'user': user_serializer.data,
                'message': 'Registration successful'
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            logger.error(f"Registration error: {str(e)}", exc_info=True)
            return Response({
                'error': {
                    'code': 'server_error',
                    'message': 'An error occurred during registration',
                    'details': {}
                }
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class LogoutView(generics.GenericAPIView):
    """User logout view that blacklists the refresh token."""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """Logout user by blacklisting refresh token."""
        try:
            refresh_token = request.data.get('refresh')
            
            if not refresh_token:
                return Response({
                    'error': {
                        'code': 'validation_error',
                        'message': 'Refresh token is required',
                        'details': {'refresh': ['This field is required.']}
                    }
                }, status=status.HTTP_400_BAD_REQUEST)
            
            try:
                token = RefreshToken(refresh_token)
                token.blacklist()
                
                logger.info(f"User {request.user.username} logged out successfully")
                
                return Response({
                    'message': 'Logout successful'
                }, status=status.HTTP_200_OK)
                
            except TokenError as e:
                return Response({
                    'error': {
                        'code': 'token_error',
                        'message': 'Invalid or expired token',
                        'details': {'refresh': ['Invalid token']}
                    }
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            logger.error(f"Logout error: {str(e)}", exc_info=True)
            return Response({
                'error': {
                    'code': 'server_error',
                    'message': 'An error occurred during logout',
                    'details': {}
                }
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class UserProfileView(generics.RetrieveAPIView):
    """Get current user profile."""
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        """Return the current user."""
        return self.request.user
    
    def get(self, request, *args, **kwargs):
        """Get current user profile."""
        try:
            user = self.get_object()
            serializer = self.get_serializer(user)
            
            return Response(serializer.data, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Get profile error: {str(e)}", exc_info=True)
            return Response({
                'error': {
                    'code': 'server_error',
                    'message': 'An error occurred while fetching profile',
                    'details': {}
                }
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class UpdateProfileView(generics.UpdateAPIView):
    """Update user profile."""
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        """Return the current user."""
        return self.request.user
    
    def put(self, request, *args, **kwargs):
        """Update user profile."""
        try:
            user = self.get_object()
            serializer = self.get_serializer(user, data=request.data, partial=False)
            
            if not serializer.is_valid():
                return Response({
                    'error': {
                        'code': 'validation_error',
                        'message': 'Invalid input provided',
                        'details': serializer.errors
                    }
                }, status=status.HTTP_400_BAD_REQUEST)
            
            serializer.save()
            
            logger.info(f"User {user.username} updated profile")
            
            return Response(serializer.data, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Update profile error: {str(e)}", exc_info=True)
            return Response({
                'error': {
                    'code': 'server_error',
                    'message': 'An error occurred while updating profile',
                    'details': {}
                }
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def patch(self, request, *args, **kwargs):
        """Partially update user profile."""
        try:
            user = self.get_object()
            serializer = self.get_serializer(user, data=request.data, partial=True)
            
            if not serializer.is_valid():
                return Response({
                    'error': {
                        'code': 'validation_error',
                        'message': 'Invalid input provided',
                        'details': serializer.errors
                    }
                }, status=status.HTTP_400_BAD_REQUEST)
            
            serializer.save()
            
            logger.info(f"User {user.username} partially updated profile")
            
            return Response(serializer.data, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Partial update profile error: {str(e)}", exc_info=True)
            return Response({
                'error': {
                    'code': 'server_error',
                    'message': 'An error occurred while updating profile',
                    'details': {}
                }
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ChangePasswordView(generics.GenericAPIView):
    """Change user password."""
    serializer_class = ChangePasswordSerializer
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """Change user password."""
        try:
            serializer = self.get_serializer(data=request.data, context={'request': request})
            
            if not serializer.is_valid():
                return Response({
                    'error': {
                        'code': 'validation_error',
                        'message': 'Invalid input provided',
                        'details': serializer.errors
                    }
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Save new password
            serializer.save()
            
            logger.info(f"User {request.user.username} changed password")
            
            return Response({
                'message': 'Password changed successfully'
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Change password error: {str(e)}", exc_info=True)
            return Response({
                'error': {
                    'code': 'server_error',
                    'message': 'An error occurred while changing password',
                    'details': {}
                }
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class DeleteAccountView(generics.DestroyAPIView):
    """Delete user account."""
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        """Return the current user."""
        return self.request.user
    
    def delete(self, request, *args, **kwargs):
        """Delete user account."""
        try:
            password = request.data.get('password')
            
            if not password:
                return Response({
                    'error': {
                        'code': 'validation_error',
                        'message': 'Password confirmation is required',
                        'details': {'password': ['This field is required.']}
                    }
                }, status=status.HTTP_400_BAD_REQUEST)
            
            user = self.get_object()
            
            # Verify password before deletion
            if not user.check_password(password):
                return Response({
                    'error': {
                        'code': 'authentication_error',
                        'message': 'Invalid password',
                        'details': {'password': ['Incorrect password']}
                    }
                }, status=status.HTTP_400_BAD_REQUEST)
            
            username = user.username
            
            # Delete the user
            user.delete()
            
            logger.info(f"User account deleted: {username}")
            
            return Response({
                'message': 'Account deleted successfully'
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Delete account error: {str(e)}", exc_info=True)
            return Response({
                'error': {
                    'code': 'server_error',
                    'message': 'An error occurred while deleting account',
                    'details': {}
                }
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# Alias for backward compatibility
LoginView = CustomTokenObtainPairView