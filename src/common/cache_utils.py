"""
Advanced caching utilities for MealPrepAI Django backend.
Implements intelligent caching strategies with performance optimization.
"""
import logging
import hashlib
import json
import time
from typing import Any, Optional, Dict, List, Callable
from functools import wraps
from django.core.cache import cache
from django.conf import settings
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class CacheConfig:
    """Centralized cache configuration."""
    
    # Cache TTL values (in seconds)
    SHORT_TTL = 300      # 5 minutes
    MEDIUM_TTL = 1800    # 30 minutes
    LONG_TTL = 3600      # 1 hour
    EXTENDED_TTL = 7200  # 2 hours
    MAX_TTL = 86400      # 24 hours
    
    # Cache key prefixes
    PREFIX_RECIPE = "recipe"
    PREFIX_AI = "ai"
    PREFIX_USER = "user"
    PREFIX_MEAL_PLAN = "meal_plan"
    PREFIX_RATE_LIMIT = "rate_limit"
    PREFIX_IMAGE = "image"
    
    # Cache strategies
    STRATEGY_LRU = "lru"
    STRATEGY_TTL = "ttl"
    STRATEGY_ADAPTIVE = "adaptive"


class SmartCacheKey:
    """Generate intelligent cache keys with collision resistance."""
    
    @staticmethod
    def generate(prefix: str, *args, **kwargs) -> str:
        """Generate a cache key with hash collision resistance."""
        # Create deterministic string from arguments
        key_parts = [str(arg) for arg in args]
        key_parts.extend([f"{k}:{v}" for k, v in sorted(kwargs.items())])
        
        # Create content hash for long keys
        content = "|".join(key_parts)
        if len(content) > 200:  # Use hash for long keys
            content_hash = hashlib.sha256(content.encode()).hexdigest()[:16]
            return f"{prefix}:hash:{content_hash}"
        else:
            # Use direct content for short keys (more readable)
            safe_content = content.replace(" ", "_").replace(":", "_")
            return f"{prefix}:{safe_content}"
    
    @staticmethod
    def generate_versioned(prefix: str, version: str, *args, **kwargs) -> str:
        """Generate a versioned cache key."""
        base_key = SmartCacheKey.generate(prefix, *args, **kwargs)
        return f"{base_key}:v{version}"


class AdaptiveTTL:
    """Calculate adaptive TTL based on content complexity and usage patterns."""
    
    @staticmethod
    def calculate(content: Any, base_ttl: int = CacheConfig.MEDIUM_TTL) -> int:
        """Calculate TTL based on content complexity."""
        complexity_score = AdaptiveTTL._calculate_complexity(content)
        usage_factor = AdaptiveTTL._calculate_usage_factor()
        
        # Adjust TTL based on complexity (more complex = longer cache)
        adaptive_multiplier = min(2.0, 1 + (complexity_score * 0.5))
        
        # Adjust based on system usage (higher usage = longer cache)
        usage_multiplier = min(1.5, 1 + (usage_factor * 0.3))
        
        final_ttl = int(base_ttl * adaptive_multiplier * usage_multiplier)
        return min(final_ttl, CacheConfig.MAX_TTL)
    
    @staticmethod
    def _calculate_complexity(content: Any) -> float:
        """Calculate content complexity score (0.0 to 1.0)."""
        if isinstance(content, dict):
            # Dictionary complexity based on size and nesting
            size_score = min(1.0, len(content) / 100)
            nesting_score = AdaptiveTTL._calculate_nesting_depth(content) / 10
            return min(1.0, size_score + nesting_score)
        elif isinstance(content, list):
            # List complexity based on length and item complexity
            length_score = min(1.0, len(content) / 50)
            if content:
                item_complexity = AdaptiveTTL._calculate_complexity(content[0])
                return min(1.0, length_score + item_complexity * 0.3)
            return length_score
        elif isinstance(content, str):
            # String complexity based on length
            return min(1.0, len(content) / 1000)
        else:
            return 0.1  # Simple types have low complexity
    
    @staticmethod
    def _calculate_nesting_depth(obj: Any, current_depth: int = 0) -> int:
        """Calculate maximum nesting depth of data structure."""
        if current_depth > 10:  # Prevent infinite recursion
            return current_depth
        
        if isinstance(obj, dict):
            if not obj:
                return current_depth
            return max(
                AdaptiveTTL._calculate_nesting_depth(v, current_depth + 1)
                for v in obj.values()
            )
        elif isinstance(obj, list):
            if not obj:
                return current_depth
            return max(
                AdaptiveTTL._calculate_nesting_depth(item, current_depth + 1)
                for item in obj
            )
        else:
            return current_depth
    
    @staticmethod
    def _calculate_usage_factor() -> float:
        """Calculate system usage factor (0.0 to 1.0)."""
        # This could be enhanced with actual system metrics
        # For now, return a moderate usage factor
        return 0.5


