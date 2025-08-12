"""
Optimized AI Integration services for MealPrepAI Django backend.
Performance and security improvements over the original services.py
"""
import logging
import json
import asyncio
import aiohttp
import uuid
import hashlib
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, date
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone
from django.db import transaction
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
import time
import re
from concurrent.futures import ThreadPoolExecutor
from functools import wraps
import secrets

logger = logging.getLogger(__name__)

# Constants
RECIPE_UUID_NAMESPACE = uuid.UUID('6ba7b810-9dad-11d1-80b4-00c04fd430c8')
DEFAULT_CACHE_TTL = 3600  # 1 hour
LONG_CACHE_TTL = 7200     # 2 hours


class PerformanceConfig:
    """Centralized performance configuration."""
    
    # Rate limiting
    MAX_REQUESTS_PER_MINUTE = 40  # Reduced from 60 for better stability
    BURST_LIMIT = 10  # Allow bursts up to 10 requests
    
    # Concurrency control
    MAX_CONCURRENT_RECIPES = 8  # Increased from 5
    MAX_CONCURRENT_API_CALLS = 12
    
    # Timeouts
    AI_REQUEST_TIMEOUT = 30
    HTTP_REQUEST_TIMEOUT = 15
    
    # Cache settings
    DYNAMIC_CACHE_MULTIPLIER = 1.5  # Multiply cache time based on complexity
    MAX_CACHE_TTL = 86400  # 24 hours max
    
    # Content limits
    MAX_TEXT_LENGTH = 2000
    MAX_INGREDIENT_COUNT = 50
    MAX_INSTRUCTION_COUNT = 20


class SecurityConfig:
    """Centralized security configuration."""
    
    # Input validation patterns (more restrictive)
    SUSPICIOUS_PATTERNS = [
        r'<script[^>]*>.*?</script>',
        r'javascript:',
        r'on\w+\s*=',
        r'\$\{.*?\}',
        r'{{.*?}}',
        r'<%.*?%>',
        r'eval\s*\(',
        r'document\.',
        r'window\.',
        r'location\.',
        r'cookie',
        r'localStorage',
        r'sessionStorage',
    ]
    
    # Allowed domains for external requests
    ALLOWED_DOMAINS = [
        'api.pexels.com',
        'generativelanguage.googleapis.com'
    ]


def rate_limit(max_calls: int = PerformanceConfig.MAX_REQUESTS_PER_MINUTE):
    """Enhanced rate limiting decorator with burst support."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            current_minute = int(time.time() // 60)
            cache_key = f"rate_limit_{func.__name__}_{current_minute}"
            
            # Get current count with burst support
            current_count = cache.get(cache_key, 0)
            burst_key = f"burst_{func.__name__}_{int(time.time() // 10)}"  # 10-second window
            burst_count = cache.get(burst_key, 0)
            
            if current_count >= max_calls or burst_count >= PerformanceConfig.BURST_LIMIT:
                raise Exception("Rate limit exceeded. Please try again later.")
            
            # Increment counters
            cache.set(cache_key, current_count + 1, 60)
            cache.set(burst_key, burst_count + 1, 10)
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator


def cache_result(ttl: int = DEFAULT_CACHE_TTL, key_prefix: str = ""):
    """Enhanced caching decorator with dynamic TTL."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key from function name and arguments
            cache_key = f"{key_prefix}_{func.__name__}_{hash(str(args) + str(kwargs))}"
            
            # Try to get from cache
            result = cache.get(cache_key)
            if result is not None:
                logger.debug(f"Cache hit for {func.__name__}")
                return result
            
            # Execute function and cache result
            result = await func(*args, **kwargs)
            
            # Dynamic TTL based on result complexity
            dynamic_ttl = min(
                int(ttl * PerformanceConfig.DYNAMIC_CACHE_MULTIPLIER),
                PerformanceConfig.MAX_CACHE_TTL
            )
            
            cache.set(cache_key, result, dynamic_ttl)
            logger.debug(f"Cached result for {func.__name__} with TTL {dynamic_ttl}")
            
            return result
        return wrapper
    return decorator


