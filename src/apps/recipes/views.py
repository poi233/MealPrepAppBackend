"""
Recipe views for MealPrepAI Django backend.
"""
from django.db.models import Q
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets, generics, status, filters
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied, NotFound

from src.common.pagination import StandardResultsSetPagination
from src.common.permissions import IsAuthenticatedAndActive, ReadOnlyOrOwner
from .models import Recipe
from .serializers import (
    RecipeSerializer, 
    RecipeListSerializer, 
    RecipeCreateSerializer
)


class RecipeViewSet(viewsets.ModelViewSet):
    """Recipe CRUD operations with filtering, pagination, and search."""
    
    queryset = Recipe.objects.all()
    permission_classes = [IsAuthenticatedAndActive, ReadOnlyOrOwner]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    
    # Search fields
    search_fields = ['name', 'description', 'cuisine', 'tags']
    
    # Ordering fields
    ordering_fields = ['name', 'created_at', 'updated_at', 'avg_rating', 'prep_time', 'cook_time']
    ordering = ['-created_at']  # Default ordering
    
    # Filter fields (removed tags from filterset_fields to handle manually)
    filterset_fields = {
        'cuisine': ['exact', 'icontains'],
        'difficulty': ['exact'],
        'prep_time': ['lte', 'gte'],
        'cook_time': ['lte', 'gte'],
        'avg_rating': ['gte'],
        'created_by_user': ['exact'],
    }

    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'list':
            return RecipeListSerializer
        elif self.action == 'create':
            return RecipeCreateSerializer
        return RecipeSerializer

    def get_queryset(self):
        """Get filtered queryset based on query parameters."""
        queryset = Recipe.objects.all()
        
        # Filter by user's own recipes if requested
        if self.request.query_params.get('my_recipes') == 'true':
            queryset = queryset.filter(created_by_user=self.request.user)
        
        # Filter by tags (support multiple tags)
        tags = self.request.query_params.getlist('tags')
        if tags:
            for tag in tags:
                queryset = queryset.filter(tags__contains=[tag])
        
        # Filter by meal type (if provided in tags)
        meal_type = self.request.query_params.get('meal_type')
        if meal_type:
            queryset = queryset.filter(tags__contains=[meal_type])
        
        # Filter by total time (prep_time + cook_time)
        max_total_time = self.request.query_params.get('max_total_time')
        if max_total_time:
            try:
                max_time = int(max_total_time)
                queryset = queryset.extra(
                    where=["prep_time + cook_time <= %s"],
                    params=[max_time]
                )
            except ValueError:
                pass
        
        # Filter by minimum rating
        min_rating = self.request.query_params.get('min_rating')
        if min_rating:
            try:
                rating = float(min_rating)
                queryset = queryset.filter(avg_rating__gte=rating)
            except ValueError:
                pass
        
        return queryset.select_related('created_by_user')

    def list(self, request):
        """List recipes with filtering, pagination, and search."""
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
            return Response(
                {'error': f'Failed to retrieve recipes: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def create(self, request):
        """Create a new recipe with validation."""
        try:
            serializer = self.get_serializer(data=request.data)
            if serializer.is_valid():
                # The serializer will automatically set created_by_user from request context
                recipe = serializer.save()
                
                # Return full recipe data
                response_serializer = RecipeSerializer(recipe)
                return Response(
                    response_serializer.data, 
                    status=status.HTTP_201_CREATED
                )
            
            return Response(
                {'error': 'Validation failed', 'details': serializer.errors}, 
                status=status.HTTP_400_BAD_REQUEST
            )
            
        except Exception as e:
            return Response(
                {'error': f'Failed to create recipe: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def retrieve(self, request, pk=None):
        """Get individual recipe details."""
        try:
            recipe = self.get_object()
            serializer = self.get_serializer(recipe)
            return Response(serializer.data)
            
        except Recipe.DoesNotExist:
            return Response(
                {'error': 'Recipe not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': f'Failed to retrieve recipe: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def update(self, request, pk=None):
        """Update an existing recipe (full update)."""
        try:
            recipe = self.get_object()
            
            # Check ownership permission
            if recipe.created_by_user != request.user:
                raise PermissionDenied("You can only update your own recipes")
            
            serializer = self.get_serializer(recipe, data=request.data)
            if serializer.is_valid():
                updated_recipe = serializer.save()
                return Response(serializer.data)
            
            return Response(
                {'error': 'Validation failed', 'details': serializer.errors}, 
                status=status.HTTP_400_BAD_REQUEST
            )
            
        except Recipe.DoesNotExist:
            return Response(
                {'error': 'Recipe not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        except PermissionDenied as e:
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_403_FORBIDDEN
            )
        except Exception as e:
            return Response(
                {'error': f'Failed to update recipe: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def partial_update(self, request, pk=None):
        """Partially update an existing recipe."""
        try:
            recipe = self.get_object()
            
            # Check ownership permission
            if recipe.created_by_user != request.user:
                raise PermissionDenied("You can only update your own recipes")
            
            serializer = self.get_serializer(recipe, data=request.data, partial=True)
            if serializer.is_valid():
                updated_recipe = serializer.save()
                return Response(serializer.data)
            
            return Response(
                {'error': 'Validation failed', 'details': serializer.errors}, 
                status=status.HTTP_400_BAD_REQUEST
            )
            
        except Recipe.DoesNotExist:
            return Response(
                {'error': 'Recipe not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        except PermissionDenied as e:
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_403_FORBIDDEN
            )
        except Exception as e:
            return Response(
                {'error': f'Failed to update recipe: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def destroy(self, request, pk=None):
        """Delete a recipe (only by owner)."""
        try:
            recipe = self.get_object()
            
            # Check ownership permission
            if recipe.created_by_user != request.user:
                raise PermissionDenied("You can only delete your own recipes")
            
            recipe_name = recipe.name
            recipe.delete()
            
            return Response(
                {'message': f'Recipe "{recipe_name}" has been deleted successfully'}, 
                status=status.HTTP_204_NO_CONTENT
            )
            
        except Recipe.DoesNotExist:
            return Response(
                {'error': 'Recipe not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        except PermissionDenied as e:
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_403_FORBIDDEN
            )
        except Exception as e:
            return Response(
                {'error': f'Failed to delete recipe: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def my_recipes(self, request):
        """Get current user's recipes."""
        try:
            queryset = self.get_queryset().filter(created_by_user=request.user)
            queryset = self.filter_queryset(queryset)
            page = self.paginate_queryset(queryset)
            
            if page is not None:
                serializer = RecipeListSerializer(page, many=True)
                return self.get_paginated_response(serializer.data)
            
            serializer = RecipeListSerializer(queryset, many=True)
            return Response({
                'count': queryset.count(),
                'results': serializer.data
            })
            
        except Exception as e:
            return Response(
                {'error': f'Failed to retrieve your recipes: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def search(self, request):
        """Advanced search endpoint with multiple criteria."""
        try:
            query = request.query_params.get('q', '')
            if not query:
                return Response(
                    {'error': 'Search query parameter "q" is required'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Build complex search query
            search_query = Q()
            
            # Search in name, description, cuisine, and tags
            search_query |= Q(name__icontains=query)
            search_query |= Q(description__icontains=query)
            search_query |= Q(cuisine__icontains=query)
            search_query |= Q(tags__contains=[query])
            
            # Search in ingredients (JSON field)
            search_query |= Q(ingredients__icontains=query)
            
            queryset = self.get_queryset().filter(search_query).distinct()
            queryset = self.filter_queryset(queryset)
            
            page = self.paginate_queryset(queryset)
            if page is not None:
                serializer = RecipeListSerializer(page, many=True)
                return self.get_paginated_response(serializer.data)
            
            serializer = RecipeListSerializer(queryset, many=True)
            return Response({
                'count': queryset.count(),
                'results': serializer.data
            })
            
        except Exception as e:
            return Response(
                {'error': f'Search failed: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class GenerateRecipeDetailsView(generics.CreateAPIView):
    """AI-powered recipe detail generation."""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        # Basic implementation - will be expanded in task 8
        return Response({'message': 'Generate recipe details endpoint - to be implemented'}, 
                       status=status.HTTP_501_NOT_IMPLEMENTED)