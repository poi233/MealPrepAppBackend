"""
Django WSGI handler for Vercel deployment.
This handles all Django API routes.
"""
import os
import sys
import io
import json
from pathlib import Path
from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

# Add the src directory to Python path
BASE_DIR = Path(__file__).resolve().parent.parent
src_path = BASE_DIR / 'src'
sys.path.insert(0, str(src_path))

# Set Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mealprep_project.settings.production')

# Initialize Django with error handling
django_app = None
setup_error = None

try:
    import django
    from django.core.wsgi import get_wsgi_application
    
    # Setup Django
    django.setup()
    django_app = get_wsgi_application()
    
except Exception as e:
    setup_error = e

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self._handle_request()
    
    def do_POST(self):
        self._handle_request()
    
    def do_PUT(self):
        self._handle_request()
    
    def do_PATCH(self):
        self._handle_request()
    
    def do_DELETE(self):
        self._handle_request()
    
    def do_OPTIONS(self):
        self._handle_request()
    
    def _handle_request(self):
        """Handle all HTTP methods through Django WSGI."""
        try:
            if setup_error:
                # Django setup failed
                self._send_error_response({
                    'error': 'Django setup failed',
                    'details': str(setup_error),
                    'error_type': type(setup_error).__name__
                })
                return
            
            # Parse URL
            parsed_url = urlparse(self.path)
            path_info = parsed_url.path
            query_string = parsed_url.query
            
            # Read request body
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length) if content_length > 0 else b''
            
            # Create WSGI environ dictionary
            environ = {
                'REQUEST_METHOD': self.command,
                'PATH_INFO': path_info,
                'QUERY_STRING': query_string,
                'CONTENT_TYPE': self.headers.get('Content-Type', ''),
                'CONTENT_LENGTH': str(len(body)),
                'SERVER_NAME': 'meal-prep-app-backend.vercel.app',
                'SERVER_PORT': '443',
                'SERVER_PROTOCOL': 'HTTP/1.1',
                'wsgi.version': (1, 0),
                'wsgi.url_scheme': 'https',
                'wsgi.input': io.BytesIO(body),
                'wsgi.errors': sys.stderr,
                'wsgi.multithread': False,
                'wsgi.multiprocess': True,
                'wsgi.run_once': False,
            }
            
            # Add HTTP headers to environ
            for header, value in self.headers.items():
                key = header.upper().replace('-', '_')
                if key not in ('CONTENT_TYPE', 'CONTENT_LENGTH'):
                    key = 'HTTP_' + key
                environ[key] = value
            
            # Capture the response
            response_data = {'status': 200, 'headers': [], 'body': b''}
            
            def start_response(status, response_headers, exc_info=None):
                response_data['status'] = int(status.split()[0])
                response_data['headers'] = response_headers
            
            # Call Django WSGI application
            response_body = django_app(environ, start_response)
            
            # Collect response body
            body_parts = []
            for part in response_body:
                body_parts.append(part)
            
            response_data['body'] = b''.join(body_parts)
            
            # Close the response if it has a close method
            if hasattr(response_body, 'close'):
                response_body.close()
            
            # Send response
            self.send_response(response_data['status'])
            
            # Send headers
            for header_name, header_value in response_data['headers']:
                self.send_header(header_name, header_value)
            
            self.end_headers()
            
            # Send body
            self.wfile.write(response_data['body'])
            
        except Exception as e:
            import traceback
            self._send_error_response({
                'error': str(e),
                'error_type': type(e).__name__,
                'traceback': traceback.format_exc(),
                'request_info': {
                    'method': self.command,
                    'path': self.path,
                }
            })
    
    def _send_error_response(self, error_data):
        """Send a JSON error response."""
        try:
            response_body = json.dumps(error_data, indent=2).encode('utf-8')
            
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Content-Length', str(len(response_body)))
            self.end_headers()
            
            self.wfile.write(response_body)
        except Exception as e:
            # Fallback error response
            fallback_response = f'{{"error": "Failed to send error response: {str(e)}"}}'.encode('utf-8')
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(fallback_response)))
            self.end_headers()
            self.wfile.write(fallback_response)
    
    def log_message(self, format, *args):
        """Override to prevent default logging."""
        pass