class CacheStats:
    """Track cache performance statistics."""
    
    @staticmethod
    def record_hit(cache_key: str):
        """Record cache hit."""
        stats_key = f"cache_stats:hits:{datetime.now().strftime('%Y%m%d%H')}"
        cache.set(stats_key, cache.get(stats_key, 0) + 1, 3600)
    
    @staticmethod
    def record_miss(cache_key: str):
        """Record cache miss."""
        stats_key = f"cache_stats:misses:{datetime.now().strftime('%Y%m%d%H')}"
        cache.set(stats_key, cache.get(stats_key, 0) + 1, 3600)
    
    @staticmethod
    def get_hit_ratio() -> float:
        """Get current cache hit ratio."""
        hour = datetime.now().strftime('%Y%m%d%H')
        hits = cache.get(f"cache_stats:hits:{hour}", 0)
        misses = cache.get(f"cache_stats:misses:{hour}", 0)
        
        total = hits + misses
        return hits / total if total > 0 else 0.0


def smart_cache(
    prefix: str,
    ttl: Optional[int] = None,
    adaptive: bool = True,
    version: Optional[str] = None,
    key_generator: Optional[Callable] = None
):
    """
    Advanced caching decorator with intelligent features.
    
    Args:
        prefix: Cache key prefix
        ttl: Time to live in seconds (None for adaptive TTL)
        adaptive: Whether to use adaptive TTL calculation
        version: Cache version for invalidation
        key_generator: Custom key generation function
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            if key_generator:
                cache_key = key_generator(*args, **kwargs)
            elif version:
                cache_key = SmartCacheKey.generate_versioned(prefix, version, *args, **kwargs)
            else:
                cache_key = SmartCacheKey.generate(prefix, *args, **kwargs)
            
            # Try to get from cache
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                CacheStats.record_hit(cache_key)
                logger.debug(f"Cache hit for key: {cache_key}")
                return cached_result
            
            # Cache miss - execute function
            CacheStats.record_miss(cache_key)
            logger.debug(f"Cache miss for key: {cache_key}")
            
            start_time = time.time()
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time
            
            # Calculate TTL
            if ttl is not None:
                final_ttl = ttl
            elif adaptive:
                final_ttl = AdaptiveTTL.calculate(result)
            else:
                final_ttl = CacheConfig.MEDIUM_TTL
            
            # Cache the result
            cache.set(cache_key, result, final_ttl)
            
            logger.debug(
                f"Cached result for key: {cache_key}, "
                f"TTL: {final_ttl}s, "
                f"Execution time: {execution_time:.3f}s"
            )
            
            return result
        
        return wrapper
    return decorator


class CacheInvalidator:
    """Handle intelligent cache invalidation."""
    
    @staticmethod
    def invalidate_pattern(pattern: str):
        """Invalidate all cache keys matching a pattern."""
        # Note: This is a simplified implementation
        # In production, consider using Redis with SCAN for better performance
        pass
    
    @staticmethod
    def invalidate_user_cache(user_id: str):
        """Invalidate all cache entries for a specific user."""
        pattern = f"{CacheConfig.PREFIX_USER}:*{user_id}*"
        CacheInvalidator.invalidate_pattern(pattern)
    
    @staticmethod
    def invalidate_recipe_cache(recipe_id: str):
        """Invalidate all cache entries for a specific recipe."""
        pattern = f"{CacheConfig.PREFIX_RECIPE}:*{recipe_id}*"
        CacheInvalidator.invalidate_pattern(pattern)


class WarmupManager:
    """Manage cache warmup strategies."""
    
    @staticmethod
    async def warmup_popular_recipes():
        """Warm up cache for popular recipes."""
        # This would fetch and cache popular recipes
        # Implementation depends on your analytics data
        pass
    
    @staticmethod
    async def warmup_user_data(user_id: str):
        """Warm up cache for user-specific data."""
        # This would pre-fetch and cache user's favorite recipes, meal plans, etc.
        pass


# Convenience functions for common caching patterns

def cache_recipe(ttl: int = CacheConfig.LONG_TTL):
    """Cache decorator specifically for recipes."""
    return smart_cache(CacheConfig.PREFIX_RECIPE, ttl=ttl, adaptive=True)


def cache_ai_response(ttl: int = CacheConfig.EXTENDED_TTL):
    """Cache decorator specifically for AI responses."""
    return smart_cache(CacheConfig.PREFIX_AI, ttl=ttl, adaptive=True)


def cache_user_data(ttl: int = CacheConfig.MEDIUM_TTL):
    """Cache decorator specifically for user data."""
    return smart_cache(CacheConfig.PREFIX_USER, ttl=ttl, adaptive=False)


def cache_meal_plan(ttl: int = CacheConfig.LONG_TTL):
    """Cache decorator specifically for meal plans."""
    return smart_cache(CacheConfig.PREFIX_MEAL_PLAN, ttl=ttl, adaptive=True)


# Cache monitoring utilities

def get_cache_health() -> Dict[str, Any]:
    """Get cache system health information."""
    return {
        'hit_ratio': CacheStats.get_hit_ratio(),
        'timestamp': datetime.now().isoformat(),
        'status': 'healthy' if CacheStats.get_hit_ratio() > 0.5 else 'degraded'
    }


def cache_maintenance():
    """Perform cache maintenance tasks."""
    # Clear expired entries, update statistics, etc.
    logger.info("Performing cache maintenance")
    
    # Get cache health
    health = get_cache_health()
    logger.info(f"Cache health: {health}")
    
    # Additional maintenance tasks can be added here