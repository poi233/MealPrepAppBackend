"""
Recipe serializers for MealPrepAI Django backend.
"""
import re
from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Recipe

User = get_user_model()


class IngredientSerializer(serializers.Serializer):
    """Serializer for recipe ingredients."""
    name = serializers.CharField(max_length=100)
    amount = serializers.DecimalField(max_digits=8, decimal_places=2, min_value=0)
    unit = serializers.CharField(max_length=20)
    notes = serializers.CharField(max_length=200, required=False, allow_blank=True)

    def validate_name(self, value):
        """Validate ingredient name."""
        if not value or not value.strip():
            raise serializers.ValidationError("Ingredient name is required")
        return self._sanitize_text(value.strip(), 100)

    def validate_unit(self, value):
        """Validate ingredient unit."""
        if not value or not value.strip():
            raise serializers.ValidationError("Ingredient unit is required")
        return self._sanitize_text(value.strip(), 20)

    def validate_notes(self, value):
        """Validate ingredient notes."""
        if value:
            return self._sanitize_text(value.strip(), 200)
        return value

    def _sanitize_text(self, text, max_length):
        """Sanitize text input."""
        if not text:
            return text
        
        # Remove HTML tags and potentially harmful content
        text = re.sub(r'<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>', '', text, flags=re.IGNORECASE)
        text = re.sub(r'<[^>]*>', '', text)
        text = re.sub(r'javascript:', '', text, flags=re.IGNORECASE)
        
        return text.strip()[:max_length]


class NutritionInfoSerializer(serializers.Serializer):
    """Serializer for nutrition information."""
    calories = serializers.DecimalField(
        max_digits=8, decimal_places=2, required=False, allow_null=True, min_value=0
    )
    protein = serializers.DecimalField(
        max_digits=8, decimal_places=2, required=False, allow_null=True, min_value=0
    )
    carbs = serializers.DecimalField(
        max_digits=8, decimal_places=2, required=False, allow_null=True, min_value=0
    )
    fat = serializers.DecimalField(
        max_digits=8, decimal_places=2, required=False, allow_null=True, min_value=0
    )
    fiber = serializers.DecimalField(
        max_digits=8, decimal_places=2, required=False, allow_null=True, min_value=0
    )
    sugar = serializers.DecimalField(
        max_digits=8, decimal_places=2, required=False, allow_null=True, min_value=0
    )
    sodium = serializers.DecimalField(
        max_digits=8, decimal_places=2, required=False, allow_null=True, min_value=0
    )

    def validate(self, attrs):
        """Validate nutrition info values."""
        # Round all values to 2 decimal places
        for field, value in attrs.items():
            if value is not None:
                attrs[field] = round(float(value), 2)
        return attrs