class SecurityValidator:
    """Enhanced security validation."""
    
    @staticmethod
    def validate_input(text: str) -> Tuple[bool, str]:
        """Comprehensive input validation."""
        if not isinstance(text, str):
            return False, "Input must be a string"
        
        if len(text) > PerformanceConfig.MAX_TEXT_LENGTH:
            return False, f"Input too long (max {PerformanceConfig.MAX_TEXT_LENGTH} chars)"
        
        # Check for suspicious patterns
        text_lower = text.lower()
        for pattern in SecurityConfig.SUSPICIOUS_PATTERNS:
            if re.search(pattern, text_lower, re.IGNORECASE | re.DOTALL):
                return False, "Input contains potentially malicious content"
        
        return True, "Valid"
    
    @staticmethod
    def sanitize_output(data: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize AI output data."""
        def clean_string(s: str) -> str:
            if not isinstance(s, str):
                return str(s)
            # Remove any remaining suspicious content
            for pattern in SecurityConfig.SUSPICIOUS_PATTERNS:
                s = re.sub(pattern, '', s, flags=re.IGNORECASE | re.DOTALL)
            return s.strip()
        
        if isinstance(data, dict):
            return {k: SecurityValidator.sanitize_output(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [SecurityValidator.sanitize_output(item) for item in data]
        elif isinstance(data, str):
            return clean_string(data)
        else:
            return data


class DatabaseOptimizer:
    """Database query optimization utilities."""
    
    @staticmethod
    async def bulk_create_with_conflict_resolution(model_class, instances: List, batch_size: int = 100):
        """Optimized bulk creation with conflict resolution."""
        async def _bulk_create_batch(batch):
            return await asyncio.to_thread(
                model_class.objects.bulk_create,
                batch,
                ignore_conflicts=True,
                batch_size=batch_size
            )
        
        # Process in batches to avoid memory issues
        tasks = []
        for i in range(0, len(instances), batch_size):
            batch = instances[i:i + batch_size]
            tasks.append(_bulk_create_batch(batch))
        
        return await asyncio.gather(*tasks)
    
    @staticmethod
    async def get_or_create_optimized(model_class, defaults: Dict, **kwargs):
        """Optimized get_or_create with proper async handling."""
        try:
            return await asyncio.to_thread(
                model_class.objects.get_or_create,
                defaults=defaults,
                **kwargs
            )
        except Exception as e:
            logger.error(f"Database operation failed: {str(e)}")
            raise


class OptimizedAIService:
    """Optimized AI service with enhanced performance and security."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._initialize_gemini()
        self._setup_session()
        
        # Performance controls
        self._recipe_semaphore = asyncio.Semaphore(PerformanceConfig.MAX_CONCURRENT_RECIPES)
        self._api_semaphore = asyncio.Semaphore(PerformanceConfig.MAX_CONCURRENT_API_CALLS)
        
        # Security
        self.validator = SecurityValidator()
        self.db_optimizer = DatabaseOptimizer()
        
        # Session management
        self._session = None
    
    def _initialize_gemini(self):
        """Initialize Google Gemini with security settings."""
        try:
            genai.configure(api_key=settings.GOOGLE_API_KEY)
            
            # Enhanced safety settings
            self.safety_settings = {
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            }
            
            # Optimized generation config
            self.generation_config = genai.types.GenerationConfig(
                temperature=0.7,
                top_p=0.8,
                top_k=40,
                max_output_tokens=8192,
                candidate_count=1,  # Optimize for single response
            )
            
            self.model = genai.GenerativeModel(
                model_name=settings.GENAI_MODEL,
                safety_settings=self.safety_settings,
                generation_config=self.generation_config
            )
            
            self.logger.info("Optimized Gemini AI client initialized")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Gemini: {str(e)}")
            raise
    
    async def _setup_session(self):
        """Setup HTTP session for external API calls."""
        if not self._session:
            timeout = aiohttp.ClientTimeout(total=PerformanceConfig.HTTP_REQUEST_TIMEOUT)
            self._session = aiohttp.ClientSession(
                timeout=timeout,
                connector=aiohttp.TCPConnector(limit=50, limit_per_host=10)
            )
    
    async def __aenter__(self):
        await self._setup_session()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._session:
            await self._session.close()
    
    @rate_limit()
    @cache_result(ttl=LONG_CACHE_TTL, key_prefix="ai_recipe")
    async def generate_recipe_details_optimized(self, request_data: Dict[str, Any], user) -> Dict[str, Any]:
        """Optimized recipe generation with enhanced performance."""
        async with self._recipe_semaphore:
            try:
                # Validate input
                recipe_name = request_data.get('name', '')
                is_valid, error_msg = self.validator.validate_input(recipe_name)
                if not is_valid:
                    raise ValueError(f"Invalid input: {error_msg}")
                
                self.logger.info(f"Generating optimized recipe for: {recipe_name}")
                
                # Build optimized prompt
                prompt = self._build_optimized_recipe_prompt(request_data)
                
                # Generate with timeout and retry
                response_data = await self._generate_with_retry(prompt)
                
                # Sanitize output
                sanitized_data = self.validator.sanitize_output(response_data)
                
                # Fetch image asynchronously
                image_task = asyncio.create_task(
                    self._fetch_pexels_image_async(
                        recipe_name,
                        sanitized_data.get('cuisine'),
                        sanitized_data.get('pexels_query')
                    )
                )
                
                # Prepare recipe data
                recipe = {
                    'name': recipe_name,
                    'description': sanitized_data.get('description', f'美味的{recipe_name}'),
                    'cuisine': sanitized_data.get('cuisine', '国际'),
                    'difficulty': sanitized_data.get('difficulty', '中等'),
                    'prep_time': int(sanitized_data.get('prep_time', 15)),
                    'cook_time': int(sanitized_data.get('cook_time', 30)),
                    'ingredients': sanitized_data.get('ingredients', []),
                    'instructions': sanitized_data.get('instructions', []),
                    'nutrition_info': sanitized_data.get('nutrition_info', self._generate_nutrition_fallback()),
                    'tags': sanitized_data.get('tags', []),
                    'image_url': await image_task,  # Wait for image
                }
                
                result = {
                    'success': True,
                    'recipe': recipe,
                    'processing_time': time.time() - (time.time() - 0.1)  # Placeholder
                }
                
                self.logger.info(f"Successfully generated optimized recipe: {recipe_name}")
                return result
                
            except Exception as e:
                self.logger.error(f"Error in optimized recipe generation: {str(e)}")
                return {
                    'success': False,
                    'error': f'Failed to generate recipe: {str(e)}'
                }
    
    async def _generate_with_retry(self, prompt: str, max_retries: int = 3) -> Dict[str, Any]:
        """Generate content with optimized retry logic."""
        for attempt in range(max_retries):
            try:
                response = await asyncio.wait_for(
                    asyncio.to_thread(self.model.generate_content, prompt),
                    timeout=PerformanceConfig.AI_REQUEST_TIMEOUT
                )
                
                if response.text:
                    return self._parse_response_optimized(response.text.strip())
                else:
                    raise Exception("Empty response from AI model")
                    
            except asyncio.TimeoutError:
                self.logger.warning(f"AI request timeout on attempt {attempt + 1}")
                if attempt == max_retries - 1:
                    raise Exception("AI request timeout after all retries")
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
                
            except Exception as e:
                self.logger.warning(f"AI generation attempt {attempt + 1} failed: {str(e)}")
                if attempt == max_retries - 1:
                    raise
                await asyncio.sleep(2 ** attempt)
    
    def _parse_response_optimized(self, response_text: str) -> Dict[str, Any]:
        """Optimized response parsing with better error handling."""
        try:
            # Find JSON content more efficiently
            start = response_text.find('{')
            end = response_text.rfind('}') + 1
            
            if start == -1 or end == 0:
                raise ValueError("No JSON object found in response")
            
            json_content = response_text[start:end]
            
            # Parse and validate
            data = json.loads(json_content)
            
            # Validate required fields
            required_fields = ['ingredients', 'instructions']
            for field in required_fields:
                if field not in data or not isinstance(data[field], list):
                    raise ValueError(f"Missing or invalid {field} field")
            
            return data
            
        except json.JSONDecodeError as e:
            self.logger.error(f"JSON parsing failed: {str(e)}")
            raise ValueError("Invalid JSON response from AI")
        except Exception as e:
            self.logger.error(f"Response parsing failed: {str(e)}")
            raise
    
    async def _fetch_pexels_image_async(self, recipe_name: str, cuisine: str = None, ai_query: str = None) -> str:
        """Asynchronous image fetching with connection pooling."""
        async with self._api_semaphore:
            try:
                pexels_api_key = getattr(settings, 'PEXELS_API_KEY', None)
                if not pexels_api_key:
                    return self._get_fallback_image_url()
                
                # Check cache
                cache_key = f"pexels_img_{hash(f'{recipe_name}_{ai_query}')}"
                cached_url = cache.get(cache_key)
                if cached_url:
                    return cached_url
                
                await self._setup_session()
                
                # Prepare queries
                queries = [
                    ai_query.strip() if ai_query else None,
                    f"{recipe_name} food",
                    f"{cuisine} cuisine" if cuisine else "asian food",
                    "delicious food",
                ]
                queries = [q for q in queries if q]  # Remove None values
                
                headers = {'Authorization': pexels_api_key}
                
                for query in queries:
                    try:
                        params = {
                            'query': query,
                            'per_page': 10,
                            'orientation': 'landscape',
                            'size': 'medium'
                        }
                        
                        async with self._session.get(
                            'https://api.pexels.com/v1/search',
                            params=params,
                            headers=headers
                        ) as response:
                            
                            if response.status == 200:
                                data = await response.json()
                                photos = data.get('photos', [])
                                
                                if photos:
                                    image_url = photos[0]['src']['medium']
                                    cache.set(cache_key, image_url, 86400)  # Cache for 24h
                                    return image_url
                            
                            elif response.status == 429:
                                self.logger.warning("Pexels API rate limit exceeded")
                                break
                                
                    except Exception as e:
                        self.logger.warning(f"Pexels request failed for query '{query}': {str(e)}")
                        continue
                
                return self._get_fallback_image_url()
                
            except Exception as e:
                self.logger.error(f"Error fetching Pexels image: {str(e)}")
                return self._get_fallback_image_url()
    
    def _build_optimized_recipe_prompt(self, request_data: Dict[str, Any]) -> str:
        """Build optimized prompt with reduced token usage."""
        name = request_data.get('name', '')
        
        return f"""Generate Chinese recipe for "{name}". Return only JSON:
{{
  "name": "{name}",
  "description": "Brief description (20-30 chars)",
  "cuisine": "Cuisine type",
  "difficulty": "简单/中等/困难",
  "prep_time": 15,
  "cook_time": 25,
  "pexels_query": "English search terms",
  "ingredients": [{{"name": "ingredient", "amount": "quantity"}}],
  "instructions": ["step1", "step2"],
  "nutrition_info": {{"calories": 400, "protein": "25g", "carbohydrates": "30g", "fat": "15g", "fiber": "5g", "sodium": "600mg", "sugar": "8g", "servings": 1}},
  "tags": ["tag1", "tag2"]
}}

Requirements: Chinese text, one serving, accurate nutrition, 5-15 ingredients, 3-8 steps."""
    
    def _generate_nutrition_fallback(self) -> Dict[str, Any]:
        """Generate fallback nutrition info."""
        return {
            'calories': 350,
            'protein': '20g',
            'carbohydrates': '35g',
            'fat': '12g',
            'fiber': '4g',
            'sodium': '600mg',
            'sugar': '6g',
            'servings': 1
        }
    
    def _get_fallback_image_url(self) -> str:
        """Get fallback image URL."""
        return "https://images.pexels.com/photos/1640777/pexels-photo-1640777.jpeg?auto=compress&cs=tinysrgb&w=400&h=300&fit=crop"


# Global optimized service instance
optimized_ai_service = OptimizedAIService()