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

    def __str__(self):
        return self.name
    
    @property
    def total_time(self):
        """Get the total time (computed in database)."""
        # This will be populated by the database's generated column
        # We can also compute it here as a fallback
        return getattr(self, '_total_time', self.prep_time + self.cook_time)