"""
Meal plan models for MealPrepAI Django backend.
"""
import uuid
from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from apps.recipes.models import Recipe, MEAL_TYPE_CHOICES

User = get_user_model()


class MealPlan(models.Model):
    """
    Meal plan model for organizing weekly meal plans.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='meal_plans', db_column='user_id')
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    week_start_date = models.DateField()
    is_active = models.BooleanField(default=False)
    plan_description = models.TextField(blank=True)
    analysis_text = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'meal_plans'
        verbose_name = 'Meal Plan'
        verbose_name_plural = 'Meal Plans'
        ordering = ['-created_at']
        unique_together = ['user', 'name']

    def __str__(self):
        return f"{self.name} - {self.week_start_date}"


class MealPlanItem(models.Model):
    """
    Individual meal plan items linking recipes to specific days and meal types.
    """
    id = models.AutoField(primary_key=True)
    meal_plan = models.ForeignKey(MealPlan, on_delete=models.CASCADE, related_name='items', db_column='meal_plan_id')
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE, db_column='recipe_id')
    day_of_week = models.IntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(6)],
        help_text="0=Monday, 1=Tuesday, ..., 6=Sunday"
    )
    meal_type = models.CharField(max_length=20, choices=MEAL_TYPE_CHOICES)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'meal_plan_items'
        verbose_name = 'Meal Plan Item'
        verbose_name_plural = 'Meal Plan Items'
        unique_together = ['meal_plan', 'day_of_week', 'meal_type', 'recipe']
    
    def __str__(self):
        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        return f"{self.recipe.name} - {days[self.day_of_week]} {self.meal_type}"