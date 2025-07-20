"""
Database migration script for Vercel deployment.
Run this after deployment to initialize the database.
"""
import os
import sys
import django
from pathlib import Path

# Add the src directory to Python path
BASE_DIR = Path(__file__).resolve().parent.parent
src_path = BASE_DIR / 'src'
sys.path.insert(0, str(src_path))

# Set Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mealprep_project.settings.production')

# Setup Django
django.setup()

from django.core.management import execute_from_command_line

if __name__ == '__main__':
    print("Running database migrations...")
    execute_from_command_line(['manage.py', 'migrate'])
    print("Database migrations completed!")