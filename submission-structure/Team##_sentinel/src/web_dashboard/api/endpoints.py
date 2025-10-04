#!/usr/bin/env python3
"""API endpoints for Project Sentinel dashboard.

Provides RESTful API endpoints for dashboard data including alerts,
station status, metrics, and system health information.
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


class DashboardAPI:
    """RESTful API for dashboard data access."""
    
    def __init__(self, detection_engine=None):
        self.detection_engine = detection_engine
        self.standalone_mode = detection_engine is None
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get comprehensive dashboard data."""
        try:
            if self.standalone_mode:
                return self._get_fallback_data()
            
            return {
                'metrics': self.get_metrics_data(),
                'alerts': self.get_recent_alerts(limit=20),
                'stations': self.get_stations_data(),
                'queue': self.get_queue_data(),
                'system': self.get_system_data(),
                'chart_data': self.get_chart_data()
            }
        except Exception as e:
            logger.error(f"Error generating dashboard data: {e}")
            return self._get_fallback_data()
    
    def get_metrics_data(self) -> Dict[str, Any]:
        """Get current metrics for the dashboard."""
        if self.standalone_mode or not hasattr(self.detection_engine, 'get_system_status'):
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
                        queue_stats = detector.get_queue_analytics()
                        queue_customers += queue_stats.get('total_customers', 0)
                        total_wait_time += queue_stats.get('total_wait_time', 0)
                        station_count += queue_stats.get('stations_count', 0)
                    except Exception:
                        pass
            
            avg_wait_time = total_wait_time / max(station_count, 1)
            transaction_rate = status.get('events_per_minute', 0)
            inventory_issues = len([a for a in recent_alerts if 'inventory' in a.get('event_data', {}).get('event_name', '').lower()])
            
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
    
    def get_recent_alerts(self, limit: int = 20, severity: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get recent alerts with optional severity filtering."""
        if self.standalone_mode or not hasattr(self.detection_engine, 'get_all_alerts'):
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
    
    def get_stations_data(self) -> Dict[str, Any]:
        """Get station status and queue information."""
        if self.standalone_mode:
            return self._get_demo_stations()
            
        try:
            stations = {}
            
            # Get station data from queue monitor
            if hasattr(self.detection_engine, 'queue_monitor'):
                queue_data = self.detection_engine.queue_monitor.get_current_queue_status()
                for station_id, data in queue_data.items():
                    stations[station_id] = {
                        'status': 'active',
                        'queue_length': data.get('customer_count', 0),
                        'avg_wait_time': data.get('average_dwell_time', 0),
                        'alerts': 0,
                        'last_transaction': data.get('last_transaction', 'N/A')
                    }
            
            # Add system crash detector data
            if hasattr(self.detection_engine, 'crash_detector'):
                crash_data = self.detection_engine.crash_detector.get_system_health_overview()
                for station_id in crash_data.get('stations', []):
                    if station_id not in stations:
                        stations[station_id] = {
                            'status': 'unknown',
                            'queue_length': 0,
                            'avg_wait_time': 0,
                            'alerts': 0,
                            'last_transaction': 'N/A'
                        }
            
            # If no real data, return demo data
            if not stations:
                return self._get_demo_stations()
            
            return {'stations': stations}
            
        except Exception as e:
            logger.error(f"Error getting stations data: {e}")
            return self._get_demo_stations()
    
    def get_queue_data(self) -> Dict[str, Any]:
        """Get queue performance metrics."""
        if self.standalone_mode:
            return self._get_demo_queue_data()
            
        try:
            if hasattr(self.detection_engine, 'queue_monitor'):
                queue_analytics = self.detection_engine.queue_monitor.get_analytics()
                return {
                    'total_customers': queue_analytics.get('total_customers', 0),
                    'avg_wait_time': queue_analytics.get('avg_wait_time', 0),
                    'peak_queue_length': queue_analytics.get('peak_queue_length', 0),
                    'service_rate': queue_analytics.get('service_rate', 0)
                }
            else:
                return self._get_demo_queue_data()
        except Exception as e:
            logger.error(f"Error getting queue data: {e}")
            return self._get_demo_queue_data()
    
    def get_system_data(self) -> Dict[str, Any]:
        """Get system health and performance data."""
        if self.standalone_mode:
            return self._get_demo_system_data()
            
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
                return self._get_demo_system_data()
        except Exception as e:
            logger.error(f"Error getting system data: {e}")
            return self._get_demo_system_data()
    
    def get_chart_data(self) -> Dict[str, Any]:
        """Get data for charts and visualizations."""
        try:
            # This would be populated from historical data
            # For now, returning demo data structure
            return {
                'alerts_timeline': self._get_alerts_timeline(),
                'queue_trends': self._get_queue_trends(),
                'transaction_volume': self._get_transaction_volume()
            }
        except Exception as e:
            logger.error(f"Error getting chart data: {e}")
            return {}
    
    def _is_recent(self, timestamp_str: str, hours: int = 1) -> bool:
        """Check if timestamp is within the specified hours."""
        try:
            timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            return timestamp >= datetime.now() - timedelta(hours=hours)
        except:
            return False
    
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
    
    def _get_fallback_data(self) -> Dict[str, Any]:
        """Get fallback data when main data source fails."""
        return {
            'metrics': self._get_demo_metrics(),
            'alerts': self._get_demo_alerts(),
            'stations': self._get_demo_stations(),
            'queue': self._get_demo_queue_data(),
            'system': self._get_demo_system_data(),
            'chart_data': {}
        }
    
    def _get_demo_metrics(self) -> Dict[str, Any]:
        """Get demo metrics for testing."""
        import random
        base_time = datetime.now()
        
        return {
            'active_alerts': random.randint(1, 5),
            'queue_customers': random.randint(3, 12),
            'transaction_rate': random.randint(10, 25),
            'inventory_issues': random.randint(0, 3),
            'alerts_change': random.randint(1, 8),
            'avg_wait_time': random.randint(20, 80)
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
            },
            {
                'timestamp': (datetime.now() - timedelta(minutes=5)).isoformat(),
                'event_data': {
                    'event_name': 'Long Queue',
                    'station_id': 'SCC1',
                    'customer_count': 8
                },
                'severity': 'warning'
            }
        ]
    
    def _get_demo_stations(self) -> Dict[str, Any]:
        """Get demo station data."""
        return {
            'stations': {
                'SCC1': {
                    'status': 'active',
                    'queue_length': 3,
                    'avg_wait_time': 45,
                    'alerts': 2,
                    'last_transaction': '2 minutes ago'
                },
                'SCC2': {
                    'status': 'active',
                    'queue_length': 1,
                    'avg_wait_time': 23,
                    'alerts': 1,
                    'last_transaction': '30 seconds ago'
                },
                'SCC3': {
                    'status': 'maintenance',
                    'queue_length': 0,
                    'avg_wait_time': 0,
                    'alerts': 0,
                    'last_transaction': '15 minutes ago'
                }
            }
        }
    
    def _get_demo_queue_data(self) -> Dict[str, Any]:
        """Get demo queue data."""
        return {
            'total_customers': 12,
            'avg_wait_time': 34,
            'peak_queue_length': 8,
            'service_rate': 2.3
        }
    
    def _get_demo_system_data(self) -> Dict[str, Any]:
        """Get demo system data."""
        return {
            'events_processed': 1247,
            'processing_rate': 8.5,
            'uptime': 3600,
            'health': {
                'stream': 'healthy',
                'engine': 'healthy',
                'rfid': 'healthy',
                'pos': 'healthy'
            }
        }
    
    def _get_alerts_timeline(self) -> List[Dict[str, Any]]:
        """Get alerts timeline data for charts."""
        # Generate demo timeline data
        timeline = []
        now = datetime.now()
        for i in range(24):
            hour = now - timedelta(hours=i)
            timeline.append({
                'time': hour.strftime('%H:00'),
                'alerts': max(0, 5 - (i // 3))  # Decreasing alerts over time
            })
        return timeline[::-1]  # Reverse to show chronologically
    
    def _get_queue_trends(self) -> List[Dict[str, Any]]:
        """Get queue trends data for charts."""
        # Generate demo queue trends
        trends = []
        now = datetime.now()
        for i in range(12):
            hour = now - timedelta(hours=i)
            trends.append({
                'time': hour.strftime('%H:00'),
                'avg_wait': max(10, 60 - (i * 3)),  # Varying wait times
                'customers': max(1, 8 - (i // 2))   # Varying customer count
            })
        return trends[::-1]
    
    def get_all_events(self, limit: int = 100, station_id: Optional[str] = None, 
                      event_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all events/alerts from all checkout counters with filtering options."""
        try:
            # Get all alerts/events from the detection engine
            if hasattr(self.detection_engine, 'get_all_alerts'):
                all_events = self.detection_engine.get_all_alerts()
            else:
                all_events = self._get_demo_events()
            
            # Filter by station if specified
            if station_id:
                all_events = [e for e in all_events if e.get('station_id') == station_id or 
                             e.get('event_data', {}).get('station_id') == station_id]
            
            # Filter by event type if specified
            if event_type:
                all_events = [e for e in all_events if e.get('event_name') == event_type or
                             e.get('event_data', {}).get('event_name') == event_type]
            
            # Sort by timestamp (most recent first)
            sorted_events = sorted(all_events, 
                                 key=lambda x: x.get('timestamp', ''), 
                                 reverse=True)
            
            # Format events for web display
            formatted_events = []
            for event in sorted_events[:limit]:
                formatted_event = self._format_event_for_display(event)
                formatted_events.append(formatted_event)
            
            return formatted_events
            
        except Exception as e:
            logger.error(f"Error getting events: {e}")
            return self._get_demo_events()
    
    def _format_event_for_display(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Format event data for web display."""
        event_data = event.get('event_data', {})
        
        return {
            'id': event.get('event_id', 'N/A'),
            'timestamp': event.get('timestamp', ''),
            'event_name': event_data.get('event_name', event.get('event_name', 'Unknown Event')),
            'station_id': event_data.get('station_id', event.get('station_id', 'N/A')),
            'customer_id': event_data.get('customer_id', 'N/A'),
            'product_sku': event_data.get('product_sku', event_data.get('SKU', 'N/A')),
            'severity': event.get('severity', self._determine_event_severity(event_data)),
            'details': self._get_event_details(event_data),
            'raw_data': event_data
        }
    
    def _determine_event_severity(self, event_data: Dict[str, Any]) -> str:
        """Determine event severity based on event type."""
        event_name = event_data.get('event_name', '').lower()
        
        if any(keyword in event_name for keyword in ['crash', 'error', 'failure', 'discrepancy']):
            return 'critical'
        elif any(keyword in event_name for keyword in ['warning', 'switching', 'avoidance', 'weight']):
            return 'warning'
        elif 'success' in event_name:
            return 'success'
        else:
            return 'info'
    
    def _get_event_details(self, event_data: Dict[str, Any]) -> str:
        """Generate a human-readable description of the event."""
        event_name = event_data.get('event_name', 'Unknown Event')
        
        if event_name == 'Success Operation':
            return f"Successful checkout completed"
        elif event_name == 'Inventory Discrepancy':
            expected = event_data.get('Expected_Inventory', 'N/A')
            actual = event_data.get('Actual_Inventory', 'N/A')
            return f"Inventory mismatch: Expected {expected}, Found {actual}"
        elif event_name == 'Weight Discrepancies':
            expected = event_data.get('expected_weight', 'N/A')
            actual = event_data.get('actual_weight', 'N/A')
            return f"Weight mismatch: Expected {expected}g, Actual {actual}g"
        elif event_name == 'Barcode Switching':
            actual_sku = event_data.get('actual_sku', 'N/A')
            scanned_sku = event_data.get('scanned_sku', 'N/A')
            return f"Barcode switching detected: Scanned {scanned_sku}, Actual {actual_sku}"
        elif event_name == 'Scanner Avoidance':
            return "Item detected in scan area but not scanned"
        elif event_name == 'Long Queue Length':
            customer_count = event_data.get('num_of_customers', event_data.get('customer_count', 'N/A'))
            return f"Long queue detected: {customer_count} customers waiting"
        elif event_name == 'Long Wait Time':
            wait_time = event_data.get('wait_time_seconds', 'N/A')
            return f"Long wait time: {wait_time} seconds"
        elif event_name == 'Unexpected Systems Crash':
            duration = event_data.get('duration_seconds', 'N/A')
            return f"System crash detected, duration: {duration} seconds"
        else:
            return event_name
    
    def _get_demo_events(self) -> List[Dict[str, Any]]:
        """Generate demo events for testing."""
        demo_events = [
            {
                'event_id': 'DEMO_001',
                'timestamp': (datetime.now() - timedelta(minutes=5)).isoformat(),
                'event_data': {
                    'event_name': 'Success Operation',
                    'station_id': 'SCC1',
                    'customer_id': 'C001',
                    'product_sku': 'PRD_F_01'
                }
            },
            {
                'event_id': 'DEMO_002',
                'timestamp': (datetime.now() - timedelta(minutes=10)).isoformat(),
                'event_data': {
                    'event_name': 'Inventory Discrepancy',
                    'SKU': 'PRD_F_03',
                    'Expected_Inventory': 100,
                    'Actual_Inventory': 95,
                    'difference': -5,
                    'severity': 'WARNING'
                }
            },
            {
                'event_id': 'DEMO_003',
                'timestamp': (datetime.now() - timedelta(minutes=15)).isoformat(),
                'event_data': {
                    'event_name': 'Weight Discrepancies',
                    'station_id': 'SCC2',
                    'customer_id': 'C003',
                    'product_sku': 'PRD_F_05',
                    'expected_weight': 50,
                    'actual_weight': 75
                }
            }
        ]
        return demo_events

    def _get_transaction_volume(self) -> List[Dict[str, Any]]:
        """Get transaction volume data for charts."""
        # Generate demo transaction data
        volume = []
        now = datetime.now()
        for i in range(12):
            hour = now - timedelta(hours=i)
            volume.append({
                'time': hour.strftime('%H:00'),
                'transactions': max(5, 25 - (i // 2))  # Varying transaction volume
            })
        return volume[::-1]