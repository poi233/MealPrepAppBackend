"""
Recipe models for MealPrepAI Django backend.
"""
import uuid
from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator

User = get_user_model()

MEAL_TYPE_CHOICES = [
    ('breakfast', 'Breakfast'),
    ('lunch', 'Lunch'),
    ('dinner', 'Dinner'),
    ('snack', 'Snack'),
]

DIFFICULTY_CHOICES = [
    ('easy', 'Easy'),
    ('medium', 'Medium'),
    ('hard', 'Hard'),
]


class Recipe(models.Model):
    """
    Recipe model matching the existing database schema.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_by_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, db_column='created_by_user_id')
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    ingredients = models.JSONField(default=list)
    instructions = models.TextField()
    nutrition_info = models.JSONField(default=dict, blank=True)
    cuisine = models.CharField(max_length=100, blank=True)
    prep_time = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    cook_time = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    difficulty = models.CharField(max_length=10, choices=DIFFICULTY_CHOICES, default='medium')
    avg_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.00)
    rating_count = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    image_url = models.URLField(blank=True)
    tags = ArrayField(models.CharField(max_length=50), default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'recipes'
        verbose_name = 'Recipe'
        verbose_name_plural = 'Recipes'
        ordering = ['-created_at']
        
        # Database indexes for performance optimization
        indexes = [
            # Performance indexes for common query patterns
            models.Index(fields=['created_by_user', '-created_at'], name='recipe_user_created_idx'),
            models.Index(fields=['cuisine', '-created_at'], name='recipe_cuisine_created_idx'),
            models.Index(fields=['difficulty', '-avg_rating'], name='recipe_difficulty_rating_idx'),
            models.Index(fields=['-avg_rating', 'rating_count'], name='recipe_rating_popularity_idx'),
            models.Index(fields=['prep_time', 'cook_time'], name='recipe_time_idx'),
            models.Index(fields=['-created_at', 'avg_rating'], name='recipe_recent_rated_idx'),
            
            # Search optimization indexes
            models.Index(fields=['name'], name='recipe_name_search_idx'),
            
            # Compound indexes for common filter combinations
            models.Index(fields=['created_by_user', 'cuisine'], name='recipe_user_cuisine_idx'),
            models.Index(fields=['difficulty', 'cuisine'], name='recipe_difficulty_cuisine_idx'),
        ]

    def __str__(self):
        return self.name
    
    @property
    def total_time(self):
        """Get the total time (computed in database)."""
        # This will be populated by the database's generated column
        # We can also compute it here as a fallback
        return getattr(self, '_total_time', self.prep_time + self.cook_time)