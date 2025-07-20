"""
Authentication models for MealPrepAI Django backend.
"""
import uuid
from django.contrib.auth.hashers import make_password, check_password
from django.contrib.auth.models import BaseUserManager
from django.db import models


class UserManager(BaseUserManager):
    """Custom user manager for the User model."""
    
    def create_user(self, username, email, password=None, **extra_fields):
        """Create and return a regular user."""
        if not email:
            raise ValueError('The Email field must be set')
        if not username:
            raise ValueError('The Username field must be set')
        
        email = self.normalize_email(email)
        user = self.model(username=username, email=email, **extra_fields)
        if password:
            user.password_hash = make_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, username, email, password=None, **extra_fields):
        """Create and return a superuser."""
        return self.create_user(username, email, password, **extra_fields)


class User(models.Model):
    """
    Custom User model matching the existing database schema exactly.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    username = models.CharField(max_length=50, unique=True)
    email = models.EmailField(max_length=255, unique=True)
    password_hash = models.CharField(max_length=255, default='')
    display_name = models.CharField(max_length=100, blank=True)
    dietary_preferences = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    objects = UserManager()
    
    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email']

    class Meta:
        db_table = 'users'
        verbose_name = 'User'
        verbose_name_plural = 'Users'

    def __str__(self):
        return self.username or self.email
    
    def set_password(self, raw_password):
        """Set the user's password."""
        self.password_hash = make_password(raw_password)
    
    def check_password(self, raw_password):
        """Check if the provided password is correct."""
        return check_password(raw_password, self.password_hash)
    
    @property
    def password(self):
        """Return password_hash for Django compatibility."""
        return self.password_hash
    
    @password.setter
    def password(self, value):
        """Set password_hash when password is set."""
        self.password_hash = value
    
    @property
    def is_authenticated(self):
        """Always return True for authenticated users."""
        return True
    
    @property
    def is_anonymous(self):
        """Always return False for authenticated users."""
        return False
    
    @property
    def is_active(self):
        """Return True for all users (no deactivation in this model)."""
        return True
    
    @property
    def is_staff(self):
        """Return True for admin users."""
        # For simplicity, admin users are those with username 'admin' or email containing 'admin'
        return self.username == 'admin' or 'admin' in self.email
    
    @property
    def is_superuser(self):
        """Return True for admin users."""
        # For simplicity, admin users are those with username 'admin' or email containing 'admin'
        return self.username == 'admin' or 'admin' in self.email
    
    def has_perm(self, perm, obj=None):
        """Return True for admin users, False for regular users."""
        return self.is_superuser
    
    def has_module_perms(self, app_label):
        """Return True for admin users, False for regular users."""
        return self.is_superuser