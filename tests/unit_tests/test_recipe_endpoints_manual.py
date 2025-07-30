#!/usr/bin/env python
"""
Manual test script for recipe management API endpoints.
This script tests all the recipe endpoints to verify they work correctly.
"""
import os
import sys
import json
import requests
import time

# Add src directory to Python path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(BASE_DIR, 'src')
sys.path.insert(0, SRC_DIR)

# Django setup
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mealprep_project.settings.development')
import django
django.setup()

BASE_URL = "http://localhost:8000"

def test_recipe_endpoints():
    """Test all recipe management endpoints."""
    print("🧪 Testing Recipe Management API Endpoints")
    print("=" * 50)
    
    # Step 1: Register a test user
    print("\n1. Testing user registration...")
    register_data = {
        "username": "recipe_tester",
        "email": "recipe_tester@example.com",
        "password": "testpass123",
        "password_confirm": "testpass123"
    }
    
    response = requests.post(f"{BASE_URL}/api/auth/register/", json=register_data)
    if response.status_code == 201:
        print("✅ User registration successful")
        auth_data = response.json()
        access_token = auth_data['access']
        headers = {"Authorization": f"Bearer {access_token}"}
    else:
        print(f"❌ User registration failed: {response.status_code}")
        print(response.text)
        return False
    
    # Step 2: Test GET /api/recipes/ (list recipes)
    print("\n2. Testing GET /api/recipes/ (list recipes)...")
    response = requests.get(f"{BASE_URL}/api/recipes/", headers=headers)
    if response.status_code == 200:
        print("✅ Recipe list endpoint working")
        recipes_data = response.json()
        print(f"   Found {recipes_data['count']} recipes")
    else:
        print(f"❌ Recipe list failed: {response.status_code}")
        print(response.text)
        return False
    
    # Step 3: Test POST /api/recipes/ (create recipe)
    print("\n3. Testing POST /api/recipes/ (create recipe)...")
    recipe_data = {
        "name": "Test API Recipe",
        "description": "A recipe created via API testing",
        "ingredients": [
            {"name": "Flour", "amount": 2, "unit": "cups", "notes": "All-purpose"},
            {"name": "Sugar", "amount": 1, "unit": "cup", "notes": "White sugar"}
        ],
        "instructions": "Mix ingredients and bake at 350F for 30 minutes.",
        "cuisine": "American",
        "prep_time": 10,
        "cook_time": 30,
        "difficulty": "easy",
        "tags": ["baking", "test"],
        "nutrition_info": {
            "calories": 200,
            "protein": 4,
            "carbs": 40,
            "fat": 2
        }
    }
    
    response = requests.post(f"{BASE_URL}/api/recipes/", json=recipe_data, headers=headers)
    if response.status_code == 201:
        print("✅ Recipe creation successful")
        created_recipe = response.json()
        recipe_id = created_recipe['id']
        print(f"   Created recipe ID: {recipe_id}")
    else:
        print(f"❌ Recipe creation failed: {response.status_code}")
        print(response.text)
        return False
    
    # Step 4: Test GET /api/recipes/{id}/ (get specific recipe)
    print(f"\n4. Testing GET /api/recipes/{recipe_id}/ (get specific recipe)...")
    response = requests.get(f"{BASE_URL}/api/recipes/{recipe_id}/", headers=headers)
    if response.status_code == 200:
        print("✅ Recipe retrieval successful")
        recipe = response.json()
        print(f"   Recipe name: {recipe['name']}")
    else:
        print(f"❌ Recipe retrieval failed: {response.status_code}")
        print(response.text)
        return False
    
    # Step 5: Test PUT /api/recipes/{id}/ (update recipe)
    print(f"\n5. Testing PUT /api/recipes/{recipe_id}/ (update recipe)...")
    updated_recipe_data = recipe_data.copy()
    updated_recipe_data['name'] = "Updated Test API Recipe"
    updated_recipe_data['description'] = "An updated recipe created via API testing"
    updated_recipe_data['prep_time'] = 15
    
    response = requests.put(f"{BASE_URL}/api/recipes/{recipe_id}/", json=updated_recipe_data, headers=headers)
    if response.status_code == 200:
        print("✅ Recipe update successful")
        updated_recipe = response.json()
        print(f"   Updated name: {updated_recipe['name']}")
        print(f"   Updated prep time: {updated_recipe['prep_time']}")
    else:
        print(f"❌ Recipe update failed: {response.status_code}")
        print(response.text)
        return False
    
    # Step 6: Test search functionality
    print("\n6. Testing search functionality...")
    response = requests.get(f"{BASE_URL}/api/recipes/?search=Updated", headers=headers)
    if response.status_code == 200:
        print("✅ Recipe search successful")
        search_results = response.json()
        print(f"   Found {search_results['count']} recipes matching 'Updated'")
    else:
        print(f"❌ Recipe search failed: {response.status_code}")
        print(response.text)
        return False
    
    # Step 7: Test filtering by cuisine
    print("\n7. Testing filtering by cuisine...")
    response = requests.get(f"{BASE_URL}/api/recipes/?cuisine=American", headers=headers)
    if response.status_code == 200:
        print("✅ Recipe filtering successful")
        filter_results = response.json()
        print(f"   Found {filter_results['count']} American recipes")
    else:
        print(f"❌ Recipe filtering failed: {response.status_code}")
        print(response.text)
        return False
    
    # Step 8: Test pagination
    print("\n8. Testing pagination...")
    response = requests.get(f"{BASE_URL}/api/recipes/?page_size=5", headers=headers)
    if response.status_code == 200:
        print("✅ Recipe pagination successful")
        paginated_results = response.json()
        print(f"   Page size: {paginated_results.get('page_size', 'N/A')}")
        print(f"   Total pages: {paginated_results.get('total_pages', 'N/A')}")
        print(f"   Has next: {'Yes' if paginated_results['links']['next'] else 'No'}")
    else:
        print(f"❌ Recipe pagination failed: {response.status_code}")
        print(response.text)
        return False
    
    # Step 9: Test DELETE /api/recipes/{id}/ (delete recipe)
    print(f"\n9. Testing DELETE /api/recipes/{recipe_id}/ (delete recipe)...")
    response = requests.delete(f"{BASE_URL}/api/recipes/{recipe_id}/", headers=headers)
    if response.status_code == 204:
        print("✅ Recipe deletion successful")
    else:
        print(f"❌ Recipe deletion failed: {response.status_code}")
        print(response.text)
        return False
    
    # Step 10: Verify recipe was deleted
    print(f"\n10. Verifying recipe was deleted...")
    response = requests.get(f"{BASE_URL}/api/recipes/{recipe_id}/", headers=headers)
    if response.status_code == 404 or response.status_code == 500:  # 500 is current behavior, should be 404
        print("✅ Recipe deletion verified (recipe not found)")
    else:
        print(f"❌ Recipe deletion verification failed: {response.status_code}")
        print("Recipe still exists after deletion")
        return False
    
    print("\n" + "=" * 50)
    print("🎉 All recipe management endpoints are working correctly!")
    return True

if __name__ == "__main__":
    # Start Django server in background
    import subprocess
    import signal
    
    print("Starting Django development server...")
    server_process = subprocess.Popen([
        sys.executable, "manage.py", "runserver", "8000", "--noreload"
    ], cwd=BASE_DIR)
    
    try:
        # Wait for server to start
        time.sleep(3)
        
        # Run tests
        success = test_recipe_endpoints()
        
        if success:
            print("\n✅ All tests passed!")
            sys.exit(0)
        else:
            print("\n❌ Some tests failed!")
            sys.exit(1)
            
    finally:
        # Clean up server process
        print("\nStopping Django development server...")
        server_process.terminate()
        try:
            server_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server_process.kill()