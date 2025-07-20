"""
URL configuration for meal_plans app.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'', views.MealPlanViewSet, basename='mealplan')

urlpatterns = [
    # ViewSet routes (includes list, create, retrieve, update, destroy, activate, deactivate, active, analyze)
    path('', include(router.urls)),
    
    # Meal plan item management
    path('<uuid:meal_plan_id>/items/', views.MealPlanItemView.as_view(), name='meal_plan_items'),
    path('<uuid:meal_plan_id>/items/<int:day_of_week>/<str:meal_type>/', 
         views.MealPlanItemDetailView.as_view(), name='meal_plan_item_detail'),
]