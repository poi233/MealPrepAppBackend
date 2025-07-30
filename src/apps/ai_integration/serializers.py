"""
AI Integration serializers for MealPrepAI Django backend.
"""
from rest_framework import serializers
from datetime import date, datetime
from typing import Dict, Any
from django.utils import timezone
from django.conf import settings


class GenerateMealPlanSerializer(serializers.Serializer):
    """Serializer for meal plan generation requests."""
    plan_description = serializers.CharField(
        max_length=2000,
        help_text="Description of the desired meal plan"
    )
    dietary_preferences = serializers.JSONField(
        required=False,
        help_text="User's dietary preferences (vegetarian, vegan, etc.)"
    )
    allergies = serializers.ListField(
        child=serializers.CharField(max_length=100),
        required=False,
        help_text="List of food allergies to avoid"
    )
    dislikes = serializers.ListField(
        child=serializers.CharField(max_length=100),
        required=False,
        help_text="List of foods the user dislikes"
    )
    calorie_target = serializers.IntegerField(
        required=False,
        min_value=1000,
        max_value=5000,
        help_text="Daily calorie target"
    )
    week_start_date = serializers.DateField(
        required=False,
        help_text="Start date for the meal plan (defaults to next Monday)"
    )
    additional_requirements = serializers.CharField(
        max_length=1000,
        required=False,
        allow_blank=True,
        help_text="Any additional requirements or preferences"
    )

    def validate_plan_description(self, value):
        """Validate plan description."""
        if not value or not value.strip():
            raise serializers.ValidationError("Plan description is required")
        return value.strip()

    def validate_week_start_date(self, value):
        """Validate week start date."""
        if value and value < date.today():
            raise serializers.ValidationError("Week start date cannot be in the past")
        return value

    def validate_dietary_preferences(self, value):
        """Validate dietary preferences JSON."""
        if value and not isinstance(value, dict):
            raise serializers.ValidationError("Dietary preferences must be a valid JSON object")
        return value

    def validate_allergies(self, value):
        """Validate allergies list."""
        if value and len(value) > 20:
            raise serializers.ValidationError("Too many allergies specified (max 20)")
        return value

    def validate_dislikes(self, value):
        """Validate dislikes list."""
        if value and len(value) > 30:
            raise serializers.ValidationError("Too many dislikes specified (max 30)")
        return value


class GeneratedMealPlanSerializer(serializers.Serializer):
    """Serializer for generated meal plan response."""
    id = serializers.CharField(default="ai-generated")  # Add ID field for iOS compatibility
    user_id = serializers.CharField(required=False)  # Add user_id field
    name = serializers.CharField()
    description = serializers.CharField()
    week_start_date = serializers.DateField()
    is_active = serializers.BooleanField(default=False)  # Add is_active field
    plan_description = serializers.CharField()
    analysis_text = serializers.CharField()
    items = serializers.JSONField(required=False)  # Add items field for compatibility
    items_count = serializers.IntegerField(default=0)  # Add items_count field
    daily_meals = serializers.JSONField()
    created_at = serializers.DateTimeField(default=serializers.CreateOnlyDefault(timezone.now))  # Add created_at
    updated_at = serializers.DateTimeField(default=serializers.CreateOnlyDefault(timezone.now))  # Add updated_at


