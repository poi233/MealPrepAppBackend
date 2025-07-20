"""
WSGI entry point for Vercel deployment.
"""
import os
import sys
from pathlib import Path

# Add the src directory to Python path
BASE_DIR = Path(__file__).resolve().parent.parent
src_path = BASE_DIR / 'src'
sys.path.insert(0, str(src_path))

# Set Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mealprep_project.settings.production')

from django.core.wsgi import get_wsgi_application

application = get_wsgi_application()