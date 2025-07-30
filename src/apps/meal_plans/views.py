"""
Meal plan views for MealPrepAI Django backend.
"""
import logging
from django.db import transaction
from django.db.models import Q
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets, generics, status, filters
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied, NotFound
from django.http import Http404

from src.common.pagination import StandardResultsSetPagination
from src.common.permissions import IsAuthenticatedAndActive
from apps.recipes.models import Recipe
from .models import MealPlan, MealPlanItem
from .serializers import (
    MealPlanSerializer,
    MealPlanListSerializer,
    MealPlanCreateSerializer,
    MealPlanUpdateSerializer,
    MealPlanItemSerializer,
    AddMealPlanItemSerializer,
    MealPlanAnalysisSerializer
)

logger = logging.getLogger(__name__)


class MealPlanViewSet(viewsets.ModelViewSet):
    """Meal plan CRUD operations with filtering and pagination."""
    
    permission_classes = [IsAuthenticatedAndActive]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    
    # Search fields
    search_fields = ['name', 'description', 'plan_description']
    
    # Ordering fields
    ordering_fields = ['name', 'week_start_date', 'created_at', 'updated_at', 'is_active']
    ordering = ['-created_at']
    
    # Filter fields
    filterset_fields = {
        'is_active': ['exact'],
        'week_start_date': ['exact', 'gte', 'lte'],
        'created_at': ['gte', 'lte'],
    }

    def get_queryset(self):
        """Get meal plans for the authenticated user only."""
        return MealPlan.objects.filter(user=self.request.user).select_related('user').prefetch_related('items__recipe')

    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'list':
            return MealPlanListSerializer
        elif self.action == 'create':
            return MealPlanCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return MealPlanUpdateSerializer
        return MealPlanSerializer

    def list(self, request):
        """List user's meal plans with filtering and pagination."""
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
            logger.error(f"Error listing meal plans for user {request.user.id}: {str(e)}", exc_info=True)
            return Response(
                {'error': 'Failed to retrieve meal plans'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @transaction.atomic
    def create(self, request):
        """Create a new meal plan with optional items."""
        try:
            # Log the incoming request data for debugging
            logger.info(f"[SaveTemplate] Creating meal plan for user {request.user.id}")
            logger.info(f"[SaveTemplate] Request data: {request.data}")
            logger.info(f"[SaveTemplate] Request content type: {request.content_type}")
            logger.info(f"[SaveTemplate] Request method: {request.method}")
            
            serializer = self.get_serializer(data=request.data, context={'request': request})
            
            if serializer.is_valid():
                meal_plan = serializer.save()
                
                logger.info(f"[SaveTemplate] Meal plan '{meal_plan.name}' created successfully by user {request.user.id}")
                
                # Return meal plan data without items for now to avoid composite key issues
                response_serializer = MealPlanListSerializer(meal_plan, context={'request': request})
                return Response(
                    response_serializer.data,
                    status=status.HTTP_201_CREATED
                )
            
            # Log detailed validation errors
            logger.error(f"[SaveTemplate] Validation failed for user {request.user.id}")
            logger.error(f"[SaveTemplate] Validation errors: {serializer.errors}")
            logger.error(f"[SaveTemplate] Request data that failed validation: {request.data}")
            
            return Response(
                {'error': 'Validation failed', 'details': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        except Exception as e:
            logger.error(f"[SaveTemplate] Exception creating meal plan for user {request.user.id}: {str(e)}", exc_info=True)
            logger.error(f"[SaveTemplate] Request data when exception occurred: {request.data}")
            return Response(
                {'error': 'Failed to create meal plan'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def retrieve(self, request, pk=None):
        """Get individual meal plan details."""
        try:
            meal_plan = self.get_object()
            serializer = self.get_serializer(meal_plan)
            return Response(serializer.data)
            
        except (MealPlan.DoesNotExist, NotFound, Http404):
            return Response(
                {'error': 'Meal plan not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error retrieving meal plan {pk}: {str(e)}", exc_info=True)
            return Response(
                {'error': 'Failed to retrieve meal plan'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @transaction.atomic
    def update(self, request, pk=None):
        """Update an existing meal plan (full update)."""
        try:
            meal_plan = self.get_object()
            serializer = self.get_serializer(meal_plan, data=request.data, context={'request': request})
            
            if serializer.is_valid():
                updated_meal_plan = serializer.save()
                
                logger.info(f"Meal plan '{updated_meal_plan.name}' updated by user {request.user.id}")
                
                return Response(serializer.data)
            
            return Response(
                {'error': 'Validation failed', 'details': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        except MealPlan.DoesNotExist:
            return Response(
                {'error': 'Meal plan not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error updating meal plan {pk}: {str(e)}", exc_info=True)
            return Response(
                {'error': 'Failed to update meal plan'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @transaction.atomic
    def partial_update(self, request, pk=None):
        """Partially update an existing meal plan."""
        try:
            meal_plan = self.get_object()
            serializer = self.get_serializer(meal_plan, data=request.data, partial=True, context={'request': request})
            
            if serializer.is_valid():
                updated_meal_plan = serializer.save()
                
                logger.info(f"Meal plan '{updated_meal_plan.name}' partially updated by user {request.user.id}")
                
                return Response(serializer.data)
            
            return Response(
                {'error': 'Validation failed', 'details': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        except MealPlan.DoesNotExist:
            return Response(
                {'error': 'Meal plan not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error partially updating meal plan {pk}: {str(e)}", exc_info=True)
            return Response(
                {'error': 'Failed to update meal plan'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @transaction.atomic
    def destroy(self, request, pk=None):
        """Delete a meal plan."""
        try:
            meal_plan = self.get_object()
            meal_plan_name = meal_plan.name
            meal_plan.delete()
            
            logger.info(f"Meal plan '{meal_plan_name}' deleted by user {request.user.id}")
            
            return Response(
                {'message': f'Meal plan "{meal_plan_name}" has been deleted successfully'},
                status=status.HTTP_204_NO_CONTENT
            )
            
        except MealPlan.DoesNotExist:
            return Response(
                {'error': 'Meal plan not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error deleting meal plan {pk}: {str(e)}", exc_info=True)
            return Response(
                {'error': 'Failed to delete meal plan'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        """Activate a meal plan (deactivate others for the same week)."""
        try:
            meal_plan = self.get_object()
            
            # Deactivate any other active meal plans for this week
            MealPlan.objects.filter(
                user=request.user,
                week_start_date=meal_plan.week_start_date,
                is_active=True
            ).exclude(pk=meal_plan.pk).update(is_active=False)
            
            # Activate this meal plan
            meal_plan.is_active = True
            meal_plan.save()
            
            logger.info(f"Meal plan '{meal_plan.name}' activated by user {request.user.id}")
            
            serializer = self.get_serializer(meal_plan)
            return Response(serializer.data)
            
        except MealPlan.DoesNotExist:
            return Response(
                {'error': 'Meal plan not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error activating meal plan {pk}: {str(e)}", exc_info=True)
            return Response(
                {'error': 'Failed to activate meal plan'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        """Deactivate a meal plan."""
        try:
            meal_plan = self.get_object()
            meal_plan.is_active = False
            meal_plan.save()
            
            logger.info(f"Meal plan '{meal_plan.name}' deactivated by user {request.user.id}")
            
            serializer = self.get_serializer(meal_plan)
            return Response(serializer.data)
            
        except MealPlan.DoesNotExist:
            return Response(
                {'error': 'Meal plan not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error deactivating meal plan {pk}: {str(e)}", exc_info=True)
            return Response(
                {'error': 'Failed to deactivate meal plan'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def active(self, request):
        """Get the currently active meal plan."""
        try:
            active_meal_plan = self.get_queryset().filter(is_active=True).first()
            
            if not active_meal_plan:
                return Response(
                    {'message': 'No active meal plan found'},
                    status=status.HTTP_204_NO_CONTENT
                )
            
            serializer = self.get_serializer(active_meal_plan)
            return Response(serializer.data)
            
        except Exception as e:
            logger.error(f"Error getting active meal plan for user {request.user.id}: {str(e)}", exc_info=True)
            return Response(
                {'error': 'Failed to get active meal plan'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'])
    def analyze(self, request, pk=None):
        """Analyze a meal plan for nutrition, variety, and balance."""
        try:
            meal_plan = self.get_object()
            
            # This would integrate with AI service for analysis
            # For now, return a placeholder
            analysis = {
                'meal_plan_id': str(meal_plan.id),
                'analysis_type': 'placeholder',
                'nutrition_summary': {
                    'total_recipes': meal_plan.items.count(),
                    'calories_estimate': 'Analysis coming soon',
                    'macros': 'Analysis coming soon'
                },
                'variety_score': 'Analysis coming soon',
                'balance_assessment': 'Analysis coming soon',
                'recommendations': ['AI analysis will be implemented soon']
            }
            
            return Response(analysis)
            
        except MealPlan.DoesNotExist:
            return Response(
                {'error': 'Meal plan not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error analyzing meal plan {pk}: {str(e)}", exc_info=True)
            return Response(
                {'error': 'Failed to analyze meal plan'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class MealPlanItemView(generics.CreateAPIView):
    """Add items to meal plans."""
    permission_classes = [IsAuthenticated]
    serializer_class = AddMealPlanItemSerializer

    def get_meal_plan(self, meal_plan_id):
        """Get meal plan and verify ownership."""
        try:
            meal_plan = MealPlan.objects.get(id=meal_plan_id, user=self.request.user)
            return meal_plan
        except MealPlan.DoesNotExist:
            raise NotFound('Meal plan not found')

    @transaction.atomic
    def post(self, request, meal_plan_id):
        """Add or update a meal plan item."""
        try:
            meal_plan = self.get_meal_plan(meal_plan_id)
            
            serializer = self.get_serializer(
                data=request.data,
                context={'meal_plan': meal_plan, 'request': request}
            )
            
            if serializer.is_valid():
                item = serializer.save()
                
                logger.info(f"Meal plan item added to '{meal_plan.name}' by user {request.user.id}")
                
                # Return the created item with full recipe details
                response_serializer = MealPlanItemSerializer(item)
                return Response(
                    response_serializer.data,
                    status=status.HTTP_201_CREATED
                )
            
            return Response(
                {'error': 'Validation failed', 'details': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        except NotFound as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error adding meal plan item: {str(e)}", exc_info=True)
            return Response(
                {'error': 'Failed to add meal plan item'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class MealPlanItemDetailView(generics.DestroyAPIView):
    """Remove items from meal plans."""
    permission_classes = [IsAuthenticated]

    def get_meal_plan_item(self, meal_plan_id, day_of_week, meal_type):
        """Get meal plan item and verify ownership."""
        try:
            meal_plan = MealPlan.objects.get(id=meal_plan_id, user=self.request.user)
            item = MealPlanItem.objects.get(
                meal_plan=meal_plan,
                day_of_week=day_of_week,
                meal_type=meal_type
            )
            return item
        except (MealPlan.DoesNotExist, MealPlanItem.DoesNotExist):
            raise NotFound('Meal plan item not found')

    @transaction.atomic
    def delete(self, request, meal_plan_id, day_of_week, meal_type):
        """Remove a specific meal plan item."""
        try:
            # Validate day_of_week
            try:
                day_of_week = int(day_of_week)
                if day_of_week < 0 or day_of_week > 6:
                    return Response(
                        {'error': 'Day of week must be between 0 (Monday) and 6 (Sunday)'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            except ValueError:
                return Response(
                    {'error': 'Day of week must be a valid integer'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Validate meal_type
            valid_meal_types = ['breakfast', 'lunch', 'dinner', 'snack']
            if meal_type not in valid_meal_types:
                return Response(
                    {'error': f'Meal type must be one of: {", ".join(valid_meal_types)}'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            item = self.get_meal_plan_item(meal_plan_id, day_of_week, meal_type)
            recipe_name = item.recipe.name
            item.delete()
            
            logger.info(f"Meal plan item '{recipe_name}' removed by user {request.user.id}")
            
            return Response(
                {'message': f'Recipe "{recipe_name}" has been removed from the meal plan'},
                status=status.HTTP_204_NO_CONTENT
            )
            
        except NotFound as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error removing meal plan item: {str(e)}", exc_info=True)
            return Response(
                {'error': 'Failed to remove meal plan item'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )