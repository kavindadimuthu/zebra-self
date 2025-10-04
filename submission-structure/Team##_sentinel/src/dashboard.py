#!/usr/bin/env python3
"""Real-time Dashboard for Project Sentinel.

Provides a console-based dashboard showing real-time store status,
alerts, queue information, and system health.
"""

import os
import time
import json
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from collections import defaultdict

try:
    import curses
    HAS_CURSES = True
except ImportError:
    HAS_CURSES = False

try:
    from web_dashboard import WebDashboard as ModularWebDashboard, DashboardManager
    HAS_NEW_WEB_DASHBOARD = True
except ImportError:
    try:
        from web_server import DashboardWebServer
        HAS_WEB_SERVER = True
        HAS_NEW_WEB_DASHBOARD = False
    except ImportError:
        HAS_WEB_SERVER = False
        HAS_NEW_WEB_DASHBOARD = False
        DashboardWebServer = None


class ConsoleDashboard:
    """Console-based dashboard for real-time monitoring."""
    
    def __init__(self, detection_engine):
        self.engine = detection_engine
        self.running = False
        self.refresh_interval = 2.0  # seconds
        self.alerts_history = []
        self.max_alerts_display = 10
        
    def start(self) -> None:
        """Start the dashboard."""
        self.running = True
        
        if HAS_CURSES:
            curses.wrapper(self._curses_main)
        else:
            self._simple_main()
    
    def stop(self) -> None:
        """Stop the dashboard."""
        self.running = False
    
    def _simple_main(self) -> None:
        """Simple text-based dashboard without curses."""
        print("Project Sentinel - Retail Intelligence Dashboard")
        print("=" * 60)
        print("(Press Ctrl+C to stop)")
        print()
        
        try:
            while self.running:
                self._print_simple_dashboard()
                time.sleep(self.refresh_interval)
        except KeyboardInterrupt:
            print("\nDashboard stopped.")
    
    def _print_simple_dashboard(self) -> None:
        """Print simple dashboard to console."""
        # Clear screen
        os.system('clear' if os.name == 'posix' else 'cls')
        
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        print("╔" + "═" * 78 + "╗")
        print(f"║ Project Sentinel - Retail Intelligence Dashboard{' ' * 22}║")
        print(f"║ {current_time}{' ' * 56}║")
        print("╠" + "═" * 78 + "╣")
        
        # System Status
        status = self.engine.get_system_status()
        print(f"║ System Status: {status['status']:<10} │ Events: {status['events_processed']:<8} │ Alerts: {status['alerts_generated']:<8}║")
        print(f"║ Uptime: {self._format_duration(status['uptime_seconds']):<15} │ Rate: {status['events_per_minute']:<6.1f}/min │ Pending: {status['pending_alerts']:<8}║")
        print("╠" + "═" * 78 + "╣")
        
        # Recent Alerts
        recent_alerts = self.engine.get_alerts(self.max_alerts_display)
        self.alerts_history.extend(recent_alerts)
        
        # Keep only recent alerts in history
        cutoff_time = datetime.now() - timedelta(minutes=30)
        self.alerts_history = [
            alert for alert in self.alerts_history
            if datetime.fromisoformat(alert['timestamp']) >= cutoff_time
        ]
        
        print("║ RECENT ALERTS" + " " * 64 + "║")
        print("╠" + "═" * 78 + "╣")
        
        if self.alerts_history:
            # Show most recent alerts
            for alert in self.alerts_history[-10:]:
                event_data = alert.get('event_data', {})
                event_name = event_data.get('event_name', 'Unknown')[:25]
                station = event_data.get('station_id', 'N/A')
                severity = event_data.get('severity', 'UNKNOWN')
                timestamp = alert.get('timestamp', '')[:16]  # Just date and time
                
                # Color coding based on severity
                severity_indicator = "🔴" if severity == "HIGH" else "🟡" if severity == "MEDIUM" else "🟢"
                
                line = f"║ {severity_indicator} {timestamp} │ {station:<8} │ {event_name:<25} │ {severity:<6} ║"
                print(line[:80])  # Truncate if too long
        else:
            print("║ No recent alerts" + " " * 59 + "║")
        
        print("╠" + "═" * 78 + "╣")
        
        # Queue Status
        queue_status = self._get_queue_overview()
        print("║ QUEUE STATUS" + " " * 65 + "║")
        print("╠" + "═" * 78 + "╣")
        
        if queue_status:
            for station_id, info in queue_status.items():
                customers = info.get('customer_count', 0)
                wait_time = info.get('average_dwell_time', 0)
                status_icon = "🔴" if customers >= 5 else "🟡" if customers >= 3 else "🟢"
                
                line = f"║ {status_icon} {station_id:<8} │ Customers: {customers:<3} │ Avg Wait: {wait_time:<6.1f}s{' ' * 20}║"
                print(line[:80])
        else:
            print("║ No queue data available" + " " * 55 + "║")
        
        print("╠" + "═" * 78 + "╣")
        
        # System Health
        health = self._get_system_health()
        print("║ SYSTEM HEALTH" + " " * 63 + "║")
        print("╠" + "═" * 78 + "╣")
        
        health_status = health.get('system_health', 'UNKNOWN')
        health_icon = "🟢" if health_status == "GOOD" else "🟡" if health_status == "DEGRADED" else "🔴"
        
        active_stations = health.get('active_stations', 0)
        total_stations = health.get('total_stations', 0)
        
        print(f"║ {health_icon} Overall Health: {health_status:<10} │ Active Stations: {active_stations}/{total_stations}{' ' * 20}║")
        
        if health.get('stations_in_crash_state', 0) > 0:
            print(f"║ ⚠️  {health['stations_in_crash_state']} station(s) experiencing issues{' ' * 32}║")
        
        print("╚" + "═" * 78 + "╝")
        
        # Instructions
        print()
        print("Press Ctrl+C to stop monitoring")
    
    def _get_queue_overview(self) -> Dict[str, Any]:
        """Get queue overview for all stations."""
        try:
            return self.engine.queue_monitor.get_current_queue_status()
        except Exception:
            return {}
    
    def _get_system_health(self) -> Dict[str, Any]:
        """Get system health overview."""
        try:
            return self.engine.crash_detector.get_system_health_overview()
        except Exception:
            return {"system_health": "UNKNOWN", "active_stations": 0, "total_stations": 0}
    
    def _format_duration(self, seconds: float) -> str:
        """Format duration in a human-readable way."""
        if seconds < 60:
            return f"{seconds:.0f}s"
        elif seconds < 3600:
            return f"{seconds/60:.1f}m"
        else:
            return f"{seconds/3600:.1f}h"
    
    def _curses_main(self, stdscr) -> None:
        """Main curses-based dashboard (if available)."""
        curses.curs_set(0)  # Hide cursor
        stdscr.nodelay(1)   # Non-blocking input
        stdscr.timeout(100) # Refresh every 100ms
        
        # Initialize colors
        curses.start_color()
        curses.init_pair(1, curses.COLOR_RED, curses.COLOR_BLACK)     # High severity
        curses.init_pair(2, curses.COLOR_YELLOW, curses.COLOR_BLACK)  # Medium severity
        curses.init_pair(3, curses.COLOR_GREEN, curses.COLOR_BLACK)   # Low severity/Good
        curses.init_pair(4, curses.COLOR_CYAN, curses.COLOR_BLACK)    # Headers
        curses.init_pair(5, curses.COLOR_WHITE, curses.COLOR_BLACK)   # Normal text
        
        last_refresh = 0
        
        try:
            while self.running:
                current_time = time.time()
                
                # Check for input
                key = stdscr.getch()
                if key == ord('q') or key == 27:  # 'q' or ESC
                    break
                
                # Refresh dashboard
                if current_time - last_refresh >= self.refresh_interval:
                    self._draw_curses_dashboard(stdscr)
                    last_refresh = current_time
                
                time.sleep(0.1)
                
        except KeyboardInterrupt:
            pass
    
    def _draw_curses_dashboard(self, stdscr) -> None:
        """Draw the curses-based dashboard."""
        stdscr.clear()
        height, width = stdscr.getmaxyx()
        
        # Title
        title = "Project Sentinel - Retail Intelligence Dashboard"
        stdscr.addstr(0, (width - len(title)) // 2, title, curses.color_pair(4) | curses.A_BOLD)
        
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        stdscr.addstr(1, (width - len(current_time)) // 2, current_time, curses.color_pair(5))
        
        # System status
        status = self.engine.get_system_status()
        stdscr.addstr(3, 2, "System Status:", curses.color_pair(4) | curses.A_BOLD)
        stdscr.addstr(4, 4, f"Status: {status['status']}")
        stdscr.addstr(4, 20, f"Events: {status['events_processed']}")
        stdscr.addstr(4, 35, f"Alerts: {status['alerts_generated']}")
        stdscr.addstr(4, 50, f"Rate: {status['events_per_minute']:.1f}/min")
        
        # Recent alerts
        y_pos = 6
        stdscr.addstr(y_pos, 2, "Recent Alerts:", curses.color_pair(4) | curses.A_BOLD)
        y_pos += 1
        
        recent_alerts = self.engine.get_alerts(min(height - y_pos - 5, 10))
        
        for alert in recent_alerts:
            if y_pos >= height - 3:
                break
                
            event_data = alert.get('event_data', {})
            severity = event_data.get('severity', 'UNKNOWN')
            
            # Choose color based on severity
            color = curses.color_pair(1) if severity == "HIGH" else \
                   curses.color_pair(2) if severity == "MEDIUM" else \
                   curses.color_pair(3)
            
            alert_text = f"  {event_data.get('event_name', 'Unknown')[:30]} at {event_data.get('station_id', 'N/A')}"
            stdscr.addstr(y_pos, 2, alert_text, color)
            y_pos += 1
        
        if not recent_alerts:
            stdscr.addstr(y_pos, 4, "No recent alerts", curses.color_pair(3))
        
        # Instructions
        stdscr.addstr(height - 2, 2, "Press 'q' or ESC to quit", curses.color_pair(5))
        
        stdscr.refresh()


class WebDashboard:
    """Web-based dashboard using HTTP server with HTML/JS interface."""
    
    def __init__(self, detection_engine, host: str = 'localhost', port: int = 8080):
        self.engine = detection_engine
        self.host = host
        self.port = port
        self.server = None
        
        # Use the new modular web dashboard if available
        if HAS_NEW_WEB_DASHBOARD:
            self._use_new_dashboard = True
            self._dashboard = ModularWebDashboard(detection_engine, host, port)
        elif HAS_WEB_SERVER:
            self._use_new_dashboard = False
            self._dashboard = None
        else:
            raise ImportError("Web dashboard modules not available. Please ensure web_dashboard package or web_server.py is present.")
    
    def start(self) -> None:
        """Start the web dashboard server."""
        try:
            if self._use_new_dashboard:
                # Use new modular dashboard
                self._dashboard.start()
            else:
                # Use legacy dashboard
                self.server = DashboardWebServer(self.engine, self.host, self.port)
                self.server.start()
                print(f"\nWeb Dashboard started!")
                print(f"Open your browser and go to: {self.server.get_url()}")
                print("The dashboard will show real-time alerts, station status, and analytics.")
                print("Press Ctrl+C to stop the dashboard.\n")
            
        except Exception as e:
            print(f"Failed to start web dashboard: {e}")
            raise
    
    def stop(self) -> None:
        """Stop the web dashboard server."""
        try:
            if self._use_new_dashboard and self._dashboard:
                self._dashboard.stop()
            elif self.server:
                self.server.stop()
            print("Web dashboard stopped.")
        except Exception as e:
            print(f"Error stopping web dashboard: {e}")
    
    def get_url(self) -> str:
        """Get the dashboard URL."""
        if self._use_new_dashboard and self._dashboard:
            return self._dashboard.get_url()
        elif self.server:
            return self.server.get_url()
        return f"http://{self.host}:{self.port}"
if __name__ == "__main__":
    # Example usage - would normally be integrated with detection engine
    print("Dashboard module - use with detection engine")