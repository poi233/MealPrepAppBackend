"""
AI Integration services for MealPrepAI Django backend.
"""
import logging
import json
import asyncio
import requests
import uuid
import hashlib
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, date
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
import time
import re
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)

# UUID namespace for deterministic recipe IDs
RECIPE_UUID_NAMESPACE = uuid.UUID('6ba7b810-9dad-11d1-80b4-00c04fd430c8')


@dataclass
class MealPlanRequest:
    """Data class for meal plan generation requests."""
    plan_description: str
    dietary_preferences: Optional[Dict[str, Any]] = None
    allergies: Optional[List[str]] = None
    dislikes: Optional[List[str]] = None
    calorie_target: Optional[int] = None
    week_start_date: Optional[date] = None
    additional_requirements: Optional[str] = None


@dataclass
class RecipeGenerationRequest:
    """Data class for recipe generation requests."""
    name: str
    description: Optional[str] = None
    cuisine: Optional[str] = None
    difficulty: str = 'medium'
    prep_time: Optional[int] = None
    cook_time: Optional[int] = None
    meal_type: Optional[str] = None
    dietary_restrictions: Optional[List[str]] = None
    ingredients: Optional[List[str]] = None
    additional_requirements: Optional[str] = None


def generate_deterministic_recipe_uuid(recipe_data: Dict[str, Any]) -> str:
    """
    Generate a deterministic UUID based on recipe content.
    
    This ensures that identical recipes always get the same ID,
    enabling proper deduplication and frontend predictability.
    
    Args:
        recipe_data: Dictionary containing recipe information
        
    Returns:
        Deterministic UUID string
    """
    # Normalize and standardize recipe data for consistent hashing
    normalized_data = _normalize_recipe_data_for_uuid(recipe_data)
    
    # Create content hash
    content_string = json.dumps(normalized_data, sort_keys=True, ensure_ascii=False)
    content_hash = hashlib.sha256(content_string.encode('utf-8')).hexdigest()
    
    # Generate deterministic UUID using namespace and content hash
    deterministic_uuid = uuid.uuid5(RECIPE_UUID_NAMESPACE, content_hash)
    
    logger.debug(f"Generated deterministic UUID {deterministic_uuid} for recipe: {recipe_data.get('name', 'Unknown')}")
    return str(deterministic_uuid)


