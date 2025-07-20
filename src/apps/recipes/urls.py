"""
URL configuration for recipes app.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'', views.RecipeViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('generate/', views.GenerateRecipeDetailsView.as_view(), name='generate_recipe'),
]