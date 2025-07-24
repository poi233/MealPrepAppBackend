"""
Meal plan serializers for MealPrepAI Django backend.
"""
from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import datetime, date
from apps.recipes.models import Recipe
from apps.recipes.serializers import RecipeListSerializer
from .models import MealPlan, MealPlanItem

User = get_user_model()


class MealPlanItemSerializer(serializers.ModelSerializer):
    """Serializer for meal plan items with recipe details."""
    recipe = RecipeListSerializer(read_only=True)
    recipe_id = serializers.UUIDField(write_only=True)

    class Meta:
        model = MealPlanItem
        fields = [
            'meal_plan', 'recipe', 'recipe_id', 'day_of_week', 
            'meal_type', 'added_at'
        ]
        read_only_fields = ['added_at']

    def validate_day_of_week(self, value):
        """Validate day of week."""
        if value is not None and (value < 0 or value > 6):
            raise serializers.ValidationError("Day of week must be between 0 (Monday) and 6 (Sunday)")
        return value

    def validate_meal_type(self, value):
        """Validate meal type."""
        valid_meal_types = ['breakfast', 'lunch', 'dinner', 'snack']
        if value and value not in valid_meal_types:
            raise serializers.ValidationError(f"Invalid meal type. Must be one of: {', '.join(valid_meal_types)}")
        return value

    def validate_recipe_id(self, value):
        """Validate that recipe exists."""
        try:
            Recipe.objects.get(id=value)
        except Recipe.DoesNotExist:
            raise serializers.ValidationError("Recipe not found")
        return value


