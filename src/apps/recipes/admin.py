"""
Admin configuration for recipes app.
"""
from django.contrib import admin
from .models import Recipe


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    """Admin interface for Recipe model."""
    
    list_display = ('name', 'created_by_user', 'cuisine', 'difficulty', 'prep_time', 'cook_time', 'avg_rating', 'created_at')
    list_filter = ('cuisine', 'difficulty', 'created_at', 'updated_at')
    search_fields = ('name', 'description', 'tags', 'cuisine')
    readonly_fields = ('avg_rating', 'rating_count', 'created_at', 'updated_at')
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'created_by_user', 'cuisine', 'difficulty')
        }),
        ('Timing', {
            'fields': ('prep_time', 'cook_time')
        }),
        ('Content', {
            'fields': ('ingredients', 'instructions', 'nutrition_info', 'tags', 'image_url')
        }),
        ('Ratings', {
            'fields': ('avg_rating', 'rating_count'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    # Enable filtering by foreign key
    autocomplete_fields = ['created_by_user']