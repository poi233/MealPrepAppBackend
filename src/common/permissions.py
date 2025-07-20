"""
Custom permissions for the MealPrepAI Django backend.
"""
from rest_framework import permissions
from rest_framework.exceptions import PermissionDenied
import logging

logger = logging.getLogger(__name__)


class IsAuthenticatedAndActive(permissions.BasePermission):
    """
    Custom permission to check if user is authenticated and active.
    """
    
    def has_permission(self, request, view):
        """Check if user is authenticated and active."""
        if not request.user or not hasattr(request.user, 'is_authenticated'):
            return False
        
        if not request.user.is_authenticated:
            return False
        
        # Additional check for user existence in database
        try:
            # This will raise an exception if user doesn't exist
            request.user.refresh_from_db()
            return True
        except Exception as e:
            logger.warning(f"User authentication check failed: {str(e)}")
            return False


class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow owners of an object to edit it.
    """

    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed for any request,
        # so we'll always allow GET, HEAD or OPTIONS requests.
        if request.method in permissions.SAFE_METHODS:
            return True

        # Write permissions are only allowed to the owner of the object.
        if hasattr(obj, 'user'):
            return obj.user == request.user
        elif hasattr(obj, 'created_by_user'):
            return obj.created_by_user == request.user
        
        return False


class IsOwner(permissions.BasePermission):
    """
    Custom permission to only allow owners of an object to access it.
    """

    def has_object_permission(self, request, view, obj):
        # Only allow access to the owner of the object
        if hasattr(obj, 'user'):
            return obj.user == request.user
        elif hasattr(obj, 'created_by_user'):
            return obj.created_by_user == request.user
        
        return False


class IsRecipeOwnerOrReadOnly(permissions.BasePermission):
    """
    Custom permission for recipes - owners can edit, others can read.
    """

    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed for any request
        if request.method in permissions.SAFE_METHODS:
            return True

        # Write permissions are only allowed to the recipe creator
        return obj.created_by_user == request.user


class IsSelfOrReadOnly(permissions.BasePermission):
    """
    Custom permission for user profiles - users can only edit their own profile.
    """
    
    def has_object_permission(self, request, view, obj):
        # Read permissions for safe methods
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Write permissions only for the user themselves
        return obj == request.user


class IsSelf(permissions.BasePermission):
    """
    Custom permission for user-specific resources - users can only access their own data.
    """
    
    def has_object_permission(self, request, view, obj):
        # Only allow access to the user themselves
        return obj == request.user


class IsAuthenticatedOrCreateOnly(permissions.BasePermission):
    """
    Custom permission for registration - allow creation for anonymous users,
    but require authentication for other operations.
    """
    
    def has_permission(self, request, view):
        # Allow POST (creation) for anonymous users
        if request.method == 'POST':
            return True
        
        # Require authentication for other methods
        return request.user and request.user.is_authenticated


class CanManageOwnData(permissions.BasePermission):
    """
    Permission class for resources that belong to the authenticated user.
    Checks that the resource belongs to the current user.
    """
    
    def has_permission(self, request, view):
        """Check basic authentication."""
        return request.user and request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        """Check that the object belongs to the current user."""
        # For meal plans, favorites, etc. that have a user field
        if hasattr(obj, 'user'):
            return obj.user == request.user
        
        # For recipes that have created_by_user field
        if hasattr(obj, 'created_by_user'):
            return obj.created_by_user == request.user
        
        # For user objects themselves
        if hasattr(obj, 'id') and hasattr(request.user, 'id'):
            return obj.id == request.user.id
        
        return False


class ReadOnlyOrOwner(permissions.BasePermission):
    """
    Permission class that allows read access to all authenticated users,
    but write access only to owners.
    """
    
    def has_permission(self, request, view):
        """Check basic authentication."""
        return request.user and request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        """Allow read access to all, write access only to owners."""
        # Read permissions for safe methods
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Write permissions only for owners
        if hasattr(obj, 'user'):
            return obj.user == request.user
        elif hasattr(obj, 'created_by_user'):
            return obj.created_by_user == request.user
        
        return False