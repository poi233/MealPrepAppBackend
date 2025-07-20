"""
URL configuration for favorites app.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# Set up routers for ViewSets
favorites_router = DefaultRouter()
favorites_router.register(r'favorites', views.FavoriteViewSet, basename='favorite')

collections_router = DefaultRouter()
collections_router.register(r'collections', views.CollectionViewSet, basename='collection')

urlpatterns = [
    # ViewSet routes
    path('', include(favorites_router.urls)),
    path('', include(collections_router.urls)),
    
    # Recipe-specific favorite endpoints (for compatibility with existing frontend)
    path('recipe/<uuid:recipe_id>/', views.FavoriteByRecipeView.as_view(), name='favorite_by_recipe'),
    
    # Legacy endpoints for backward compatibility
    path('list/', views.FavoriteListView.as_view(), name='favorite_list_legacy'),
    path('<uuid:recipe_id>/', views.FavoriteDetailView.as_view(), name='favorite_detail_legacy'),
]