#!/usr/bin/env python3
"""System Crash and Error Detection for Project Sentinel.

Detects POS system failures, unexpected downtime, and other technical issues
that affect checkout operations and customer experience.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Set
from collections import defaultdict

logger = logging.getLogger(__name__)


class SystemCrashDetector:
    """Detects system crashes and technical failures."""
    
    def __init__(self, inactivity_timeout_minutes: int = 5, min_crash_duration_seconds: int = 30):
        self.inactivity_timeout = timedelta(minutes=inactivity_timeout_minutes)
        self.min_crash_duration = timedelta(seconds=min_crash_duration_seconds)
        self.station_last_activity: Dict[str, datetime] = {}
        self.station_status: Dict[str, str] = {}  # station_id -> status
        self.crash_periods: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self.error_events: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self.active_crashes: Dict[str, Dict[str, Any]] = {}
        
    # @algorithm SystemCrashDetector | Detect POS system failures and downtime
    def process_station_event(self, event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process any station event to track activity and detect crashes."""
        event_data = event.get("event", {})
        station_id = event_data.get("station_id")
        status = event_data.get("status")
        timestamp_str = event_data.get("timestamp")
        dataset = event.get("dataset", "")
        
        if not all([station_id, timestamp_str]):
            return None
        
        try:
            timestamp = datetime.fromisoformat(timestamp_str)
        except ValueError:
            logger.error(f"Invalid timestamp: {timestamp_str}")
            return None
        
        # Update last activity
        self.station_last_activity[station_id] = timestamp
        
        # Track station status
        if status:
            previous_status = self.station_status.get(station_id)
            self.station_status[station_id] = status
            
            # Detect status changes that indicate problems
            if status in ["Error", "Offline", "Maintenance"]:
                return self._handle_station_error(station_id, status, timestamp, event)
            
            # If station comes back online after being down
            elif status == "Active" and previous_status in ["Error", "Offline"]:
                return self._handle_station_recovery(station_id, timestamp)
        
        # Check for inactivity-based crashes
        return self._check_inactivity_crash(station_id, timestamp)
    
    def process_error_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Process explicit error events."""
        event_data = event.get("event", {})
        station_id = event_data.get("station_id", "UNKNOWN")
        timestamp_str = event_data.get("timestamp")
        error_type = event_data.get("error_type", "UNKNOWN_ERROR")
        
        try:
            timestamp = datetime.fromisoformat(timestamp_str)
        except ValueError:
            timestamp = datetime.now()
        
        # Store error event
        error_data = {
            "timestamp": timestamp,
            "error_type": error_type,
            "event_data": event_data
        }
        
        self.error_events[station_id].append(error_data)
        
        # Keep only recent errors (last 24 hours)
        cutoff_time = timestamp - timedelta(hours=24)
        self.error_events[station_id] = [
            err for err in self.error_events[station_id]
            if err["timestamp"] >= cutoff_time
        ]
        
        # Generate system crash alert
        return self._generate_system_crash_alert(
            station_id, error_type, timestamp, None, "ERROR_EVENT"
        )
    
    def _handle_station_error(self, station_id: str, status: str, 
                            timestamp: datetime, event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Handle station entering error state."""
        if station_id not in self.active_crashes:
            # Start tracking new crash
            self.active_crashes[station_id] = {
                "start_time": timestamp,
                "status": status,
                "event": event
            }
            logger.info(f"Station {station_id} entered error state: {status}")
        
        return None  # Don't alert immediately, wait for recovery to calculate duration
    
    def _handle_station_recovery(self, station_id: str, timestamp: datetime) -> Optional[Dict[str, Any]]:
        """Handle station recovery from error state."""
        if station_id in self.active_crashes:
            crash_data = self.active_crashes[station_id]
            start_time = crash_data["start_time"]
            duration = timestamp - start_time
            
            # Only alert if crash was significant
            if duration >= self.min_crash_duration:
                # Record crash period
                crash_period = {
                    "start_time": start_time,
                    "end_time": timestamp,
                    "duration_seconds": duration.total_seconds(),
                    "status": crash_data["status"]
                }
                self.crash_periods[station_id].append(crash_period)
                
                # Generate alert
                alert = self._generate_system_crash_alert(
                    station_id, crash_data["status"], start_time, 
                    duration.total_seconds(), "SYSTEM_CRASH"
                )
                
                # Clean up
                del self.active_crashes[station_id]
                
                return alert
            else:
                # Short outage, just clean up
                del self.active_crashes[station_id]
        
        return None
    
    def _check_inactivity_crash(self, station_id: str, current_time: datetime) -> Optional[Dict[str, Any]]:
        """Check if a station has been inactive long enough to indicate a crash."""
        # This is handled by periodic checks, not per-event
        return None
    
    def check_station_timeouts(self) -> List[Dict[str, Any]]:
        """Check all stations for inactivity timeouts (call periodically)."""
        current_time = datetime.now()
        alerts = []
        
        for station_id, last_activity in self.station_last_activity.items():
            time_since_activity = current_time - last_activity
            
            # Skip if station is already in active crash state
            if station_id in self.active_crashes:
                continue
            
            # Check for timeout
            if time_since_activity >= self.inactivity_timeout:
                # Mark as crashed due to inactivity
                self.active_crashes[station_id] = {
                    "start_time": last_activity,
                    "status": "INACTIVE",
                    "event": None
                }
                
                alert = self._generate_system_crash_alert(
                    station_id, "INACTIVITY_TIMEOUT", last_activity,
                    time_since_activity.total_seconds(), "TIMEOUT"
                )
                alerts.append(alert)
        
        return alerts
    
    def _generate_system_crash_alert(self, station_id: str, error_type: str,
                                   timestamp: datetime, duration_seconds: Optional[float],
                                   crash_type: str) -> Dict[str, Any]:
        """Generate system crash alert."""
        alert_data = {
            "event_name": "Unexpected Systems Crash",
            "station_id": station_id,
            "error_type": error_type,
            "crash_type": crash_type,
            "crash_timestamp": timestamp.isoformat()
        }
        
        if duration_seconds is not None:
            alert_data["duration_seconds"] = round(duration_seconds, 1)
            alert_data["severity"] = "HIGH" if duration_seconds > 300 else "MEDIUM"
        else:
            alert_data["severity"] = "MEDIUM"
        
        return {
            "timestamp": timestamp.isoformat(),
            "event_id": f"SC_{station_id}_{crash_type}_{int(timestamp.timestamp())}",
            "event_data": alert_data
        }
    
    def get_station_reliability_report(self, station_id: str, hours: int = 24) -> Dict[str, Any]:
        """Get reliability report for a station."""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        # Get crash periods in timeframe
        relevant_crashes = [
            crash for crash in self.crash_periods.get(station_id, [])
            if crash["start_time"] >= cutoff_time
        ]
        
        # Get error events in timeframe
        relevant_errors = [
            error for error in self.error_events.get(station_id, [])
            if error["timestamp"] >= cutoff_time
        ]
        
        # Calculate downtime
        total_downtime = sum(crash["duration_seconds"] for crash in relevant_crashes)
        total_period_seconds = hours * 3600
        uptime_percentage = ((total_period_seconds - total_downtime) / total_period_seconds) * 100
        
        # Get current status
        current_status = self.station_status.get(station_id, "UNKNOWN")
        last_activity = self.station_last_activity.get(station_id)
        
        return {
            "station_id": station_id,
            "report_period_hours": hours,
            "current_status": current_status,
            "last_activity": last_activity.isoformat() if last_activity else None,
            "total_crashes": len(relevant_crashes),
            "total_errors": len(relevant_errors),
            "total_downtime_seconds": round(total_downtime, 1),
            "uptime_percentage": round(uptime_percentage, 2),
            "avg_crash_duration": round(total_downtime / len(relevant_crashes), 1) if relevant_crashes else 0,
            "longest_crash_seconds": max([c["duration_seconds"] for c in relevant_crashes], default=0)
        }
    
    def get_system_health_overview(self) -> Dict[str, Any]:
        """Get overall system health overview."""
        current_time = datetime.now()
        total_stations = len(self.station_last_activity)
        
        if total_stations == 0:
            return {"error": "No station data available"}
        
        # Count stations by status
        status_counts = defaultdict(int)
        active_stations = 0
        inactive_stations = 0
        
        for station_id, last_activity in self.station_last_activity.items():
            current_status = self.station_status.get(station_id, "UNKNOWN")
            status_counts[current_status] += 1
            
            # Check if station is currently active
            time_since_activity = current_time - last_activity
            if time_since_activity < self.inactivity_timeout:
                active_stations += 1
            else:
                inactive_stations += 1
        
        active_percentage = (active_stations / total_stations) * 100
        
        return {
            "report_timestamp": current_time.isoformat(),
            "total_stations": total_stations,
            "active_stations": active_stations,
            "inactive_stations": inactive_stations,
            "active_percentage": round(active_percentage, 1),
            "stations_in_crash_state": len(self.active_crashes),
            "status_distribution": dict(status_counts),
            "system_health": "GOOD" if active_percentage >= 90 else "DEGRADED" if active_percentage >= 70 else "POOR"
        }
    
    def cleanup_old_data(self, hours_to_keep: int = 48) -> None:
        """Clean up old crash and error data."""
        cutoff_time = datetime.now() - timedelta(hours=hours_to_keep)
        
        # Clean crash periods
        for station_id in list(self.crash_periods.keys()):
            crashes = self.crash_periods[station_id]
            recent_crashes = [crash for crash in crashes if crash["start_time"] >= cutoff_time]
            
            if recent_crashes:
                self.crash_periods[station_id] = recent_crashes
            else:
                del self.crash_periods[station_id]
        
        # Clean error events
        for station_id in list(self.error_events.keys()):
            errors = self.error_events[station_id]
            recent_errors = [error for error in errors if error["timestamp"] >= cutoff_time]
            
            if recent_errors:
                self.error_events[station_id] = recent_errors
            else:
                del self.error_events[station_id]


