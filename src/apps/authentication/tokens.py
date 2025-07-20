"""
Custom JWT token serializers and utilities for MealPrepAI Django backend.
"""
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework import serializers
from django.contrib.auth import authenticate
from .models import User
from .serializers import UserProfileSerializer


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Custom token serializer that includes user data in the response.
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Remove the username field and add our custom fields
        self.fields.pop('username', None)
        self.fields['username'] = serializers.CharField(required=True)
        self.fields['password'] = serializers.CharField(required=True, write_only=True)
    
    def validate(self, attrs):
        """
        Validate credentials and return tokens with user data.
        """
        username = attrs.get('username')
        password = attrs.get('password')
        
        if not username or not password:
            raise serializers.ValidationError({
                'non_field_errors': ['Username and password are required']
            })
        
        # Try to find user by username or email
        user = None
        try:
            if '@' in username:
                user = User.objects.get(email__iexact=username)
            else:
                user = User.objects.get(username__iexact=username)
        except User.DoesNotExist:
            raise serializers.ValidationError({
                'non_field_errors': ['Invalid credentials']
            })
        
        # Check password
        if not user.check_password(password):
            raise serializers.ValidationError({
                'non_field_errors': ['Invalid credentials']
            })
        
        # Generate tokens
        refresh = RefreshToken.for_user(user)
        
        # Get user data
        user_serializer = UserProfileSerializer(user)
        
        return {
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user': user_serializer.data
        }


class TokenRefreshSerializer(serializers.Serializer):
    """
    Custom token refresh serializer.
    """
    refresh = serializers.CharField(required=True)
    
    def validate(self, attrs):
        """
        Validate refresh token and return new access token.
        """
        refresh_token = attrs.get('refresh')
        
        try:
            refresh = RefreshToken(refresh_token)
            access_token = refresh.access_token
            
            return {
                'access': str(access_token),
                'refresh': str(refresh)
            }
        except Exception as e:
            raise serializers.ValidationError({
                'refresh': ['Invalid or expired token']
            })


class TokenBlacklistSerializer(serializers.Serializer):
    """
    Serializer for blacklisting refresh tokens (logout).
    """
    refresh = serializers.CharField(required=True)
    
    def validate(self, attrs):
        """
        Validate and blacklist refresh token.
        """
        refresh_token = attrs.get('refresh')
        
        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
            return attrs
        except Exception as e:
            raise serializers.ValidationError({
                'refresh': ['Invalid or expired token']
            })