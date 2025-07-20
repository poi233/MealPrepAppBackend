"""
Health check endpoint for MealPrepAI Backend.
"""
from http.server import BaseHTTPRequestHandler
import json
import os
import sys
from pathlib import Path

# Add the src directory to Python path
BASE_DIR = Path(__file__).resolve().parent.parent
src_path = BASE_DIR / 'src'
sys.path.insert(0, str(src_path))

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            # Try to import Django to verify setup
            import django
            from django.conf import settings
            
            # Set Django settings if not already set
            os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mealprep_project.settings.production')
            
            # Setup Django
            if not settings.configured:
                django.setup()
            
            response_data = {
                'status': 'healthy',
                'message': 'MealPrepAI Backend is running on Vercel!',
                'django_version': django.get_version(),
                'debug_mode': settings.DEBUG,
                'installed_apps': len(settings.INSTALLED_APPS),
                'environment_check': {
                    'SECRET_KEY': 'SET' if os.environ.get('SECRET_KEY') else 'NOT SET',
                    'POSTGRES_DATABASE': 'SET' if os.environ.get('POSTGRES_DATABASE') else 'NOT SET',
                    'POSTGRES_PASSWORD': 'SET' if os.environ.get('POSTGRES_PASSWORD') else 'NOT SET',
                    'GEMINI_API_KEY': 'SET' if os.environ.get('GEMINI_API_KEY') else 'NOT SET',
                },
                'api_endpoints': [
                    '/api/auth/',
                    '/api/recipes/',
                    '/api/meal-plans/',
                    '/api/favorites/',
                    '/api/ai/'
                ]
            }
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            self.wfile.write(json.dumps(response_data, indent=2).encode())
            
        except Exception as e:
            import traceback
            error_data = {
                'status': 'error',
                'error': str(e),
                'error_type': type(e).__name__,
                'traceback': traceback.format_exc(),
                'environment_vars': {
                    'SECRET_KEY': 'SET' if os.environ.get('SECRET_KEY') else 'NOT SET',
                    'POSTGRES_DATABASE': 'SET' if os.environ.get('POSTGRES_DATABASE') else 'NOT SET',
                    'POSTGRES_PASSWORD': 'SET' if os.environ.get('POSTGRES_PASSWORD') else 'NOT SET',
                    'GEMINI_API_KEY': 'SET' if os.environ.get('GEMINI_API_KEY') else 'NOT SET',
                }
            }
            
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            self.wfile.write(json.dumps(error_data, indent=2).encode())