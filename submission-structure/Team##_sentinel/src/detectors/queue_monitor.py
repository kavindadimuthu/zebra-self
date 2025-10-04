#!/usr/bin/env python3
"""Queue Monitoring and Optimization for Project Sentinel.

Monitors customer queue lengths and wait times to detect when additional
staff or checkout stations are needed to improve customer experience.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from collections import defaultdict

logger = logging.getLogger(__name__)


class QueueMonitor:
    """Monitors queue lengths and wait times for optimization."""
    
    def __init__(self, long_queue_threshold: int = 5, long_wait_threshold_seconds: int = 300):
        self.long_queue_threshold = long_queue_threshold
        self.long_wait_threshold = timedelta(seconds=long_wait_threshold_seconds)
        self.queue_history: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self.customer_sessions: Dict[str, Dict[str, Any]] = {}  # customer_id -> session_data
        self.station_status: Dict[str, str] = {}  # station_id -> status
        
    # @algorithm QueueOptimizer | Monitor customer wait times and suggest staffing
    def process_queue_event(self, event: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Process queue monitoring event and generate alerts if needed."""
        event_data = event.get("event", {})
        data = event_data.get("data", {})
        
        station_id = event_data.get("station_id")
        customer_count = data.get("customer_count")
        avg_dwell_time = data.get("average_dwell_time")
        timestamp_str = event_data.get("timestamp")
        
        if not all([station_id, timestamp_str]) or customer_count is None:
            return []
        
        try:
            timestamp = datetime.fromisoformat(timestamp_str)
        except ValueError:
            logger.error(f"Invalid timestamp: {timestamp_str}")
            return []
        
        # Store queue data
        queue_data = {
            "timestamp": timestamp,
            "customer_count": customer_count,
            "average_dwell_time": avg_dwell_time,
            "station_id": station_id
        }
        
        self.queue_history[station_id].append(queue_data)
        
        # Keep only recent history (last 2 hours)
        cutoff_time = timestamp - timedelta(hours=2)
        self.queue_history[station_id] = [
            data for data in self.queue_history[station_id]
            if data["timestamp"] >= cutoff_time
        ]
        
        alerts = []
        
        # Check for long queue
        if customer_count >= self.long_queue_threshold:
            alerts.append(self._generate_long_queue_alert(
                station_id, customer_count, timestamp
            ))
        
        # Check for long wait times
        if avg_dwell_time and avg_dwell_time >= self.long_wait_threshold.total_seconds():
            alerts.append(self._generate_long_wait_alert(
                station_id, avg_dwell_time, customer_count, timestamp
            ))
        
        # Analyze if staffing needs are required
        staffing_alert = self._check_staffing_needs(station_id, queue_data)
        if staffing_alert:
            alerts.append(staffing_alert)
        
        # Check if station action is needed
        station_action = self._check_station_action_needed(station_id, queue_data)
        if station_action:
            alerts.append(station_action)
        
        return alerts
    
    def process_customer_entry(self, customer_id: str, station_id: str, timestamp: datetime) -> None:
        """Track when a customer enters a queue."""
        self.customer_sessions[customer_id] = {
            "station_id": station_id,
            "entry_time": timestamp,
            "status": "in_queue"
        }
    
    def process_customer_service_start(self, customer_id: str, timestamp: datetime) -> None:
        """Track when customer service begins."""
        if customer_id in self.customer_sessions:
            session = self.customer_sessions[customer_id]
            session["service_start"] = timestamp
            session["status"] = "being_served"
            session["wait_time"] = (timestamp - session["entry_time"]).total_seconds()
    
    def process_customer_exit(self, customer_id: str, timestamp: datetime) -> Optional[Dict[str, Any]]:
        """Track when customer exits and check for long wait time."""
        if customer_id not in self.customer_sessions:
            return None
        
        session = self.customer_sessions[customer_id]
        total_time = (timestamp - session["entry_time"]).total_seconds()
        
        # Check if wait time was too long
        if total_time >= self.long_wait_threshold.total_seconds():
            alert = {
                "timestamp": timestamp.isoformat(),
                "event_id": f"LW_{session['station_id']}_{customer_id}_{int(timestamp.timestamp())}",
                "event_data": {
                    "event_name": "Long Wait Time",
                    "station_id": session["station_id"],
                    "customer_id": customer_id,
                    "wait_time_seconds": round(total_time, 1),
                    "severity": "HIGH" if total_time > 600 else "MEDIUM"
                }
            }
            
            # Clean up session
            del self.customer_sessions[customer_id]
            return alert
        
        # Clean up session
        del self.customer_sessions[customer_id]
        return None
    
    def _generate_long_queue_alert(self, station_id: str, customer_count: int, 
                                 timestamp: datetime) -> Dict[str, Any]:
        """Generate alert for long queue."""
        return {
            "timestamp": timestamp.isoformat(),
            "event_id": f"LQ_{station_id}_{int(timestamp.timestamp())}",
            "event_data": {
                "event_name": "Long Queue Length",
                "station_id": station_id,
                "num_of_customers": customer_count,
                "severity": "HIGH" if customer_count >= self.long_queue_threshold * 2 else "MEDIUM"
            }
        }
    
    def _generate_long_wait_alert(self, station_id: str, wait_time_seconds: float,
                                customer_count: int, timestamp: datetime) -> Dict[str, Any]:
        """Generate alert for long wait times."""
        return {
            "timestamp": timestamp.isoformat(),
            "event_id": f"LWT_{station_id}_{int(timestamp.timestamp())}",
            "event_data": {
                "event_name": "Long Wait Time",
                "station_id": station_id,
                "wait_time_seconds": round(wait_time_seconds, 1),
                "num_customers_waiting": customer_count,
                "severity": "HIGH" if wait_time_seconds > 600 else "MEDIUM"
            }
        }
    
    def _check_staffing_needs(self, station_id: str, queue_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Check if additional staffing is needed."""
        customer_count = queue_data["customer_count"]
        avg_dwell_time = queue_data.get("average_dwell_time", 0)
        
        # Simple heuristic: if queue is long and dwell time is high, need staff
        if customer_count >= 4 and avg_dwell_time >= 180:  # 3+ minutes average
            return {
                "timestamp": queue_data["timestamp"].isoformat(),
                "event_id": f"SN_{station_id}_{int(queue_data['timestamp'].timestamp())}",
                "event_data": {
                    "event_name": "Staffing Needs",
                    "station_id": station_id,
                    "Staff_type": "Cashier",
                    "reason": "High queue length with slow service",
                    "customer_count": customer_count,
                    "avg_dwell_time": avg_dwell_time
                }
            }
        
        return None
    
    def _check_station_action_needed(self, station_id: str, queue_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Check if station needs to be opened/closed."""
        customer_count = queue_data["customer_count"]
        
        # Get recent queue trend
        recent_counts = [
            data["customer_count"] for data in self.queue_history[station_id][-5:]
        ]
        
        if len(recent_counts) >= 3:
            avg_recent_count = sum(recent_counts) / len(recent_counts)
            
            # If consistently high queues, suggest opening more stations
            if avg_recent_count >= self.long_queue_threshold:
                return {
                    "timestamp": queue_data["timestamp"].isoformat(),
                    "event_id": f"SA_{station_id}_{int(queue_data['timestamp'].timestamp())}",
                    "event_data": {
                        "event_name": "Checkout Station Action",
                        "station_id": station_id,
                        "Action": "Open",
                        "reason": "Consistently high queue volume",
                        "avg_customer_count": round(avg_recent_count, 1)
                    }
                }
        
        return None
    
    def get_queue_analytics(self, station_id: str, hours: int = 1) -> Dict[str, Any]:
        """Get queue analytics for a station."""
        if station_id not in self.queue_history:
            return {"station_id": station_id, "error": "No queue data available"}
        
        cutoff_time = datetime.now() - timedelta(hours=hours)
        recent_data = [
            data for data in self.queue_history[station_id]
            if data["timestamp"] >= cutoff_time
        ]
        
        if not recent_data:
            return {"station_id": station_id, "error": "No recent queue data"}
        
        customer_counts = [data["customer_count"] for data in recent_data]
        dwell_times = [data.get("average_dwell_time", 0) for data in recent_data if data.get("average_dwell_time")]
        
        return {
            "station_id": station_id,
            "analysis_period_hours": hours,
            "total_observations": len(recent_data),
            "avg_customer_count": round(sum(customer_counts) / len(customer_counts), 1) if customer_counts else 0,
            "max_customer_count": max(customer_counts) if customer_counts else 0,
            "avg_dwell_time_seconds": round(sum(dwell_times) / len(dwell_times), 1) if dwell_times else 0,
            "long_queue_incidents": len([c for c in customer_counts if c >= self.long_queue_threshold])
        }
    
    def get_current_queue_status(self) -> Dict[str, Dict[str, Any]]:
        """Get current queue status for all monitored stations."""
        status = {}
        current_time = datetime.now()
        
        for station_id, history in self.queue_history.items():
            if history:
                latest = history[-1]
                time_since_update = (current_time - latest["timestamp"]).total_seconds()
                
                status[station_id] = {
                    "customer_count": latest["customer_count"],
                    "average_dwell_time": latest.get("average_dwell_time"),
                    "last_update_seconds_ago": round(time_since_update, 1),
                    "queue_status": "LONG" if latest["customer_count"] >= self.long_queue_threshold else "NORMAL"
                }
        
        return status
    
    def get_analytics(self, hours: int = 1) -> Dict[str, Any]:
        """Get aggregated analytics for all stations."""
        all_customers = 0
        all_wait_times = []
        max_queue_length = 0
        total_observations = 0
        station_count = len(self.queue_history)
        
        # Aggregate data from all stations
        for station_id in self.queue_history.keys():
            station_analytics = self.get_queue_analytics(station_id, hours)
            if "error" not in station_analytics:
                total_observations += station_analytics.get('total_observations', 0)
                max_queue_length = max(max_queue_length, station_analytics.get('max_customer_count', 0))
                
                # Collect wait times if available
                avg_dwell = station_analytics.get('avg_dwell_time_seconds', 0)
                if avg_dwell > 0:
                    all_wait_times.append(avg_dwell)
        
        # Get current status for active customer count
        current_status = self.get_current_queue_status()
        for station_status in current_status.values():
            all_customers += station_status.get('customer_count', 0)
        
        # Calculate service rate (customers per hour) - rough estimate
        avg_wait_time = sum(all_wait_times) / len(all_wait_times) if all_wait_times else 60
        service_rate = 3600 / avg_wait_time if avg_wait_time > 0 else 0  # customers per hour
        
        return {
            'total_customers': all_customers,
            'avg_wait_time': round(avg_wait_time, 1),
            'peak_queue_length': max_queue_length,
            'service_rate': round(service_rate, 2),
            'active_stations': station_count,
            'total_observations': total_observations
        }
    
    def cleanup_old_data(self, hours_to_keep: int = 4) -> None:
        """Clean up old queue data and customer sessions."""
        cutoff_time = datetime.now() - timedelta(hours=hours_to_keep)
        
        # Clean queue history
        for station_id in list(self.queue_history.keys()):
            history = self.queue_history[station_id]
            recent_history = [data for data in history if data["timestamp"] >= cutoff_time]
            
            if recent_history:
                self.queue_history[station_id] = recent_history
            else:
                del self.queue_history[station_id]
        
        # Clean old customer sessions
        for customer_id in list(self.customer_sessions.keys()):
            session = self.customer_sessions[customer_id]
            if session["entry_time"] < cutoff_time:
                del self.customer_sessions[customer_id]


if __name__ == "__main__":
    # Example usage
    logging.basicConfig(level=logging.DEBUG)
    
    monitor = QueueMonitor(long_queue_threshold=3, long_wait_threshold_seconds=180)
    
    # Simulate queue event
    queue_event = {
        "dataset": "Queue_monitor",
        "event": {
            "timestamp": "2025-08-13T16:00:03",
            "station_id": "SCC1",
            "data": {
                "customer_count": 6,
                "average_dwell_time": 250.0
            }
        }
    }
    
    alerts = monitor.process_queue_event(queue_event)
    print(f"Generated {len(alerts)} queue alerts")
    
    for alert in alerts:
        print(f"Alert: {alert['event_data']['event_name']} at {alert['event_data']['station_id']}")
    
    # Get queue analytics
    analytics = monitor.get_queue_analytics("SCC1")
    print(f"Queue analytics: {analytics}")
    
    # Get current status
    status = monitor.get_current_queue_status()
    print(f"Current queue status: {status}")