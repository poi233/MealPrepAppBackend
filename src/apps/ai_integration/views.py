"""
AI Integration views for MealPrepAI Django backend.
"""
import logging
import uuid
from datetime import date, timedelta
from django.db import transaction
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from common.permissions import IsAuthenticatedAndActive
from apps.recipes.models import Recipe
from apps.recipes.serializers import RecipeSerializer
from apps.meal_plans.models import MealPlan, MealPlanItem
from .services import ai_service, AIService, MealPlanRequest, RecipeGenerationRequest, generate_deterministic_recipe_uuid
from .serializers import (
    GenerateMealPlanSerializer,
    GeneratedMealPlanSerializer,
    GenerateRecipeSerializer,
    GeneratedRecipeSerializer,
    AnalyzeMealPlanSerializer,
    MealPlanAnalysisSerializer,
    CreateRecipeFromAISerializer,
    SuggestRecipeModificationsSerializer,
    RecipeModificationSuggestionsSerializer,
    RecipeCreationResponseSerializer,
    BatchCreateRecipesResponseSerializer,
    StandardAPIResponseSerializer
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
            
            # DEBUG: Log the serialized response
            logger.info(f"AI meal plan generated for user {request.user.id}")
            logger.info(f"[DEBUG] Serialized meal plan response: {meal_plan_serializer.data}")
            
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
    """
    Create a recipe from AI-generated data with enhanced duplicate checking and batch support.
    
    This endpoint supports Scene A: "Save to Template" functionality where users can save
    individual AI-generated recipes to their account with comprehensive duplicate detection.
    
    Key Features:
    - Deterministic UUID generation based on recipe content
    - Advanced duplicate detection using content similarity
    - Comprehensive data validation and sanitization
    - Optional meal plan integration
    - Performance monitoring and logging
    
    Response Format:
    - success: Boolean indicating operation success
    - recipe: Full recipe data if successful
    - status: 'created', 'already_exists', 'updated', or 'failed'
    - message: User-friendly status description
    - recipe_id: UUID of the created/existing recipe
    - timestamp: ISO timestamp of the operation
    """
    permission_classes = [IsAuthenticatedAndActive]
    serializer_class = CreateRecipeFromAISerializer
    
    def _validate_nutrition_info(self, nutrition_info):
        """Validate nutrition info structure and content with enhanced security."""
        from apps.recipes.serializers import NutritionInfoSerializer
        
        if not nutrition_info:
            return True, "No nutrition info provided"
        
        if not isinstance(nutrition_info, dict):
            return False, "Nutrition info must be a dictionary"
        
        # DEBUG: Log the nutrition data being validated
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"🔬 DEBUG: Validating nutrition data: {nutrition_info}")
        
        # Use the enhanced NutritionInfoSerializer for validation
        nutrition_serializer = NutritionInfoSerializer(data=nutrition_info)
        if not nutrition_serializer.is_valid():
            # DEBUG: Log detailed error information
            logger.error(f"🚨 DEBUG: Nutrition validation failed with errors: {nutrition_serializer.errors}")
            logger.error(f"🔍 DEBUG: Input data was: {nutrition_info}")
            
            errors = []
            for field, field_errors in nutrition_serializer.errors.items():
                errors.append(f"{field}: {', '.join(field_errors)}")
            return False, f"Nutrition info validation failed: {'; '.join(errors)}"
        
        logger.info(f"✅ DEBUG: Nutrition validation passed: {nutrition_serializer.validated_data}")
        return True, "Nutrition info validation passed"
    
    def _clean_nutrition_values(self, nutrition_info: dict) -> dict:
        """
        Clean AI-generated nutrition values by converting strings with units to pure numbers.
        
        Args:
            nutrition_info: Nutrition info dictionary that may contain values with units
            
        Returns:
            Cleaned nutrition info dictionary with numeric values
        """
        if not nutrition_info or not isinstance(nutrition_info, dict):
            return nutrition_info
        
        import re
        import logging
        logger = logging.getLogger(__name__)
        
        cleaned = {}
        
        for key, value in nutrition_info.items():
            if value is None:
                cleaned[key] = None
                continue
                
            # If it's already a number, keep it
            if isinstance(value, (int, float)):
                cleaned[key] = float(value)
                continue
            
            # If it's a string, try to extract the number
            if isinstance(value, str):
                # Remove common units and extract the number
                # Examples: "25g" -> 25, "800mg" -> 800, "12.5g" -> 12.5
                number_match = re.search(r'(\d+\.?\d*)', str(value))
                if number_match:
                    try:
                        cleaned_value = float(number_match.group(1))
                        cleaned[key] = cleaned_value
                        logger.info(f"🧹 Cleaned nutrition value: {key} '{value}' -> {cleaned_value}")
                    except ValueError:
                        logger.warning(f"⚠️ Could not convert nutrition value: {key}='{value}', keeping as 0")
                        cleaned[key] = 0.0
                else:
                    logger.warning(f"⚠️ No number found in nutrition value: {key}='{value}', keeping as 0")
                    cleaned[key] = 0.0
            else:
                # For any other type, try to convert to float
                try:
                    cleaned[key] = float(value)
                except (ValueError, TypeError):
                    logger.warning(f"⚠️ Could not convert nutrition value: {key}={value}, keeping as 0")
                    cleaned[key] = 0.0
        
        logger.info(f"🧹 Nutrition cleanup completed: {nutrition_info} -> {cleaned}")
        return cleaned
    
    def _normalize_difficulty(self, difficulty: str) -> str:
        """
        Normalize AI-generated difficulty values to database-accepted English values.
        
        Args:
            difficulty: Difficulty string that may be in Chinese or non-standard format
            
        Returns:
            Normalized difficulty value ('easy', 'medium', or 'hard')
        """
        if not difficulty or not isinstance(difficulty, str):
            return 'medium'  # Default fallback
        
        difficulty_lower = difficulty.lower().strip()
        
        # Chinese to English mapping
        difficulty_mapping = {
            # Chinese values
            '简单': 'easy', '容易': 'easy', '初级': 'easy', '新手': 'easy',
            '中等': 'medium', '普通': 'medium', '中级': 'medium', '适中': 'medium',
            '困难': 'hard', '复杂': 'hard', '高级': 'hard', '专业': 'hard',
            
            # English variations
            'easy': 'easy', 'simple': 'easy', 'basic': 'easy', 'beginner': 'easy',
            'medium': 'medium', 'moderate': 'medium', 'intermediate': 'medium', 'normal': 'medium',
            'hard': 'hard', 'difficult': 'hard', 'complex': 'hard', 'advanced': 'hard', 'expert': 'hard',
            
            # Number-based
            '1': 'easy', '2': 'medium', '3': 'hard'
        }
        
        # Try exact match first
        if difficulty_lower in difficulty_mapping:
            normalized = difficulty_mapping[difficulty_lower]
            logger.info(f"🗺️ Normalized difficulty: '{difficulty}' -> '{normalized}'")
            return normalized
        
        # Try partial matching for Chinese characters
        if '简' in difficulty or '易' in difficulty:
            logger.info(f"🗺️ Normalized difficulty (partial match): '{difficulty}' -> 'easy'")
            return 'easy'
        elif '难' in difficulty or '复' in difficulty:
            logger.info(f"🗺️ Normalized difficulty (partial match): '{difficulty}' -> 'hard'")
            return 'hard'
        elif '中' in difficulty or '普' in difficulty:
            logger.info(f"🗺️ Normalized difficulty (partial match): '{difficulty}' -> 'medium'")
            return 'medium'
        
        # Default fallback
        logger.warning(f"⚠️ Unknown difficulty value: '{difficulty}', defaulting to 'medium'")
        return 'medium'
    
    def _validate_ingredients_structure(self, ingredients_data):
        """Validate ingredients structure with enhanced security checks."""
        if not ingredients_data:
            return False, "At least one ingredient is required"
        
        if not isinstance(ingredients_data, list):
            return False, "Ingredients must be a list"
        
        if len(ingredients_data) > 50:
            return False, "Too many ingredients (max 50)"
        
        for i, ingredient in enumerate(ingredients_data):
            if isinstance(ingredient, str):
                # String ingredients are acceptable
                if len(ingredient.strip()) == 0:
                    return False, f"Ingredient {i} cannot be empty"
            elif isinstance(ingredient, dict):
                # Structured ingredient validation
                if 'name' not in ingredient:
                    return False, f"Ingredient {i}: 'name' field is required"
                
                if not isinstance(ingredient['name'], str) or not ingredient['name'].strip():
                    return False, f"Ingredient {i}: name must be a non-empty string"
                
                # Validate amount if present
                if 'amount' in ingredient:
                    amount = ingredient['amount']
                    if not isinstance(amount, (str, int, float)):
                        return False, f"Ingredient {i}: amount must be a string or number"
                    
                    if isinstance(amount, str) and not amount.strip():
                        return False, f"Ingredient {i}: amount cannot be empty"
                
                # Validate other optional fields
                optional_fields = ['unit', 'notes']
                for field in optional_fields:
                    if field in ingredient and ingredient[field] is not None:
                        if not isinstance(ingredient[field], str):
                            return False, f"Ingredient {i}: {field} must be a string"
                        
                        # Check for excessively long strings
                        max_lengths = {'unit': 50, 'notes': 500}
                        if field in max_lengths and len(ingredient[field]) > max_lengths[field]:
                            return False, f"Ingredient {i}: {field} is too long (max {max_lengths[field]} characters)"
            else:
                return False, f"Ingredient {i}: must be a string or dictionary"
        
        return True, "Ingredients validation passed"
    
    def _validate_recipe_data(self, recipe_data: dict) -> tuple[bool, str]:
        """Enhanced validation for recipe data completeness and integrity.
        
        Args:
            recipe_data: Dictionary containing recipe data
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            # Required fields validation
            required_fields = ['name', 'ingredients', 'instructions']
            for field in required_fields:
                if field not in recipe_data or not recipe_data[field]:
                    return False, f"Missing required field: {field}"
            
            # Name validation
            if not isinstance(recipe_data['name'], str) or len(recipe_data['name'].strip()) < 2:
                return False, "Recipe name must be a non-empty string with at least 2 characters"
            
            # Validate name length and content
            name = recipe_data['name'].strip()
            if len(name) > 255:
                return False, "Recipe name is too long (max 255 characters)"
            
            # Check for potentially malicious content in name
            if any(char in name for char in ['<', '>', '{', '}', '"', "'", ';']):
                return False, "Recipe name contains invalid characters"
            
            # Enhanced ingredients validation
            is_valid, error_msg = self._validate_ingredients_structure(recipe_data['ingredients'])
            if not is_valid:
                return False, error_msg
            
            # Instructions validation (can be list or string)
            instructions = recipe_data['instructions']
            if isinstance(instructions, list):
                if len(instructions) == 0:
                    return False, "Instructions list cannot be empty"
                for i, instruction in enumerate(instructions):
                    if not isinstance(instruction, str) or not instruction.strip():
                        return False, f"Instruction {i} must be a non-empty string"
                    if len(instruction) > 1000:
                        return False, f"Instruction {i} is too long (max 1000 characters)"
            elif isinstance(instructions, str):
                if not instructions.strip():
                    return False, "Instructions string cannot be empty"
                if len(instructions) > 10000:
                    return False, "Instructions are too long (max 10,000 characters)"
            else:
                return False, "Instructions must be a list of strings or a single string"
            
            # Enhanced nutrition info validation
            if 'nutrition_info' in recipe_data and recipe_data['nutrition_info']:
                is_valid, error_msg = self._validate_nutrition_info(recipe_data['nutrition_info'])
                if not is_valid:
                    return False, error_msg
            
            # Numeric fields validation with reasonable ranges
            numeric_fields = ['prep_time', 'cook_time']
            for field in numeric_fields:
                if field in recipe_data and recipe_data[field] is not None:
                    value = recipe_data[field]
                    if not isinstance(value, (int, float)):
                        return False, f"{field} must be a number"
                    if value < 0:
                        return False, f"{field} cannot be negative"
                    if value > 1440:  # Max 24 hours in minutes
                        return False, f"{field} cannot exceed 1440 minutes (24 hours)"
            
            # String fields validation with length limits
            string_field_limits = {
                'description': 2000,
                'cuisine': 100,
                'difficulty': 20,
                'image_url': 500
            }
            
            for field, max_length in string_field_limits.items():
                if field in recipe_data and recipe_data[field] is not None:
                    value = recipe_data[field]
                    if not isinstance(value, str):
                        return False, f"{field} must be a string"
                    if len(value) > max_length:
                        return False, f"{field} is too long (max {max_length} characters)"
            
            # Validate difficulty enum
            if 'difficulty' in recipe_data and recipe_data['difficulty'] is not None:
                valid_difficulties = ['easy', 'medium', 'hard', '简单', '中等', '困难', 'Easy', 'Medium', 'Hard']
                if recipe_data['difficulty'] not in valid_difficulties:
                    return False, f"Invalid difficulty level. Must be one of: {', '.join(valid_difficulties[:3])}"
            
            # Validate tags if present
            if 'tags' in recipe_data and recipe_data['tags'] is not None:
                tags = recipe_data['tags']
                if not isinstance(tags, list):
                    return False, "Tags must be a list"
                if len(tags) > 20:
                    return False, "Too many tags (max 20)"
                for i, tag in enumerate(tags):
                    if not isinstance(tag, str):
                        return False, f"Tag {i} must be a string"
                    if len(tag.strip()) == 0:
                        return False, f"Tag {i} cannot be empty"
                    if len(tag) > 50:
                        return False, f"Tag {i} is too long (max 50 characters)"
            
            return True, "Enhanced validation passed"
            
        except Exception as e:
            logger.error(f"Error validating recipe data: {str(e)}", exc_info=True)
            return False, f"Validation error: {str(e)}"
    
    def _sanitize_recipe_data(self, recipe_data: dict) -> dict:
        """Sanitize and normalize recipe data.
        
        Args:
            recipe_data: Raw recipe data dictionary
            
        Returns:
            Sanitized recipe data dictionary
        """
        try:
            sanitized = recipe_data.copy()
            
            # Sanitize string fields
            string_fields = ['name', 'description', 'cuisine', 'difficulty', 'image_url']
            for field in string_fields:
                if field in sanitized and sanitized[field] is not None:
                    if isinstance(sanitized[field], str):
                        sanitized[field] = sanitized[field].strip()
                    else:
                        sanitized[field] = str(sanitized[field]).strip()
            
            # Ensure numeric fields are integers
            numeric_fields = ['prep_time', 'cook_time']
            for field in numeric_fields:
                if field in sanitized and sanitized[field] is not None:
                    try:
                        sanitized[field] = int(float(sanitized[field]))
                    except (ValueError, TypeError):
                        logger.warning(f"Invalid {field} value: {sanitized[field]}, setting to default")
                        sanitized[field] = 30 if field == 'cook_time' else 15
            
            # Sanitize ingredients
            if 'ingredients' in sanitized and isinstance(sanitized['ingredients'], list):
                sanitized_ingredients = []
                for ingredient in sanitized['ingredients']:
                    if isinstance(ingredient, dict) and 'name' in ingredient and 'amount' in ingredient:
                        sanitized_ingredients.append({
                            'name': str(ingredient['name']).strip(),
                            'amount': str(ingredient['amount']).strip()
                        })
                sanitized['ingredients'] = sanitized_ingredients
            
            # Sanitize and normalize instructions (handle list to TextField conversion)
            if 'instructions' in sanitized:
                instructions_data = sanitized['instructions']
                if isinstance(instructions_data, list):
                    # Convert list to numbered text format for TextField storage
                    steps = [str(step).strip() for step in instructions_data if step]
                    if steps:
                        numbered_steps = [f"{i+1}. {step}" for i, step in enumerate(steps)]
                        sanitized['instructions'] = '\n'.join(numbered_steps)
                    else:
                        sanitized['instructions'] = ''
                elif isinstance(instructions_data, str):
                    sanitized['instructions'] = instructions_data.strip()
                else:
                    sanitized['instructions'] = ''
            
            # Ensure tags is a list
            if 'tags' not in sanitized or not isinstance(sanitized['tags'], list):
                sanitized['tags'] = []
            else:
                sanitized['tags'] = [str(tag).strip() for tag in sanitized['tags'] if str(tag).strip()]
            
            # Set default values for missing optional fields
            defaults = {
                'description': f"美味的{sanitized.get('name', '食谱')}",
                'cuisine': '国际',
                'difficulty': '中等',
                'prep_time': 15,
                'cook_time': 30,
                'image_url': '',
                'nutrition_info': {},
                'tags': []
            }
            
            for field, default_value in defaults.items():
                if field not in sanitized or sanitized[field] is None or sanitized[field] == '':
                    sanitized[field] = default_value
            
            return sanitized
            
        except Exception as e:
            logger.error(f"Error sanitizing recipe data: {str(e)}", exc_info=True)
            return recipe_data  # Return original data if sanitization fails
    
    def _check_content_similarity(self, new_recipe_data: dict, user) -> tuple[bool, Recipe or None]:
        """Check for content similarity with existing recipes.
        
        Args:
            new_recipe_data: New recipe data to check
            user: User creating the recipe
            
        Returns:
            Tuple of (is_duplicate, existing_recipe_or_none)
        """
        try:
            # Generate content-based UUID for the new recipe
            content_uuid = generate_deterministic_recipe_uuid(new_recipe_data)
            
            # Check if a recipe with this content-based UUID already exists
            try:
                existing_recipe = Recipe.objects.get(id=content_uuid)
                logger.info(f"Found existing recipe with content-based ID {content_uuid}: {existing_recipe.name}")
                return True, existing_recipe
            except Recipe.DoesNotExist:
                pass
            
            # Additional similarity check for user-specific recipes
            # Check recipes created by the same user with similar names
            similar_name_recipes = Recipe.objects.filter(
                created_by_user=user,
                name__icontains=new_recipe_data['name'][:20]  # First 20 chars of name
            ).exclude(id=content_uuid)  # Exclude the content-based UUID we just checked
            
            for recipe in similar_name_recipes:
                # Simple similarity check based on ingredient count and name similarity
                if (abs(len(recipe.ingredients) - len(new_recipe_data['ingredients'])) <= 2 and
                    self._calculate_name_similarity(recipe.name, new_recipe_data['name']) > 0.8):
                    logger.info(f"Found similar recipe by name/ingredients: {recipe.name} (ID: {recipe.id})")
                    return True, recipe
            
            return False, None
            
        except Exception as e:
            logger.error(f"Error checking content similarity: {str(e)}", exc_info=True)
            return False, None
    
    def _needs_ai_generation(self, ai_recipe_data: dict) -> bool:
        """
        Check if the recipe data needs AI generation for complete details.
        
        Args:
            ai_recipe_data: Dictionary containing AI recipe data
            
        Returns:
            Boolean indicating if AI generation is needed
        """
        try:
            # Check if essential detailed information is missing or insufficient
            ingredients = ai_recipe_data.get('ingredients', [])
            instructions = ai_recipe_data.get('instructions', [])
            
            # Consider data incomplete if:
            # 1. No ingredients or very few ingredients (< 2)
            # 2. No instructions or very few instructions (< 2)  
            # 3. Ingredients are just placeholder/generic data
            # 4. Instructions are just placeholder/generic data
            
            needs_generation = False
            
            # Check ingredients
            if not ingredients or len(ingredients) < 2:
                needs_generation = True
                logger.info("Recipe needs AI generation: insufficient ingredients")
            elif isinstance(ingredients, list):
                # Check for placeholder ingredients
                placeholder_indicators = ['主要食材', '调料', 'ingredient', 'amount', '适量']
                for ingredient in ingredients:
                    if isinstance(ingredient, dict):
                        ingredient_name = ingredient.get('name', '').lower()
                        if any(placeholder in ingredient_name for placeholder in placeholder_indicators):
                            needs_generation = True
                            logger.info("Recipe needs AI generation: placeholder ingredients detected")
                            break
                    elif isinstance(ingredient, str) and any(placeholder in ingredient.lower() for placeholder in placeholder_indicators):
                        needs_generation = True
                        logger.info("Recipe needs AI generation: placeholder ingredients detected")
                        break
            
            # Check instructions
            if not instructions or len(instructions) < 2:
                needs_generation = True
                logger.info("Recipe needs AI generation: insufficient instructions")
            elif isinstance(instructions, list):
                # Check for placeholder instructions
                placeholder_indicators = ['准备所需食材', '按照传统做法', '调味并完成', 'step', '做法']
                for instruction in instructions:
                    if isinstance(instruction, str) and any(placeholder in instruction.lower() for placeholder in placeholder_indicators):
                        needs_generation = True
                        logger.info("Recipe needs AI generation: placeholder instructions detected")
                        break
            
            return needs_generation
            
        except Exception as e:
            logger.error(f"Error checking if AI generation needed: {str(e)}")
            return True  # Default to generating if there's an error
    
    def _generate_unique_recipe_image(self, recipe_name: str, cuisine: str = None, ingredients: list = None) -> str:
        """
        Generate a unique image URL for each recipe using enhanced search terms.
        
        Args:
            recipe_name: Name of the recipe
            cuisine: Cuisine type (optional)
            ingredients: List of ingredients (optional)
            
        Returns:
            Image URL string
        """
        try:
            # Create more specific search query using recipe characteristics
            search_terms = []
            
            # Add recipe name
            if recipe_name:
                search_terms.append(recipe_name.lower())
            
            # Add cuisine for context
            if cuisine:
                search_terms.append(cuisine.lower())
            
            # Add key ingredients for specificity
            if ingredients and isinstance(ingredients, list):
                # Extract key ingredients (up to 2 most important ones)
                key_ingredients = []
                for ingredient in ingredients[:2]:  # Only use first 2 ingredients
                    if isinstance(ingredient, dict) and 'name' in ingredient:
                        ingredient_name = ingredient['name'].lower()
                        # Filter out generic terms
                        if not any(generic in ingredient_name for generic in ['调料', '适量', 'seasoning', 'salt', 'pepper']):
                            key_ingredients.append(ingredient_name)
                    elif isinstance(ingredient, str):
                        ingredient_name = ingredient.lower()
                        if not any(generic in ingredient_name for generic in ['调料', '适量', 'seasoning', 'salt', 'pepper']):
                            key_ingredients.append(ingredient_name)
                
                search_terms.extend(key_ingredients)
            
            # Create unique search query
            unique_query = ' '.join(search_terms) + ' food dish'
            
            # Try to use Pexels API with unique search terms
            try:
                image_url = ai_service._fetch_pexels_image(
                    recipe_name=recipe_name,
                    cuisine=cuisine, 
                    ai_query=unique_query
                )
                
                # If we got a valid non-fallback image, return it
                if image_url and not image_url.endswith('pexels-photo-1640777.jpeg'):
                    return image_url
            except Exception as e:
                logger.warning(f"Pexels API failed for recipe '{recipe_name}': {str(e)}")
            
            # Generate unique fallback URLs based on recipe characteristics
            # Use different placeholder images for different types of dishes
            recipe_name_lower = recipe_name.lower() if recipe_name else ''
            cuisine_lower = cuisine.lower() if cuisine else ''
            
            # Create hash-based unique image selection
            import hashlib
            unique_string = f"{recipe_name}_{cuisine}_{len(ingredients) if ingredients else 0}"
            hash_value = int(hashlib.md5(unique_string.encode()).hexdigest()[:8], 16)
            
            # Select from different food image URLs based on hash
            food_images = [
                "https://images.pexels.com/photos/1640777/pexels-photo-1640777.jpeg?auto=compress&cs=tinysrgb&w=400&h=300&fit=crop",
                "https://images.pexels.com/photos/376464/pexels-photo-376464.jpeg?auto=compress&cs=tinysrgb&w=400&h=300&fit=crop", 
                "https://images.pexels.com/photos/70497/pexels-photo-70497.jpeg?auto=compress&cs=tinysrgb&w=400&h=300&fit=crop",
                "https://images.pexels.com/photos/461198/pexels-photo-461198.jpeg?auto=compress&cs=tinysrgb&w=400&h=300&fit=crop",
                "https://images.pexels.com/photos/1279330/pexels-photo-1279330.jpeg?auto=compress&cs=tinysrgb&w=400&h=300&fit=crop",
                "https://images.pexels.com/photos/699953/pexels-photo-699953.jpeg?auto=compress&cs=tinysrgb&w=400&h=300&fit=crop",
                "https://images.pexels.com/photos/1352199/pexels-photo-1352199.jpeg?auto=compress&cs=tinysrgb&w=400&h=300&fit=crop",
                "https://images.pexels.com/photos/1099680/pexels-photo-1099680.jpeg?auto=compress&cs=tinysrgb&w=400&h=300&fit=crop"
            ]
            
            # Select image based on hash for consistency but uniqueness
            selected_image = food_images[hash_value % len(food_images)]
            
            logger.info(f"Generated unique fallback image for recipe '{recipe_name}': {selected_image}")
            return selected_image
            
        except Exception as e:
            logger.error(f"Error generating unique recipe image: {str(e)}")
            # Final fallback - return the original fallback image
            return "https://images.pexels.com/photos/1640777/pexels-photo-1640777.jpeg?auto=compress&cs=tinysrgb&w=400&h=300&fit=crop"

    def _calculate_name_similarity(self, name1: str, name2: str) -> float:
        """Calculate simple name similarity score.
        
        Args:
            name1: First name to compare
            name2: Second name to compare
            
        Returns:
            Similarity score between 0 and 1
        """
        try:
            # Simple Jaccard similarity based on character sets
            set1 = set(name1.lower().replace(' ', ''))
            set2 = set(name2.lower().replace(' ', ''))
            
            if not set1 and not set2:
                return 1.0
            if not set1 or not set2:
                return 0.0
            
            intersection = len(set1.intersection(set2))
            union = len(set1.union(set2))
            
            return intersection / union if union > 0 else 0.0
            
        except Exception:
            return 0.0
    
    def _create_recipe_with_predefined_id(self, recipe_data: dict, recipe_id: str, user) -> tuple[Recipe, bool]:
        """Create a recipe with a predefined ID, implementing comprehensive duplicate checking.
        
        Args:
            recipe_data: Dictionary containing recipe data (must be sanitized)
            recipe_id: The predefined UUID string to use as the recipe ID
            user: The user creating the recipe
            
        Returns:
            Tuple of (Recipe instance, was_created)
            
        Raises:
            ValueError: If recipe_id is not a valid UUID format or data is invalid
        """
        try:
            # Validate UUID format
            try:
                uuid_obj = uuid.UUID(recipe_id)
            except ValueError:
                raise ValueError(f"Invalid UUID format: {recipe_id}")
            
            # Check if recipe with this exact ID already exists (direct lookup)
            try:
                existing_recipe = Recipe.objects.get(id=recipe_id)
                logger.info(f"Recipe with ID {recipe_id} already exists: {existing_recipe.name}")
                return existing_recipe, False
            except Recipe.DoesNotExist:
                pass
            
            # Generate deterministic UUID based on content for consistency check
            content_based_uuid = generate_deterministic_recipe_uuid(recipe_data)
            
            # Check if the provided ID matches the content-based ID
            if content_based_uuid != recipe_id:
                logger.warning(
                    f"Provided ID {recipe_id} doesn't match content-based ID {content_based_uuid}. "
                    f"Recipe: {recipe_data.get('name', 'Unknown')}"
                )
                
                # Check if a recipe with the content-based UUID already exists
                try:
                    existing_recipe = Recipe.objects.get(id=content_based_uuid)
                    logger.info(
                        f"Found existing recipe with content-based ID {content_based_uuid}: {existing_recipe.name}"
                    )
                    return existing_recipe, False
                except Recipe.DoesNotExist:
                    pass
            
            # For deterministic behavior, always use the content-based UUID
            final_recipe_id = content_based_uuid
            final_uuid_obj = uuid.UUID(final_recipe_id)
            
            # Final check: if recipe with content-based ID exists, return it
            try:
                existing_recipe = Recipe.objects.get(id=final_recipe_id)
                logger.info(
                    f"Recipe with content-based ID {final_recipe_id} already exists: {existing_recipe.name}"
                )
                return existing_recipe, False
            except Recipe.DoesNotExist:
                pass
            
            # Perform additional similarity check
            is_duplicate, similar_recipe = self._check_content_similarity(recipe_data, user)
            if is_duplicate and similar_recipe:
                logger.info(
                    f"Found similar recipe during similarity check: {similar_recipe.name} (ID: {similar_recipe.id})"
                )
                return similar_recipe, False
            
            # Create new recipe with content-based deterministic ID
            # Remove 'id' from recipe_data to avoid conflict with constructor parameter
            recipe_data_clean = {k: v for k, v in recipe_data.items() if k != 'id'}
            recipe = Recipe(
                id=final_uuid_obj,
                created_by_user=user,
                **recipe_data_clean
            )
            recipe.save()
            
            logger.info(
                f"Created new recipe with deterministic content-based ID: {final_recipe_id}, "
                f"Name: {recipe.name}, User: {user.id}"
            )
            return recipe, True
            
        except Exception as e:
            logger.error(f"Error creating recipe with predefined ID: {str(e)}", exc_info=True)
            raise
    
    @swagger_auto_schema(
        operation_description="Create a single recipe from AI-generated data (Scene A: Save to Template)",
        operation_summary="Save AI Recipe to Template",
        request_body=CreateRecipeFromAISerializer,
        responses={
            201: openapi.Response('Recipe created successfully', RecipeCreationResponseSerializer),
            200: openapi.Response('Recipe already exists', RecipeCreationResponseSerializer),
            400: openapi.Response('Validation failed'),
            500: openapi.Response('Server error')
        },
        tags=['AI Integration - Recipe Creation']
    )
    @transaction.atomic
    def post(self, request):
        """Create a recipe from AI-generated data with enhanced validation and duplicate checking."""
        try:
            # Start timing for performance monitoring
            start_time = timezone.now()
            
            # Validate request data
            serializer = self.get_serializer(data=request.data, context={'request': request})
            
            if not serializer.is_valid():
                logger.warning(
                    f"Recipe creation validation failed for user {request.user.id}: {serializer.errors}"
                )
                return Response(
                    {
                        'success': False,
                        'message': '输入数据验证失败',
                        'errors': serializer.errors,
                        'timestamp': timezone.now().isoformat()
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            validated_data = serializer.validated_data
            ai_recipe_data = validated_data['ai_recipe_data']
            save_to_account = validated_data.get('save_to_account', True)
            
            logger.info(
                f"Processing recipe creation request for user {request.user.id}: "
                f"Recipe='{ai_recipe_data.get('name', 'Unknown')}', Save={save_to_account}"
            )
            
            if not save_to_account:
                # Just return the AI-generated data without saving
                logger.info(f"Returning AI data without saving for user {request.user.id}")
                return Response(
                    ai_recipe_data,
                    status=status.HTTP_200_OK
                )
            
            # Check if we need to generate complete recipe details using AI
            needs_ai_generation = self._needs_ai_generation(ai_recipe_data)
            
            if needs_ai_generation:
                logger.info(f"Recipe data incomplete, generating detailed information using AI for: {ai_recipe_data.get('name', 'Unknown')}")
                
                # Create recipe generation request
                recipe_request = RecipeGenerationRequest(
                    name=ai_recipe_data.get('name', 'Unknown Recipe'),
                    description=ai_recipe_data.get('description', ''),
                    cuisine=ai_recipe_data.get('cuisine', ''),
                    difficulty=ai_recipe_data.get('difficulty', 'medium'),
                    prep_time=ai_recipe_data.get('prep_time'),
                    cook_time=ai_recipe_data.get('cook_time'),
                    meal_type='dinner',  # Default meal type
                    dietary_restrictions=[],
                    ingredients=ai_recipe_data.get('ingredients', []) if isinstance(ai_recipe_data.get('ingredients'), list) and ai_recipe_data.get('ingredients') else [],
                    additional_requirements=f"Generate complete detailed recipe for {ai_recipe_data.get('name', 'this dish')} with authentic ingredients and step-by-step instructions."
                )
                
                # Generate detailed recipe using AI service
                import asyncio
                result = asyncio.run(ai_service.generate_recipe_details(recipe_request, request.user))
                
                if result.get('success') and result.get('recipe'):
                    # Use AI-generated detailed recipe data
                    generated_recipe = result['recipe']
                    logger.info(f"Successfully generated detailed recipe via AI: {generated_recipe.get('name')}")
                    
                    # Extract and enhance recipe data with AI-generated content
                    recipe_data = {
                        'name': generated_recipe.get('name', ai_recipe_data.get('name')),
                        'description': generated_recipe.get('description', ai_recipe_data.get('description', '')),
                        'cuisine': generated_recipe.get('cuisine', ai_recipe_data.get('cuisine', '')),
                        'difficulty': self._normalize_difficulty(generated_recipe.get('difficulty', ai_recipe_data.get('difficulty', 'medium'))),
                        'prep_time': generated_recipe.get('prep_time', ai_recipe_data.get('prep_time', 30)),
                        'cook_time': generated_recipe.get('cook_time', ai_recipe_data.get('cook_time', 30)),
                        'ingredients': generated_recipe.get('ingredients', ai_recipe_data.get('ingredients', [])),
                        'instructions': generated_recipe.get('instructions', ai_recipe_data.get('instructions', [])),
                        'nutrition_info': self._clean_nutrition_values(generated_recipe.get('nutrition_info', ai_recipe_data.get('nutrition_info', {}))),
                        'image_url': generated_recipe.get('image_url', ''),
                        'tags': generated_recipe.get('tags', ai_recipe_data.get('tags', []))
                    }
                else:
                    logger.warning(f"AI recipe generation failed, using original data: {result.get('error', 'Unknown error')}")
                    # Fall back to original data
                    recipe_data = {
                        'name': ai_recipe_data.get('name'),
                        'description': ai_recipe_data.get('description', ''),
                        'cuisine': ai_recipe_data.get('cuisine', ''),
                        'difficulty': self._normalize_difficulty(ai_recipe_data.get('difficulty', 'medium')),
                        'prep_time': ai_recipe_data.get('prep_time', 30),
                        'cook_time': ai_recipe_data.get('cook_time', 30),
                        'ingredients': ai_recipe_data.get('ingredients', []),
                        'instructions': ai_recipe_data.get('instructions', []),
                        'nutrition_info': self._clean_nutrition_values(ai_recipe_data.get('nutrition_info', {})),
                        'image_url': '',
                        'tags': ai_recipe_data.get('tags', [])
                    }
            else:
                # Use the provided complete recipe data
                recipe_data = {
                    'name': ai_recipe_data.get('name'),
                    'description': ai_recipe_data.get('description', ''),
                    'cuisine': ai_recipe_data.get('cuisine', ''),
                    'difficulty': ai_recipe_data.get('difficulty', 'medium'),
                    'prep_time': ai_recipe_data.get('prep_time', 30),
                    'cook_time': ai_recipe_data.get('cook_time', 30),
                    'ingredients': ai_recipe_data.get('ingredients', []),
                    'instructions': ai_recipe_data.get('instructions', []),
                    'nutrition_info': ai_recipe_data.get('nutrition_info', {}),
                    'image_url': ai_recipe_data.get('image_url', ''),
                    'tags': ai_recipe_data.get('tags', [])
                }
            
            # Handle image_url - auto generate from Pexels if empty or missing
            image_url = recipe_data.get('image_url', '').strip()
            if not image_url:
                # Generate unique image for this specific recipe
                image_url = self._generate_unique_recipe_image(
                    recipe_name=recipe_data.get('name', ''),
                    cuisine=recipe_data.get('cuisine', ''),
                    ingredients=recipe_data.get('ingredients', [])
                )
                recipe_data['image_url'] = image_url
                logger.info(f"Auto-generated unique image URL for recipe '{recipe_data.get('name')}': {image_url}")
            
            # Validate recipe data completeness
            is_valid, validation_error = self._validate_recipe_data(recipe_data)
            if not is_valid:
                logger.error(f"Recipe data validation failed for user {request.user.id}: {validation_error}")
                return Response(
                    {
                        'success': False,
                        'message': '食谱数据无效',
                        'errors': {'recipe_data': validation_error},
                        'timestamp': timezone.now().isoformat()
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Sanitize recipe data
            recipe_data = self._sanitize_recipe_data(recipe_data)
            
            # Extract recipe ID from AI data if available
            ai_recipe_id = ai_recipe_data.get('id')
            recipe = None
            was_created = False
            
            try:
                if ai_recipe_id:
                    # Use predefined ID method with enhanced duplicate checking
                    recipe, was_created = self._create_recipe_with_predefined_id(
                        recipe_data, ai_recipe_id, request.user
                    )
                    action_type = "created" if was_created else "found_existing"
                    logger.info(
                        f"Recipe {action_type} with predefined ID {ai_recipe_id} for user {request.user.id}: "
                        f"{recipe.name} (Final ID: {recipe.id})"
                    )
                else:
                    # Check for duplicates before creating
                    is_duplicate, existing_recipe = self._check_content_similarity(recipe_data, request.user)
                    if is_duplicate and existing_recipe:
                        recipe = existing_recipe
                        was_created = False
                        logger.info(
                            f"Found existing similar recipe for user {request.user.id}: "
                            f"{recipe.name} (ID: {recipe.id})"
                        )
                    else:
                        # Create new recipe with content-based deterministic ID
                        content_uuid = generate_deterministic_recipe_uuid(recipe_data)
                        # Remove 'id' from recipe_data to avoid conflict with constructor parameter
                        recipe_data_clean = {k: v for k, v in recipe_data.items() if k != 'id'}
                        recipe = Recipe(
                            id=uuid.UUID(content_uuid),
                            created_by_user=request.user,
                            **recipe_data_clean
                        )
                        recipe.save()
                        was_created = True
                        logger.info(
                            f"Created new recipe with content-based ID {content_uuid} for user {request.user.id}: "
                            f"{recipe.name}"
                        )
                
            except ValueError as e:
                logger.error(f"Recipe creation failed with ValueError for user {request.user.id}: {str(e)}")
                return Response(
                    {
                        'success': False,
                        'message': '食谱创建失败',
                        'errors': {'creation_error': str(e)},
                        'timestamp': timezone.now().isoformat()
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Add to meal plan if requested
            meal_plan_added = False
            if validated_data.get('add_to_meal_plan'):
                try:
                    meal_plan = MealPlan.objects.get(
                        id=validated_data['add_to_meal_plan'],
                        user=request.user
                    )
                    
                    # Check if the recipe is already in the meal plan for this day/meal
                    existing_item = MealPlanItem.objects.filter(
                        meal_plan=meal_plan,
                        recipe=recipe,
                        day_of_week=validated_data['meal_plan_day'],
                        meal_type=validated_data['meal_plan_type']
                    ).first()
                    
                    if not existing_item:
                        MealPlanItem.objects.create(
                            meal_plan=meal_plan,
                            recipe=recipe,
                            day_of_week=validated_data['meal_plan_day'],
                            meal_type=validated_data['meal_plan_type']
                        )
                        meal_plan_added = True
                        logger.info(
                            f"Added recipe {recipe.id} to meal plan {meal_plan.id} for user {request.user.id}"
                        )
                    else:
                        logger.info(
                            f"Recipe {recipe.id} already exists in meal plan {meal_plan.id} for the specified day/meal"
                        )
                        
                except MealPlan.DoesNotExist:
                    logger.error(f"Meal plan {validated_data['add_to_meal_plan']} not found for user {request.user.id}")
                    return Response(
                        {
                            'success': False,
                            'message': '膳食计划未找到',
                            'errors': {'meal_plan_id': 'Meal plan not found or not accessible'},
                            'timestamp': timezone.now().isoformat()
                        },
                        status=status.HTTP_404_NOT_FOUND
                    )
                except Exception as e:
                    logger.error(f"Error adding recipe to meal plan: {str(e)}", exc_info=True)
                    # Don't fail the entire request if meal plan addition fails
                    meal_plan_added = False
            
            # Prepare standardized response data for Scene A: Save to Template
            recipe_data_for_response = {
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
            
            # Determine status message
            if was_created:
                status_msg = "created"
                user_message = f"成功创建新食谱: {recipe.name}"
            else:
                status_msg = "already_exists"
                user_message = f"食谱已存在: {recipe.name}"
            
            if meal_plan_added:
                user_message += " 并已添加到膳食计划"
            
            # Create standardized response using new serializer format
            response_data = {
                'success': True,
                'recipe': recipe_data_for_response,
                'status': status_msg,
                'message': user_message,
                'recipe_id': str(recipe.id),
                'timestamp': timezone.now().isoformat()
            }
            
            # Log success metrics
            end_time = timezone.now()
            processing_time = (end_time - start_time).total_seconds() * 1000
            logger.info(
                f"Recipe creation completed for user {request.user.id}: "
                f"Recipe={recipe.name} (ID: {recipe.id}), "
                f"Created={was_created}, MealPlanAdded={meal_plan_added}, "
                f"ProcessingTime={processing_time:.2f}ms"
            )
            
            return Response(
                response_data,
                status=status.HTTP_201_CREATED if was_created else status.HTTP_200_OK
            )
            
        except Exception as e:
            user_id = getattr(request.user, 'id', 'unknown') if hasattr(request, 'user') else 'unknown'
            logger.error(f"Unexpected error in recipe creation for user {user_id}: {str(e)}", exc_info=True)
            return Response(
                {
                    'success': False,
                    'message': '服务器内部错误',
                    'errors': {'server_error': 'Internal server error during recipe creation'},
                    'timestamp': timezone.now().isoformat()
                },
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


@swagger_auto_schema(
    method='post',
    operation_description="""
    Create multiple recipes from AI-generated data in batch (Scene B: Apply Meal Plan).
    
    This endpoint supports efficient batch processing of up to 20 recipes at once,
    with individual transaction control and detailed status reporting.
    
    Key Features:
    - Batch processing with individual transaction rollback capability
    - Comprehensive duplicate detection across the batch
    - Optional meal plan integration for all recipes
    - Detailed per-recipe status reporting
    - Performance optimization for large batches
    - Partial success handling (some recipes can fail without affecting others)
    
    Performance Targets:
    - Processing time: < 2 seconds for typical batches
    - Memory efficient processing with individual transactions
    - Graceful degradation under high load
    
    Response Format:
    - success: Boolean indicating overall batch success
    - total_processed: Total number of recipes in the batch
    - successful: Number of successfully processed recipes
    - failed: Number of failed recipe creations
    - already_exists: Number of recipes that already existed
    - summary: Detailed processing statistics and metadata
    - results: Array of per-recipe processing results
    - timestamp: ISO timestamp of batch completion
    - processing_time: Actual processing time in seconds
    """,
    operation_summary="Batch Create AI Recipes (Apply Meal Plan)",
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            'recipes': openapi.Schema(
                type=openapi.TYPE_ARRAY,
                items=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'ai_recipe_data': openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            description='AI-generated recipe data'
                        ),
                        'meal_plan_day': openapi.Schema(
                            type=openapi.TYPE_INTEGER,
                            minimum=0,
                            maximum=6,
                            description='Day of week (0=Monday, 6=Sunday)'
                        ),
                        'meal_plan_type': openapi.Schema(
                            type=openapi.TYPE_STRING,
                            enum=['breakfast', 'lunch', 'dinner', 'snack']
                        )
                    }
                ),
                min_items=1,
                max_items=20
            ),
            'meal_plan_id': openapi.Schema(
                type=openapi.TYPE_STRING,
                format=openapi.FORMAT_UUID,
                description='Optional meal plan ID to add all recipes to'
            ),
            'save_to_account': openapi.Schema(
                type=openapi.TYPE_BOOLEAN,
                default=True,
                description='Whether to save all recipes to user account'
            ),
            'skip_duplicates': openapi.Schema(
                type=openapi.TYPE_BOOLEAN,
                default=True,
                description='Whether to skip recipes that already exist'
            )
        },
        required=['recipes']
    ),
    responses={
        200: openapi.Response('Batch processing completed', BatchCreateRecipesResponseSerializer),
        400: openapi.Response('Validation failed or invalid request format'),
        404: openapi.Response('Meal plan not found'),
        500: openapi.Response('Server error during batch processing')
    },
    tags=['AI Integration - Batch Operations']
)
@api_view(['POST'])
@permission_classes([IsAuthenticatedAndActive])
def batch_create_recipes_from_ai(request):
    """
    Create multiple recipes from AI-generated data in batch for optimal performance.
    
    Scene B: "Apply Meal Plan" - Efficiently processes entire meal plans with
    up to 20 recipes while maintaining data integrity and providing detailed feedback.
    """
    try:
        start_time = timezone.now()
        
        # Validate request data structure
        if not isinstance(request.data, dict) or 'recipes' not in request.data:
            return Response(
                {
                    'success': False,
                    'total_processed': 0,
                    'successful': 0,
                    'failed': 0,
                    'already_exists': 0,
                    'summary': {'error': 'Invalid request format'},
                    'results': [],
                    'timestamp': timezone.now().isoformat(),
                    'processing_time': 0.0
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        recipes_data = request.data['recipes']
        if not isinstance(recipes_data, list) or len(recipes_data) == 0:
            return Response(
                {
                    'success': False,
                    'total_processed': 0,
                    'successful': 0,
                    'failed': 0,
                    'already_exists': 0,
                    'summary': {'error': 'Recipes must be a non-empty array'},
                    'results': [],
                    'timestamp': timezone.now().isoformat(),
                    'processing_time': 0.0
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Performance optimization: Limit batch size and add processing hints
        max_batch_size = 20
        if len(recipes_data) > max_batch_size:
            return Response(
                {
                    'success': False,
                    'total_processed': 0,
                    'successful': 0,
                    'failed': 0,
                    'already_exists': 0,
                    'summary': {
                        'error': f'Maximum {max_batch_size} recipes per batch for optimal performance',
                        'recommendation': 'Split large batches into smaller chunks for better reliability'
                    },
                    'results': [],
                    'timestamp': timezone.now().isoformat(),
                    'processing_time': 0.0
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        logger.info(f"Starting batch recipe creation for user {request.user.id}: {len(recipes_data)} recipes")
        
        # Get optional meal plan info for bulk assignment
        meal_plan_id = request.data.get('meal_plan_id')
        meal_plan = None
        if meal_plan_id:
            try:
                meal_plan = MealPlan.objects.get(id=meal_plan_id, user=request.user)
            except MealPlan.DoesNotExist:
                return Response(
                    {
                        'success': False,
                        'total_processed': 0,
                        'successful': 0,
                        'failed': 0,
                        'already_exists': 0,
                        'summary': {'error': 'Meal plan not found'},
                        'results': [],
                        'timestamp': timezone.now().isoformat(),
                        'processing_time': 0.0
                    },
                    status=status.HTTP_404_NOT_FOUND
                )
        
        # Process each recipe
        results = []
        created_count = 0
        existing_count = 0
        error_count = 0
        
        # Performance optimization: Pre-initialize recipe view and prepare bulk operations
        recipe_view = CreateRecipeFromAIView()
        
        # Performance monitoring: Track processing speed
        recipes_per_second_target = 10  # Target processing speed
        estimated_time = len(recipes_data) / recipes_per_second_target
        logger.info(f"Starting batch processing: {len(recipes_data)} recipes, estimated time: {estimated_time:.1f}s")
        
        # Process recipes with granular transaction control to avoid long locks
        # Each recipe gets its own transaction for individual rollback capability
        for i, recipe_item in enumerate(recipes_data):
            try:
                # Validate recipe item structure first
                if not isinstance(recipe_item, dict) or 'ai_recipe_data' not in recipe_item:
                    results.append({
                        'index': i,
                        'success': False,
                        'error': 'Invalid recipe format - missing ai_recipe_data',
                        'recipe_name': recipe_item.get('name', f'Recipe {i}')
                    })
                    error_count += 1
                    continue
                
                # Process within individual transaction
                with transaction.atomic():
                    
                    ai_recipe_data = recipe_item['ai_recipe_data']
                    recipe_name = ai_recipe_data.get('name', f'Recipe {i}')
                    
                    # Extract recipe data and validate
                    recipe_data = {
                        'name': ai_recipe_data.get('name'),
                        'description': ai_recipe_data.get('description'),
                        'cuisine': ai_recipe_data.get('cuisine'),
                        'difficulty': ai_recipe_data.get('difficulty'),
                        'prep_time': ai_recipe_data.get('prep_time'),
                        'cook_time': ai_recipe_data.get('cook_time'),
                        'ingredients': ai_recipe_data.get('ingredients'),
                        'instructions': ai_recipe_data.get('instructions'),
                        'nutrition_info': self._clean_nutrition_values(ai_recipe_data.get('nutrition_info', {})),
                        'image_url': ai_recipe_data.get('image_url', ''),
                        'tags': ai_recipe_data.get('tags', [])
                    }
                    
                    # Validate recipe data
                    is_valid, validation_error = recipe_view._validate_recipe_data(recipe_data)
                    if not is_valid:
                        # Don't need transaction rollback as we'll exit the transaction context
                        raise ValueError(f'Validation failed: {validation_error}')
                    
                    # Sanitize recipe data
                    recipe_data = recipe_view._sanitize_recipe_data(recipe_data)
                    
                    # Create or find recipe
                    ai_recipe_id = ai_recipe_data.get('id')
                    recipe = None
                    was_created = False
                    
                    if ai_recipe_id:
                        recipe, was_created = recipe_view._create_recipe_with_predefined_id(
                            recipe_data, ai_recipe_id, request.user
                        )
                    else:
                        # Check for duplicates
                        is_duplicate, existing_recipe = recipe_view._check_content_similarity(recipe_data, request.user)
                        if is_duplicate and existing_recipe:
                            recipe = existing_recipe
                            was_created = False
                        else:
                            # Create new recipe
                            content_uuid = generate_deterministic_recipe_uuid(recipe_data)
                            # Remove 'id' from recipe_data to avoid conflict with constructor parameter
                            recipe_data_clean = {k: v for k, v in recipe_data.items() if k != 'id'}
                            recipe = Recipe(
                                id=uuid.UUID(content_uuid),
                                created_by_user=request.user,
                                **recipe_data_clean
                            )
                            recipe.save()
                            was_created = True
                    
                    # Add to meal plan if specified
                    meal_plan_added = False
                    if meal_plan and 'meal_plan_day' in recipe_item and 'meal_plan_type' in recipe_item:
                        try:
                            existing_item = MealPlanItem.objects.filter(
                                meal_plan=meal_plan,
                                recipe=recipe,
                                day_of_week=recipe_item['meal_plan_day'],
                                meal_type=recipe_item['meal_plan_type']
                            ).first()
                            
                            if not existing_item:
                                MealPlanItem.objects.create(
                                    meal_plan=meal_plan,
                                    recipe=recipe,
                                    day_of_week=recipe_item['meal_plan_day'],
                                    meal_type=recipe_item['meal_plan_type']
                                )
                                meal_plan_added = True
                        except Exception as e:
                            logger.warning(f"Failed to add recipe {recipe.id} to meal plan: {str(e)}")
                    
                    # Record success
                    results.append({
                        'index': i,
                        'success': True,
                        'recipe_id': str(recipe.id),
                        'recipe_name': recipe.name,
                        'was_created': was_created,
                        'meal_plan_added': meal_plan_added
                    })
                    
                    if was_created:
                        created_count += 1
                    else:
                        existing_count += 1
                        
            except Exception as e:
                logger.error(f"Error processing recipe {i} in batch: {str(e)}", exc_info=True)
                results.append({
                    'index': i,
                    'success': False,
                    'error': str(e),
                    'recipe_name': recipe_item.get('ai_recipe_data', {}).get('name', f'Recipe {i}')
                })
                error_count += 1
        
        # Prepare enhanced summary response for Scene B: Apply Meal Plan
        end_time = timezone.now()
        processing_time = (end_time - start_time).total_seconds()
        
        # Convert results to new standardized format
        formatted_results = []
        for result in results:
            if result['success']:
                formatted_results.append({
                    'recipe_id': result['recipe_id'],
                    'name': result['recipe_name'],
                    'status': 'created' if result['was_created'] else 'already_exists',
                    'error': None,
                    'meal_plan_added': result.get('meal_plan_added', False)
                })
            else:
                formatted_results.append({
                    'recipe_id': None,
                    'name': result['recipe_name'],
                    'status': 'failed',
                    'error': result['error'],
                    'meal_plan_added': False
                })
        
        # Create standardized response using BatchCreateRecipesResponseSerializer format
        response_data = {
            'success': True,
            'total_processed': len(recipes_data),
            'successful': created_count + existing_count,
            'failed': error_count,
            'already_exists': existing_count,
            'summary': {
                'total_recipes': len(recipes_data),
                'new_recipes_created': created_count,
                'existing_recipes_found': existing_count,
                'failed_recipes': error_count,
                'meal_plan_id': str(meal_plan.id) if meal_plan else None,
                'meal_plan_name': meal_plan.name if meal_plan else None,
                'processing_time_seconds': round(processing_time, 2)
            },
            'results': formatted_results,
            'timestamp': timezone.now().isoformat(),
            'processing_time': processing_time
        }
        
        logger.info(
            f"Batch recipe creation completed for user {request.user.id}: "
            f"Total={len(recipes_data)}, Created={created_count}, Existing={existing_count}, "
            f"Errors={error_count}, Time={processing_time:.2f}ms"
        )
        
        return Response(response_data, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Unexpected error in batch recipe creation: {str(e)}", exc_info=True)
        return Response(
            {
                'success': False,
                'total_processed': 0,
                'successful': 0,
                'failed': 0,
                'already_exists': 0,
                'summary': {'error': 'Internal server error during batch processing'},
                'results': [],
                'timestamp': timezone.now().isoformat(),
                'processing_time': 0.0
            },
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


class GenerateRecipeDetailsOnDemandView(generics.CreateAPIView):
    """Generate detailed recipe information on-demand for fast meal plan generation."""
    permission_classes = [IsAuthenticatedAndActive]
    
    @swagger_auto_schema(
        operation_description="""
        Generate detailed recipe information on-demand for recipes created during fast meal plan generation.
        
        This endpoint supports the two-phase meal plan generation approach:
        1. Phase 1: Fast meal plan generation with basic recipe info (< 10s for Vercel)
        2. Phase 2: On-demand detailed recipe generation when users need full recipe details
        
        Use Cases:
        - User clicks on a basic recipe in their meal plan to see full details
        - Batch enhancement of multiple basic recipes in a meal plan
        - Progressive loading of recipe details in mobile apps
        
        Performance:
        - Optimized for single recipe detail generation
        - Supports batch requests for up to 10 recipes
        - Implements smart caching to avoid duplicate AI calls
        """,
        operation_summary="Generate Recipe Details On-Demand",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'recipe_id': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    format=openapi.FORMAT_UUID,
                    description='ID of the basic recipe to enhance with details'
                ),
                'recipe_name': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='Name of the recipe (for AI generation if recipe not found in DB)'
                ),
                'meal_type': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    enum=['breakfast', 'lunch', 'dinner', 'snack'],
                    description='Meal type for context-aware generation'
                ),
                'dietary_preferences': openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    description='User dietary preferences for customization'
                ),
                'detail_level': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    enum=['basic', 'full'],
                    default='full',
                    description='Level of detail to generate'
                )
            },
            required=['recipe_name']
        ),
        responses={
            200: openapi.Response('Recipe details generated successfully', GeneratedRecipeSerializer),
            400: openapi.Response('Validation failed'),
            404: openapi.Response('Recipe not found'),
            500: openapi.Response('Server error')
        },
        tags=['AI Integration - On-Demand Generation']
    )
    def post(self, request):
        """Generate detailed recipe information on-demand."""
        try:
            # Validate request data
            recipe_id = request.data.get('recipe_id')
            recipe_name = request.data.get('recipe_name')
            meal_type = request.data.get('meal_type', 'dinner')
            dietary_preferences = request.data.get('dietary_preferences', {})
            detail_level = request.data.get('detail_level', 'full')
            
            if not recipe_name:
                return Response(
                    {'error': 'Recipe name is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            logger.info(f"On-demand recipe generation request for user {request.user.id}: {recipe_name}")
            
            # Check if we have a basic recipe in the database first
            existing_recipe = None
            if recipe_id:
                try:
                    existing_recipe = Recipe.objects.get(id=recipe_id)
                    logger.info(f"Found existing recipe {recipe_id}: {existing_recipe.name}")
                    
                    # If the existing recipe already has detailed information, return it
                    if (existing_recipe.instructions and 
                        len(existing_recipe.instructions) > 50 and 
                        existing_recipe.ingredients and 
                        len(existing_recipe.ingredients) > 0):
                        
                        logger.info(f"Recipe {recipe_id} already has detailed information, returning existing data")
                        
                        # Convert existing recipe to response format
                        recipe_data = {
                            'id': str(existing_recipe.id),
                            'name': existing_recipe.name,
                            'description': existing_recipe.description,
                            'cuisine': existing_recipe.cuisine,
                            'difficulty': existing_recipe.difficulty,
                            'prep_time': existing_recipe.prep_time,
                            'cook_time': existing_recipe.cook_time,
                            'image_url': existing_recipe.image_url,
                            'ingredients': existing_recipe.ingredients,
                            'instructions': existing_recipe.instructions.split('\n') if existing_recipe.instructions else [],
                            'nutrition_info': existing_recipe.nutrition_info or {},
                            'tags': existing_recipe.tags or []
                        }
                        
                        return Response(recipe_data, status=status.HTTP_200_OK)
                        
                except Recipe.DoesNotExist:
                    logger.info(f"Recipe {recipe_id} not found in database, will generate from scratch")
                    pass
            
            # Generate detailed recipe using AI service
            recipe_request = RecipeGenerationRequest(
                name=recipe_name,
                description=f"Detailed recipe for {recipe_name}",
                meal_type=meal_type,
                dietary_restrictions=dietary_preferences.get('dietary_restrictions', []),
                additional_requirements=f"Generate a complete, detailed recipe with full ingredient list and step-by-step instructions. Detail level: {detail_level}"
            )
            
            # Generate recipe using AI service with asyncio
            import asyncio
            result = asyncio.run(ai_service.generate_recipe_details(recipe_request, request.user))
            
            if not result['success']:
                logger.error(f"AI recipe generation failed: {result['error']}")
                return Response(
                    {'error': result['error']},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            
            # Update existing recipe if we have one, otherwise return the generated data
            generated_recipe = result['recipe']
            
            if existing_recipe and recipe_id:
                try:
                    # Update the existing basic recipe with detailed information
                    existing_recipe.description = generated_recipe.get('description', existing_recipe.description)
                    existing_recipe.ingredients = generated_recipe.get('ingredients', existing_recipe.ingredients)
                    existing_recipe.instructions = '\n'.join(generated_recipe.get('instructions', [])) if generated_recipe.get('instructions') else existing_recipe.instructions
                    existing_recipe.nutrition_info = self._clean_nutrition_values(generated_recipe.get('nutrition_info', existing_recipe.nutrition_info))
                    existing_recipe.prep_time = generated_recipe.get('prep_time', existing_recipe.prep_time)
                    existing_recipe.cook_time = generated_recipe.get('cook_time', existing_recipe.cook_time)
                    existing_recipe.difficulty = self._normalize_difficulty(generated_recipe.get('difficulty', existing_recipe.difficulty))
                    existing_recipe.cuisine = generated_recipe.get('cuisine', existing_recipe.cuisine)
                    existing_recipe.tags = generated_recipe.get('tags', existing_recipe.tags)
                    existing_recipe.save()
                    
                    logger.info(f"Updated existing recipe {recipe_id} with detailed information")
                    
                    # Return updated recipe data
                    recipe_data = {
                        'id': str(existing_recipe.id),
                        'name': existing_recipe.name,
                        'description': existing_recipe.description,
                        'cuisine': existing_recipe.cuisine,
                        'difficulty': existing_recipe.difficulty,
                        'prep_time': existing_recipe.prep_time,
                        'cook_time': existing_recipe.cook_time,
                        'image_url': existing_recipe.image_url,
                        'ingredients': existing_recipe.ingredients,
                        'instructions': existing_recipe.instructions.split('\n') if existing_recipe.instructions else [],
                        'nutrition_info': existing_recipe.nutrition_info or {},
                        'tags': existing_recipe.tags or []
                    }
                    
                    return Response(recipe_data, status=status.HTTP_200_OK)
                    
                except Exception as e:
                    logger.error(f"Error updating existing recipe {recipe_id}: {str(e)}")
                    # Fall through to return generated data without saving
            
            # Serialize and return the generated recipe data
            recipe_serializer = GeneratedRecipeSerializer(generated_recipe)
            
            logger.info(f"On-demand recipe details generated for user {request.user.id}: {recipe_name}")
            
            return Response(
                recipe_serializer.data,
                status=status.HTTP_200_OK
            )
            
        except Exception as e:
            logger.error(f"Error generating recipe details on-demand: {str(e)}", exc_info=True)
            return Response(
                {'error': 'Failed to generate recipe details'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


@swagger_auto_schema(
    method='post',
    operation_description="""
    Apply a RecipeStub to user's meal plan by converting it to a complete Recipe.
    
    This is the second phase of the lightweight meal plan system:
    1. Takes a RecipeStub from the lightweight meal plan generation
    2. Converts it to a complete Recipe with full details using AI
    3. Optionally saves the recipe to user's account
    4. Optionally adds the recipe to a specific meal plan
    
    Key Features:
    - Converts lightweight RecipeStub to complete Recipe
    - AI-powered recipe detail generation
    - Optional meal plan integration
    - Automatic recipe deduplication
    - Serving size adjustment support
    """,
    operation_summary="Apply Recipe Stub to Meal Plan",
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=['recipe_stub', 'day_of_week', 'meal_type'],
        properties={
            'recipe_stub': openapi.Schema(
                type=openapi.TYPE_OBJECT,
                description="RecipeStub object from lightweight meal plan",
                properties={
                    'id': openapi.Schema(type=openapi.TYPE_STRING, allow_null=True, description="Recipe ID if exists"),
                    'name': openapi.Schema(type=openapi.TYPE_STRING, description="Recipe name"),
                    'cuisine': openapi.Schema(type=openapi.TYPE_STRING, allow_null=True, description="Cuisine type"),
                    'description': openapi.Schema(type=openapi.TYPE_STRING, allow_null=True, description="Short description"),
                    'estimated_calories': openapi.Schema(type=openapi.TYPE_INTEGER, allow_null=True, description="Estimated calories"),
                    'estimated_prep_time': openapi.Schema(type=openapi.TYPE_INTEGER, allow_null=True, description="Estimated prep time"),
                    'image_url': openapi.Schema(type=openapi.TYPE_STRING, allow_null=True, description="Image URL"),
                    'tags': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Schema(type=openapi.TYPE_STRING), description="Recipe tags")
                }
            ),
            'meal_plan_id': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_UUID, description="Target meal plan ID (optional)"),
            'day_of_week': openapi.Schema(type=openapi.TYPE_INTEGER, minimum=0, maximum=6, description="Day of week (0=Monday, 6=Sunday)"),
            'meal_type': openapi.Schema(type=openapi.TYPE_STRING, enum=['breakfast', 'lunch', 'dinner', 'snack'], description="Meal type"),
            'serving_size': openapi.Schema(type=openapi.TYPE_NUMBER, format=openapi.FORMAT_FLOAT, default=1.0, description="Serving size multiplier"),
            'save_to_account': openapi.Schema(type=openapi.TYPE_BOOLEAN, default=True, description="Save recipe to user account")
        }
    ),
    responses={
        200: openapi.Response(
            'Recipe successfully applied',
            openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'success': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                    'recipe': openapi.Schema(type=openapi.TYPE_OBJECT, description="Complete recipe data"),
                    'meal_plan_item': openapi.Schema(type=openapi.TYPE_OBJECT, description="Created meal plan item (if added)"),
                    'message': openapi.Schema(type=openapi.TYPE_STRING, description="Success message")
                }
            )
        ),
        400: openapi.Response('Invalid request data'),
        401: openapi.Response('Authentication required'),
        404: openapi.Response('Meal plan not found'),
        500: openapi.Response('Server error during recipe application')
    },
    tags=['AI Integration - Apply Meal']
)
@api_view(['POST'])
@permission_classes([IsAuthenticatedAndActive])
def apply_meal_to_plan(request):
    """
    Apply a RecipeStub to user's meal plan by converting it to a complete Recipe.
    
    This endpoint handles the second phase of the lightweight meal plan system.
    """
    try:
        # Import serializers here to avoid circular imports
        from .serializers import ApplyMealRequestSerializer, ApplyMealResponseSerializer
        
        # Validate request data
        serializer = ApplyMealRequestSerializer(data=request.data, context={'request': request})
        
        if not serializer.is_valid():
            return Response(
                {
                    'success': False,
                    'errors': serializer.errors
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        validated_data = serializer.validated_data
        
        # Extract parameters
        recipe_stub = validated_data['recipe_stub']
        meal_plan_id = validated_data.get('meal_plan_id')
        day_of_week = validated_data['day_of_week']
        meal_type = validated_data['meal_type']
        serving_size = validated_data.get('serving_size', 1.0)
        save_to_account = validated_data.get('save_to_account', True)
        
        # Log the operation
        logger.info(f"Applying meal to plan for user {request.user.id}: {recipe_stub.get('name', 'Unknown')}")
        
        # Call the AI service to apply the meal
        result = ai_service.apply_meal_to_plan(
            recipe_stub=recipe_stub,
            user=request.user,
            meal_plan_id=str(meal_plan_id) if meal_plan_id else None,
            day_of_week=day_of_week,
            meal_type=meal_type,
            serving_size=serving_size,
            save_to_account=save_to_account
        )
        
        # Since ai_service.apply_meal_to_plan is async, we need to await it
        import asyncio
        if asyncio.iscoroutine(result):
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(result)
            finally:
                loop.close()
        
        if result.get('success'):
            logger.info(f"Successfully applied meal for user {request.user.id}")
            
            # Serialize the response
            response_serializer = ApplyMealResponseSerializer(result)
            
            return Response(
                response_serializer.data,
                status=status.HTTP_200_OK
            )
        else:
            logger.error(f"Failed to apply meal for user {request.user.id}: {result.get('error', 'Unknown error')}")
            return Response(
                result,
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
            
    except Exception as e:
        logger.error(f"Error in apply_meal_to_plan view: {str(e)}", exc_info=True)
        return Response(
            {
                'success': False,
                'error': 'Failed to apply meal to plan'
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )