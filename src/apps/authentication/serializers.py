"""
Authentication serializers for MealPrepAI Django backend.
"""
from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from .models import User


class DietaryPreferencesSerializer(serializers.Serializer):
    """Serializer for dietary preferences nested object."""
    allergies = serializers.ListField(
        child=serializers.CharField(max_length=100),
        required=False,
        allow_empty=True
    )
    diet_type = serializers.CharField(max_length=50, required=False, allow_blank=True)
    dislikes = serializers.ListField(
        child=serializers.CharField(max_length=100),
        required=False,
        allow_empty=True
    )
    calorie_target = serializers.IntegerField(
        required=False,
        allow_null=True,
        min_value=800,
        max_value=5000
    )

    def validate_allergies(self, value):
        """Validate allergies list."""
        if value and len(value) > 20:
            raise serializers.ValidationError("Too many allergies (max 20)")
        return [allergy.strip()[:100] for allergy in value if allergy.strip()]

    def validate_dislikes(self, value):
        """Validate dislikes list."""
        if value and len(value) > 30:
            raise serializers.ValidationError("Too many dislikes (max 30)")
        return [dislike.strip()[:100] for dislike in value if dislike.strip()]

    def validate_diet_type(self, value):
        """Validate diet type."""
        if value:
            valid_diet_types = [
                'vegetarian', 'vegan', 'pescatarian', 'keto', 'paleo',
                'mediterranean', 'low-carb', 'low-fat', 'gluten-free', 'dairy-free'
            ]
            if value.lower() not in valid_diet_types:
                raise serializers.ValidationError(f"Invalid diet type. Must be one of: {', '.join(valid_diet_types)}")
            return value.lower()
        return value


class UserSerializer(serializers.ModelSerializer):
    """Serializer for User model with nested dietary preferences."""
    dietary_preferences = DietaryPreferencesSerializer(required=False)
    password = serializers.CharField(write_only=True, required=False)
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'display_name', 
            'dietary_preferences', 'created_at', 'updated_at', 'password'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
        extra_kwargs = {
            'email': {'required': True},
            'username': {'required': True}
        }

    def validate_username(self, value):
        """Validate username."""
        if not value or len(value.strip()) < 3:
            raise serializers.ValidationError("Username must be at least 3 characters long")
        
        username = value.strip()[:50]
        
        # Check for existing username (excluding current user during updates)
        queryset = User.objects.filter(username__iexact=username)
        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)
        
        if queryset.exists():
            raise serializers.ValidationError("A user with this username already exists")
        
        return username

    def validate_email(self, value):
        """Validate email."""
        if not value:
            raise serializers.ValidationError("Email is required")
        
        email = value.strip().lower()
        
        # Check for existing email (excluding current user during updates)
        queryset = User.objects.filter(email__iexact=email)
        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)
        
        if queryset.exists():
            raise serializers.ValidationError("A user with this email already exists")
        
        return email

    def validate_display_name(self, value):
        """Validate display name."""
        if value:
            return value.strip()[:100]
        return value

    def validate_password(self, value):
        """Validate password using Django's password validators."""
        if value:
            try:
                validate_password(value)
            except DjangoValidationError as e:
                raise serializers.ValidationError(list(e.messages))
        return value

    def validate_dietary_preferences(self, value):
        """Validate dietary preferences."""
        if not value:
            return {}
        
        # Ensure it's a dictionary
        if not isinstance(value, dict):
            raise serializers.ValidationError("Dietary preferences must be an object")
        
        return value

    def create(self, validated_data):
        """Create a new user with hashed password."""
        password = validated_data.pop('password', None)
        dietary_preferences = validated_data.pop('dietary_preferences', {})
        
        user = User.objects.create(
            **validated_data,
            dietary_preferences=dietary_preferences
        )
        
        if password:
            user.set_password(password)
            user.save()
        
        return user

    def update(self, instance, validated_data):
        """Update user instance."""
        password = validated_data.pop('password', None)
        dietary_preferences = validated_data.pop('dietary_preferences', None)
        
        # Update basic fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        # Update dietary preferences if provided
        if dietary_preferences is not None:
            instance.dietary_preferences = dietary_preferences
        
        # Update password if provided
        if password:
            instance.set_password(password)
        
        instance.save()
        return instance


class UserRegistrationSerializer(UserSerializer):
    """Serializer for user registration with required password."""
    password = serializers.CharField(write_only=True, required=True)
    password_confirm = serializers.CharField(write_only=True, required=True)

    class Meta(UserSerializer.Meta):
        fields = UserSerializer.Meta.fields + ['password_confirm']

    def validate(self, attrs):
        """Validate password confirmation."""
        if attrs.get('password') != attrs.get('password_confirm'):
            raise serializers.ValidationError({
                'password_confirm': 'Password confirmation does not match'
            })
        attrs.pop('password_confirm')
        return attrs


class UserProfileSerializer(UserSerializer):
    """Serializer for user profile updates (no password field)."""
    class Meta(UserSerializer.Meta):
        fields = [
            'id', 'username', 'email', 'display_name', 
            'dietary_preferences', 'created_at', 'updated_at'
        ]


class ChangePasswordSerializer(serializers.Serializer):
    """Serializer for password change."""
    current_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True)
    new_password_confirm = serializers.CharField(required=True)

    def validate_current_password(self, value):
        """Validate current password."""
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Current password is incorrect")
        return value

    def validate_new_password(self, value):
        """Validate new password."""
        try:
            validate_password(value)
        except DjangoValidationError as e:
            raise serializers.ValidationError(list(e.messages))
        return value

    def validate(self, attrs):
        """Validate password confirmation."""
        if attrs.get('new_password') != attrs.get('new_password_confirm'):
            raise serializers.ValidationError({
                'new_password_confirm': 'Password confirmation does not match'
            })
        return attrs

    def save(self):
        """Save the new password."""
        user = self.context['request'].user
        user.set_password(self.validated_data['new_password'])
        user.save()
        return user