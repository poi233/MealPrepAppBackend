#!/bin/bash

# Build script for Vercel deployment
echo "Starting build process..."

# Install dependencies
pip install -r requirements.txt

# Add src to Python path
export PYTHONPATH="${PYTHONPATH}:./src"

# Set Django settings
export DJANGO_SETTINGS_MODULE=mealprep_project.settings.production

# Collect static files
python manage.py collectstatic --noinput

echo "Build process completed!"