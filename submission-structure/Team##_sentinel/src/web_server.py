#!/usr/bin/env python3
"""Web Dashboard Server for Project Sentinel.

Serves the interactive HTML/JS dashboard and provides REST API endpoints
for real-time data access by the web interface.
"""

import json
import logging
import threading
import time
from datetime import datetime, timedelta
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from typing import Dict, List, Any, Optional
from urllib.parse import urlparse, parse_qs
import mimetypes

logger = logging.getLogger(__name__)


class DashboardRequestHandler(BaseHTTPRequestHandler):
    """HTTP request handler for the dashboard web server."""
    
    def __init__(self, detection_engine, *args, **kwargs):
        self.detection_engine = detection_engine
        super().__init__(*args, **kwargs)
    
    def do_GET(self):
        """Handle GET requests for static files and API endpoints."""
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        
        try:
            if path == '/' or path == '/index.html':
                self._serve_dashboard_file('index.html')
            elif path == '/styles.css':
                self._serve_dashboard_file('styles.css')
            elif path == '/dashboard.js':
                self._serve_dashboard_file('dashboard.js')
            elif path == '/api/dashboard-data':
                self._serve_dashboard_data()
            elif path == '/api/alerts':
                self._serve_alerts_data()
            elif path == '/api/stations':
                self._serve_stations_data()
            elif path == '/api/system-status':
                self._serve_system_status()
            elif path == '/api/metrics':
                self._serve_metrics_data()
            elif path.startswith('/api/'):
                self._send_error(404, "API endpoint not found")
            else:
                self._send_error(404, "File not found")
                
        except Exception as e:
            logger.error(f"Error handling request {path}: {e}")
            self._send_error(500, str(e))
    
    def _serve_dashboard_file(self, filename: str):
        """Serve static dashboard files."""
        dashboard_dir = Path(__file__).parent / 'web_dashboard'
        file_path = dashboard_dir / filename
        
        if not file_path.exists():
            self._send_error(404, f"File {filename} not found")
            return
        
        # Determine content type
        content_type, _ = mimetypes.guess_type(str(file_path))
        if content_type is None:
            if filename.endswith('.html'):
                content_type = 'text/html'
            elif filename.endswith('.css'):
                content_type = 'text/css'
            elif filename.endswith('.js'):
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
            logger.error(f"Error serving file {filename}: {e}")
            self._send_error(500, f"Error reading file: {e}")
    
    def _serve_dashboard_data(self):
        """Serve comprehensive dashboard data."""
        try:
            data = {
                'metrics': self._get_metrics_data(),
                'alerts': self._get_recent_alerts(limit=20),
                'stations': self._get_stations_data(),
                'queue': self._get_queue_data(),
                'system': self._get_system_data(),
                'chart_data': self._get_chart_data()
            }
            self._send_json_response(data)
            
        except Exception as e:
            logger.error(f"Error generating dashboard data: {e}")
            self._send_error(500, str(e))
    
    def _serve_alerts_data(self):
        """Serve alerts data with optional filtering."""
        try:
            query_params = parse_qs(urlparse(self.path).query)
            limit = int(query_params.get('limit', [50])[0])
            severity = query_params.get('severity', [None])[0]
            
            alerts = self._get_recent_alerts(limit=limit, severity=severity)
            self._send_json_response({'alerts': alerts})
            
        except Exception as e:
            logger.error(f"Error serving alerts data: {e}")
            self._send_error(500, str(e))
    
    def _serve_stations_data(self):
        """Serve station status data."""
        try:
            stations = self._get_stations_data()
            self._send_json_response({'stations': stations})
            
        except Exception as e:
            logger.error(f"Error serving stations data: {e}")
            self._send_error(500, str(e))
    
    def _serve_system_status(self):
        """Serve system health and status data."""
        try:
            status = self._get_system_data()
            self._send_json_response(status)
            
        except Exception as e:
            logger.error(f"Error serving system status: {e}")
            self._send_error(500, str(e))
    
    def _serve_metrics_data(self):
        """Serve key metrics data."""
        try:
            metrics = self._get_metrics_data()
            self._send_json_response(metrics)
            
        except Exception as e:
            logger.error(f"Error serving metrics data: {e}")
            self._send_error(500, str(e))
    
    def _get_metrics_data(self) -> Dict[str, Any]:
        """Get current metrics for the dashboard."""
        if not hasattr(self.detection_engine, 'get_system_status'):
            return self._get_demo_metrics()
        
        try:
            status = self.detection_engine.get_system_status()
            alerts = self.detection_engine.get_all_alerts()
            
            # Count alerts by severity
            recent_alerts = [a for a in alerts if self._is_recent(a.get('timestamp'), hours=1)]
            active_alerts = len([a for a in recent_alerts if a.get('severity') in ['critical', 'warning']])
            
            # Calculate queue metrics
            queue_customers = 0
            total_wait_time = 0
            station_count = 0
            
            for detector in getattr(self.detection_engine, 'detectors', {}).values():
                if hasattr(detector, 'get_queue_analytics'):
                    try:
                        analytics = detector.get_queue_analytics('ALL', hours=1)
                        queue_customers += analytics.get('current_customers', 0)
                        total_wait_time += analytics.get('avg_wait_time', 0)
                        station_count += 1
                    except:
                        pass
            
            avg_wait_time = total_wait_time / max(station_count, 1)
            
            # Transaction rate
            transaction_rate = len([a for a in alerts if 'POS' in str(a) and self._is_recent(a.get('timestamp'), minutes=5)])
            
            # Inventory issues
            inventory_issues = len([a for a in recent_alerts if 'Inventory' in str(a.get('event_data', {}).get('event_name', ''))])
            
            return {
                'active_alerts': active_alerts,
                'queue_customers': queue_customers,
                'transaction_rate': transaction_rate,
                'inventory_issues': inventory_issues,
                'alerts_change': len(recent_alerts),
                'avg_wait_time': int(avg_wait_time)
            }
            
        except Exception as e:
            logger.error(f"Error getting metrics: {e}")
            return self._get_demo_metrics()
    
    def _get_recent_alerts(self, limit: int = 20, severity: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get recent alerts with optional severity filtering."""
        if not hasattr(self.detection_engine, 'get_all_alerts'):
            return self._get_demo_alerts()
        
        try:
            all_alerts = self.detection_engine.get_all_alerts()
            
            # Sort by timestamp (most recent first)
            sorted_alerts = sorted(all_alerts, 
                                 key=lambda x: x.get('timestamp', ''), 
                                 reverse=True)
            
            # Filter by severity if specified
            if severity:
                sorted_alerts = [a for a in sorted_alerts if a.get('severity') == severity]
            
            # Add severity and format for web display
            formatted_alerts = []
            for alert in sorted_alerts[:limit]:
                formatted_alert = dict(alert)
                if 'severity' not in formatted_alert:
                    formatted_alert['severity'] = self._determine_alert_severity(alert)
                formatted_alerts.append(formatted_alert)
            
            return formatted_alerts
            
        except Exception as e:
            logger.error(f"Error getting alerts: {e}")
            return self._get_demo_alerts()
    
    def _get_stations_data(self) -> Dict[str, Any]:
        """Get station status and queue information."""
        try:
            stations = {}
            
            # Get station data from queue monitor if available
            for detector_name, detector in getattr(self.detection_engine, 'detectors', {}).items():
                if hasattr(detector, 'get_queue_analytics'):
                    try:
                        # Get known stations
                        for station_id in ['SCC1', 'SCC2', 'SCC3', 'SCC4']:
                            analytics = detector.get_queue_analytics(station_id, hours=1)
                            stations[station_id] = {
                                'status': 'Active' if analytics.get('current_customers', 0) > 0 or analytics.get('recent_activity', False) else 'Inactive',
                                'queue_length': analytics.get('current_customers', 0),
                                'avg_wait_time': int(analytics.get('avg_wait_time', 0))
                            }
                    except:
                        pass
            
            # If no data available, provide default stations
            if not stations:
                stations = {
                    'SCC1': {'status': 'Active', 'queue_length': 0, 'avg_wait_time': 0},
                    'SCC2': {'status': 'Active', 'queue_length': 0, 'avg_wait_time': 0},
                    'SCC3': {'status': 'Inactive', 'queue_length': 0, 'avg_wait_time': 0}
                }
            
            return stations
            
        except Exception as e:
            logger.error(f"Error getting stations data: {e}")
            return {
                'SCC1': {'status': 'Active', 'queue_length': 0, 'avg_wait_time': 0},
                'SCC2': {'status': 'Active', 'queue_length': 0, 'avg_wait_time': 0},
                'SCC3': {'status': 'Inactive', 'queue_length': 0, 'avg_wait_time': 0}
            }
    
    def _get_queue_data(self) -> Dict[str, Any]:
        """Get queue performance metrics."""
        try:
            total_wait_time = 0
            peak_length = 0
            service_count = 0
            
            for detector in getattr(self.detection_engine, 'detectors', {}).values():
                if hasattr(detector, 'get_queue_analytics'):
                    try:
                        analytics = detector.get_queue_analytics('ALL', hours=1)
                        total_wait_time += analytics.get('avg_wait_time', 0)
                        peak_length = max(peak_length, analytics.get('peak_customers', 0))
                        service_count += analytics.get('customers_served', 0)
                    except:
                        pass
            
            return {
                'avg_wait_time': int(total_wait_time / max(1, len(getattr(self.detection_engine, 'detectors', {})))),
                'peak_length': peak_length,
                'service_rate': int(service_count / max(1, 60))  # per minute
            }
            
        except Exception as e:
            logger.error(f"Error getting queue data: {e}")
            return {'avg_wait_time': 0, 'peak_length': 0, 'service_rate': 0}
    
    def _get_system_data(self) -> Dict[str, Any]:
        """Get system health and performance data."""
        try:
            if hasattr(self.detection_engine, 'get_system_status'):
                status = self.detection_engine.get_system_status()
                return {
                    'events_processed': status.get('events_processed', 0),
                    'processing_rate': status.get('processing_rate', 0),
                    'uptime': status.get('uptime_seconds', 0),
                    'health': {
                        'stream': 'healthy' if status.get('streaming_connected', False) else 'error',
                        'engine': 'healthy' if status.get('engine_running', False) else 'error',
                        'rfid': 'healthy',
                        'pos': 'healthy'
                    }
                }
            else:
                return {
                    'events_processed': 0,
                    'processing_rate': 0,
                    'uptime': 0,
                    'health': {
                        'stream': 'healthy',
                        'engine': 'healthy',
                        'rfid': 'healthy',
                        'pos': 'healthy'
                    }
                }
                
        except Exception as e:
            logger.error(f"Error getting system data: {e}")
            return {
                'events_processed': 0,
                'processing_rate': 0,
                'uptime': 0,
                'health': {
                    'stream': 'error',
                    'engine': 'error',
                    'rfid': 'warning',
                    'pos': 'warning'
                }
            }
    
    def _get_chart_data(self) -> Dict[str, Any]:
        """Get data for charts and visualizations."""
        try:
            # Generate time labels for the last hour
            now = datetime.now()
            labels = []
            for i in range(12):  # 12 5-minute intervals
                time_point = now - timedelta(minutes=i*5)
                labels.append(time_point.strftime('%H:%M'))
            labels.reverse()
            
            # Get alerts in time buckets
            alerts = self.detection_engine.get_all_alerts() if hasattr(self.detection_engine, 'get_all_alerts') else []
            
            scan_avoidance_data = []
            weight_discrepancy_data = []
            queue_issues_data = []
            
            for i in range(12):
                bucket_start = now - timedelta(minutes=(i+1)*5)
                bucket_end = now - timedelta(minutes=i*5)
                
                bucket_alerts = [a for a in alerts if self._is_in_time_bucket(a.get('timestamp'), bucket_start, bucket_end)]
                
                scan_avoidance_data.append(len([a for a in bucket_alerts if 'Scan' in str(a.get('event_data', {}).get('event_name', ''))]))
                weight_discrepancy_data.append(len([a for a in bucket_alerts if 'Weight' in str(a.get('event_data', {}).get('event_name', ''))]))
                queue_issues_data.append(len([a for a in bucket_alerts if 'Queue' in str(a.get('event_data', {}).get('event_name', ''))]))
            
            scan_avoidance_data.reverse()
            weight_discrepancy_data.reverse()
            queue_issues_data.reverse()
            
            # Queue wait times by station
            stations_data = self._get_stations_data()
            queue_labels = list(stations_data.keys())
            queue_wait_data = [stations_data[station]['avg_wait_time'] for station in queue_labels]
            
            return {
                'detection': {
                    'labels': labels,
                    'datasets': [
                        {'data': scan_avoidance_data},
                        {'data': weight_discrepancy_data},
                        {'data': queue_issues_data}
                    ]
                },
                'queue': {
                    'labels': queue_labels,
                    'data': queue_wait_data
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting chart data: {e}")
            return {
                'detection': {
                    'labels': [],
                    'datasets': [{'data': []}, {'data': []}, {'data': []}]
                },
                'queue': {
                    'labels': [],
                    'data': []
                }
            }
    
    def _determine_alert_severity(self, alert: Dict[str, Any]) -> str:
        """Determine alert severity based on content."""
        event_name = alert.get('event_data', {}).get('event_name', '')
        
        if 'Crash' in event_name or 'System' in event_name:
            return 'critical'
        elif 'Weight' in event_name or 'Barcode' in event_name:
            return 'warning'
        elif 'Queue' in event_name or 'Wait' in event_name:
            return 'warning'
        else:
            return 'info'
    
    def _is_recent(self, timestamp_str: str, hours: int = 1, minutes: int = 0) -> bool:
        """Check if timestamp is within the specified time window."""
        try:
            if not timestamp_str:
                return False
            
            timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            cutoff = datetime.now() - timedelta(hours=hours, minutes=minutes)
            return timestamp >= cutoff
            
        except:
            return False
    
    def _is_in_time_bucket(self, timestamp_str: str, start: datetime, end: datetime) -> bool:
        """Check if timestamp falls within the time bucket."""
        try:
            if not timestamp_str:
                return False
            
            timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            return start <= timestamp < end
            
        except:
            return False
    
    def _get_demo_metrics(self) -> Dict[str, Any]:
        """Get demo metrics for testing."""
        return {
            'active_alerts': 3,
            'queue_customers': 7,
            'transaction_rate': 15,
            'inventory_issues': 2,
            'alerts_change': 5,
            'avg_wait_time': 45
        }
    
    def _get_demo_alerts(self) -> List[Dict[str, Any]]:
        """Get demo alerts for testing."""
        return [
            {
                'timestamp': datetime.now().isoformat(),
                'event_data': {
                    'event_name': 'Scan Avoidance',
                    'station_id': 'SCC1',
                    'product_sku': 'PRD_F_01'
                },
                'severity': 'warning'
            },
            {
                'timestamp': (datetime.now() - timedelta(minutes=2)).isoformat(),
                'event_data': {
                    'event_name': 'Weight Discrepancy',
                    'station_id': 'SCC2',
                    'product_sku': 'PRD_B_01',
                    'expected_weight': 150,
                    'actual_weight': 200
                },
                'severity': 'critical'
            }
        ]
    
    def _send_json_response(self, data: Any):
        """Send JSON response."""
        json_data = json.dumps(data, indent=2, default=str)
        
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(json_data.encode('utf-8'))))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Cache-Control', 'no-cache')
        self.end_headers()
        self.wfile.write(json_data.encode('utf-8'))
    
    def _send_error(self, code: int, message: str):
        """Send error response."""
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        
        error_data = {
            'error': {
                'code': code,
                'message': message
            }
        }
        self.wfile.write(json.dumps(error_data).encode('utf-8'))
    
    def log_message(self, format, *args):
        """Override to use our logger."""
        logger.info(f"{self.address_string()} - {format % args}")


class DashboardWebServer:
    """Web server for the Project Sentinel dashboard."""
    
    def __init__(self, detection_engine, host: str = 'localhost', port: int = 8080):
        self.detection_engine = detection_engine
        self.host = host
        self.port = port
        self.server = None
        self.server_thread = None
        self.running = False
    
    def start(self) -> None:
        """Start the web server."""
        if self.running:
            return
        
        try:
            # Create handler class with detection engine
            handler_class = lambda *args, **kwargs: DashboardRequestHandler(self.detection_engine, *args, **kwargs)
            
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
            self.running = False
            if self.server:
                self.server.shutdown()
                self.server.server_close()
            
            if self.server_thread and self.server_thread.is_alive():
                self.server_thread.join(timeout=5)
            
            logger.info("Dashboard web server stopped")
            
        except Exception as e:
            logger.error(f"Error stopping web server: {e}")
    
    def _run_server(self) -> None:
        """Run the server in a separate thread."""
        try:
            self.server.serve_forever()
        except Exception as e:
            if self.running:  # Only log if we're supposed to be running
                logger.error(f"Web server error: {e}")
    
    def get_url(self) -> str:
        """Get the dashboard URL."""
        return f"http://{self.host}:{self.port}"


if __name__ == "__main__":
    # Demo mode for testing
    logging.basicConfig(level=logging.INFO)
    
    class MockDetectionEngine:
        def get_all_alerts(self):
            return [
                {
                    'timestamp': datetime.now().isoformat(),
                    'event_data': {'event_name': 'Scan Avoidance', 'station_id': 'SCC1'},
                    'severity': 'warning'
                }
            ]
        
        def get_system_status(self):
            return {
                'events_processed': 1247,
                'processing_rate': 15,
                'streaming_connected': True,
                'engine_running': True
            }
    
    # Start demo server
    mock_engine = MockDetectionEngine()
    server = DashboardWebServer(mock_engine, host='localhost', port=8080)
    
    try:
        server.start()
        print(f"Demo dashboard running at {server.get_url()}")
        print("Press Ctrl+C to stop")
        
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\nStopping demo server...")
        server.stop()