if __name__ == "__main__":
    # Example usage
    logging.basicConfig(level=logging.DEBUG)
    
    detector = SystemCrashDetector(inactivity_timeout_minutes=2, min_crash_duration_seconds=10)
    
    # Simulate station going active
    active_event = {
        "dataset": "POS_Transactions",
        "event": {
            "timestamp": "2025-08-13T16:00:01",
            "station_id": "SCC1",
            "status": "Active",
            "data": {"customer_id": "C001", "sku": "PRD_F_01"}
        }
    }
    
    alert = detector.process_station_event(active_event)
    print(f"Active event alert: {alert}")
    
    # Simulate station error
    error_event = {
        "dataset": "POS_Transactions",
        "event": {
            "timestamp": "2025-08-13T16:02:00",
            "station_id": "SCC1",
            "status": "Error",
            "error_type": "SCANNER_MALFUNCTION"
        }
    }
    
    alert = detector.process_station_event(error_event)
    print(f"Error event alert: {alert}")
    
    # Simulate station recovery
    recovery_event = {
        "dataset": "POS_Transactions",
        "event": {
            "timestamp": "2025-08-13T16:04:30",
            "station_id": "SCC1",
            "status": "Active"
        }
    }
    
    alert = detector.process_station_event(recovery_event)
    print(f"Recovery alert: {alert}")
    
    # Get reliability report
    report = detector.get_station_reliability_report("SCC1")
    print(f"Reliability report: {report}")
    
    # Get system health
    health = detector.get_system_health_overview()
    print(f"System health: {health}")