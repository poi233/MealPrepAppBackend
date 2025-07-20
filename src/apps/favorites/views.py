"""
Favorites views for MealPrepAI Django backend.
"""
import logging
from django.db import transaction
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets, generics, status, filters
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.exceptions import NotFound

from src.common.pagination import StandardResultsSetPagination
from src.common.permissions import IsAuthenticatedAndActive
from apps.recipes.models import Recipe
from .models import Favorite, Collection, CollectionRecipe
from .serializers import (
    FavoriteSerializer,
    FavoriteListSerializer,
    FavoriteCreateSerializer,
    CollectionSerializer,
    CollectionListSerializer,
    CollectionCreateSerializer,
    AddRecipeToCollectionSerializer
)

logger = logging.getLogger(__name__)


class FavoriteViewSet(viewsets.ModelViewSet):
    """Favorite recipes CRUD operations."""
    
    permission_classes = [IsAuthenticatedAndActive]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    
    # Search fields (search within recipe fields)
    search_fields = ['recipe__name', 'recipe__description', 'recipe__cuisine', 'personal_notes']
    
    # Ordering fields
    ordering_fields = ['added_at', 'personal_rating', 'recipe__name', 'recipe__created_at']
    ordering = ['-added_at']
    
    # Filter fields
    filterset_fields = {
        'personal_rating': ['exact', 'gte', 'lte'],
        'recipe__cuisine': ['exact', 'icontains'],
        'recipe__difficulty': ['exact'],
        'added_at': ['gte', 'lte'],
    }

    def get_queryset(self):
        """Get favorites for the authenticated user only."""
        return Favorite.objects.filter(user=self.request.user).select_related('user', 'recipe')

    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'list':
            return FavoriteListSerializer
        elif self.action == 'create':
            return FavoriteCreateSerializer
        return FavoriteSerializer

    def list(self, request):
        """List user's favorite recipes with filtering and pagination."""
        try:
            queryset = self.filter_queryset(self.get_queryset())
            page = self.paginate_queryset(queryset)
            
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                return self.get_paginated_response(serializer.data)
            
            serializer = self.get_serializer(queryset, many=True)
            return Response({
                'count': queryset.count(),
                'results': serializer.data
            })
            
        except Exception as e:
            logger.error(f"Error listing favorites for user {request.user.id}: {str(e)}", exc_info=True)
            return Response(
                {'error': 'Failed to retrieve favorites'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @transaction.atomic
    def create(self, request):
        """Add a recipe to favorites."""
        try:
            serializer = self.get_serializer(data=request.data, context={'request': request})
            
            if serializer.is_valid():
                favorite = serializer.save()
                
                logger.info(f"Recipe {favorite.recipe.name} added to favorites by user {request.user.id}")
                
                # Return full favorite data
                response_serializer = FavoriteSerializer(favorite, context={'request': request})
                return Response(
                    response_serializer.data,
                    status=status.HTTP_201_CREATED
                )
            
            return Response(
                {'error': 'Validation failed', 'details': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        except Exception as e:
            logger.error(f"Error adding favorite for user {request.user.id}: {str(e)}", exc_info=True)
            return Response(
                {'error': 'Failed to add favorite'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def retrieve(self, request, pk=None):
        """Get individual favorite details."""
        try:
            favorite = self.get_object()
            serializer = self.get_serializer(favorite)
            return Response(serializer.data)
            
        except Favorite.DoesNotExist:
            return Response(
                {'error': 'Favorite not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error retrieving favorite: {str(e)}", exc_info=True)
            return Response(
                {'error': 'Failed to retrieve favorite'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @transaction.atomic
    def update(self, request, pk=None):
        """Update favorite (rating and notes)."""
        try:
            favorite = self.get_object()
            serializer = self.get_serializer(favorite, data=request.data, context={'request': request})
            
            if serializer.is_valid():
                updated_favorite = serializer.save()
                
                logger.info(f"Favorite updated by user {request.user.id}")
                
                return Response(serializer.data)
            
            return Response(
                {'error': 'Validation failed', 'details': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        except Favorite.DoesNotExist:
            return Response(
                {'error': 'Favorite not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error updating favorite: {str(e)}", exc_info=True)
            return Response(
                {'error': 'Failed to update favorite'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @transaction.atomic
    def destroy(self, request, pk=None):
        """Remove recipe from favorites."""
        try:
            favorite = self.get_object()
            recipe_name = favorite.recipe.name
            favorite.delete()
            
            logger.info(f"Recipe '{recipe_name}' removed from favorites by user {request.user.id}")
            
            return Response(
                {'message': f'Recipe "{recipe_name}" has been removed from favorites'},
                status=status.HTTP_204_NO_CONTENT
            )
            
        except Favorite.DoesNotExist:
            return Response(
                {'error': 'Favorite not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error removing favorite: {str(e)}", exc_info=True)
            return Response(
                {'error': 'Failed to remove favorite'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class FavoriteByRecipeView(generics.CreateAPIView, generics.DestroyAPIView):
    """Add/remove recipes from favorites by recipe ID."""
    permission_classes = [IsAuthenticated]
    
    def get_favorite(self, recipe_id):
        """Get favorite by recipe ID and verify ownership."""
        try:
            recipe = Recipe.objects.get(id=recipe_id)
            favorite = Favorite.objects.get(user=self.request.user, recipe=recipe)
            return favorite
        except (Recipe.DoesNotExist, Favorite.DoesNotExist):
            return None

    @transaction.atomic
    def post(self, request, recipe_id):
        """Add recipe to favorites by recipe ID."""
        try:
            # Check if recipe exists
            try:
                recipe = Recipe.objects.get(id=recipe_id)
            except Recipe.DoesNotExist:
                return Response(
                    {'error': 'Recipe not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Check if already favorited
            existing_favorite = self.get_favorite(recipe_id)
            if existing_favorite:
                return Response(
                    {'error': 'Recipe is already in favorites'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Create favorite
            data = {
                'recipe_id': recipe_id,
                'personal_rating': request.data.get('personal_rating'),
                'personal_notes': request.data.get('personal_notes', '')
            }
            
            serializer = FavoriteCreateSerializer(data=data, context={'request': request})
            
            if serializer.is_valid():
                favorite = serializer.save()
                
                logger.info(f"Recipe {recipe.name} added to favorites by user {request.user.id}")
                
                # Return full favorite data
                response_serializer = FavoriteSerializer(favorite, context={'request': request})
                return Response(
                    response_serializer.data,
                    status=status.HTTP_201_CREATED
                )
            
            return Response(
                {'error': 'Validation failed', 'details': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        except Exception as e:
            logger.error(f"Error adding recipe to favorites: {str(e)}", exc_info=True)
            return Response(
                {'error': 'Failed to add recipe to favorites'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @transaction.atomic
    def delete(self, request, recipe_id):
        """Remove recipe from favorites by recipe ID."""
        try:
            favorite = self.get_favorite(recipe_id)
            
            if not favorite:
                return Response(
                    {'error': 'Recipe is not in favorites'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            recipe_name = favorite.recipe.name
            favorite.delete()
            
            logger.info(f"Recipe '{recipe_name}' removed from favorites by user {request.user.id}")
            
            return Response(
                {'message': f'Recipe "{recipe_name}" has been removed from favorites'},
                status=status.HTTP_204_NO_CONTENT
            )
            
        except Exception as e:
            logger.error(f"Error removing recipe from favorites: {str(e)}", exc_info=True)
            return Response(
                {'error': 'Failed to remove recipe from favorites'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def get(self, request, recipe_id):
        """Check if recipe is in favorites."""
        try:
            favorite = self.get_favorite(recipe_id)
            
            if favorite:
                serializer = FavoriteSerializer(favorite, context={'request': request})
                return Response(serializer.data)
            else:
                return Response(
                    {'is_favorite': False},
                    status=status.HTTP_200_OK
                )
                
        except Exception as e:
            logger.error(f"Error checking favorite status: {str(e)}", exc_info=True)
            return Response(
                {'error': 'Failed to check favorite status'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class CollectionViewSet(viewsets.ModelViewSet):
    """Collection CRUD operations."""
    
    permission_classes = [IsAuthenticatedAndActive]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    
    # Search fields
    search_fields = ['name', 'description']
    
    # Ordering fields
    ordering_fields = ['name', 'created_at', 'updated_at']
    ordering = ['-created_at']
    
    # Filter fields
    filterset_fields = {
        'is_public': ['exact'],
        'created_at': ['gte', 'lte'],
    }

    def get_queryset(self):
        """Get collections for the authenticated user only."""
        return Collection.objects.filter(user=self.request.user).prefetch_related('recipes')

    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'list':
            return CollectionListSerializer
        elif self.action == 'create':
            return CollectionCreateSerializer
        return CollectionSerializer

    def list(self, request):
        """List user's collections with filtering and pagination."""
        try:
            queryset = self.filter_queryset(self.get_queryset())
            page = self.paginate_queryset(queryset)
            
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                return self.get_paginated_response(serializer.data)
            
            serializer = self.get_serializer(queryset, many=True)
            return Response({
                'count': queryset.count(),
                'results': serializer.data
            })
            
        except Exception as e:
            logger.error(f"Error listing collections for user {request.user.id}: {str(e)}", exc_info=True)
            return Response(
                {'error': 'Failed to retrieve collections'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @transaction.atomic
    def create(self, request):
        """Create a new collection."""
        try:
            serializer = self.get_serializer(data=request.data, context={'request': request})
            
            if serializer.is_valid():
                collection = serializer.save()
                
                logger.info(f"Collection '{collection.name}' created by user {request.user.id}")
                
                # Return full collection data
                response_serializer = CollectionSerializer(collection, context={'request': request})
                return Response(
                    response_serializer.data,
                    status=status.HTTP_201_CREATED
                )
            
            return Response(
                {'error': 'Validation failed', 'details': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        except Exception as e:
            logger.error(f"Error creating collection for user {request.user.id}: {str(e)}", exc_info=True)
            return Response(
                {'error': 'Failed to create collection'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'])
    def add_recipe(self, request, pk=None):
        """Add a recipe to the collection."""
        try:
            collection = self.get_object()
            
            serializer = AddRecipeToCollectionSerializer(
                data=request.data,
                context={'collection': collection, 'request': request}
            )
            
            if serializer.is_valid():
                collection_recipe = serializer.save()
                
                logger.info(f"Recipe added to collection '{collection.name}' by user {request.user.id}")
                
                return Response(
                    {'message': f'Recipe added to collection "{collection.name}"'},
                    status=status.HTTP_201_CREATED
                )
            
            return Response(
                {'error': 'Validation failed', 'details': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        except Collection.DoesNotExist:
            return Response(
                {'error': 'Collection not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error adding recipe to collection: {str(e)}", exc_info=True)
            return Response(
                {'error': 'Failed to add recipe to collection'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['delete'], url_path='remove-recipe/(?P<recipe_id>[^/.]+)')
    def remove_recipe(self, request, pk=None, recipe_id=None):
        """Remove a recipe from the collection."""
        try:
            collection = self.get_object()
            
            # Find and delete the collection recipe
            try:
                collection_recipe = CollectionRecipe.objects.get(
                    collection=collection,
                    recipe_id=recipe_id
                )
                recipe_name = collection_recipe.recipe.name
                collection_recipe.delete()
                
                logger.info(f"Recipe '{recipe_name}' removed from collection '{collection.name}' by user {request.user.id}")
                
                return Response(
                    {'message': f'Recipe "{recipe_name}" removed from collection "{collection.name}"'},
                    status=status.HTTP_204_NO_CONTENT
                )
                
            except CollectionRecipe.DoesNotExist:
                return Response(
                    {'error': 'Recipe is not in this collection'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
        except Collection.DoesNotExist:
            return Response(
                {'error': 'Collection not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error removing recipe from collection: {str(e)}", exc_info=True)
            return Response(
                {'error': 'Failed to remove recipe from collection'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# Legacy endpoints for backward compatibility
class FavoriteListView(generics.ListAPIView):
    """List user's favorite recipes."""
    permission_classes = [IsAuthenticated]
    serializer_class = FavoriteListSerializer
    pagination_class = StandardResultsSetPagination
    
    def get_queryset(self):
        """Get favorites for the authenticated user only."""
        return Favorite.objects.filter(user=self.request.user).select_related('user', 'recipe')


class FavoriteDetailView(generics.CreateAPIView, generics.DestroyAPIView):
    """Add/remove recipes from favorites."""
    permission_classes = [IsAuthenticated]
    
    def post(self, request, recipe_id):
        """Add recipe to favorites."""
        view = FavoriteByRecipeView()
        view.setup(request)
        return view.post(request, recipe_id)
    
    def delete(self, request, recipe_id):
        """Remove recipe from favorites."""
        view = FavoriteByRecipeView()
        view.setup(request)
        return view.delete(request, recipe_id)