class MealPlanSerializer(serializers.ModelSerializer):
    """Serializer for meal plans with nested meal plan items."""
    items = MealPlanItemSerializer(many=True, read_only=True)
    user = serializers.StringRelatedField(read_only=True)
    user_id = serializers.UUIDField(source='user.id', read_only=True)

    class Meta:
        model = MealPlan
        fields = [
            'id', 'user', 'user_id', 'name', 'description', 'week_start_date',
            'is_active', 'plan_description', 'analysis_text', 'items',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate_name(self, value):
        """Validate meal plan name."""
        if not value or not value.strip():
            raise serializers.ValidationError("Meal plan name is required")
        
        name = value.strip()[:255]
        
        # Check for duplicate names for the same user
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            queryset = MealPlan.objects.filter(user=request.user, name__iexact=name)
            if self.instance:
                queryset = queryset.exclude(pk=self.instance.pk)
            
            if queryset.exists():
                raise serializers.ValidationError("You already have a meal plan with this name")
        
        return name

    def validate_description(self, value):
        """Validate meal plan description."""
        if value:
            return value.strip()[:1000]
        return value

    def validate_plan_description(self, value):
        """Validate plan description."""
        if value:
            return value.strip()[:2000]
        return value

    def validate_analysis_text(self, value):
        """Validate analysis text."""
        if value:
            return value.strip()[:5000]
        return value

    def validate_week_start_date(self, value):
        """Validate week start date."""
        if not value:
            raise serializers.ValidationError("Week start date is required")
        
        # Ensure it's a Monday (weekday 0)
        if value.weekday() != 0:
            raise serializers.ValidationError("Week start date must be a Monday")
        
        # Don't allow dates too far in the past
        if value < date.today().replace(day=1) - timezone.timedelta(days=365):
            raise serializers.ValidationError("Week start date cannot be more than a year in the past")
        
        return value

    def validate(self, attrs):
        """Cross-field validation."""
        # If setting is_active to True, ensure no other meal plan is active for the same week
        if attrs.get('is_active', False):
            week_start_date = attrs.get('week_start_date')
            request = self.context.get('request')
            
            if week_start_date and request and hasattr(request, 'user'):
                queryset = MealPlan.objects.filter(
                    user=request.user,
                    week_start_date=week_start_date,
                    is_active=True
                )
                
                if self.instance:
                    queryset = queryset.exclude(pk=self.instance.pk)
                
                if queryset.exists():
                    raise serializers.ValidationError({
                        'is_active': 'Another meal plan is already active for this week'
                    })
        
        return attrs

    def create(self, validated_data):
        """Create a new meal plan."""
        request = self.context.get('request')
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            validated_data['user'] = request.user
        
        return MealPlan.objects.create(**validated_data)

    def update(self, instance, validated_data):
        """Update an existing meal plan."""
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        instance.save()
        return instance


class MealPlanListSerializer(MealPlanSerializer):
    """Simplified serializer for meal plan lists (excludes items)."""
    items_count = serializers.SerializerMethodField()

    class Meta(MealPlanSerializer.Meta):
        fields = [
            'id', 'user_id', 'name', 'description', 'week_start_date',
            'is_active', 'items_count', 'created_at', 'updated_at'
        ]

    def get_items_count(self, obj):
        """Get count of items in the meal plan."""
        return obj.items.count()


class MealPlanItemCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating meal plan items during meal plan creation."""
    recipe_id = serializers.UUIDField()

    class Meta:
        model = MealPlanItem
        fields = ['recipe_id', 'day_of_week', 'meal_type']

    def validate_day_of_week(self, value):
        """Validate day of week."""
        if value is not None and (value < 0 or value > 6):
            raise serializers.ValidationError("Day of week must be between 0 (Monday) and 6 (Sunday)")
        return value

    def validate_meal_type(self, value):
        """Validate meal type."""
        valid_meal_types = ['breakfast', 'lunch', 'dinner', 'snack']
        if value and value not in valid_meal_types:
            raise serializers.ValidationError(f"Invalid meal type. Must be one of: {', '.join(valid_meal_types)}")
        return value

    def validate_recipe_id(self, value):
        """Validate that recipe exists."""
        try:
            Recipe.objects.get(id=value)
        except Recipe.DoesNotExist:
            raise serializers.ValidationError("Recipe not found")
        return value


class MealPlanCreateSerializer(MealPlanSerializer):
    """Serializer for meal plan creation."""
    items = MealPlanItemCreateSerializer(many=True, required=False)

    class Meta(MealPlanSerializer.Meta):
        fields = MealPlanSerializer.Meta.fields

    def create(self, validated_data):
        """Create meal plan with items."""
        items_data = validated_data.pop('items', [])
        meal_plan = super().create(validated_data)
        
        # Create meal plan items
        for item_data in items_data:
            recipe_id = item_data.pop('recipe_id')
            recipe = Recipe.objects.get(id=recipe_id)
            MealPlanItem.objects.create(
                meal_plan=meal_plan,
                recipe=recipe,
                **item_data
            )
        
        return meal_plan


class AddMealPlanItemSerializer(serializers.Serializer):
    """Serializer for adding items to a meal plan."""
    recipe_id = serializers.UUIDField()
    day_of_week = serializers.IntegerField(min_value=0, max_value=6)
    meal_type = serializers.ChoiceField(choices=['breakfast', 'lunch', 'dinner', 'snack'])

    def validate_recipe_id(self, value):
        """Validate that recipe exists."""
        try:
            Recipe.objects.get(id=value)
        except Recipe.DoesNotExist:
            raise serializers.ValidationError("Recipe not found")
        return value

    def validate(self, attrs):
        """Validate that the combination doesn't already exist."""
        meal_plan = self.context.get('meal_plan')
        if meal_plan:
            existing = MealPlanItem.objects.filter(
                meal_plan=meal_plan,
                day_of_week=attrs['day_of_week'],
                meal_type=attrs['meal_type']
            ).exists()
            
            if existing:
                raise serializers.ValidationError(
                    "A recipe is already assigned to this day and meal type"
                )
        
        return attrs

    def save(self):
        """Create the meal plan item."""
        meal_plan = self.context['meal_plan']
        recipe = Recipe.objects.get(id=self.validated_data['recipe_id'])
        
        # Remove existing item if it exists (for updates)
        MealPlanItem.objects.filter(
            meal_plan=meal_plan,
            day_of_week=self.validated_data['day_of_week'],
            meal_type=self.validated_data['meal_type']
        ).delete()
        
        # Create new item
        item = MealPlanItem.objects.create(
            meal_plan=meal_plan,
            recipe=recipe,
            day_of_week=self.validated_data['day_of_week'],
            meal_type=self.validated_data['meal_type']
        )
        
        return item


class MealPlanAnalysisSerializer(serializers.Serializer):
    """Serializer for meal plan analysis requests."""
    analysis_type = serializers.ChoiceField(
        choices=['nutrition', 'variety', 'balance', 'full'],
        default='full'
    )
    include_recommendations = serializers.BooleanField(default=True)

    def validate_analysis_type(self, value):
        """Validate analysis type."""
        valid_types = ['nutrition', 'variety', 'balance', 'full']
        if value not in valid_types:
            raise serializers.ValidationError(f"Invalid analysis type. Must be one of: {', '.join(valid_types)}")
        return value