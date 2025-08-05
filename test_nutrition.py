#!/usr/bin/env python3
"""
Test nutrition serializer using Django shell
"""

from apps.recipes.serializers import NutritionInfoSerializer

def test_nutrition_validation():
    """Test nutrition info validation with partial data"""
    
    print("🔬 Testing nutrition serializer...")
    
    # Test data similar to what our API test sends
    test_data = {
        "calories": 300,
        "protein": 15,
        "carbohydrates": 30,
        "fat": 10
    }
    
    print(f"📦 Test data: {test_data}")
    
    serializer = NutritionInfoSerializer(data=test_data)
    
    if serializer.is_valid():
        print(f"✅ VALID: {serializer.validated_data}")
        return True
    else:
        print(f"❌ INVALID: {serializer.errors}")
        for field, errors in serializer.errors.items():
            print(f"   Field '{field}': {errors}")
        return False

if __name__ == "__main__":
    success = test_nutrition_validation()
    exit(0 if success else 1)