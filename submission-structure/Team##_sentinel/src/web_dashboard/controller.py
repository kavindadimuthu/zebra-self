#!/usr/bin/env python3
"""Dashboard Controller for Project Sentinel.

Main controller that orchestrates console and web dashboards.
Provides a unified interface for dashboard management.
"""

import logging
from typing import Optional, Union

from .server import DashboardWebServer

logger = logging.getLogger(__name__)


class ConsoleDashboard:
    """Console-based dashboard for real-time monitoring."""
    
    def __init__(self, detection_engine):
        # Import console dashboard from original module
        try:
            from dashboard import ConsoleDashboard as OriginalConsoleDashboard
            self._dashboard = OriginalConsoleDashboard(detection_engine)
        except ImportError:
            logger.error("Could not import original ConsoleDashboard")
            self._dashboard = None
    
    def start(self) -> None:
        """Start the console dashboard."""
        if self._dashboard:
            self._dashboard.start()
        else:
            print("Console dashboard not available")
    
    def stop(self) -> None:
        """Stop the console dashboard."""
        if self._dashboard:
            self._dashboard.stop()


class WebDashboard:
    """Enhanced web-based dashboard with improved architecture."""
    
    def __init__(self, detection_engine=None, host: str = 'localhost', port: int = 8080):
        self.engine = detection_engine
        self.host = host
        self.port = port
        self.server: Optional[DashboardWebServer] = None
        self.standalone_mode = detection_engine is None
    
    def start(self) -> None:
        """Start the web dashboard server."""
        try:
            self.server = DashboardWebServer(self.engine, self.host, self.port)
            self.server.start()
            
            mode_text = " (Standalone Mode - Server Offline)" if self.standalone_mode else " (Connected to Detection Engine)"
            print(f"\n🚀 Project Sentinel Web Dashboard Started{mode_text}!")
            print(f"📊 Dashboard URL: {self.server.get_url()}")
            print(f"🔗 Open your browser to view the dashboard")
            
            if self.standalone_mode:
                print(f"⚠️  WARNING: Detection engine is not connected")
                print(f"📡 Status: Server offline - showing disconnection indicators")
                print(f"🔧 Features: System status monitoring and connection diagnostics")
                print(f"💡 To connect: Start the detection engine in 'both' or 'detection-only' mode")
            else:
                print(f"🎯 Features: Real-time monitoring, alerts, station status, queue analytics")
                print(f"⚡ Auto-refresh every 5 seconds")
            
            print(f"🛑 Press Ctrl+C to stop the dashboard\n")
            
        except Exception as e:
            logger.error(f"Failed to start web dashboard: {e}")
            print(f"❌ Failed to start web dashboard: {e}")
            raise
    
    def stop(self) -> None:
        """Stop the web dashboard server."""
        if self.server:
            self.server.stop()
            print("🛑 Web dashboard stopped.")
    
    def get_url(self) -> str:
        """Get the dashboard URL."""
        if self.server:
            return self.server.get_url()
        return f"http://{self.host}:{self.port}"


class DashboardManager:
    """Unified dashboard manager for console and web dashboards."""
    
    def __init__(self, detection_engine):
        self.engine = detection_engine
        self.console_dashboard: Optional[ConsoleDashboard] = None
        self.web_dashboard: Optional[WebDashboard] = None
    
    def start_console_dashboard(self) -> None:
        """Start console dashboard."""
        try:
            self.console_dashboard = ConsoleDashboard(self.engine)
            self.console_dashboard.start()
        except Exception as e:
            logger.error(f"Failed to start console dashboard: {e}")
            print(f"❌ Failed to start console dashboard: {e}")
    
    def start_web_dashboard(self, host: str = 'localhost', port: int = 8080) -> None:
        """Start web dashboard."""
        try:
            self.web_dashboard = WebDashboard(self.engine, host, port)
            self.web_dashboard.start()
        except Exception as e:
            logger.error(f"Failed to start web dashboard: {e}")
            print(f"❌ Failed to start web dashboard: {e}")
    
    def stop_all(self) -> None:
        """Stop all running dashboards."""
        if self.console_dashboard:
            self.console_dashboard.stop()
        if self.web_dashboard:
            self.web_dashboard.stop()
    
    def get_web_url(self) -> Optional[str]:
        """Get web dashboard URL if running."""
        if self.web_dashboard:
            return self.web_dashboard.get_url()
        return None


# Factory function for backward compatibility
def create_dashboard(dashboard_type: str, detection_engine, **kwargs) -> Union[ConsoleDashboard, WebDashboard]:
    """Factory function to create dashboard instances."""
    if dashboard_type.lower() == 'console':
        return ConsoleDashboard(detection_engine)
    elif dashboard_type.lower() == 'web':
        host = kwargs.get('host', 'localhost')
        port = kwargs.get('port', 8080)
        return WebDashboard(detection_engine, host, port)
    else:
        raise ValueError(f"Unknown dashboard type: {dashboard_type}")


if __name__ == "__main__":
    # Demo usage
    class MockDetectionEngine:
        def get_system_status(self):
            return {'status': 'healthy', 'events_processed': 100}
    
    print("Testing Dashboard Manager...")
    
    mock_engine = MockDetectionEngine()
    manager = DashboardManager(mock_engine)
    
    # Test web dashboard
    try:
        manager.start_web_dashboard(port=8081)
        print("Web dashboard test: ✅")
        manager.stop_all()
    except Exception as e:
        print(f"Web dashboard test: ❌ {e}")
    
    print("Dashboard manager test completed.")