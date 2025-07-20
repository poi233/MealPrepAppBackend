"""
Admin configuration for favorites app.
"""
from django.contrib import admin
from .models import Favorite, Collection, CollectionRecipe


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    """Admin interface for Favorite model."""
    
    list_display = ('user', 'recipe', 'personal_rating', 'added_at')
    list_filter = ('personal_rating', 'added_at')
    search_fields = ('user__username', 'recipe__name', 'personal_notes')
    readonly_fields = ('added_at',)
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('user', 'recipe')
        }),
        ('Personal Details', {
            'fields': ('personal_rating', 'personal_notes')
        }),
        ('Timestamps', {
            'fields': ('added_at',),
            'classes': ('collapse',)
        }),
    )
    
    autocomplete_fields = ['user', 'recipe']


class CollectionRecipeInline(admin.TabularInline):
    """Inline admin for collection recipes."""
    model = CollectionRecipe
    extra = 0
    fields = ('recipe', 'added_at')
    readonly_fields = ('added_at',)
    autocomplete_fields = ['recipe']


@admin.register(Collection)
class CollectionAdmin(admin.ModelAdmin):
    """Admin interface for Collection model."""
    
    list_display = ('name', 'user', 'color', 'icon', 'is_public', 'created_at')
    list_filter = ('color', 'is_public', 'created_at')
    search_fields = ('name', 'description', 'user__username')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'user')
        }),
        ('Appearance', {
            'fields': ('color', 'icon', 'is_public')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    autocomplete_fields = ['user']
    inlines = [CollectionRecipeInline]


@admin.register(CollectionRecipe)
class CollectionRecipeAdmin(admin.ModelAdmin):
    """Admin interface for CollectionRecipe model."""
    
    list_display = ('collection', 'recipe', 'added_at')
    list_filter = ('added_at',)
    search_fields = ('collection__name', 'recipe__name')
    readonly_fields = ('added_at',)
    
    autocomplete_fields = ['collection', 'recipe']