class GenerateRecipeSerializer(serializers.Serializer):
    """Serializer for recipe generation requests."""
    name = serializers.CharField(
        max_length=255,
        help_text="Name of the recipe to generate"
    )
    description = serializers.CharField(
        max_length=1000,
        required=False,
        allow_blank=True,
        help_text="Brief description of the desired recipe"
    )
    cuisine = serializers.CharField(
        max_length=100,
        required=False,
        allow_blank=True,
        help_text="Cuisine type (e.g., Italian, Asian, Mexican)"
    )
    difficulty = serializers.ChoiceField(
        choices=['easy', 'medium', 'hard'],
        default='medium',
        help_text="Difficulty level"
    )
    prep_time = serializers.IntegerField(
        required=False,
        min_value=1,
        max_value=300,
        help_text="Preparation time in minutes"
    )
    cook_time = serializers.IntegerField(
        required=False,
        min_value=1,
        max_value=480,
        help_text="Cooking time in minutes"
    )
    meal_type = serializers.ChoiceField(
        choices=['breakfast', 'lunch', 'dinner', 'snack'],
        required=False,
        help_text="Type of meal"
    )
    dietary_restrictions = serializers.ListField(
        child=serializers.CharField(max_length=50),
        required=False,
        help_text="Dietary restrictions (vegetarian, gluten-free, etc.)"
    )
    ingredients = serializers.ListField(
        child=serializers.CharField(max_length=200),
        required=False,
        help_text="Specific ingredients to include"
    )
    additional_requirements = serializers.CharField(
        max_length=1000,
        required=False,
        allow_blank=True,
        help_text="Additional requirements or preferences"
    )

    def validate_name(self, value):
        """Validate recipe name."""
        if not value or not value.strip():
            raise serializers.ValidationError("Recipe name is required")
        return value.strip()

    def validate_ingredients(self, value):
        """Validate ingredients list."""
        if value and len(value) > 50:
            raise serializers.ValidationError("Too many ingredients specified (max 50)")
        return value

    def validate_dietary_restrictions(self, value):
        """Validate dietary restrictions."""
        if value and len(value) > 10:
            raise serializers.ValidationError("Too many dietary restrictions specified (max 10)")
        return value


class IngredientSerializer(serializers.Serializer):
    """Serializer for individual ingredient with name and amount."""
    name = serializers.CharField(help_text="Ingredient name (e.g., '鸡胸肉')")
    amount = serializers.CharField(help_text="Ingredient amount for one serving (e.g., '150克')")


class GeneratedRecipeSerializer(serializers.Serializer):
    """Serializer for generated recipe response with deterministic UUID support."""
    id = serializers.CharField(
        required=False,
        help_text="Deterministic UUID based on recipe content"
    )
    name = serializers.CharField()
    description = serializers.CharField()
    cuisine = serializers.CharField()
    difficulty = serializers.CharField()
    prep_time = serializers.IntegerField()
    cook_time = serializers.IntegerField()
    image_url = serializers.CharField()
    ingredients = serializers.ListField(
        child=IngredientSerializer(),
        help_text="List of ingredients with name and amount for one serving"
    )
    instructions = serializers.ListField(
        child=serializers.CharField(),
        help_text="List of cooking steps as separate strings"
    )
    nutrition_info = serializers.JSONField()
    tags = serializers.ListField(child=serializers.CharField())
    
    def to_representation(self, instance):
        """Add deterministic UUID if not present."""
        data = super().to_representation(instance)
        
        # Generate deterministic UUID if not already present
        if not data.get('id'):
            from .services import generate_deterministic_recipe_uuid
            data['id'] = generate_deterministic_recipe_uuid(data)
            
        return data


class AnalyzeMealPlanSerializer(serializers.Serializer):
    """Serializer for meal plan analysis requests."""
    meal_plan_id = serializers.UUIDField(
        help_text="ID of the meal plan to analyze"
    )
    plan_description = serializers.CharField(
        max_length=2000,
        required=False,
        allow_blank=True,
        help_text="Original plan description for context"
    )
    analysis_type = serializers.ChoiceField(
        choices=['nutrition', 'variety', 'balance', 'full'],
        default='full',
        help_text="Type of analysis to perform"
    )
    include_recommendations = serializers.BooleanField(
        default=True,
        help_text="Whether to include AI recommendations"
    )

    def validate_meal_plan_id(self, value):
        """Validate meal plan exists and belongs to user."""
        from apps.meal_plans.models import MealPlan
        
        request = self.context.get('request')
        if not request or not hasattr(request, 'user'):
            raise serializers.ValidationError("Authentication required")
        
        try:
            meal_plan = MealPlan.objects.get(id=value, user=request.user)
        except MealPlan.DoesNotExist:
            raise serializers.ValidationError("Meal plan not found or not accessible")
        
        return value


class MealPlanAnalysisSerializer(serializers.Serializer):
    """Serializer for meal plan analysis response."""
    meal_plan_id = serializers.UUIDField()
    analysis_type = serializers.CharField()
    total_recipes = serializers.IntegerField()
    analysis_text = serializers.CharField()
    analysis_date = serializers.DateTimeField()


