"""
Admin configuration for authentication app.
"""
from django.contrib import admin
from .models import User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    """Admin interface for custom User model."""
    
    # Fields to display in the user list
    list_display = ('username', 'email', 'display_name', 'created_at', 'is_active')
    list_filter = ('created_at', 'updated_at')
    search_fields = ('username', 'email', 'display_name')
    
    # Fields for the user detail/edit form
    fieldsets = (
        (None, {'fields': ('username', 'password_hash')}),
        ('Personal info', {'fields': ('email', 'display_name', 'dietary_preferences')}),
        ('Timestamps', {'fields': ('created_at', 'updated_at'), 'classes': ('collapse',)}),
    )
    
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('-created_at',)