def _normalize_recipe_data_for_uuid(recipe_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize recipe data for consistent UUID generation.
    
    This function standardizes the recipe data to ensure that minor
    variations (like whitespace, capitalization) don't create different UUIDs.
    
    Args:
        recipe_data: Raw recipe data dictionary
        
    Returns:
        Normalized dictionary for UUID generation
    """
    def normalize_string(s: str) -> str:
        """Normalize a string by removing extra whitespace and converting to lowercase."""
        if not isinstance(s, str):
            return str(s)
        return ' '.join(s.strip().lower().split())
    
    def normalize_ingredients(ingredients: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """Normalize and sort ingredients list."""
        if not isinstance(ingredients, list):
            return []
        
        normalized_ingredients = []
        for ing in ingredients:
            if isinstance(ing, dict) and 'name' in ing and 'amount' in ing:
                normalized_ingredients.append({
                    'name': normalize_string(ing['name']),
                    'amount': normalize_string(ing['amount'])
                })
        
        # Sort ingredients by name for consistency
        return sorted(normalized_ingredients, key=lambda x: x['name'])
    
    def normalize_instructions(instructions: List[str]) -> List[str]:
        """Normalize instructions list."""
        if not isinstance(instructions, list):
            return []
        
        normalized_instructions = []
        for inst in instructions:
            if isinstance(inst, str) and inst.strip():
                normalized_instructions.append(normalize_string(inst))
        
        return normalized_instructions
    
    # Extract and normalize key fields that define recipe uniqueness
    normalized = {
        'name': normalize_string(recipe_data.get('name', '')),
        'ingredients': normalize_ingredients(recipe_data.get('ingredients', [])),
        'cuisine': normalize_string(recipe_data.get('cuisine', '')),
        'difficulty': normalize_string(recipe_data.get('difficulty', '')),
        # Instructions are included but with less weight since they might vary more
        'instructions_key': '|'.join(normalize_instructions(recipe_data.get('instructions', []))),
    }
    
    # Only include non-empty values to avoid UUID changes due to missing vs empty fields
    return {k: v for k, v in normalized.items() if v}


class AIService:
    """Service class for AI integrations using Google Gemini."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._initialize_gemini()
        self._rate_limit_cache_key = "ai_service_rate_limit"
        self._max_requests_per_minute = 60  # Adjust based on your API limits
        
        # Concurrency control settings
        self._max_concurrent_recipes = 5  # Maximum concurrent recipe generations
        self._recipe_generation_semaphore = asyncio.Semaphore(self._max_concurrent_recipes)
        
        # Content validation settings
        self._max_text_length = 2000  # Maximum length for text fields
        self._max_ingredient_name_length = 100
        self._max_instruction_length = 500
        self._max_ingredients_count = 50
        self._max_instructions_count = 20
    
    def _initialize_gemini(self):
        """Initialize Google Gemini AI client."""
        try:
            genai.configure(api_key=settings.GOOGLE_API_KEY)
            
            # Configure safety settings to be less restrictive for food content
            self.safety_settings = {
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            }
            
            # Initialize the model
            self.model = genai.GenerativeModel(
                model_name=settings.GENAI_MODEL,
                safety_settings=self.safety_settings
            )
            
            self.logger.info("Google Gemini AI client initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Google Gemini AI client: {str(e)}")
            raise
    
    def _check_rate_limit(self) -> bool:
        """Check if we're within rate limits."""
        current_minute = int(time.time() // 60)
        cache_key = f"{self._rate_limit_cache_key}_{current_minute}"
        
        current_count = cache.get(cache_key, 0)
        if current_count >= self._max_requests_per_minute:
            return False
        
        cache.set(cache_key, current_count + 1, 60)  # Expire after 1 minute
        return True
    
    def _validate_ai_content(self, content: Dict[str, Any]) -> Tuple[bool, str]:
        """Validate AI-generated content for security and length constraints."""
        try:
            # Validate recipe name (optional since it comes from request)
            name = content.get('name', '')
            if name and not isinstance(name, str):
                return False, "Recipe name must be a string"
            if name and len(name) > self._max_text_length:
                return False, f"Recipe name too long (max {self._max_text_length} chars)"
            
            # Validate description
            description = content.get('description', '')
            if description and len(description) > self._max_text_length:
                return False, f"Description too long (max {self._max_text_length} chars)"
            
            # Validate ingredients
            ingredients = content.get('ingredients', [])
            if not isinstance(ingredients, list):
                return False, "Ingredients must be a list"
            if len(ingredients) > self._max_ingredients_count:
                return False, f"Too many ingredients (max {self._max_ingredients_count})"
            
            for i, ingredient in enumerate(ingredients):
                if not isinstance(ingredient, dict):
                    return False, f"Ingredient {i} must be an object"
                
                ing_name = ingredient.get('name', '')
                ing_amount = ingredient.get('amount', '')
                
                if not isinstance(ing_name, str) or not ing_name.strip():
                    return False, f"Ingredient {i} name is required"
                if len(ing_name) > self._max_ingredient_name_length:
                    return False, f"Ingredient {i} name too long"
                
                if not isinstance(ing_amount, str) or not ing_amount.strip():
                    return False, f"Ingredient {i} amount is required"
                if len(ing_amount) > self._max_ingredient_name_length:
                    return False, f"Ingredient {i} amount too long"
                
                # Basic security check for malicious content
                if self._contains_suspicious_content(ing_name) or self._contains_suspicious_content(ing_amount):
                    return False, f"Ingredient {i} contains suspicious content"
            
            # Validate instructions
            instructions = content.get('instructions', [])
            if not isinstance(instructions, list):
                return False, "Instructions must be a list"
            if len(instructions) > self._max_instructions_count:
                return False, f"Too many instructions (max {self._max_instructions_count})"
            
            for i, instruction in enumerate(instructions):
                if not isinstance(instruction, str) or not instruction.strip():
                    return False, f"Instruction {i} must be a non-empty string"
                if len(instruction) > self._max_instruction_length:
                    return False, f"Instruction {i} too long (max {self._max_instruction_length} chars)"
                
                # Basic security check for malicious content
                if self._contains_suspicious_content(instruction):
                    return False, f"Instruction {i} contains suspicious content"
            
            return True, "Content validation passed"
            
        except Exception as e:
            self.logger.error(f"Error validating AI content: {str(e)}")
            return False, f"Content validation error: {str(e)}"
    
    def _contains_suspicious_content(self, text: str) -> bool:
        """Check for suspicious content in text."""
        # Basic patterns to detect potentially malicious content
        suspicious_patterns = [
            r'<script[^>]*>.*?</script>',  # Script tags
            r'javascript:',  # JavaScript URLs
            r'on\w+\s*=',  # Event handlers
            r'\$\{.*?\}',  # Template injection patterns
            r'{{.*?}}',  # Template injection patterns
            r'<%.*?%>',  # Server-side template patterns
        ]
        
        text_lower = text.lower()
        for pattern in suspicious_patterns:
            if re.search(pattern, text_lower, re.IGNORECASE | re.DOTALL):
                return True
        
        return False
    
    def _classify_exception(self, exception: Exception) -> Tuple[str, bool, int]:
        """Classify exception type and determine retry strategy.
        
        Returns:
            Tuple[exception_type, should_retry, retry_delay_seconds]
        """
        if isinstance(exception, json.JSONDecodeError):
            return "json_decode_error", False, 0
        elif isinstance(exception, KeyError):
            return "key_error", False, 0
        elif isinstance(exception, requests.exceptions.ConnectionError):
            return "connection_error", True, 5
        elif isinstance(exception, requests.exceptions.Timeout):
            return "timeout_error", True, 3
        elif isinstance(exception, requests.exceptions.HTTPError):
            status_code = getattr(exception.response, 'status_code', 0) if hasattr(exception, 'response') else 0
            if status_code >= 500:
                return "server_error", True, 10
            elif status_code == 429:
                return "rate_limit_error", True, 30
            else:
                return "http_error", False, 0
        elif isinstance(exception, requests.exceptions.RequestException):
            return "request_error", True, 5
        elif "rate limit" in str(exception).lower():
            return "ai_rate_limit_error", True, 60
        elif "safety" in str(exception).lower() or "blocked" in str(exception).lower():
            return "content_safety_error", False, 0
        else:
            return "unknown_error", False, 0
    
    async def _generate_content_with_retry(self, prompt: str, max_retries: int = 3) -> str:
        """Generate content with retry logic and rate limiting."""
        if not self._check_rate_limit():
            raise Exception("Rate limit exceeded. Please try again later.")
        
        for attempt in range(max_retries):
            try:
                response = await asyncio.to_thread(
                    self.model.generate_content,
                    prompt,
                    generation_config=genai.types.GenerationConfig(
                        temperature=0.7,
                        top_p=0.8,
                        top_k=40,
                        max_output_tokens=8192,
                    )
                )
                
                if response.text:
                    return response.text.strip()
                else:
                    raise Exception("Empty response from AI model")
                    
            except Exception as e:
                exception_type, should_retry, retry_delay = self._classify_exception(e)
                
                self.logger.warning(
                    f"AI generation attempt {attempt + 1} failed with {exception_type}: {str(e)}"
                )
                
                if attempt == max_retries - 1 or not should_retry:
                    self.logger.error(f"Final attempt failed for {exception_type}: {str(e)}")
                    raise
                
                # Use classified retry delay or exponential backoff
                delay = retry_delay if retry_delay > 0 else (2 ** attempt)
                await asyncio.sleep(delay)
        
        raise Exception("Failed to generate content after all retries")
    
    async def _generate_recipes_batch(self, recipe_requests: List[Tuple[Dict[str, Any], str, Any]]) -> List[Dict[str, Any]]:
        """Generate multiple recipes concurrently with controlled concurrency.
        
        Args:
            recipe_requests: List of tuples (basic_recipe, meal_type, user)
            
        Returns:
            List of detailed recipe dictionaries
        """
        async def generate_single_recipe_with_semaphore(basic_recipe: Dict[str, Any], meal_type: str, user) -> Dict[str, Any]:
            """Generate a single recipe with semaphore control."""
            async with self._recipe_generation_semaphore:
                try:
                    # Create RecipeGenerationRequest
                    recipe_request = RecipeGenerationRequest(
                        name=basic_recipe['name'],
                        description=basic_recipe.get('description'),
                        cuisine=basic_recipe.get('cuisine'),
                        meal_type=meal_type
                    )
                    
                    # Generate detailed recipe
                    recipe_result = await self.generate_recipe_details(recipe_request, user)
                    
                    if recipe_result.get('success') and recipe_result.get('recipe'):
                        detailed_recipe = recipe_result['recipe']
                        
                        # Validate AI-generated content
                        is_valid, validation_message = self._validate_ai_content(detailed_recipe)
                        if not is_valid:
                            self.logger.warning(f"Recipe validation failed for {basic_recipe['name']}: {validation_message}")
                            # Create fallback instead of using invalid content
                            return self._create_smart_fallback_recipe(basic_recipe, meal_type)
                        
                        # Generate deterministic UUID for the recipe based on content
                        recipe_id = generate_deterministic_recipe_uuid(detailed_recipe)
                        
                        # Convert to the format expected by iOS
                        formatted_recipe = {
                            'id': recipe_id,
                            'name': detailed_recipe['name'],
                            'description': detailed_recipe['description'],
                            'ingredients': detailed_recipe['ingredients'],
                            'instructions': detailed_recipe['instructions'],
                            'nutrition_info': detailed_recipe['nutrition_info'],
                            'cuisine': detailed_recipe['cuisine'],
                            'prep_time': detailed_recipe['prep_time'],
                            'cook_time': detailed_recipe['cook_time'],
                            'difficulty': detailed_recipe['difficulty'],
                            'avg_rating': 0.0,
                            'rating_count': 0,
                            'image_url': detailed_recipe['image_url'],
                            'tags': detailed_recipe['tags'],
                            'created_by_user': 'AI Assistant',
                            'created_by_user_id': 'ai-generated',
                            'created_at': datetime.now().isoformat(),
                            'updated_at': datetime.now().isoformat()
                        }
                        return formatted_recipe
                    else:
                        self.logger.warning(f"Failed to generate detailed recipe for: {basic_recipe['name']}")
                        return self._create_smart_fallback_recipe(basic_recipe, meal_type)
                        
                except Exception as e:
                    exception_type, should_retry, retry_delay = self._classify_exception(e)
                    self.logger.error(
                        f"Error generating detailed recipe for {basic_recipe['name']} ({exception_type}): {str(e)}"
                    )
                    return self._create_smart_fallback_recipe(basic_recipe, meal_type)
        
        # Execute all recipe generations concurrently with semaphore control
        tasks = [
            generate_single_recipe_with_semaphore(basic_recipe, meal_type, user)
            for basic_recipe, meal_type, user in recipe_requests
        ]
        
        self.logger.info(f"Starting batch generation of {len(tasks)} recipes with max concurrency {self._max_concurrent_recipes}")
        detailed_recipes = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out exceptions and log them
        valid_recipes = []
        for i, result in enumerate(detailed_recipes):
            if isinstance(result, Exception):
                basic_recipe = recipe_requests[i][0]
                meal_type = recipe_requests[i][1]
                self.logger.error(f"Recipe generation completely failed for {basic_recipe['name']}: {str(result)}")
                # Create emergency fallback
                fallback = self._create_smart_fallback_recipe(basic_recipe, meal_type)
                valid_recipes.append(fallback)
            else:
                valid_recipes.append(result)
        
        self.logger.info(f"Completed batch generation: {len(valid_recipes)} recipes generated")
        return valid_recipes
    
    async def _generate_recipe_with_retry(self, prompt: str, max_retries: int = 3) -> Dict[str, Any]:
        """Generate recipe content with retry logic including JSON parsing validation and enhanced error handling."""
        if not self._check_rate_limit():
            raise Exception("Rate limit exceeded. Please try again later.")
        
        for attempt in range(max_retries):
            try:
                response = await asyncio.to_thread(
                    self.model.generate_content,
                    prompt,
                    generation_config=genai.types.GenerationConfig(
                        temperature=0.7,
                        top_p=0.8,
                        top_k=40,
                        max_output_tokens=8192,
                    )
                )
                
                if not response.text:
                    raise Exception("Empty response from AI model")
                
                # Try to parse the response
                recipe_data = self._parse_recipe_details_response(response.text.strip())
                
                # Validate the parsed content
                is_valid, validation_message = self._validate_ai_content(recipe_data)
                if not is_valid:
                    raise Exception(f"Content validation failed: {validation_message}")
                
                return recipe_data
                    
            except Exception as e:
                exception_type, should_retry, retry_delay = self._classify_exception(e)
                
                self.logger.warning(
                    f"Recipe generation attempt {attempt + 1} failed with {exception_type}: {str(e)}"
                )
                
                if attempt == max_retries - 1 or not should_retry:
                    self.logger.error(f"Final recipe generation attempt failed for {exception_type}: {str(e)}")
                    raise Exception(f"Failed to generate valid recipe after {max_retries} attempts ({exception_type}): {str(e)}")
                
                # Use classified retry delay or exponential backoff
                delay = retry_delay if retry_delay > 0 else (2 ** attempt)
                await asyncio.sleep(delay)
        
        raise Exception("Failed to generate valid recipe after all retries")
    
    async def generate_meal_plan(self, request: MealPlanRequest, user) -> Dict[str, Any]:
        """
        Generate a weekly meal plan using Google Gemini AI.
        """
        try:
            self.logger.info(f"Generating meal plan for user {user.id}")
            
            # Check cache first
            cache_key = f"meal_plan_{hash(request.plan_description)}_{user.id}"
            cached_result = cache.get(cache_key)
            if cached_result:
                self.logger.info(f"Returning cached meal plan for user {user.id}")
                return cached_result
            
            # Build the prompt for meal plan generation
            prompt = self._build_meal_plan_prompt(request)
            
            # Generate content using Gemini
            response_text = await self._generate_content_with_retry(prompt)
            
            # Parse the JSON response and generate detailed recipes
            meal_plan_data = await self._parse_meal_plan_response(response_text, user)
            
            # Get the processed lightweight daily meals (RecipeStub format)
            processed_lightweight_meals = meal_plan_data.get('lightweightMealPlan', [])
            
            # Create the final meal plan structure with lightweight format
            meal_plan = {
                'id': f'ai-generated-{user.id}-{datetime.now().strftime("%Y%m%d%H%M%S")}',
                'user_id': str(user.id),
                'name': f'AI Generated Plan - {datetime.now().strftime("%Y-%m-%d")}',
                'description': 'AI-generated lightweight meal plan with recipe suggestions',
                'week_start_date': request.week_start_date or date.today(),
                'is_active': False,
                'plan_description': request.plan_description,
                'analysis_text': self._generate_analysis_text(request),
                'items': None,  # No items initially for lightweight plans
                'items_count': 0,
                'daily_meals': None,  # No full recipes in lightweight mode
                'lightweight_daily_meals': processed_lightweight_meals,  # RecipeStub format
                'created_at': datetime.now(),
                'updated_at': datetime.now()
            }
            
            result = {
                'success': True,
                'meal_plan': meal_plan
            }
            
            # Cache the result for 1 hour
            cache.set(cache_key, result, 3600)
            
            self.logger.info(f"Successfully generated meal plan for user {user.id}")
            self.logger.info(f"[DEBUG] Generated meal plan structure: {meal_plan}")
            self.logger.info(f"[DEBUG] Sample daily meal from response: {meal_plan_data.get('weeklyMealPlan', [{}])[0] if meal_plan_data.get('weeklyMealPlan') else 'No daily meals'}")
            return result
            
        except Exception as e:
            self.logger.error(f"Error generating meal plan for user {user.id}: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': f'Failed to generate meal plan: {str(e)}'
            }
    

    
    async def generate_recipe_details(self, request: RecipeGenerationRequest, user) -> Dict[str, Any]:
        """
        Generate detailed recipe information using Google Gemini AI.
        """
        try:
            self.logger.info(f"Generating recipe details for user {user.id}")
            
            # Check cache first
            cache_key = f"recipe_details_{hash(request.name)}_{user.id}"
            cached_result = cache.get(cache_key)
            if cached_result:
                self.logger.info(f"Returning cached recipe details for user {user.id}")
                return cached_result
            
            # Build the prompt for recipe generation
            prompt = self._build_recipe_details_prompt(request)
            
            # Generate content with retry and parsing validation
            recipe_data = await self._generate_recipe_with_retry(prompt)
            
            # Fetch image from Pexels API using AI-generated query
            image_url = self._fetch_pexels_image(
                recipe_name=request.name,
                cuisine=recipe_data.get('cuisine'),
                ai_query=recipe_data.get('pexels_query')
            )
                        
            recipe = {
                'name': request.name,
                'description': recipe_data.get('description', f'美味的{request.name}食谱'),
                'cuisine': recipe_data.get('cuisine', '国际'),
                'difficulty': recipe_data.get('difficulty', '中等'),
                'prep_time': int(recipe_data.get('prep_time', request.prep_time or 15)),
                'cook_time': int(recipe_data.get('cook_time', request.cook_time or 30)),
                'image_url': image_url,
                'ingredients': recipe_data.get('ingredients', []),  # List of {name, amount} objects
                'instructions': recipe_data.get('instructions', []),  # List of strings
                'nutrition_info': recipe_data.get('nutrition_info', self._generate_mock_nutrition()),  # Use AI-generated nutrition or fallback
                'tags': recipe_data.get('tags', self._generate_tags(request))  # Use AI-generated tags or fallback
            }
                        
            result = {
                'success': True,
                'recipe': recipe
            }
            
            # Cache the result for 2 hours
            cache.set(cache_key, result, 7200)
            
            self.logger.info(f"Successfully generated recipe details for user {user.id}")
            return result
            
        except Exception as e:
            self.logger.error(f"Error generating recipe details for user {user.id}: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': f'Failed to generate recipe details: {str(e)}'
            }
    
    async def apply_meal_to_plan(self, recipe_stub: Dict[str, Any], user, meal_plan_id: str = None, day_of_week: int = 0, meal_type: str = 'lunch', serving_size: float = 1.0, save_to_account: bool = True) -> Dict[str, Any]:
        """
        Convert a RecipeStub to a complete Recipe and optionally add to meal plan.
        This is the second phase of the lightweight meal plan system.
        """
        try:
            self.logger.info(f"Applying meal to plan for user {user.id}: {recipe_stub.get('name', 'Unknown')}")
            
            # Extract recipe stub data
            recipe_name = recipe_stub.get('name', '')
            if not recipe_name.strip():
                raise ValueError("Recipe name is required")
            
            # Check if this recipe already exists in database
            existing_recipe = None
            if recipe_stub.get('id'):
                from apps.recipes.models import Recipe
                try:
                    existing_recipe = await asyncio.to_thread(
                        Recipe.objects.get, 
                        id=recipe_stub['id']
                    )
                    self.logger.info(f"Found existing recipe with ID: {recipe_stub['id']}")
                except Recipe.DoesNotExist:
                    pass
            
            # If recipe doesn't exist, generate it using AI
            if not existing_recipe:
                self.logger.info(f"Generating detailed recipe for: {recipe_name}")
                
                # Create recipe generation request with enhanced context from stub
                recipe_request = RecipeGenerationRequest(
                    name=recipe_name,
                    description=recipe_stub.get('description', ''),
                    cuisine=recipe_stub.get('cuisine', ''),
                    prep_time=recipe_stub.get('estimated_prep_time'),
                    cook_time=None,  # Will be estimated by AI
                    meal_type=meal_type
                )
                
                # Generate detailed recipe using existing AI service
                recipe_result = await self.generate_recipe_details(recipe_request, user)
                
                if not recipe_result.get('success'):
                    raise Exception(f"Failed to generate recipe details: {recipe_result.get('error', 'Unknown error')}")
                
                recipe_data = recipe_result['recipe']
            else:
                # Use existing recipe data
                recipe_data = {
                    'id': str(existing_recipe.id),
                    'name': existing_recipe.name,
                    'description': existing_recipe.description,
                    'cuisine': existing_recipe.cuisine,
                    'difficulty': existing_recipe.difficulty,
                    'prep_time': existing_recipe.prep_time,
                    'cook_time': existing_recipe.cook_time,
                    'image_url': existing_recipe.image_url,
                    'ingredients': [
                        {'name': ing.name, 'amount': ing.amount}
                        for ing in existing_recipe.ingredients.all()
                    ],
                    'instructions': existing_recipe.instructions,
                    'nutrition_info': existing_recipe.nutrition_info or {},
                    'tags': existing_recipe.tags or [],
                    'avg_rating': float(existing_recipe.avg_rating or 0),
                    'rating_count': existing_recipe.rating_count or 0,
                    'created_by_user': existing_recipe.created_by_user,
                    'created_by_user_id': str(existing_recipe.created_by_user_id),
                    'created_at': existing_recipe.created_at.isoformat(),
                    'updated_at': existing_recipe.updated_at.isoformat()
                }
            
            # If save_to_account is True, save the recipe to user's account
            saved_recipe = None
            if save_to_account and not existing_recipe:
                from apps.ai_integration.serializers import CreateRecipeFromAISerializer
                from apps.ai_integration.views import create_recipe_from_ai
                
                # Create recipe from AI data
                create_request = {
                    'ai_recipe_data': recipe_data,
                    'save_to_account': True
                }
                
                # This is a bit circular, but we need to call the existing recipe creation logic
                # TODO: Refactor to extract the recipe creation logic into a separate service method
                
            # If meal_plan_id is provided, add the recipe to the meal plan
            meal_plan_item = None
            if meal_plan_id:
                from apps.meal_plans.models import MealPlan, MealPlanItem
                from apps.recipes.models import Recipe
                
                try:
                    # Get the meal plan
                    meal_plan = await asyncio.to_thread(
                        MealPlan.objects.get, 
                        id=meal_plan_id, 
                        user=user
                    )
                    
                    # Get or create the recipe
                    if existing_recipe:
                        recipe_obj = existing_recipe
                    else:
                        # Create recipe in database if it doesn't exist
                        recipe_obj = await asyncio.to_thread(self._create_recipe_from_data, recipe_data, user)
                    
                    # Create meal plan item
                    meal_plan_item_data = {
                        'meal_plan': meal_plan,
                        'recipe': recipe_obj,
                        'day_of_week': day_of_week,
                        'meal_type': meal_type,
                        'serving_size': serving_size
                    }
                    
                    meal_plan_item = await asyncio.to_thread(
                        MealPlanItem.objects.create, 
                        **meal_plan_item_data
                    )
                    
                    self.logger.info(f"Added recipe to meal plan: {meal_plan_id}")
                    
                except Exception as e:
                    self.logger.error(f"Error adding recipe to meal plan: {str(e)}")
                    # Don't fail the entire operation if meal plan addition fails
                    pass
            
            # Prepare response
            result = {
                'success': True,
                'recipe': recipe_data,
                'message': f'Successfully created recipe: {recipe_name}'
            }
            
            if meal_plan_item:
                result['meal_plan_item'] = {
                    'id': meal_plan_item.id,
                    'meal_plan_id': str(meal_plan_item.meal_plan_id),
                    'recipe_id': str(meal_plan_item.recipe_id),
                    'day_of_week': meal_plan_item.day_of_week,
                    'meal_type': meal_plan_item.meal_type,
                    'serving_size': float(meal_plan_item.serving_size),
                    'added_at': meal_plan_item.added_at.isoformat()
                }
                result['message'] += f' and added to meal plan'
            
            self.logger.info(f"Successfully applied meal for user {user.id}")
            return result
            
        except Exception as e:
            self.logger.error(f"Error applying meal to plan for user {user.id}: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': f'Failed to apply meal to plan: {str(e)}'
            }
    
    def _create_recipe_from_data(self, recipe_data: Dict[str, Any], user) -> 'Recipe':
        """Create a Recipe model instance from recipe data."""
        from apps.recipes.models import Recipe, Ingredient as RecipeIngredient
        
        # Create the recipe
        recipe = Recipe.objects.create(
            name=recipe_data['name'],
            description=recipe_data.get('description', ''),
            cuisine=recipe_data.get('cuisine', ''),
            difficulty=recipe_data.get('difficulty', 'medium'),
            prep_time=recipe_data.get('prep_time', 30),
            cook_time=recipe_data.get('cook_time', 30),
            image_url=recipe_data.get('image_url', ''),
            instructions=recipe_data.get('instructions', []),
            nutrition_info=recipe_data.get('nutrition_info', {}),
            tags=recipe_data.get('tags', []),
            created_by_user=user,
            avg_rating=recipe_data.get('avg_rating', 0.0),
            rating_count=recipe_data.get('rating_count', 0)
        )
        
        # Create ingredients
        for ingredient_data in recipe_data.get('ingredients', []):
            RecipeIngredient.objects.create(
                recipe=recipe,
                name=ingredient_data.get('name', ''),
                amount=ingredient_data.get('amount', ''),
                unit='',
                notes=''
            )
        
        return recipe
    
    async def analyze_meal_plan(self, meal_plan, plan_description: str = '', analysis_type: str = 'full') -> Dict[str, Any]:
        """
        Analyze a meal plan for nutrition, variety, and balance using Google Gemini AI.
        """
        try:
            self.logger.info(f"Analyzing meal plan {meal_plan.id}")
            
            # Check cache first
            cache_key = f"meal_plan_analysis_{meal_plan.id}_{hash(plan_description)}"
            cached_result = cache.get(cache_key)
            if cached_result:
                self.logger.info(f"Returning cached analysis for meal plan {meal_plan.id}")
                return cached_result
            
            # Prepare meal plan data for analysis (using sync_to_async)
            meal_plan_data = await asyncio.to_thread(self._prepare_meal_plan_for_analysis, meal_plan)
            
            # Build the prompt for meal plan analysis
            prompt = self._build_meal_plan_analysis_prompt(plan_description, meal_plan_data)
            
            # Generate content using Gemini
            response_text = await self._generate_content_with_retry(prompt)
            
            # Parse the JSON response
            analysis_data = self._parse_analysis_response(response_text)
            
            # Get total recipes count using sync_to_async
            total_recipes = await asyncio.to_thread(lambda: meal_plan.items.count())
            
            analysis = {
                'meal_plan_id': str(meal_plan.id),
                'analysis_type': analysis_type,
                'total_recipes': total_recipes,
                'analysis_text': analysis_data.get('analysisText', ''),
                'analysis_date': datetime.now().isoformat()
            }
            
            result = {
                'success': True,
                'analysis': analysis
            }
            
            # Cache the result for 30 minutes
            cache.set(cache_key, result, 1800)
            
            self.logger.info(f"Successfully analyzed meal plan {meal_plan.id}")
            return result
            
        except Exception as e:
            self.logger.error(f"Error analyzing meal plan {meal_plan.id}: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': f'Failed to analyze meal plan: {str(e)}'
            }
    
    def _build_meal_plan_prompt(self, request: MealPlanRequest) -> str:
        """Build the prompt for simplified meal plan generation with recipe names only."""
        dietary_preferences_text = ""
        if request.dietary_preferences:
            dietary_preferences_text = f"\n饮食偏好: {request.dietary_preferences}"
        
        allergies_text = ""
        if request.allergies:
            allergies_text = f"\n过敏原: {', '.join(request.allergies)}"
        
        dislikes_text = ""
        if request.dislikes:
            dislikes_text = f"\n不喜欢的食物: {', '.join(request.dislikes)}"
        
        calorie_text = ""
        if request.calorie_target:
            calorie_text = f"\n每日卡路里目标: {request.calorie_target}千卡"
        
        additional_text = ""
        if request.additional_requirements:
            additional_text = f"\n额外要求: {request.additional_requirements}"
        
        return f"""你是一位专业的膳食计划AI。根据用户描述生成7天轻量化膳食计划，只包含食谱的基本预览信息。
输出必须是有效的JSON对象，所有文本内容用中文。

用户计划描述: {request.plan_description}{dietary_preferences_text}{allergies_text}{dislikes_text}{calorie_text}{additional_text}

要求：
1. 只生成食谱的基本预览信息，不需要详细配料和步骤
2. 所有内容用中文
3. 食谱名称要具体且有吸引力
4. 考虑营养均衡和多样性
5. 提供预估的卡路里和准备时间

输出JSON格式：
{{
  "lightweightMealPlan": [
    {{
      "day": "星期一",
      "breakfast": [食谱基本信息数组],
      "lunch": [食谱基本信息数组],
      "dinner": [食谱基本信息数组]
    }},
    ... (共7天)
  ]
}}

每个食谱对象必须包含以下字段（RecipeStub格式）：
{{
  "id": null,
  "name": "具体的食谱名称，如'香煎三文鱼配柠檬芦笋'",
  "cuisine": "菜系，如'中式'、'西式'、'日式'等",
  "description": "简短描述，15-25字",
  "estimated_calories": 300,
  "estimated_prep_time": 20,
  "image_url": null,
  "tags": ["健康", "低脂", "快手菜"]
}}

重要说明：
- 确保JSON语法正确
- 每天包含早餐、午餐、晚餐
- 每餐通常1个食谱，特殊情况可以2个
- 食谱名称要具体，不要太笼统
- 一周内避免重复食谱
- 考虑营养搭配和口味多样性
- estimated_calories：预估每份卡路里（100-800）
- estimated_prep_time：预估准备时间（5-60分钟）
- tags：相关标签数组，如["健康", "素食", "快手菜", "高蛋白"]
- id 和 image_url 字段设为 null（将在后续 applyMeal 时生成）

请生成完整的7天轻量化膳食计划JSON。
确保您的整个响应是一个以 {{ 开始并以 }} 结束的JSON对象。"""

    def _build_recipe_details_prompt(self, request: RecipeGenerationRequest) -> str:
        """Build the prompt for recipe details generation."""
        return f"""你是一位专业的烹饪助手和营养师。根据给定的食谱名称，提供完整的食谱信息，包括精确的营养分析。请用中文回答。

食谱名称: {request.name}

重要要求：
1. 所有配料用量必须严格按照**一人份**来计算
2. 配料名称和用量要分开，用量要精确具体
3. 烹饪步骤要详细清晰，包含具体的时间和温度
4. 所有内容必须是中文
5. 根据食谱名称自动判断菜系风格（如中式、西式、日式、韩式、意式、法式、泰式、印式等）
6. 根据食谱复杂程度自动判断难度等级（简单、中等、困难）
7. 估算合理的准备时间和烹饪时间（分钟）
8. 生成适合的标签（如素食、低脂、高蛋白、快手菜等）
9. **重要**：根据配料的实际营养成分，准确计算营养信息（卡路里、蛋白质、碳水化合物、脂肪等）

字段要求：
- description: 简短的食谱描述（20-30字）
- cuisine: 菜系风格（如"中式"、"西式"、"日式"等）
- difficulty: 难度等级（"简单"、"中等"、"困难"）
- prep_time: 准备时间（分钟，整数）
- cook_time: 烹饪时间（分钟，整数）
- pexels_query: 用于Pexels图片搜索的英文关键词，要简洁且准确描述这道菜的视觉特征（如"chinese braised pork belly"、"italian pasta carbonara"、"japanese sushi rolls"等）
- ingredients: 配料列表，每个配料包含name和amount字段
- instructions: 烹饪步骤列表，每个步骤为独立字符串，不需要标出数字顺序但是应符合在数组中的顺序
- nutrition_info: 营养信息对象，基于实际配料计算得出（一人份）
- tags: 标签数组，包含相关特征标签

请严格按照以下JSON格式输出：
{{
  "name": "{request.name}",
  "description": "香嫩可口的家常鸡肉料理，营养丰富",
  "cuisine": "中式",
  "difficulty": "中等",
  "prep_time": 15,
  "cook_time": 20,
  "pexels_query": "chinese braised chicken rice bowl",
  "ingredients": [
    {{"name": "鸡胸肉", "amount": "150克"}},
    {{"name": "大米", "amount": "80克"}},
    {{"name": "生抽", "amount": "1汤匙"}},
    {{"name": "料酒", "amount": "1茶匙"}},
    {{"name": "盐", "amount": "适量"}},
    {{"name": "食用油", "amount": "1汤匙"}}
  ],
  "instructions": [
    "将鸡胸肉洗净，切成2厘米见方的小块，用料酒和少许盐腌制10分钟",
    "大米淘洗干净，放入电饭煲中，加入适量清水，按下煮饭键",
    "热锅下油，油温6成热时下入鸡肉块，大火炒制3-4分钟至表面微黄",
    "加入生抽调色调味，继续炒制2分钟至鸡肉完全熟透",
    "盛起装盘，搭配米饭一起享用"
  ],
  "nutrition_info": {{
    "calories": 520,
    "protein": "35g",
    "carbohydrates": "65g",
    "fat": "8g",
    "fiber": "2g",
    "sodium": "680mg",
    "sugar": "1g",
    "servings": 1
  }},
  "tags": ["家常菜", "高蛋白", "下饭菜", "营养丰富"]
}}

营养信息计算说明：
- calories: 总卡路里数（基于所有配料的热量相加）
- protein: 蛋白质含量（克）
- carbohydrates: 碳水化合物含量（克）
- fat: 脂肪含量（克）
- fiber: 膳食纤维含量（克）
- sodium: 钠含量（毫克，包括食盐和调料中的钠）
- sugar: 糖分含量（克）
- servings: 份数（固定为1，表示一人份）

请根据实际配料的营养成分，仔细计算营养信息。例如：
- 150克鸡胸肉约含 231卡路里，43.5克蛋白质，0克碳水化合物，5克脂肪
- 80克大米约含 288卡路里，6.4克蛋白质，64克碳水化合物，0.6克脂肪
- 调料和油类也要计算在内

请为"{request.name}"提供一个营养均衡的、一人份的完整食谱信息，包括基于真实配料的准确营养分析。确保所有字段都包含在JSON中，并且格式正确。"""

    def _build_meal_plan_analysis_prompt(self, plan_description: str, meal_plan_data: str) -> str:
        """Build the prompt for meal plan analysis."""
        return f"""你是一位专业的营养师和膳食规划顾问。
你的任务是根据用户提供的7天膳食计划数据（JSON格式）和他们的计划描述（包括饮食偏好、目标等）来进行全面的分析。
请用中文提供分析结果。分析应具有建设性并提供可操作的建议。

用户计划描述: {plan_description}

每周膳食计划数据 (JSON格式):
```json
{meal_plan_data}
```

请分析以下方面：
1.  **营养均衡性**: 评估计划是否大致包含主要营养素（蛋白质、碳水化合物、脂肪）的均衡来源。提及食物多样性（蔬菜、水果、全谷物、瘦肉蛋白等）。
2.  **与计划描述的符合程度**: 评估计划是否符合用户在 `planDescription` 中提出的偏好（例如，素食、低碳水、避免特定过敏原等）。明确指出符合和不符合的地方。
3.  **多样性和趣味性**: 评价计划中的食谱是否足够多样，以避免饮食单调。
4.  **可改进的建议**: 提供1-3条具体的、可操作的建议来改进这个膳食计划，使其更健康或更符合用户目标。建议应该清晰且易于执行。

请将您的分析结果组织成清晰、易读的段落。您可以使用Markdown格式来增强可读性，例如使用**粗体**、*斜体*或项目符号列表来突出建议。
输出应该是一个包含完整分析文本的JSON对象，键为 "analysisText"。
例如:
{{
  "analysisText": "整体来看，这个膳食计划在蛋白质摄入方面做得不错，但蔬菜种类略显单一。\\n\\n该计划很好地遵循了您"低碳水"的偏好，但需要注意补充足够的膳食纤维。\\n\\n为了进一步改善，建议：\\n* 增加不同颜色的蔬菜。\\n* 在午餐中加入一份豆类或全谷物食品。"
}}

确保输出格式为有效的JSON。"""

    async def _parse_meal_plan_response(self, response_text: str, user) -> Dict[str, Any]:
        """Parse the lightweight meal plan response from Gemini and return RecipeStub format."""
        try:
            # Clean up the response text
            response_text = response_text.strip()
            
            # Find JSON content between ```json and ``` markers
            json_start = response_text.find('```json')
            json_end = response_text.rfind('```')
            
            if json_start != -1 and json_end != -1 and json_end > json_start:
                # Extract JSON content
                json_content = response_text[json_start + 7:json_end].strip()
            else:
                # Try to find JSON object directly
                brace_start = response_text.find('{')
                brace_end = response_text.rfind('}')
                
                if brace_start != -1 and brace_end != -1 and brace_end > brace_start:
                    json_content = response_text[brace_start:brace_end + 1]
                else:
                    json_content = response_text
            
            # Parse JSON
            try:
                data = json.loads(json_content)
            except json.JSONDecodeError as e:
                self.logger.error(f"Failed to parse meal plan JSON response: {str(e)}")
                self.logger.error(f"JSON content being parsed: {json_content[:1000]}...")  # First 1000 chars
                
                # Try to fix common JSON issues
                try:
                    fixed_json = self._fix_json_syntax(json_content)
                    data = json.loads(fixed_json)
                    self.logger.info("Successfully fixed and parsed JSON after syntax error")
                except Exception as fix_error:
                    self.logger.error(f"Failed to fix JSON syntax: {str(fix_error)}")
                    raise Exception("Invalid JSON response from AI model")
            
            # Validate and clean the lightweight meal plan data
            if 'lightweightMealPlan' in data and isinstance(data['lightweightMealPlan'], list):
                # Ensure we have 7 days
                if len(data['lightweightMealPlan']) == 7:
                    self.logger.info(f"Processing lightweight meal plan with RecipeStub format")
                    
                    for day_idx, day_plan in enumerate(data['lightweightMealPlan']):
                        if not isinstance(day_plan, dict):
                            continue
                        
                        # Process each meal type and validate RecipeStub format
                        for meal_type in ['breakfast', 'lunch', 'dinner']:
                            if meal_type not in day_plan:
                                day_plan[meal_type] = []
                            elif not isinstance(day_plan[meal_type], list):
                                day_plan[meal_type] = []
                            else:
                                # Validate and clean RecipeStub objects
                                valid_recipe_stubs = []
                                for recipe_stub in day_plan[meal_type]:
                                    if (isinstance(recipe_stub, dict) and 
                                        'name' in recipe_stub and 
                                        isinstance(recipe_stub['name'], str) and
                                        recipe_stub['name'].strip()):
                                        
                                        # Clean and validate RecipeStub fields
                                        cleaned_stub = self._clean_recipe_stub(recipe_stub)
                                        valid_recipe_stubs.append(cleaned_stub)
                                
                                day_plan[meal_type] = valid_recipe_stubs
                    
                    return {'lightweightMealPlan': data['lightweightMealPlan']}
            
            # If validation fails, return empty lightweight structure
            return {
                'lightweightMealPlan': [
                    {
                        'day': day,
                        'breakfast': [],
                        'lunch': [],
                        'dinner': []
                    }
                    for day in ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
                ]
            }
            
        except Exception as e:
            exception_type, should_retry, retry_delay = self._classify_exception(e)
            self.logger.error(f"Error parsing meal plan response ({exception_type}): {str(e)}")
            raise
    
    def _clean_recipe_stub(self, recipe_stub: Dict[str, Any]) -> Dict[str, Any]:
        """Clean and validate RecipeStub fields."""
        cleaned = {
            'id': recipe_stub.get('id'),  # Should be null for AI-generated
            'name': recipe_stub.get('name', '').strip(),
            'cuisine': recipe_stub.get('cuisine', '国际').strip(),
            'description': recipe_stub.get('description', '').strip(),
            'estimated_calories': recipe_stub.get('estimated_calories'),
            'estimated_prep_time': recipe_stub.get('estimated_prep_time'),
            'image_url': recipe_stub.get('image_url'),  # Should be null initially
            'tags': recipe_stub.get('tags', [])
        }
        
        # Validate and clean numeric fields
        if cleaned['estimated_calories'] is not None:
            try:
                cleaned['estimated_calories'] = max(0, min(5000, int(cleaned['estimated_calories'])))
            except (ValueError, TypeError):
                cleaned['estimated_calories'] = None
        
        if cleaned['estimated_prep_time'] is not None:
            try:
                cleaned['estimated_prep_time'] = max(0, min(480, int(cleaned['estimated_prep_time'])))
            except (ValueError, TypeError):
                cleaned['estimated_prep_time'] = None
        
        # Ensure tags is a list
        if not isinstance(cleaned['tags'], list):
            cleaned['tags'] = []
        
        # Generate fallback description if missing
        if not cleaned['description']:
            cleaned['description'] = f"美味的{cleaned['name']}"
        
        return cleaned

    def _create_smart_fallback_recipe(self, basic_recipe: Dict[str, Any], meal_type: str) -> Dict[str, Any]:
        """Create an intelligent fallback recipe based on recipe name analysis."""
        recipe_name = basic_recipe.get('name', 'Unknown Recipe')
        cuisine = basic_recipe.get('cuisine', '中式')
        
        # Analyze recipe name to determine likely ingredients and cooking method
        smart_ingredients = self._analyze_recipe_name_for_ingredients(recipe_name, meal_type, cuisine)
        smart_instructions = self._analyze_recipe_name_for_instructions(recipe_name, meal_type, cuisine)
        smart_description = self._generate_smart_description(recipe_name, cuisine)
        estimated_times = self._estimate_cooking_times(recipe_name, meal_type)
        
        # Create recipe data structure for deterministic UUID generation
        recipe_data_for_uuid = {
            'name': recipe_name,
            'ingredients': smart_ingredients,
            'instructions': smart_instructions,
            'cuisine': cuisine,
            'difficulty': self._estimate_difficulty(recipe_name)
        }
        
        # Generate deterministic UUID based on recipe content
        recipe_id = generate_deterministic_recipe_uuid(recipe_data_for_uuid)
        
        return {
            'id': recipe_id,
            'name': recipe_name,
            'description': smart_description,
            'ingredients': smart_ingredients,
            'instructions': smart_instructions,
            'nutrition_info': self._generate_mock_nutrition(),
            'cuisine': cuisine,
            'prep_time': estimated_times['prep_time'],
            'cook_time': estimated_times['cook_time'],
            'difficulty': self._estimate_difficulty(recipe_name),
            'avg_rating': 0.0,
            'rating_count': 0,
            'image_url': self._get_fallback_image_url(),
            'tags': self._generate_smart_tags(recipe_name, meal_type, cuisine),
            'created_by_user': 'AI Assistant',
            'created_by_user_id': 'ai-generated-smart-fallback',
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }
    
    def _analyze_recipe_name_for_ingredients(self, recipe_name: str, meal_type: str, cuisine: str) -> List[Dict[str, str]]:
        """Analyze recipe name to predict likely ingredients."""
        ingredients = []
        name_lower = recipe_name.lower()
        
        # Basic seasonings always included
        ingredients.extend([
            {'name': '盐', 'amount': '适量'},
            {'name': '食用油', 'amount': '1汤匙'}
        ])
        
        # Protein detection
        if any(protein in name_lower for protein in ['鸡', '鸡肉', 'chicken']):
            ingredients.append({'name': '鸡肉', 'amount': '150克'})
        elif any(protein in name_lower for protein in ['猪', '猪肉', 'pork']):
            ingredients.append({'name': '猪肉', 'amount': '150克'})
        elif any(protein in name_lower for protein in ['牛', '牛肉', 'beef']):
            ingredients.append({'name': '牛肉', 'amount': '150克'})
        elif any(protein in name_lower for protein in ['鱼', 'fish', '三文鱼', 'salmon']):
            ingredients.append({'name': '鱼肉', 'amount': '150克'})
        elif any(protein in name_lower for protein in ['虾', 'shrimp']):
            ingredients.append({'name': '虾', 'amount': '200克'})
        elif any(protein in name_lower for protein in ['蛋', 'egg']):
            ingredients.append({'name': '鸡蛋', 'amount': '2个'})
        elif any(protein in name_lower for protein in ['豆腐', 'tofu']):
            ingredients.append({'name': '豆腐', 'amount': '200克'})
        
        # Vegetable detection
        if any(veg in name_lower for veg in ['西红柿', '番茄', 'tomato']):
            ingredients.append({'name': '西红柿', 'amount': '2个'})
        elif any(veg in name_lower for veg in ['土豆', 'potato']):
            ingredients.append({'name': '土豆', 'amount': '1个'})
        elif any(veg in name_lower for veg in ['胡萝卜', 'carrot']):
            ingredients.append({'name': '胡萝卜', 'amount': '1根'})
        elif any(veg in name_lower for veg in ['洋葱', 'onion']):
            ingredients.append({'name': '洋葱', 'amount': '半个'})
        elif any(veg in name_lower for veg in ['青椒', 'pepper']):
            ingredients.append({'name': '青椒', 'amount': '1个'})
        elif any(veg in name_lower for veg in ['芦笋', 'asparagus']):
            ingredients.append({'name': '芦笋', 'amount': '200克'})
        
        # Grain/starch detection
        if any(grain in name_lower for grain in ['米饭', 'rice', '饭']):
            ingredients.append({'name': '大米', 'amount': '80克'})
        elif any(grain in name_lower for grain in ['面条', 'noodle', '面']):
            ingredients.append({'name': '面条', 'amount': '100克'})
        elif any(grain in name_lower for grain in ['面包', 'bread']):
            ingredients.append({'name': '面包', 'amount': '2片'})
        
        # Add cuisine-specific ingredients
        if cuisine == '中式':
            ingredients.extend([
                {'name': '生抽', 'amount': '1汤匙'},
                {'name': '料酒', 'amount': '1茶匙'},
                {'name': '大蒜', 'amount': '2瓣'}
            ])
        elif cuisine == '西式':
            ingredients.extend([
                {'name': '黑胡椒', 'amount': '适量'},
                {'name': '百里香', 'amount': '少许'}
            ])
        elif cuisine == '日式':
            ingredients.extend([
                {'name': '味噌', 'amount': '1汤匙'},
                {'name': '海苔', 'amount': '适量'}
            ])
        
        # Add meal-type specific ingredients
        if meal_type == 'breakfast' and not any('蛋' in ing['name'] for ing in ingredients):
            ingredients.append({'name': '鸡蛋', 'amount': '1个'})
        
        return ingredients
    
    def _analyze_recipe_name_for_instructions(self, recipe_name: str, meal_type: str, cuisine: str) -> List[str]:
        """Generate cooking instructions based on recipe name analysis."""
        name_lower = recipe_name.lower()
        instructions = []
        
        # Prep step
        instructions.append('准备所有食材，清洗干净并按需切好')
        
        # Cooking method detection
        if any(method in name_lower for method in ['炒', 'stir', 'fry']):
            instructions.extend([
                '热锅下油，油温6成热时下入主要食材',
                '大火快炒2-3分钟至食材断生',
                '加入调料炒匀，继续炒制1-2分钟'
            ])
        elif any(method in name_lower for method in ['煮', 'boil', '汤']):
            instructions.extend([
                '锅中加入适量清水，大火烧开',
                '放入主要食材，转中火煮10-15分钟',
                '调味后再煮5分钟即可'
            ])
        elif any(method in name_lower for method in ['蒸', 'steam']):
            instructions.extend([
                '蒸锅加水烧开，将食材放入蒸屉',
                '大火蒸15-20分钟至熟透',
                '取出后淋上调料汁即可'
            ])
        elif any(method in name_lower for method in ['烤', 'bake', 'roast']):
            instructions.extend([
                '烤箱预热至200°C',
                '将食材放入烤盘，刷上调料',
                '烤15-25分钟至表面金黄'
            ])
        elif any(method in name_lower for method in ['煎', 'pan']):
            instructions.extend([
                '平底锅刷少许油，中火加热',
                '放入食材煎制3-4分钟至一面金黄',
                '翻面继续煎2-3分钟至熟透'
            ])
        else:
            # Default cooking method
            instructions.extend([
                '热锅下油，放入食材翻炒',
                '加入调料，炒制至熟透',
                '根据口味调整调料用量'
            ])
        
        # Final step
        instructions.append('装盘即可享用这道美味的' + recipe_name)
        
        return instructions
    
    def _generate_smart_description(self, recipe_name: str, cuisine: str) -> str:
        """Generate a smart description based on recipe name and cuisine."""
        base_descriptions = {
            '中式': '香味浓郁的传统中式料理',
            '西式': '经典西式风味美食',
            '日式': '清淡健康的日式料理',
            '韩式': '鲜美可口的韩式美食',
            '意式': '地道的意大利风味',
            '泰式': '酸甜辣俱全的泰式风味'
        }
        
        base_desc = base_descriptions.get(cuisine, '美味可口的料理')
        return f'{base_desc}，{recipe_name}制作简单，营养丰富，适合家庭制作'
    
    def _estimate_cooking_times(self, recipe_name: str, meal_type: str) -> Dict[str, int]:
        """Estimate cooking times based on recipe name and meal type."""
        name_lower = recipe_name.lower()
        
        # Base times by meal type
        base_times = {
            'breakfast': {'prep_time': 10, 'cook_time': 15},
            'lunch': {'prep_time': 15, 'cook_time': 25},
            'dinner': {'prep_time': 20, 'cook_time': 30}
        }
        
        times = base_times.get(meal_type, {'prep_time': 15, 'cook_time': 25})
        
        # Adjust based on cooking method
        if any(method in name_lower for method in ['炒', 'stir']):
            times['cook_time'] = min(times['cook_time'], 15)  # Quick stir-fry
        elif any(method in name_lower for method in ['炖', 'stew', '煲']):
            times['cook_time'] = max(times['cook_time'], 45)  # Slow cooking
        elif any(method in name_lower for method in ['烤', 'bake']):
            times['cook_time'] = max(times['cook_time'], 30)  # Baking takes time
        elif any(method in name_lower for method in ['蒸', 'steam']):
            times['cook_time'] = max(times['cook_time'], 20)  # Steaming
        
        return times
    
    def _estimate_difficulty(self, recipe_name: str) -> str:
        """Estimate difficulty level based on recipe name."""
        name_lower = recipe_name.lower()
        
        # Complex cooking methods
        if any(method in name_lower for method in ['红烧', '糖醋', '宫保', '麻婆']):
            return '困难'
        elif any(method in name_lower for method in ['炖', 'stew', '煲']):
            return '中等'
        elif any(method in name_lower for method in ['炒', '煎', '蒸']):
            return '简单'
        else:
            return '中等'
    
    def _generate_smart_tags(self, recipe_name: str, meal_type: str, cuisine: str) -> List[str]:
        """Generate smart tags based on recipe analysis."""
        tags = [meal_type, cuisine]
        name_lower = recipe_name.lower()
        
        # Add cooking method tags
        if any(method in name_lower for method in ['炒', 'stir']):
            tags.append('快手菜')
        elif any(method in name_lower for method in ['蒸', 'steam']):
            tags.append('健康')
        elif any(method in name_lower for method in ['汤', 'soup']):
            tags.append('暖胃')
        
        # Add nutrition tags
        if any(protein in name_lower for protein in ['鸡', '鱼', '虾']):
            tags.append('高蛋白')
        if any(veg in name_lower for veg in ['蔬菜', '青菜', '菠菜', '芦笋']):
            tags.append('营养丰富')
        
        # Add difficulty tags
        difficulty = self._estimate_difficulty(recipe_name)
        if difficulty == '简单':
            tags.append('新手友好')
        
        return list(set(tags))  # Remove duplicates
    
    def _create_fallback_recipe(self, basic_recipe: Dict[str, Any], meal_type: str) -> Dict[str, Any]:
        """Create a fallback recipe when detailed generation fails (legacy method)."""
        # Use the new smart fallback method
        return self._create_smart_fallback_recipe(basic_recipe, meal_type)
    
    def _get_basic_ingredients_by_meal_type(self, meal_type: str) -> List[Dict[str, str]]:
        """Get basic ingredients based on meal type."""
        base_ingredients = [
            {'name': '食用油', 'amount': '1汤匙'},
            {'name': '盐', 'amount': '适量'},
            {'name': '生抽', 'amount': '1汤匙'}
        ]
        
        if meal_type == 'breakfast':
            base_ingredients.extend([
                {'name': '鸡蛋', 'amount': '2个'},
                {'name': '面包', 'amount': '2片'},
                {'name': '牛奶', 'amount': '200毫升'}
            ])
        elif meal_type == 'lunch':
            base_ingredients.extend([
                {'name': '米饭', 'amount': '150克'},
                {'name': '蔬菜', 'amount': '200克'},
                {'name': '蛋白质食材', 'amount': '100克'}
            ])
        elif meal_type == 'dinner':
            base_ingredients.extend([
                {'name': '主食', 'amount': '150克'},
                {'name': '蔬菜', 'amount': '250克'},
                {'name': '肉类', 'amount': '120克'}
            ])
        
        return base_ingredients
    
    def _get_basic_instructions_by_meal_type(self, meal_type: str) -> List[str]:
        """Get basic instructions based on meal type."""
        if meal_type == 'breakfast':
            return [
                '准备所有食材，清洗干净',
                '热锅下油，打散鸡蛋炒制',
                '烤面包片至金黄色',
                '搭配牛奶一起享用'
            ]
        elif meal_type == 'lunch':
            return [
                '准备所有食材，清洗切好',
                '热锅下油，爆炒蔬菜',
                '加入蛋白质食材继续炒制',
                '调味后搭配米饭食用'
            ]
        elif meal_type == 'dinner':
            return [
                '准备所有食材，分别处理',
                '热锅下油，先炒肉类',
                '加入蔬菜炒制至断生',
                '调味装盘，搭配主食享用'
            ]
        
        return ['根据食材特点进行烹饪', '调味后即可享用']
    
    def _fix_json_syntax(self, json_content: str) -> str:
        """Try to fix common JSON syntax errors."""
        import re
        
        # Remove trailing commas before closing brackets/braces
        json_content = re.sub(r',(\s*[}\]])', r'\1', json_content)
        
        # Fix missing commas between objects (basic attempt)
        json_content = re.sub(r'}\s*{', r'},{', json_content)
        
        # Fix missing commas between array elements
        json_content = re.sub(r']\s*\[', r'],[', json_content)
        
        # Remove any control characters that might cause issues
        json_content = ''.join(char for char in json_content if ord(char) >= 32 or char in '\n\r\t')
        
        return json_content

    def _parse_recipe_details_response(self, response_text: str) -> Dict[str, Any]:
        """Parse the recipe details response from Gemini."""
        try:
            # Clean up the response text
            response_text = response_text.strip()
            
            # Find JSON content between ```json and ``` markers
            json_start = response_text.find('```json')
            json_end = response_text.rfind('```')
            
            if json_start != -1 and json_end != -1 and json_end > json_start:
                # Extract JSON content
                json_content = response_text[json_start + 7:json_end].strip()
            else:
                # Try to find JSON object directly
                brace_start = response_text.find('{')
                brace_end = response_text.rfind('}')
                
                if brace_start != -1 and brace_end != -1 and brace_end > brace_start:
                    json_content = response_text[brace_start:brace_end + 1]
                else:
                    json_content = response_text
            
            # Parse JSON
            data = json.loads(json_content)
            
            # Validate the data structure
            if not isinstance(data, dict):
                raise Exception("Response is not a JSON object")
            
            # Validate description field (optional, will use default if missing)
            if 'description' in data and not isinstance(data['description'], str):
                raise Exception("Invalid description field - must be a string")
            
            # Validate cuisine field (optional, will use default if missing)
            if 'cuisine' in data and not isinstance(data['cuisine'], str):
                raise Exception("Invalid cuisine field - must be a string")
            
            # Validate difficulty field (optional, will use default if missing)
            if 'difficulty' in data and not isinstance(data['difficulty'], str):
                raise Exception("Invalid difficulty field - must be a string")
            
            # Validate prep_time field (optional, will use default if missing)
            if 'prep_time' in data and not isinstance(data['prep_time'], (int, float)):
                raise Exception("Invalid prep_time field - must be a number")
            
            # Validate cook_time field (optional, will use default if missing)
            if 'cook_time' in data and not isinstance(data['cook_time'], (int, float)):
                raise Exception("Invalid cook_time field - must be a number")
            
            # Validate pexels_query field (optional, will use default if missing)
            if 'pexels_query' in data and not isinstance(data['pexels_query'], str):
                raise Exception("Invalid pexels_query field - must be a string")
            
            # Validate nutrition_info field (optional, will use default if missing)
            if 'nutrition_info' in data:
                if not isinstance(data['nutrition_info'], dict):
                    raise Exception("Invalid nutrition_info field - must be an object")
                
                # Validate required nutrition fields
                required_nutrition_fields = ['calories', 'protein', 'carbohydrates', 'fat', 'servings']
                for field in required_nutrition_fields:
                    if field in data['nutrition_info']:
                        if field == 'servings':
                            # servings should be a number
                            if not isinstance(data['nutrition_info'][field], (int, float)):
                                raise Exception(f"Invalid nutrition_info.{field} field - must be a number")
                        elif field == 'calories':
                            # calories should be a number
                            if not isinstance(data['nutrition_info'][field], (int, float)):
                                raise Exception(f"Invalid nutrition_info.{field} field - must be a number")
                        else:
                            # other nutrition fields can be strings (e.g., "25g") or numbers
                            if not isinstance(data['nutrition_info'][field], (str, int, float)):
                                raise Exception(f"Invalid nutrition_info.{field} field - must be a string or number")
            
            # Validate tags field (optional, will use default if missing)
            if 'tags' in data:
                if not isinstance(data['tags'], list):
                    raise Exception("Invalid tags field - must be a list")
                for i, tag in enumerate(data['tags']):
                    if not isinstance(tag, str):
                        raise Exception(f"Tag {i} is not a string")
            
            # Validate ingredients field
            if 'ingredients' not in data or not isinstance(data['ingredients'], list):
                raise Exception("Missing or invalid ingredients field")
            
            # Validate each ingredient object
            for i, ingredient in enumerate(data['ingredients']):
                if not isinstance(ingredient, dict):
                    raise Exception(f"Ingredient {i} is not an object")
                if 'name' not in ingredient or not isinstance(ingredient['name'], str):
                    raise Exception(f"Ingredient {i} missing or invalid 'name' field")
                if 'amount' not in ingredient or not isinstance(ingredient['amount'], str):
                    raise Exception(f"Ingredient {i} missing or invalid 'amount' field")
            
            # Validate instructions field
            if 'instructions' not in data or not isinstance(data['instructions'], list):
                raise Exception("Missing or invalid instructions field")
            
            # Validate each instruction
            for i, instruction in enumerate(data['instructions']):
                if not isinstance(instruction, str):
                    raise Exception(f"Instruction {i} is not a string")
            
            return data
            
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse recipe details JSON response: {str(e)}")
            self.logger.error(f"Response text: {response_text}")
            raise Exception("Invalid JSON response from AI model")
        except Exception as e:
            self.logger.error(f"Error parsing recipe details response: {str(e)}")
            raise

    def _parse_analysis_response(self, response_text: str) -> Dict[str, Any]:
        """Parse the meal plan analysis response from Gemini."""
        try:
            # Clean up the response text
            response_text = response_text.strip()
            
            # Find JSON content between ```json and ``` markers
            json_start = response_text.find('```json')
            json_end = response_text.rfind('```')
            
            if json_start != -1 and json_end != -1 and json_end > json_start:
                # Extract JSON content
                json_content = response_text[json_start + 7:json_end].strip()
            else:
                # Try to find JSON object directly
                brace_start = response_text.find('{')
                brace_end = response_text.rfind('}')
                
                if brace_start != -1 and brace_end != -1 and brace_end > brace_start:
                    json_content = response_text[brace_start:brace_end + 1]
                else:
                    json_content = response_text
            
            # Parse JSON
            data = json.loads(json_content)
            
            # Validate the data
            if not isinstance(data, dict):
                raise Exception("Response is not a JSON object")
            
            if 'analysisText' not in data or not isinstance(data['analysisText'], str):
                raise Exception("Missing or invalid analysisText field")
            
            return data
            
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse analysis JSON response: {str(e)}")
            self.logger.error(f"Response text: {response_text}")
            raise Exception("Invalid JSON response from AI model")
        except Exception as e:
            self.logger.error(f"Error parsing analysis response: {str(e)}")
            raise

    def _prepare_meal_plan_for_analysis(self, meal_plan) -> str:
        """Prepare meal plan data for analysis."""
        try:
            # Convert meal plan to the format expected by the analysis prompt
            daily_meals = []
            
            # Group meal plan items by day
            items_by_day = {}
            
            # Use select_related to avoid additional queries
            meal_plan_items = meal_plan.items.select_related('recipe').all()
            
            for item in meal_plan_items:
                day_name = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"][item.day_of_week]
                if day_name not in items_by_day:
                    items_by_day[day_name] = {'breakfast': [], 'lunch': [], 'dinner': []}
                
                meal_data = {
                    'recipeName': item.recipe.name,
                    'ingredients': item.recipe.ingredients if isinstance(item.recipe.ingredients, list) else [],
                    'instructions': item.recipe.instructions or ''
                }
                
                items_by_day[day_name][item.meal_type].append(meal_data)
            
            # Create the weekly meal plan structure
            for day in ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]:
                daily_meals.append({
                    'day': day,
                    'breakfast': items_by_day.get(day, {}).get('breakfast', []),
                    'lunch': items_by_day.get(day, {}).get('lunch', []),
                    'dinner': items_by_day.get(day, {}).get('dinner', [])
                })
            
            return json.dumps(daily_meals, ensure_ascii=False, indent=2)
            
        except Exception as e:
            self.logger.error(f"Error preparing meal plan for analysis: {str(e)}")
            return "[]"

    def _generate_analysis_text(self, request: MealPlanRequest) -> str:
        """Generate analysis text for meal plan."""
        parts = []
        
        if request.dietary_preferences:
            diet_type = request.dietary_preferences.get('dietType')
            if diet_type:
                parts.append(f"Designed for {diet_type} diet")
        
        if request.allergies:
            parts.append(f"Avoids allergens: {', '.join(request.allergies)}")
        
        if request.calorie_target:
            parts.append(f"Target: {request.calorie_target} calories/day")
        
        if not parts:
            parts.append("Balanced weekly meal plan with variety and nutrition")
        
        return '. '.join(parts) + '.'
    
    def _generate_daily_meals(self, request: MealPlanRequest) -> List[Dict[str, Any]]:
        """Generate mock daily meals structure."""
        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        meal_types = ['breakfast', 'lunch', 'dinner']
        
        daily_meals = []
        for i, day in enumerate(days):
            day_meals = {
                'day': day,
                'day_of_week': i,
                'meals': {}
            }
            
            for meal_type in meal_types:
                # This would contain actual recipe recommendations from AI
                day_meals['meals'][meal_type] = {
                    'suggested_recipe_name': f'{meal_type.title()} for {day}',
                    'description': f'AI-suggested {meal_type} recipe',
                    'estimated_prep_time': 15 + (i * 2),
                    'estimated_calories': 300 + (i * 50) if meal_type == 'breakfast' else 500 + (i * 30)
                }
            
            daily_meals.append(day_meals)
        
        return daily_meals
    
    def _generate_mock_ingredients(self, request: RecipeGenerationRequest) -> List[str]:
        """Generate mock ingredients for recipe."""
        base_ingredients = [
            "2 cups all-purpose flour",
            "1 tsp salt",
            "2 tbsp olive oil",
            "1 medium onion, diced",
            "2 cloves garlic, minced"
        ]
        
        if request.meal_type == 'breakfast':
            base_ingredients.extend([
                "2 large eggs",
                "1 cup milk",
                "1 tbsp butter"
            ])
        elif request.meal_type == 'lunch':
            base_ingredients.extend([
                "1 lb protein of choice",
                "2 cups vegetables",
                "1 tbsp seasoning"
            ])
        elif request.meal_type == 'dinner':
            base_ingredients.extend([
                "1 lb main protein",
                "3 cups mixed vegetables",
                "2 tbsp herbs and spices"
            ])
        
        return base_ingredients
    
    def _generate_mock_instructions(self, request: RecipeGenerationRequest) -> str:
        """Generate mock cooking instructions."""
        return f"""
1. Prepare all ingredients by washing, chopping, and measuring as needed.

2. Heat olive oil in a large pan over medium heat. Add diced onion and cook until translucent, about 3-4 minutes.

3. Add minced garlic and cook for another minute until fragrant.

4. [Additional steps would be generated based on the specific recipe type and ingredients]

5. Season with salt and pepper to taste.

6. Serve hot and enjoy your delicious {request.name}!

Note: This is a mock recipe. In production, detailed instructions would be generated by AI based on the specific ingredients and cooking method.
        """.strip()
    
    def _generate_mock_nutrition(self) -> Dict[str, Any]:
        """Generate mock nutrition information."""
        return {
            'calories': 350,
            'protein': '25g',
            'carbohydrates': '30g',
            'fat': '15g',
            'fiber': '5g',
            'sodium': '800mg',
            'sugar': '8g',
            'servings': 4
        }
    
    def _generate_tags(self, request: RecipeGenerationRequest) -> List[str]:
        """Generate tags for recipe."""
        tags = []
        
        if request.meal_type:
            tags.append(request.meal_type)
        
        if request.difficulty:
            tags.append(request.difficulty)
        
        if request.cuisine:
            tags.append(request.cuisine.lower())
        
        if request.dietary_restrictions:
            tags.extend(request.dietary_restrictions)
        
        # Add some default tags
        if request.prep_time and request.prep_time <= 15:
            tags.append('quick')
        
        if request.cook_time and request.cook_time <= 30:
            tags.append('easy')
        
        return list(set(tags))  # Remove duplicates
    
    def _fetch_pexels_image(self, recipe_name: str, cuisine: str = None, ai_query: str = None) -> str:
        """Fetch a relevant food image from Pexels API using AI-generated query."""
        try:
            # Check if Pexels API key is configured
            pexels_api_key = getattr(settings, 'PEXELS_API_KEY', None)
            if not pexels_api_key:
                self.logger.warning("PEXELS_API_KEY not configured, using fallback image")
                return self._get_fallback_image_url()
            
            # Check cache first - include ai_query in cache key for better accuracy
            cache_key = f"pexels_image_{hash(f'{recipe_name}_{ai_query}')}"
            cached_url = cache.get(cache_key)
            if cached_url:
                return cached_url
            
            # Prepare search queries with AI-generated query as primary
            search_queries = []
            
            # Primary: Use AI-generated query if available
            if ai_query and ai_query.strip():
                search_queries.append(ai_query.strip())
            
            # Fallback queries
            search_queries.extend([
                f"{recipe_name} food",  # Secondary: specific recipe
                f"{cuisine} cuisine" if cuisine else "asian food",  # Tertiary: cuisine type
                "delicious food",  # Quaternary: generic food
                "healthy meal",  # Final: healthy food
            ])
            
            headers = {
                'Authorization': pexels_api_key
            }
            
            for query in search_queries:
                try:
                    # Make API request to Pexels
                    response = requests.get(
                        'https://api.pexels.com/v1/search',
                        params={
                            'query': query,
                            'per_page': 15,
                            'orientation': 'landscape',
                            'size': 'medium'
                        },
                        headers=headers,
                        timeout=10
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        photos = data.get('photos', [])
                        
                        if photos:
                            # Get the first suitable image
                            photo = photos[0]
                            # Use medium size for better performance
                            image_url = photo['src']['medium']
                            
                            # Cache the result for 24 hours
                            cache.set(cache_key, image_url, 86400)
                            
                            query_type = "AI-generated" if query == ai_query and ai_query else "fallback"
                            self.logger.info(f"Successfully fetched Pexels image for recipe: {recipe_name} using {query_type} query: '{query}'")
                            return image_url
                    
                    elif response.status_code == 429:
                        self.logger.warning("Pexels API rate limit exceeded")
                        break  # Don't try other queries if rate limited
                    
                    elif response.status_code == 403:
                        self.logger.warning("Pexels API access forbidden - check API key")
                        break
                    
                except requests.RequestException as e:
                    self.logger.warning(f"Request failed for query '{query}': {str(e)}")
                    continue
            
            # If all searches failed, return fallback
            self.logger.warning(f"Failed to fetch Pexels image for recipe: {recipe_name}")
            return self._get_fallback_image_url()
            
        except Exception as e:
            self.logger.error(f"Error fetching Pexels image: {str(e)}")
            return self._get_fallback_image_url()
    
    def _get_fallback_image_url(self) -> str:
        """Get a fallback image URL when Pexels API fails."""
        # Use a reliable placeholder service or a default food image
        # This is a high-quality food image from Pexels that doesn't require API access
        return "https://images.pexels.com/photos/1640777/pexels-photo-1640777.jpeg?auto=compress&cs=tinysrgb&w=400&h=300&fit=crop"
    
    def _generate_recommendations(self, meal_plan, total_recipes: int) -> List[str]:
        """Generate recommendations for meal plan."""
        recommendations = []
        
        if total_recipes < 14:
            recommendations.append("Consider adding more recipe variety to cover all meals for the week")
        
        if total_recipes >= 21:
            recommendations.append("Excellent variety! You have options for all meals and snacks")
        
        recommendations.extend([
            "Include a mix of protein sources throughout the week",
            "Add colorful vegetables to increase nutrient variety",
            "Consider prep-ahead meals for busy weekdays",
            "Include healthy snacks between main meals"
        ])
        
        return recommendations


# Global AI service instance
ai_service = AIService()