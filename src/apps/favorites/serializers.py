"""
Favorites serializers for MealPrepAI Django backend.
"""
from rest_framework import serializers
from django.contrib.auth import get_user_model
from apps.recipes.models import Recipe
from apps.recipes.serializers import RecipeListSerializer
from .models import Favorite, Collection, CollectionRecipe

User = get_user_model()


class FavoriteSerializer(serializers.ModelSerializer):
    """Serializer for favorites with recipe details inclusion."""
    recipe = RecipeListSerializer(read_only=True)
    recipe_id = serializers.UUIDField(write_only=True)
    user = serializers.StringRelatedField(read_only=True)
    user_id = serializers.UUIDField(source='user.id', read_only=True)

    class Meta:
        model = Favorite
        fields = [
            'user', 'user_id', 'recipe', 'recipe_id', 'personal_rating',
            'personal_notes', 'added_at'
        ]
        read_only_fields = ['added_at']

    def validate_recipe_id(self, value):
        """Validate that recipe exists."""
        try:
            Recipe.objects.get(id=value)
        except Recipe.DoesNotExist:
            raise serializers.ValidationError("Recipe not found")
        return value

    def validate_personal_rating(self, value):
        """Validate personal rating."""
        if value is not None and (value < 1 or value > 5):
            raise serializers.ValidationError("Personal rating must be between 1 and 5")
        return value

    def validate_personal_notes(self, value):
        """Validate personal notes."""
        if value:
            return value.strip()[:1000]
        return value

    def validate(self, attrs):
        """Cross-field validation."""
        # Check for duplicate favorites
        request = self.context.get('request')
        recipe_id = attrs.get('recipe_id')
        
        if request and hasattr(request, 'user') and recipe_id:
            existing = Favorite.objects.filter(
                user=request.user,
                recipe_id=recipe_id
            )
            
            if self.instance:
                existing = existing.exclude(pk=self.instance.pk)
            
            if existing.exists():
                raise serializers.ValidationError({
                    'recipe_id': 'This recipe is already in your favorites'
                })
        
        return attrs

    def create(self, validated_data):
        """Create a new favorite."""
        recipe_id = validated_data.pop('recipe_id')
        recipe = Recipe.objects.get(id=recipe_id)
        
        request = self.context.get('request')
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            validated_data['user'] = request.user
        
        return Favorite.objects.create(
            recipe=recipe,
            **validated_data
        )

    def update(self, instance, validated_data):
        """Update an existing favorite."""
        # Remove recipe_id from validated_data as it shouldn't be updated
        validated_data.pop('recipe_id', None)
        
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        instance.save()
        return instance


class FavoriteListSerializer(FavoriteSerializer):
    """Simplified serializer for favorite lists."""
    class Meta(FavoriteSerializer.Meta):
        fields = [
            'user_id', 'recipe', 'personal_rating', 'personal_notes', 'added_at'
        ]


class FavoriteCreateSerializer(serializers.Serializer):
    """Serializer for creating favorites."""
    recipe_id = serializers.UUIDField()
    personal_rating = serializers.IntegerField(required=False, min_value=1, max_value=5)
    personal_notes = serializers.CharField(required=False, max_length=1000, allow_blank=True)

    def validate_recipe_id(self, value):
        """Validate that recipe exists."""
        try:
            Recipe.objects.get(id=value)
        except Recipe.DoesNotExist:
            raise serializers.ValidationError("Recipe not found")
        return value

    def validate_personal_notes(self, value):
        """Validate personal notes."""
        if value:
            return value.strip()[:1000]
        return value

    def save(self):
        """Create the favorite."""
        request = self.context['request']
        recipe = Recipe.objects.get(id=self.validated_data['recipe_id'])
        
        # Use upsert behavior - update if exists, create if not
        favorite, created = Favorite.objects.update_or_create(
            user=request.user,
            recipe=recipe,
            defaults={
                'personal_rating': self.validated_data.get('personal_rating'),
                'personal_notes': self.validated_data.get('personal_notes', '')
            }
        )
        
        return favorite


