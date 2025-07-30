"""
Test setup configuration for MealPrepAppBackend.
"""
import os
import sys
import django
from django.conf import settings
from django.test.utils import get_runner

# Add the src directory to Python path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(BASE_DIR, 'src')
sys.path.insert(0, SRC_DIR)

def setup_django():
    """Setup Django for testing."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mealprep_project.settings.development')
    django.setup()

if __name__ == '__main__':
    setup_django()
    TestRunner = get_runner(settings)
    test_runner = TestRunner()
    failures = test_runner.run_tests(["test"])
    if failures:
        sys.exit(1)