class RecipeSerializer(serializers.ModelSerializer):
    """Serializer for Recipe model with ingredient and nutrition info handling."""
    ingredients = IngredientSerializer(many=True)
    nutrition_info = NutritionInfoSerializer(required=False)
    created_by_user = serializers.StringRelatedField(read_only=True)
    created_by_user_id = serializers.UUIDField(source='created_by_user.id', read_only=True)
    total_time = serializers.SerializerMethodField()

    class Meta:
        model = Recipe
        fields = [
            'id', 'created_by_user', 'created_by_user_id', 'name', 'description',
            'ingredients', 'instructions', 'nutrition_info', 'cuisine',
            'prep_time', 'cook_time', 'total_time', 'difficulty', 'avg_rating',
            'rating_count', 'image_url', 'tags', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'avg_rating', 'rating_count']

    def get_total_time(self, obj):
        """Calculate total time from prep and cook time."""
        return obj.prep_time + obj.cook_time

    def validate_name(self, value):
        """Validate recipe name."""
        if not value or not value.strip():
            raise serializers.ValidationError("Recipe name is required")
        return self._sanitize_text(value.strip(), 255)

    def validate_description(self, value):
        """Validate recipe description."""
        if value:
            return self._sanitize_text(value.strip(), 1000)
        return value

    def validate_instructions(self, value):
        """Validate recipe instructions."""
        if not value or not value.strip():
            raise serializers.ValidationError("Recipe instructions are required")
        return self._sanitize_text(value.strip(), 5000)

    def validate_cuisine(self, value):
        """Validate cuisine."""
        if value:
            return self._sanitize_text(value.strip(), 100)
        return value

    def validate_prep_time(self, value):
        """Validate prep time."""
        if value is not None and (value < 0 or value > 1440):  # Max 24 hours
            raise serializers.ValidationError("Prep time must be between 0 and 1440 minutes")
        return value

    def validate_cook_time(self, value):
        """Validate cook time."""
        if value is not None and (value < 0 or value > 1440):  # Max 24 hours
            raise serializers.ValidationError("Cook time must be between 0 and 1440 minutes")
        return value

    def validate_difficulty(self, value):
        """Validate difficulty level."""
        valid_difficulties = ['easy', 'medium', 'hard']
        if value and value not in valid_difficulties:
            raise serializers.ValidationError(f"Invalid difficulty. Must be one of: {', '.join(valid_difficulties)}")
        return value

    def validate_tags(self, value):
        """Validate tags array."""
        if not value:
            return []
        
        if not isinstance(value, list):
            raise serializers.ValidationError("Tags must be an array")
        
        if len(value) > 20:
            raise serializers.ValidationError("Too many tags (max 20)")
        
        sanitized_tags = []
        for tag in value:
            if not isinstance(tag, str):
                raise serializers.ValidationError("All tags must be strings")
            
            sanitized_tag = self._sanitize_text(tag.strip(), 30)
            if sanitized_tag and sanitized_tag not in sanitized_tags:
                sanitized_tags.append(sanitized_tag)
        
        return sanitized_tags

    def validate_ingredients(self, value):
        """Validate ingredients array."""
        if not value:
            raise serializers.ValidationError("At least one ingredient is required")
        
        if len(value) > 50:
            raise serializers.ValidationError("Too many ingredients (max 50)")
        
        return value

    def validate_image_url(self, value):
        """Validate image URL."""
        if value and not value.strip():
            return None
        return value

    def validate(self, attrs):
        """Cross-field validation."""
        # Validate total time consistency if both prep and cook times are provided
        prep_time = attrs.get('prep_time', 0)
        cook_time = attrs.get('cook_time', 0)
        
        if prep_time is not None and cook_time is not None:
            total_time = prep_time + cook_time
            if total_time > 1440:  # Max 24 hours total
                raise serializers.ValidationError({
                    'non_field_errors': ['Total cooking time cannot exceed 24 hours']
                })
        
        return attrs

    def create(self, validated_data):
        """Create a new recipe."""
        ingredients_data = validated_data.pop('ingredients')
        nutrition_info_data = validated_data.pop('nutrition_info', {})
        
        # Convert Decimal values to float for JSON serialization
        for ingredient in ingredients_data:
            if 'amount' in ingredient and ingredient['amount'] is not None:
                ingredient['amount'] = float(ingredient['amount'])
        
        # Convert nutrition info Decimal values to float
        for key, value in nutrition_info_data.items():
            if value is not None and hasattr(value, '__float__'):
                nutrition_info_data[key] = float(value)
        
        # Set the created_by_user from the request context
        request = self.context.get('request')
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            validated_data['created_by_user'] = request.user
        
        recipe = Recipe.objects.create(
            **validated_data,
            ingredients=ingredients_data,
            nutrition_info=nutrition_info_data
        )
        
        return recipe

    def update(self, instance, validated_data):
        """Update an existing recipe."""
        ingredients_data = validated_data.pop('ingredients', None)
        nutrition_info_data = validated_data.pop('nutrition_info', None)
        
        # Update basic fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        # Update ingredients if provided
        if ingredients_data is not None:
            # Convert Decimal values to float for JSON serialization
            for ingredient in ingredients_data:
                if 'amount' in ingredient and ingredient['amount'] is not None:
                    ingredient['amount'] = float(ingredient['amount'])
            instance.ingredients = ingredients_data
        
        # Update nutrition info if provided
        if nutrition_info_data is not None:
            # Convert nutrition info Decimal values to float
            for key, value in nutrition_info_data.items():
                if value is not None and hasattr(value, '__float__'):
                    nutrition_info_data[key] = float(value)
            instance.nutrition_info = nutrition_info_data
        
        instance.save()
        return instance

    def _sanitize_text(self, text, max_length):
        """Sanitize text input."""
        if not text:
            return text
        
        # Remove HTML tags and potentially harmful content
        text = re.sub(r'<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>', '', text, flags=re.IGNORECASE)
        text = re.sub(r'<[^>]*>', '', text)
        text = re.sub(r'javascript:', '', text, flags=re.IGNORECASE)
        
        return text.strip()[:max_length]


class RecipeListSerializer(RecipeSerializer):
    """Simplified serializer for recipe lists (excludes heavy fields)."""
    class Meta(RecipeSerializer.Meta):
        fields = [
            'id', 'created_by_user_id', 'name', 'description', 'cuisine',
            'prep_time', 'cook_time', 'total_time', 'difficulty', 'avg_rating',
            'rating_count', 'image_url', 'tags', 'created_at', 'updated_at'
        ]


class RecipeCreateSerializer(RecipeSerializer):
    """Serializer for recipe creation with AI-generated content validation."""
    
    def validate(self, attrs):
        """Enhanced validation for AI-generated recipes."""
        attrs = super().validate(attrs)
        
        # Additional validation for AI-generated content
        name = attrs.get('name', '')
        if len(name) < 3:
            raise serializers.ValidationError({
                'name': 'Recipe name must be at least 3 characters long'
            })
        
        instructions = attrs.get('instructions', '')
        if len(instructions) < 10:
            raise serializers.ValidationError({
                'instructions': 'Instructions must be at least 10 characters long'
            })
        
        return attrs