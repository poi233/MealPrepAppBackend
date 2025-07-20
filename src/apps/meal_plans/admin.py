"""
Admin configuration for meal_plans app.
"""
from django.contrib import admin
from .models import MealPlan, MealPlanItem


class MealPlanItemInline(admin.TabularInline):
    """Inline admin for meal plan items."""
    model = MealPlanItem
    extra = 0
    fields = ('recipe', 'day_of_week', 'meal_type', 'added_at')
    readonly_fields = ('added_at',)


@admin.register(MealPlan)
class MealPlanAdmin(admin.ModelAdmin):
    """Admin interface for MealPlan model."""
    
    list_display = ('name', 'user', 'week_start_date', 'is_active', 'created_at')
    list_filter = ('is_active', 'week_start_date', 'created_at')
    search_fields = ('name', 'description', 'user__username')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'user')
        }),
        ('Planning', {
            'fields': ('week_start_date', 'is_active', 'plan_description', 'analysis_text')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    inlines = [MealPlanItemInline]
    autocomplete_fields = ['user']


@admin.register(MealPlanItem)
class MealPlanItemAdmin(admin.ModelAdmin):
    """Admin interface for MealPlanItem model."""
    
    list_display = ('meal_plan', 'recipe', 'day_of_week', 'meal_type', 'added_at')
    list_filter = ('day_of_week', 'meal_type', 'added_at')
    search_fields = ('meal_plan__name', 'recipe__name')
    readonly_fields = ('added_at',)
    
    autocomplete_fields = ['meal_plan', 'recipe']