class CollectionSerializer(serializers.ModelSerializer):
    """Serializer for collections with recipe relationship handling."""
    recipes = RecipeListSerializer(many=True, read_only=True)
    recipe_ids = serializers.ListField(
        child=serializers.UUIDField(),
        write_only=True,
        required=False
    )
    user = serializers.StringRelatedField(read_only=True)
    user_id = serializers.UUIDField(source='user.id', read_only=True)
    recipe_count = serializers.SerializerMethodField()

    class Meta:
        model = Collection
        fields = [
            'id', 'user', 'user_id', 'name', 'description', 'color', 'icon',
            'is_public', 'recipes', 'recipe_ids', 'recipe_count',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_recipe_count(self, obj):
        """Get count of recipes in the collection."""
        return obj.recipes.count()

    def validate_name(self, value):
        """Validate collection name."""
        if not value or not value.strip():
            raise serializers.ValidationError("Collection name is required")
        
        name = value.strip()[:255]
        
        # Check for duplicate names for the same user
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            queryset = Collection.objects.filter(user=request.user, name__iexact=name)
            if self.instance:
                queryset = queryset.exclude(pk=self.instance.pk)
            
            if queryset.exists():
                raise serializers.ValidationError("You already have a collection with this name")
        
        return name

    def validate_description(self, value):
        """Validate collection description."""
        if value:
            return value.strip()[:1000]
        return value

    def validate_color(self, value):
        """Validate color hex code."""
        if value:
            # Ensure it's a valid hex color
            import re
            if not re.match(r'^#[0-9A-Fa-f]{6}$', value):
                raise serializers.ValidationError("Color must be a valid hex color code (e.g., #4DB6AC)")
        return value or '#4DB6AC'

    def validate_icon(self, value):
        """Validate icon name."""
        if value:
            return value.strip()[:50]
        return value or 'heart'

    def validate_recipe_ids(self, value):
        """Validate recipe IDs."""
        if not value:
            return []
        
        if len(value) > 100:
            raise serializers.ValidationError("Too many recipes (max 100)")
        
        # Check that all recipes exist
        existing_recipes = Recipe.objects.filter(id__in=value)
        if len(existing_recipes) != len(value):
            raise serializers.ValidationError("One or more recipes not found")
        
        return value

    def create(self, validated_data):
        """Create a new collection with recipes."""
        recipe_ids = validated_data.pop('recipe_ids', [])
        
        request = self.context.get('request')
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            validated_data['user'] = request.user
        
        collection = Collection.objects.create(**validated_data)
        
        # Add recipes to collection
        for recipe_id in recipe_ids:
            CollectionRecipe.objects.create(
                collection=collection,
                recipe_id=recipe_id
            )
        
        return collection

    def update(self, instance, validated_data):
        """Update an existing collection."""
        recipe_ids = validated_data.pop('recipe_ids', None)
        
        # Update basic fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        instance.save()
        
        # Update recipes if provided
        if recipe_ids is not None:
            # Remove existing recipes
            CollectionRecipe.objects.filter(collection=instance).delete()
            
            # Add new recipes
            for recipe_id in recipe_ids:
                CollectionRecipe.objects.create(
                    collection=instance,
                    recipe_id=recipe_id
                )
        
        return instance


class CollectionListSerializer(CollectionSerializer):
    """Simplified serializer for collection lists."""
    class Meta(CollectionSerializer.Meta):
        fields = [
            'id', 'user_id', 'name', 'description', 'color', 'icon',
            'is_public', 'recipe_count', 'created_at', 'updated_at'
        ]


class CollectionCreateSerializer(CollectionSerializer):
    """Serializer for collection creation."""
    class Meta(CollectionSerializer.Meta):
        fields = [
            'name', 'description', 'color', 'icon', 'is_public', 'recipe_ids'
        ]


class AddRecipeToCollectionSerializer(serializers.Serializer):
    """Serializer for adding recipes to collections."""
    recipe_id = serializers.UUIDField()

    def validate_recipe_id(self, value):
        """Validate that recipe exists."""
        try:
            Recipe.objects.get(id=value)
        except Recipe.DoesNotExist:
            raise serializers.ValidationError("Recipe not found")
        return value

    def validate(self, attrs):
        """Validate that recipe isn't already in collection."""
        collection = self.context.get('collection')
        recipe_id = attrs['recipe_id']
        
        if collection and CollectionRecipe.objects.filter(
            collection=collection,
            recipe_id=recipe_id
        ).exists():
            raise serializers.ValidationError({
                'recipe_id': 'Recipe is already in this collection'
            })
        
        return attrs

    def save(self):
        """Add recipe to collection."""
        collection = self.context['collection']
        recipe = Recipe.objects.get(id=self.validated_data['recipe_id'])
        
        collection_recipe = CollectionRecipe.objects.create(
            collection=collection,
            recipe=recipe
        )
        
        return collection_recipe