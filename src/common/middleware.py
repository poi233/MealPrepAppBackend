"""
Custom middleware for MealPrepAI Django backend.
"""
import logging
from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework.exceptions import AuthenticationFailed

logger = logging.getLogger(__name__)


class JWTAuthenticationMiddleware(MiddlewareMixin):
    """
    Middleware to handle JWT token validation and set user context.
    This middleware runs before view processing to validate JWT tokens
    and set the user context for authenticated requests.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.jwt_auth = JWTAuthentication()
        super().__init__(get_response)
    
    def process_request(self, request):
        """
        Process incoming request to validate JWT token and set user context.
        """
        # Skip authentication for certain paths
        skip_paths = [
            '/api/auth/login/',
            '/api/auth/register/',
            '/api/auth/token/refresh/',
            '/admin/',
            '/health/',
            '/docs/',
            '/static/',
            '/media/',
        ]
        
        # Check if request path should skip authentication
        if any(request.path.startswith(path) for path in skip_paths):
            return None
        
        # Only process requests with Authorization header
        auth_header = request.META.get('HTTP_AUTHORIZATION')
        if not auth_header:
            return None
        
        try:
            # Validate JWT token
            validated_token = self.jwt_auth.get_validated_token(
                self.jwt_auth.get_raw_token(auth_header)
            )
            user = self.jwt_auth.get_user(validated_token)
            
            # Set user in request
            request.user = user
            request.auth = validated_token
            
            logger.debug(f"JWT authentication successful for user: {user.username}")
            
        except (InvalidToken, TokenError, AuthenticationFailed) as e:
            logger.warning(f"JWT authentication failed: {str(e)}")
            # Don't return error here - let the view handle authentication
            # This allows for proper error responses from DRF
            pass
        except Exception as e:
            logger.error(f"Unexpected error in JWT middleware: {str(e)}", exc_info=True)
            pass
        
        return None


class CORSMiddleware(MiddlewareMixin):
    """
    Custom CORS middleware for handling cross-origin requests.
    This provides more control over CORS headers than django-cors-headers.
    """
    
    def process_response(self, request, response):
        """Add CORS headers to response."""
        
        # Get origin from request
        origin = request.META.get('HTTP_ORIGIN')
        
        # Allowed origins
        allowed_origins = [
            'http://localhost:3000',
            'http://localhost:9002',
            'http://127.0.0.1:3000',
            'http://127.0.0.1:9002',
        ]
        
        # Check if origin is allowed
        if origin in allowed_origins:
            response['Access-Control-Allow-Origin'] = origin
            response['Access-Control-Allow-Credentials'] = 'true'
        
        # Add other CORS headers
        response['Access-Control-Allow-Methods'] = 'GET, POST, PUT, PATCH, DELETE, OPTIONS'
        response['Access-Control-Allow-Headers'] = (
            'Accept, Accept-Language, Content-Language, Content-Type, '
            'Authorization, X-Requested-With, X-CSRFToken'
        )
        response['Access-Control-Max-Age'] = '86400'  # 24 hours
        
        return response


class RequestLoggingMiddleware(MiddlewareMixin):
    """
    Middleware to log API requests for debugging and monitoring.
    """
    
    def process_request(self, request):
        """Log incoming request details."""
        if request.path.startswith('/api/'):
            logger.info(
                f"API Request: {request.method} {request.path} "
                f"from {request.META.get('REMOTE_ADDR', 'unknown')} "
                f"User: {getattr(request.user, 'username', 'anonymous')}"
            )
        return None
    
    def process_response(self, request, response):
        """Log response status for API requests."""
        if request.path.startswith('/api/'):
            logger.info(
                f"API Response: {request.method} {request.path} "
                f"Status: {response.status_code}"
            )
        return response


class SecurityHeadersMiddleware(MiddlewareMixin):
    """
    Middleware to add security headers to responses.
    """
    
    def process_response(self, request, response):
        """Add security headers to response."""
        
        # Content Security Policy
        response['Content-Security-Policy'] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self' https:; "
            "connect-src 'self' https:;"
        )
        
        # Other security headers
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        response['X-XSS-Protection'] = '1; mode=block'
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        
        # HSTS header for HTTPS
        if request.is_secure():
            response['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        
        return response