class CreateRecipeFromAISerializer(serializers.Serializer):
    """Serializer for creating a recipe from AI-generated data with enhanced UUID support."""
    ai_recipe_data = GeneratedRecipeSerializer()
    save_to_account = serializers.BooleanField(
        default=True,
        help_text="Whether to save the recipe to user's account"
    )
    add_to_meal_plan = serializers.UUIDField(
        required=False,
        help_text="Meal plan ID to add the recipe to (optional)"
    )
    meal_plan_day = serializers.IntegerField(
        required=False,
        min_value=0,
        max_value=6,
        help_text="Day of week to add to meal plan (0=Monday, 6=Sunday)"
    )
    meal_plan_type = serializers.ChoiceField(
        choices=['breakfast', 'lunch', 'dinner', 'snack'],
        required=False,
        help_text="Meal type for meal plan assignment"
    )
    recipe_id = serializers.UUIDField(
        required=False,
        help_text="Optional: Pre-computed deterministic UUID for the recipe"
    )

    def validate(self, attrs):
        """Cross-field validation."""
        add_to_meal_plan = attrs.get('add_to_meal_plan')
        meal_plan_day = attrs.get('meal_plan_day')
        meal_plan_type = attrs.get('meal_plan_type')
        
        if add_to_meal_plan:
            if meal_plan_day is None or meal_plan_type is None:
                raise serializers.ValidationError({
                    'add_to_meal_plan': 'meal_plan_day and meal_plan_type are required when adding to meal plan'
                })
        
        return attrs


class StandardAPIResponseSerializer(serializers.Serializer):
    """Standard API response format for consistency."""
    success = serializers.BooleanField()
    message = serializers.CharField(required=False)
    data = serializers.JSONField(required=False)
    errors = serializers.JSONField(required=False)
    timestamp = serializers.DateTimeField()
    

class RecipeCreationResponseSerializer(serializers.Serializer):
    """Response serializer for single recipe creation."""
    success = serializers.BooleanField()
    recipe = serializers.JSONField(
        required=False,
        help_text="Recipe data if creation was successful"
    )
    status = serializers.ChoiceField(
        choices=['created', 'already_exists', 'updated', 'failed'],
        help_text="Status of the recipe creation operation"
    )
    message = serializers.CharField(
        help_text="User-friendly status description"
    )
    recipe_id = serializers.UUIDField(
        required=False,
        help_text="UUID of the created/existing recipe"
    )
    timestamp = serializers.DateTimeField()
    

class BatchRecipeItemResultSerializer(serializers.Serializer):
    """Individual recipe result in batch operations."""
    recipe_id = serializers.UUIDField(help_text="Recipe UUID")
    name = serializers.CharField(help_text="Recipe name")
    status = serializers.ChoiceField(
        choices=['created', 'already_exists', 'failed'],
        help_text="Processing status for this recipe"
    )
    error = serializers.CharField(
        required=False,
        help_text="Error message if processing failed"
    )
    meal_plan_added = serializers.BooleanField(
        default=False,
        help_text="Whether recipe was successfully added to meal plan"
    )

    def validate_add_to_meal_plan(self, value):
        """Validate meal plan exists and belongs to user."""
        if value:
            from apps.meal_plans.models import MealPlan
            
            request = self.context.get('request')
            if not request or not hasattr(request, 'user'):
                raise serializers.ValidationError("Authentication required")
            
            try:
                meal_plan = MealPlan.objects.get(id=value, user=request.user)
            except MealPlan.DoesNotExist:
                raise serializers.ValidationError("Meal plan not found or not accessible")
        
        return value


class SuggestRecipeModificationsSerializer(serializers.Serializer):
    """Serializer for recipe modification suggestions."""
    recipe_id = serializers.UUIDField(
        help_text="ID of the recipe to modify"
    )
    modification_type = serializers.ChoiceField(
        choices=['dietary', 'difficulty', 'time', 'ingredients', 'serving_size'],
        help_text="Type of modification to suggest"
    )
    target_value = serializers.CharField(
        max_length=200,
        help_text="Target value for the modification (e.g., 'vegetarian', 'easier', '30 minutes')"
    )
    additional_notes = serializers.CharField(
        max_length=500,
        required=False,
        allow_blank=True,
        help_text="Additional notes or requirements"
    )

    def validate_recipe_id(self, value):
        """Validate recipe exists and is accessible."""
        from apps.recipes.models import Recipe
        
        try:
            recipe = Recipe.objects.get(id=value)
        except Recipe.DoesNotExist:
            raise serializers.ValidationError("Recipe not found")
        
        return value


