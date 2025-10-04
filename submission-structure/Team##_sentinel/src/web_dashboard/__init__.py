"""Project Sentinel Web Dashboard Module.

A modular web dashboard implementation with improved architecture:
- Separated API layer for data endpoints
- Clean web server implementation  
- Organized static assets (CSS, JS, HTML)
- Dashboard controller for unified management

Usage:
    from web_dashboard import WebDashboard, DashboardManager
    
    # Create web dashboard
    dashboard = WebDashboard(detection_engine)
    dashboard.start()
    
    # Or use manager for multiple dashboard types
    manager = DashboardManager(detection_engine)
    manager.start_web_dashboard()
"""

from .controller import WebDashboard, ConsoleDashboard, DashboardManager, create_dashboard
from .server import DashboardWebServer
from .api.endpoints import DashboardAPI

__version__ = "1.0.0"
__author__ = "Project Sentinel Team"

__all__ = [
    'WebDashboard',
    'ConsoleDashboard', 
    'DashboardManager',
    'create_dashboard',
    'DashboardWebServer',
    'DashboardAPI'
]