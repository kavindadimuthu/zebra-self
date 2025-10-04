#!/usr/bin/env python3
"""HTTP Web Server for Project Sentinel Dashboard.

Handles HTTP requests, serves static files, and routes API calls
to the appropriate endpoints.
"""

import json
import logging
import mimetypes
import threading
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from typing import Dict, Any, Optional
from urllib.parse import urlparse, parse_qs

from .api.endpoints import DashboardAPI

logger = logging.getLogger(__name__)


class DashboardRequestHandler(BaseHTTPRequestHandler):
    """HTTP request handler for the dashboard web server."""
    
    def __init__(self, api_handler: DashboardAPI, *args, **kwargs):
        self.api = api_handler
        super().__init__(*args, **kwargs)
    
    def do_GET(self):
        """Handle GET requests for static files and API endpoints."""
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        
        try:
            # Static files
            if path == '/' or path == '/index.html':
                self._serve_static_file('templates/index.html')
            elif path == '/styles.css':
                self._serve_static_file('static/css/styles.css')
            elif path == '/dashboard.js':
                self._serve_static_file('static/js/dashboard.js')
            elif path.startswith('/static/'):
                # Serve any static file
                static_path = path[1:]  # Remove leading slash
                self._serve_static_file(static_path)
            
            # API endpoints
            elif path == '/api/dashboard-data':
                self._serve_json(self.api.get_dashboard_data())
            elif path == '/api/alerts':
                query_params = parse_qs(parsed_path.query)
                limit = int(query_params.get('limit', [50])[0])
                severity = query_params.get('severity', [None])[0]
                alerts = self.api.get_recent_alerts(limit=limit, severity=severity)
                self._serve_json({'alerts': alerts})
            elif path == '/api/events':
                query_params = parse_qs(parsed_path.query)
                limit = int(query_params.get('limit', [100])[0])
                station_id = query_params.get('station_id', [None])[0]
                event_type = query_params.get('event_type', [None])[0]
                events = self.api.get_all_events(limit=limit, station_id=station_id, event_type=event_type)
                self._serve_json({'events': events})
            elif path == '/api/stations':
                self._serve_json(self.api.get_stations_data())
            elif path == '/api/system-status':
                self._serve_json(self.api.get_system_data())
            elif path == '/api/metrics':
                self._serve_json(self.api.get_metrics_data())
            elif path == '/api/queue':
                self._serve_json(self.api.get_queue_data())
            elif path == '/api/charts':
                self._serve_json(self.api.get_chart_data())
            elif path == '/events' or path == '/events.html':
                self._serve_static_file('templates/events.html')
            elif path.startswith('/api/'):
                self._send_error(404, "API endpoint not found")
            else:
                self._send_error(404, "File not found")
                
        except Exception as e:
            logger.error(f"Error handling request {path}: {e}")
            self._send_error(500, str(e))
    
    def _serve_static_file(self, relative_path: str):
        """Serve static files from the web_dashboard directory."""
        dashboard_dir = Path(__file__).parent
        file_path = dashboard_dir / relative_path
        
        if not file_path.exists():
            self._send_error(404, f"File {relative_path} not found")
            return
        
        # Determine content type
        content_type, _ = mimetypes.guess_type(str(file_path))
        if content_type is None:
            if relative_path.endswith('.html'):
                content_type = 'text/html'
            elif relative_path.endswith('.css'):
                content_type = 'text/css'
            elif relative_path.endswith('.js'):
                content_type = 'application/javascript'
            else:
                content_type = 'text/plain'
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            self.send_response(200)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(content.encode('utf-8'))))
            self.send_header('Cache-Control', 'no-cache')
            self.end_headers()
            self.wfile.write(content.encode('utf-8'))
            
        except Exception as e:
            logger.error(f"Error serving file {relative_path}: {e}")
            self._send_error(500, f"Error reading file: {e}")
    
    def _serve_json(self, data: Dict[str, Any]):
        """Send JSON response."""
        try:
            json_data = json.dumps(data, default=str)
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(json_data.encode('utf-8'))))
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Cache-Control', 'no-cache')
            self.end_headers()
            self.wfile.write(json_data.encode('utf-8'))
            
        except Exception as e:
            logger.error(f"Error sending JSON response: {e}")
            self._send_error(500, f"Error encoding JSON: {e}")
    
    def _send_error(self, code: int, message: str):
        """Send error response."""
        try:
            self.send_response(code)
            self.send_header('Content-Type', 'text/plain')
            self.end_headers()
            self.wfile.write(message.encode('utf-8'))
        except Exception:
            pass  # Best effort error handling
    
    def log_message(self, format, *args):
        """Override to use our logger."""
        logger.info(f"{self.address_string()} - {format % args}")


class DashboardWebServer:
    """Web server for the Project Sentinel dashboard."""
    
    def __init__(self, detection_engine, host: str = 'localhost', port: int = 8080):
        self.host = host
        self.port = port
        self.api = DashboardAPI(detection_engine)
        self.server: Optional[HTTPServer] = None
        self.server_thread: Optional[threading.Thread] = None
        self.running = False
    
    def start(self) -> None:
        """Start the web server."""
        if self.running:
            logger.warning("Web server is already running")
            return
        
        try:
            # Create handler class with API
            handler_class = lambda *args, **kwargs: DashboardRequestHandler(self.api, *args, **kwargs)
            
            # Create and start server
            self.server = HTTPServer((self.host, self.port), handler_class)
            self.server_thread = threading.Thread(target=self._run_server, daemon=True)
            self.server_thread.start()
            
            self.running = True
            logger.info(f"Dashboard web server started at http://{self.host}:{self.port}")
            
        except Exception as e:
            logger.error(f"Failed to start web server: {e}")
            raise
    
    def stop(self) -> None:
        """Stop the web server."""
        if not self.running:
            return
        
        try:
            if self.server:
                self.server.shutdown()
                self.server.server_close()
            
            if self.server_thread and self.server_thread.is_alive():
                self.server_thread.join(timeout=5)
            
            self.running = False
            logger.info("Dashboard web server stopped")
            
        except Exception as e:
            logger.error(f"Error stopping web server: {e}")
    
    def get_url(self) -> str:
        """Get the server URL."""
        return f"http://{self.host}:{self.port}"
    
    def _run_server(self) -> None:
        """Run the HTTP server in a separate thread."""
        try:
            self.server.serve_forever()
        except Exception as e:
            if self.running:  # Only log if we're supposed to be running
                logger.error(f"Web server error: {e}")


# Demo/testing functionality
if __name__ == "__main__":
    import time
    
    # Mock detection engine for testing
    class MockDetectionEngine:
        def get_system_status(self):
            return {
                'events_processed': 1247,
                'processing_rate': 8.5,
                'uptime_seconds': 3600,
                'streaming_connected': True,
                'engine_running': True,
                'events_per_minute': 15
            }
        
        def get_all_alerts(self):
            return [
                {
                    'timestamp': datetime.now().isoformat(),
                    'event_data': {
                        'event_name': 'Scan Avoidance',
                        'station_id': 'SCC1',
                        'product_sku': 'PRD_F_01'
                    }
                }
            ]
    
    # Start demo server
    logging.basicConfig(level=logging.INFO)
    mock_engine = MockDetectionEngine()
    server = DashboardWebServer(mock_engine, host='localhost', port=8080)
    
    try:
        server.start()
        print(f"Demo dashboard server running at {server.get_url()}")
        print("Press Ctrl+C to stop...")
        
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down server...")
        server.stop()
        print("Server stopped.")