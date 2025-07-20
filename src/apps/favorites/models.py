"""
Favorites models for MealPrepAI Django backend.
"""
import uuid
from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
from apps.recipes.models import Recipe

User = get_user_model()


class Favorite(models.Model):
    """
    User's favorite recipes with personal ratings and notes.
    """
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='favorites', db_column='user_id')
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE, related_name='favorited_by', db_column='recipe_id')
    personal_rating = models.IntegerField(
        null=True, 
        blank=True, 
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Personal rating from 1 to 5 stars"
    )
    personal_notes = models.TextField(blank=True)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'favorites'
        verbose_name = 'Favorite'
        verbose_name_plural = 'Favorites'
        unique_together = ['user', 'recipe']
        ordering = ['-added_at']

    def __str__(self):
        return f"{self.user.username} - {self.recipe.name}"


class Collection(models.Model):
    """
    User-created collections for organizing recipes.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='collections', db_column='user_id')
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    color = models.CharField(max_length=7, default='#4DB6AC')
    icon = models.CharField(max_length=50, default='heart')
    is_public = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'collections'
        verbose_name = 'Collection'
        verbose_name_plural = 'Collections'
        unique_together = ['user', 'name']
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.name}"


class CollectionRecipe(models.Model):
    """
    Many-to-many relationship between collections and recipes.
    """
    id = models.AutoField(primary_key=True)
    collection = models.ForeignKey(Collection, on_delete=models.CASCADE, related_name='recipes', db_column='collection_id')
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE, related_name='in_collections', db_column='recipe_id')
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'collection_recipes'
        verbose_name = 'Collection Recipe'
        verbose_name_plural = 'Collection Recipes'
        unique_together = ['collection', 'recipe']
        ordering = ['-added_at']

    def __str__(self):
        return f"{self.collection.name} - {self.recipe.name}"