"""
AI Integration views for MealPrepAI Django backend.
"""
import logging
from datetime import date, timedelta
from django.db import transaction
from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from src.common.permissions import IsAuthenticatedAndActive
from apps.recipes.models import Recipe
from apps.recipes.serializers import RecipeSerializer
from apps.meal_plans.models import MealPlan, MealPlanItem
from .services import ai_service, MealPlanRequest, RecipeGenerationRequest
from .serializers import (
    GenerateMealPlanSerializer,
    GeneratedMealPlanSerializer,
    GenerateRecipeSerializer,
    GeneratedRecipeSerializer,
    AnalyzeMealPlanSerializer,
    MealPlanAnalysisSerializer,
    CreateRecipeFromAISerializer,
    SuggestRecipeModificationsSerializer,
    RecipeModificationSuggestionsSerializer
)

logger = logging.getLogger(__name__)


class GenerateMealPlanView(generics.CreateAPIView):
    """Generate AI-powered meal plans."""
    permission_classes = [IsAuthenticatedAndActive]
    serializer_class = GenerateMealPlanSerializer
    
    def post(self, request):
        """Generate a meal plan using AI."""
        try:
            serializer = self.get_serializer(data=request.data)
            
            if not serializer.is_valid():
                return Response(
                    {'error': 'Validation failed', 'details': serializer.errors},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            validated_data = serializer.validated_data
            
            # Create meal plan request
            meal_plan_request = MealPlanRequest(
                plan_description=validated_data['plan_description'],
                dietary_preferences=validated_data.get('dietary_preferences'),
                allergies=validated_data.get('allergies'),
                dislikes=validated_data.get('dislikes'),
                calorie_target=validated_data.get('calorie_target'),
                week_start_date=validated_data.get('week_start_date'),
                additional_requirements=validated_data.get('additional_requirements')
            )
            
            # Generate meal plan using AI service
            import asyncio
            result = asyncio.run(ai_service.generate_meal_plan(meal_plan_request, request.user))
            
            if not result['success']:
                return Response(
                    {'error': result['error']},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            
            # Serialize the generated meal plan
            meal_plan_serializer = GeneratedMealPlanSerializer(result['meal_plan'])
            
            logger.info(f"AI meal plan generated for user {request.user.id}")
            
            return Response(
                meal_plan_serializer.data,
                status=status.HTTP_201_CREATED
            )
            
        except Exception as e:
            logger.error(f"Error generating AI meal plan: {str(e)}", exc_info=True)
            return Response(
                {'error': 'Failed to generate meal plan'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class GenerateRecipeDetailsView(generics.CreateAPIView):
    """Generate AI-powered recipe details."""
    permission_classes = [IsAuthenticatedAndActive]
    serializer_class = GenerateRecipeSerializer
    
    def post(self, request):
        """Generate detailed recipe information using AI."""
        try:
            serializer = self.get_serializer(data=request.data)
            
            if not serializer.is_valid():
                return Response(
                    {'error': 'Validation failed', 'details': serializer.errors},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            validated_data = serializer.validated_data
            
            # Create recipe generation request
            recipe_request = RecipeGenerationRequest(
                name=validated_data['name'],
                description=validated_data.get('description'),
                cuisine=validated_data.get('cuisine'),
                difficulty=validated_data.get('difficulty', 'medium'),
                prep_time=validated_data.get('prep_time'),
                cook_time=validated_data.get('cook_time'),
                meal_type=validated_data.get('meal_type'),
                dietary_restrictions=validated_data.get('dietary_restrictions'),
                ingredients=validated_data.get('ingredients'),
                additional_requirements=validated_data.get('additional_requirements')
            )
            
            # Generate recipe using AI service
            import asyncio
            result = asyncio.run(ai_service.generate_recipe_details(recipe_request, request.user))
            
            if not result['success']:
                return Response(
                    {'error': result['error']},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            
            # Serialize the generated recipe
            recipe_serializer = GeneratedRecipeSerializer(result['recipe'])
            
            logger.info(f"AI recipe generated for user {request.user.id}")
            
            return Response(
                recipe_serializer.data,
                status=status.HTTP_201_CREATED
            )
            
        except Exception as e:
            logger.error(f"Error generating AI recipe: {str(e)}", exc_info=True)
            return Response(
                {'error': 'Failed to generate recipe details'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AnalyzeMealPlanView(generics.CreateAPIView):
    """Analyze meal plans with AI."""
    permission_classes = [IsAuthenticatedAndActive]
    serializer_class = AnalyzeMealPlanSerializer
    
    def post(self, request):
        """Analyze a meal plan using AI."""
        try:
            serializer = self.get_serializer(data=request.data, context={'request': request})
            
            if not serializer.is_valid():
                return Response(
                    {'error': 'Validation failed', 'details': serializer.errors},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            validated_data = serializer.validated_data
            
            # Get the meal plan
            try:
                meal_plan = MealPlan.objects.get(
                    id=validated_data['meal_plan_id'],
                    user=request.user
                )
            except MealPlan.DoesNotExist:
                return Response(
                    {'error': 'Meal plan not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Analyze meal plan using AI service
            import asyncio
            result = asyncio.run(ai_service.analyze_meal_plan(
                meal_plan,
                validated_data.get('plan_description', ''),
                validated_data.get('analysis_type', 'full')
            ))
            
            if not result['success']:
                return Response(
                    {'error': result['error']},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            
            # Serialize the analysis
            analysis_serializer = MealPlanAnalysisSerializer(result['analysis'])
            
            logger.info(f"AI meal plan analysis completed for user {request.user.id}")
            
            return Response(
                analysis_serializer.data,
                status=status.HTTP_200_OK
            )
            
        except Exception as e:
            logger.error(f"Error analyzing meal plan: {str(e)}", exc_info=True)
            return Response(
                {'error': 'Failed to analyze meal plan'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class CreateRecipeFromAIView(generics.CreateAPIView):
    """Create a recipe from AI-generated data."""
    permission_classes = [IsAuthenticatedAndActive]
    serializer_class = CreateRecipeFromAISerializer
    
    @transaction.atomic
    def post(self, request):
        """Create a recipe from AI-generated data and optionally add to meal plan."""
        try:
            serializer = self.get_serializer(data=request.data, context={'request': request})
            
            if not serializer.is_valid():
                return Response(
                    {'error': 'Validation failed', 'details': serializer.errors},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            validated_data = serializer.validated_data
            ai_recipe_data = validated_data['ai_recipe_data']
            
            if validated_data.get('save_to_account', True):
                # Create recipe from AI data
                recipe_data = {
                    'name': ai_recipe_data['name'],
                    'description': ai_recipe_data['description'],
                    'cuisine': ai_recipe_data['cuisine'],
                    'difficulty': ai_recipe_data['difficulty'],
                    'prep_time': ai_recipe_data['prep_time'],
                    'cook_time': ai_recipe_data['cook_time'],
                    'ingredients': ai_recipe_data['ingredients'],
                    'instructions': ai_recipe_data['instructions'],
                    'nutrition_info': ai_recipe_data['nutrition_info'],
                    'tags': ai_recipe_data['tags']
                }
                
                # Create recipe directly (bypassing serializer validation for ingredients)
                recipe = Recipe.objects.create(
                    created_by_user=request.user,
                    **recipe_data
                )
                
                # Add to meal plan if requested
                if validated_data.get('add_to_meal_plan'):
                    meal_plan = MealPlan.objects.get(
                        id=validated_data['add_to_meal_plan'],
                        user=request.user
                    )
                    
                    # Add to meal plan
                    MealPlanItem.objects.create(
                        meal_plan=meal_plan,
                        recipe=recipe,
                        day_of_week=validated_data['meal_plan_day'],
                        meal_type=validated_data['meal_plan_type']
                    )
                
                # Return the created recipe in the expected format
                recipe_data = {
                    'id': str(recipe.id),
                    'created_by_user_id': str(recipe.created_by_user.id) if recipe.created_by_user else None,
                    'name': recipe.name,
                    'description': recipe.description,
                    'ingredients': recipe.ingredients,
                    'instructions': recipe.instructions,
                    'nutrition_info': recipe.nutrition_info,
                    'cuisine': recipe.cuisine,
                    'prep_time': recipe.prep_time,
                    'cook_time': recipe.cook_time,
                    'difficulty': recipe.difficulty,
                    'avg_rating': float(recipe.avg_rating),
                    'rating_count': recipe.rating_count,
                    'image_url': recipe.image_url,
                    'tags': recipe.tags,
                    'created_at': recipe.created_at.isoformat(),
                    'updated_at': recipe.updated_at.isoformat()
                }
                
                logger.info(f"Recipe created from AI data for user {request.user.id}")
                
                return Response(
                    recipe_data,
                    status=status.HTTP_201_CREATED
                )
            else:
                # Just return the AI-generated data without saving
                return Response(
                    ai_recipe_data,
                    status=status.HTTP_200_OK
                )
            
        except Exception as e:
            logger.error(f"Error creating recipe from AI data: {str(e)}", exc_info=True)
            return Response(
                {'error': 'Failed to create recipe from AI data'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class SuggestRecipeModificationsView(generics.CreateAPIView):
    """Suggest recipe modifications using AI."""
    permission_classes = [IsAuthenticatedAndActive]
    serializer_class = SuggestRecipeModificationsSerializer
    
    def post(self, request):
        """Suggest modifications to an existing recipe."""
        try:
            serializer = self.get_serializer(data=request.data)
            
            if not serializer.is_valid():
                return Response(
                    {'error': 'Validation failed', 'details': serializer.errors},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            validated_data = serializer.validated_data
            
            # Get the recipe
            try:
                recipe = Recipe.objects.get(id=validated_data['recipe_id'])
            except Recipe.DoesNotExist:
                return Response(
                    {'error': 'Recipe not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Mock modification suggestions
            # In production, this would use AI to suggest modifications
            modification_type = validated_data['modification_type']
            target_value = validated_data['target_value']
            
            suggestions = {
                'original_recipe_id': str(recipe.id),
                'modification_type': modification_type,
                'suggested_changes': {
                    'summary': f'Suggested modifications to make recipe {target_value}',
                    'changes': [
                        f'Adjust ingredients to meet {target_value} requirements',
                        f'Modify cooking method for {target_value} outcome',
                        f'Update nutritional profile to align with {target_value}'
                    ]
                },
                'estimated_impact': {
                    'difficulty_change': 'minimal',
                    'time_change': '5-10 minutes',
                    'taste_impact': 'positive',
                    'nutrition_impact': 'improved'
                }
            }
            
            if modification_type == 'dietary':
                suggestions['alternative_ingredients'] = [
                    {'original': 'butter', 'alternative': 'olive oil', 'reason': f'Better for {target_value} diet'},
                    {'original': 'regular flour', 'alternative': 'almond flour', 'reason': f'Suitable for {target_value} requirements'}
                ]
            
            suggestions_serializer = RecipeModificationSuggestionsSerializer(suggestions)
            
            logger.info(f"Recipe modification suggestions generated for user {request.user.id}")
            
            return Response(
                suggestions_serializer.data,
                status=status.HTTP_200_OK
            )
            
        except Exception as e:
            logger.error(f"Error suggesting recipe modifications: {str(e)}", exc_info=True)
            return Response(
                {'error': 'Failed to suggest recipe modifications'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


@api_view(['POST'])
@permission_classes([IsAuthenticatedAndActive])
def generate_shopping_list(request, meal_plan_id):
    """Generate a shopping list for a meal plan."""
    try:
        # Get the meal plan
        try:
            meal_plan = MealPlan.objects.get(id=meal_plan_id, user=request.user)
        except MealPlan.DoesNotExist:
            return Response(
                {'error': 'Meal plan not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Get all recipes in the meal plan
        meal_plan_items = meal_plan.items.select_related('recipe').all()
        
        if not meal_plan_items:
            return Response(
                {'error': 'Meal plan has no recipes'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Generate shopping list (mock implementation)
        # In production, this would use AI to combine and optimize ingredients
        shopping_list = {
            'meal_plan_id': str(meal_plan.id),
            'meal_plan_name': meal_plan.name,
            'total_recipes': len(meal_plan_items),
            'categories': {
                'Proteins': [
                    '2 lbs chicken breast',
                    '1 lb ground beef',
                    '12 eggs'
                ],
                'Vegetables': [
                    '2 lbs mixed vegetables',
                    '1 bag spinach',
                    '3 onions',
                    '1 head garlic'
                ],
                'Pantry': [
                    '2 cups rice',
                    '1 bottle olive oil',
                    'Salt and pepper',
                    'Various spices'
                ],
                'Dairy': [
                    '1 gallon milk',
                    '1 lb butter',
                    '1 package cheese'
                ]
            },
            'estimated_cost': '$75-90',
            'serving_info': f'Shopping list for {len(meal_plan_items)} recipes',
            'generated_at': date.today().isoformat()
        }
        
        logger.info(f"Shopping list generated for meal plan {meal_plan_id}")
        
        return Response(shopping_list, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error generating shopping list: {str(e)}", exc_info=True)
        return Response(
            {'error': 'Failed to generate shopping list'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticatedAndActive])
def suggest_recipe_substitutions(request, recipe_id):
    """Suggest ingredient substitutions for a recipe."""
    try:
        # Get the recipe
        try:
            recipe = Recipe.objects.get(id=recipe_id)
        except Recipe.DoesNotExist:
            return Response(
                {'error': 'Recipe not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Mock substitution suggestions
        # In production, this would use AI to suggest ingredient substitutions
        substitutions = {
            'recipe_id': str(recipe.id),
            'recipe_name': recipe.name,
            'suggested_substitutions': [
                {
                    'original_ingredient': 'all-purpose flour',
                    'substitutions': [
                        {'ingredient': 'almond flour', 'ratio': '1:1', 'notes': 'Gluten-free option'},
                        {'ingredient': 'coconut flour', 'ratio': '1:4', 'notes': 'Use 1/4 amount, add extra liquid'},
                        {'ingredient': 'oat flour', 'ratio': '1:1', 'notes': 'Adds slight nutty flavor'}
                    ]
                },
                {
                    'original_ingredient': 'butter',
                    'substitutions': [
                        {'ingredient': 'olive oil', 'ratio': '3:4', 'notes': 'Use 3/4 amount'},
                        {'ingredient': 'coconut oil', 'ratio': '1:1', 'notes': 'Solid at room temperature'},
                        {'ingredient': 'applesauce', 'ratio': '1:2', 'notes': 'For baking, use half amount'}
                    ]
                }
            ],
            'dietary_considerations': [
                'Gluten-free options available',
                'Vegan substitutions included',
                'Lower-fat alternatives provided'
            ]
        }
        
        logger.info(f"Recipe substitutions suggested for recipe {recipe_id}")
        
        return Response(substitutions, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error suggesting recipe substitutions: {str(e)}", exc_info=True)
        return Response(
            {'error': 'Failed to suggest recipe substitutions'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )