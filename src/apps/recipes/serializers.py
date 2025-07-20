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
    ingredients = serializers.SerializerMethodField()
    nutrition_info = serializers.SerializerMethodField()
    created_by_user = serializers.StringRelatedField(read_only=True)
    created_by_user_id = serializers.UUIDField(source='created_by_user.id', read_only=True)
    total_time = serializers.SerializerMethodField()

    def get_ingredients(self, obj):
        """Handle ingredients field - can be strings or objects."""
        if not obj.ingredients:
            return []
        
        # If ingredients is already a list of objects with proper structure, return as is
        if isinstance(obj.ingredients, list) and obj.ingredients:
            first_ingredient = obj.ingredients[0]
            if isinstance(first_ingredient, dict) and 'name' in first_ingredient:
                return obj.ingredients
            elif isinstance(first_ingredient, str):
                # Convert string ingredients to object format
                return [{'name': ingredient, 'amount': 1, 'unit': 'piece', 'notes': ''} 
                       for ingredient in obj.ingredients]
        
        # Fallback: return raw ingredients data
        return obj.ingredients

    def get_nutrition_info(self, obj):
        """Handle nutrition_info field safely."""
        if not obj.nutrition_info:
            return {}
        
        # If it's already a dict, return as is
        if isinstance(obj.nutrition_info, dict):
            # Ensure all values are numbers or None
            safe_nutrition = {}
            for key, value in obj.nutrition_info.items():
                if value is not None:
                    try:
                        safe_nutrition[key] = float(value)
                    except (ValueError, TypeError):
                        safe_nutrition[key] = None
                else:
                    safe_nutrition[key] = None
            return safe_nutrition
        
        # Fallback: return empty dict
        return {}

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

    def validate(self, attrs):
        """Cross-field validation including ingredients."""
        # Validate ingredients from initial_data since we use SerializerMethodField
        ingredients_data = self.initial_data.get('ingredients', [])
        if not ingredients_data:
            raise serializers.ValidationError({
                'ingredients': 'At least one ingredient is required'
            })
        
        if len(ingredients_data) > 50:
            raise serializers.ValidationError({
                'ingredients': 'Too many ingredients (max 50)'
            })
        
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

    def validate_image_url(self, value):
        """Validate image URL."""
        if value and not value.strip():
            return None
        return value



    def create(self, validated_data):
        """Create a new recipe."""
        # Handle ingredients and nutrition_info from initial_data since we use SerializerMethodField
        ingredients_data = self.initial_data.get('ingredients', [])
        nutrition_info_data = self.initial_data.get('nutrition_info', {})
        
        # Process ingredients data
        if ingredients_data:
            processed_ingredients = []
            for ingredient in ingredients_data:
                if isinstance(ingredient, dict):
                    # Convert Decimal values to float for JSON serialization
                    if 'amount' in ingredient and ingredient['amount'] is not None:
                        try:
                            ingredient['amount'] = float(ingredient['amount'])
                        except (ValueError, TypeError):
                            ingredient['amount'] = 1.0
                    processed_ingredients.append(ingredient)
                elif isinstance(ingredient, str):
                    # Convert string to object format
                    processed_ingredients.append({
                        'name': ingredient,
                        'amount': 1.0,
                        'unit': 'piece',
                        'notes': ''
                    })
            ingredients_data = processed_ingredients
        
        # Process nutrition info data safely
        processed_nutrition = {}
        if nutrition_info_data and isinstance(nutrition_info_data, dict):
            for key, value in nutrition_info_data.items():
                if value is not None:
                    try:
                        processed_nutrition[key] = float(value)
                    except (ValueError, TypeError):
                        processed_nutrition[key] = None
                else:
                    processed_nutrition[key] = None
        
        # Set the created_by_user from the request context
        request = self.context.get('request')
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            validated_data['created_by_user'] = request.user
        
        recipe = Recipe.objects.create(
            **validated_data,
            ingredients=ingredients_data,
            nutrition_info=processed_nutrition
        )
        
        return recipe

    def update(self, instance, validated_data):
        """Update an existing recipe."""
        # Handle ingredients and nutrition_info from initial_data since we use SerializerMethodField
        ingredients_data = self.initial_data.get('ingredients')
        nutrition_info_data = self.initial_data.get('nutrition_info')
        
        # Update basic fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        # Update ingredients if provided
        if ingredients_data is not None:
            processed_ingredients = []
            for ingredient in ingredients_data:
                if isinstance(ingredient, dict):
                    # Convert Decimal values to float for JSON serialization
                    if 'amount' in ingredient and ingredient['amount'] is not None:
                        try:
                            ingredient['amount'] = float(ingredient['amount'])
                        except (ValueError, TypeError):
                            ingredient['amount'] = 1.0
                    processed_ingredients.append(ingredient)
                elif isinstance(ingredient, str):
                    # Convert string to object format
                    processed_ingredients.append({
                        'name': ingredient,
                        'amount': 1.0,
                        'unit': 'piece',
                        'notes': ''
                    })
            instance.ingredients = processed_ingredients
        
        # Update nutrition info if provided
        if nutrition_info_data is not None:
            processed_nutrition = {}
            if isinstance(nutrition_info_data, dict):
                for key, value in nutrition_info_data.items():
                    if value is not None:
                        try:
                            processed_nutrition[key] = float(value)
                        except (ValueError, TypeError):
                            processed_nutrition[key] = None
                    else:
                        processed_nutrition[key] = None
            instance.nutrition_info = processed_nutrition
        
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
    """Full serializer for recipe lists (includes all fields including ingredients and instructions)."""
    class Meta(RecipeSerializer.Meta):
        fields = [
            'id', 'created_by_user', 'created_by_user_id', 'name', 'description',
            'ingredients', 'instructions', 'nutrition_info', 'cuisine',
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