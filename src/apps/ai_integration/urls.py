"""
URL configuration for ai_integration app.
"""
from django.urls import path
from . import views

urlpatterns = [
    # Meal plan generation
    path('generate-meal-plan/', views.GenerateMealPlanView.as_view(), name='generate_meal_plan'),
    path('analyze-meal-plan/', views.AnalyzeMealPlanView.as_view(), name='analyze_meal_plan'),
    
    # Recipe generation and modification
    path('generate-recipe-details/', views.GenerateRecipeDetailsView.as_view(), name='generate_recipe_details'),
    path('create-recipe-from-ai/', views.CreateRecipeFromAIView.as_view(), name='create_recipe_from_ai'),
    path('suggest-recipe-modifications/', views.SuggestRecipeModificationsView.as_view(), name='suggest_recipe_modifications'),
    
    # Shopping and substitutions
    path('generate-shopping-list/<uuid:meal_plan_id>/', views.generate_shopping_list, name='generate_shopping_list'),
    path('suggest-recipe-substitutions/<uuid:recipe_id>/', views.suggest_recipe_substitutions, name='suggest_recipe_substitutions'),
]