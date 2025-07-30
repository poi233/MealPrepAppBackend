"""
URL configuration for ai_integration app.
Supports API versioning and comprehensive documentation.
"""
from django.urls import path
from . import views

# API version for backward compatibility
API_VERSION = 'v1'

# API versioning patterns for future compatibility
versioned_patterns = [
    # Versioned patterns can be added here for API evolution
    # Example: path('v2/create-recipe-from-ai/', views.CreateRecipeFromAIV2View.as_view())
]

urlpatterns = [
    # Meal plan generation
    path(
        'generate-meal-plan/', 
        views.GenerateMealPlanView.as_view(), 
        name='generate_meal_plan'
    ),
    path(
        'analyze-meal-plan/', 
        views.AnalyzeMealPlanView.as_view(), 
        name='analyze_meal_plan'
    ),
    
    # Recipe generation and modification
    path(
        'generate-recipe-details/', 
        views.GenerateRecipeDetailsView.as_view(), 
        name='generate_recipe_details'
    ),
    
    # Scene A: Single recipe creation ("Save to Template")
    path(
        'create-recipe-from-ai/', 
        views.CreateRecipeFromAIView.as_view(), 
        name='create_recipe_from_ai'
    ),
    
    # Scene B: Batch recipe creation ("Apply Meal Plan")
    path(
        'batch-create-recipes-from-ai/', 
        views.batch_create_recipes_from_ai, 
        name='batch_create_recipes_from_ai'
    ),
    
    path(
        'suggest-recipe-modifications/', 
        views.SuggestRecipeModificationsView.as_view(), 
        name='suggest_recipe_modifications'
    ),
    
    # Shopping and substitutions
    path(
        'generate-shopping-list/<uuid:meal_plan_id>/', 
        views.generate_shopping_list, 
        name='generate_shopping_list'
    ),
    path(
        'suggest-recipe-substitutions/<uuid:recipe_id>/', 
        views.suggest_recipe_substitutions, 
        name='suggest_recipe_substitutions'
    ),
] + versioned_patterns