class RecipeModificationSuggestionsSerializer(serializers.Serializer):
    """Serializer for recipe modification suggestions response."""
    original_recipe_id = serializers.UUIDField()
    modification_type = serializers.CharField()
    suggested_changes = serializers.JSONField()
    estimated_impact = serializers.JSONField()
    alternative_ingredients = serializers.ListField(
        child=serializers.JSONField(),
        required=False
    )
    modified_instructions = serializers.CharField(required=False)
    modified_nutrition = serializers.JSONField(required=False)


class BatchCreateRecipeItemSerializer(serializers.Serializer):
    """Serializer for individual recipe item in batch creation."""
    ai_recipe_data = GeneratedRecipeSerializer()
    meal_plan_day = serializers.IntegerField(
        required=False,
        min_value=0,
        max_value=6,
        help_text="Day of week to add to meal plan (0=Monday, 6=Sunday)"
    )
    meal_plan_type = serializers.ChoiceField(
        choices=['breakfast', 'lunch', 'dinner', 'snack'],
        required=False,
        help_text="Meal type for meal plan assignment"
    )


class BatchCreateRecipesFromAISerializer(serializers.Serializer):
    """Enhanced serializer for batch recipe creation with improved response format."""
    recipes = serializers.ListField(
        child=BatchCreateRecipeItemSerializer(),
        min_length=1,
        max_length=20,
        help_text="List of recipes to create (max 20 per batch)"
    )
    meal_plan_id = serializers.UUIDField(
        required=False,
        help_text="Optional meal plan ID to add all recipes to"
    )
    save_to_account = serializers.BooleanField(
        default=True,
        help_text="Whether to save all recipes to user's account"
    )
    skip_duplicates = serializers.BooleanField(
        default=True,
        help_text="Whether to skip recipes that already exist"
    )

    def validate_meal_plan_id(self, value):
        """Validate meal plan exists and belongs to user."""
        if value:
            from apps.meal_plans.models import MealPlan
            
            request = self.context.get('request')
            if not request or not hasattr(request, 'user'):
                raise serializers.ValidationError("Authentication required")
            
            try:
                meal_plan = MealPlan.objects.get(id=value, user=request.user)
            except MealPlan.DoesNotExist:
                raise serializers.ValidationError("Meal plan not found or not accessible")
        
        return value

    def validate(self, attrs):
        """Enhanced cross-field validation for batch creation."""
        meal_plan_id = attrs.get('meal_plan_id')
        recipes = attrs.get('recipes', [])
        
        # If meal plan is specified, validate that recipes with meal plan assignment have required fields
        if meal_plan_id:
            for i, recipe_item in enumerate(recipes):
                if 'meal_plan_day' in recipe_item or 'meal_plan_type' in recipe_item:
                    if recipe_item.get('meal_plan_day') is None or recipe_item.get('meal_plan_type') is None:
                        raise serializers.ValidationError({
                            'recipes': f'Recipe {i}: meal_plan_day and meal_plan_type are required when meal_plan_id is specified'
                        })
        
        # Validate batch size for performance
        if len(recipes) > 20:
            raise serializers.ValidationError({
                'recipes': 'Maximum 20 recipes allowed per batch operation'
            })
            
        # Validate recipe data structure
        for i, recipe_item in enumerate(recipes):
            ai_recipe_data = recipe_item.get('ai_recipe_data', {})
            if not ai_recipe_data.get('name'):
                raise serializers.ValidationError({
                    'recipes': f'Recipe {i}: name is required'
                })
        
        return attrs


class BatchCreateRecipesResponseSerializer(serializers.Serializer):
    """Enhanced serializer for batch recipe creation response."""
    success = serializers.BooleanField()
    total_processed = serializers.IntegerField()
    successful = serializers.IntegerField()
    failed = serializers.IntegerField()
    already_exists = serializers.IntegerField(default=0)
    summary = serializers.JSONField(
        help_text="Summary statistics and processing information"
    )
    results = serializers.ListField(
        child=serializers.JSONField(),
        help_text="Detailed results for each recipe processed"
    )
    timestamp = serializers.DateTimeField()
    processing_time = serializers.FloatField(
        required=False,
        help_text="Processing time in seconds"
    )