#!/usr/bin/env python3
"""Scan Avoidance Detection for Project Sentinel.

Detects when items are present in the scan area (via RFID) but not scanned 
at the POS terminal, indicating potential theft or scanning issues.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Set
from collections import defaultdict

logger = logging.getLogger(__name__)


class ScanAvoidanceDetector:
    """Detects items in scan area that aren't being scanned."""
    
    def __init__(self, scan_timeout_seconds: int = 60):
        self.scan_timeout = timedelta(seconds=scan_timeout_seconds)
        self.rfid_items_in_area: Dict[str, Dict[str, Any]] = {}  # station -> {sku: event_data}
        self.recent_scans: Dict[str, List[Dict[str, Any]]] = defaultdict(list)  # station -> scan_events
        self.alerts_generated: Set[str] = set()  # Track to avoid duplicates
        
    # @algorithm ScanAvoidanceDetector | Detect items in scan area but not in POS
    def process_rfid_event(self, event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process an RFID event and track items in scan area."""
        event_data = event.get("event", {})
        data = event_data.get("data", {})
        station_id = event_data.get("station_id")
        location = data.get("location")
        sku = data.get("sku")
        timestamp_str = event_data.get("timestamp")
        
        if not all([station_id, sku, location, timestamp_str]):
            return None
        
        try:
            timestamp = datetime.fromisoformat(timestamp_str)
        except ValueError:
            logger.error(f"Invalid timestamp in RFID event: {timestamp_str}")
            return None
        
        # Track items entering scan area
        if location == "IN_SCAN_AREA":
            if station_id not in self.rfid_items_in_area:
                self.rfid_items_in_area[station_id] = {}
            
            self.rfid_items_in_area[station_id][sku] = {
                "sku": sku,
                "timestamp": timestamp,
                "event": event_data
            }
            logger.debug(f"Item {sku} entered scan area at {station_id}")
        
        # Remove items leaving scan area
        elif location == "OUT_OF_AREA":
            if (station_id in self.rfid_items_in_area and 
                sku in self.rfid_items_in_area[station_id]):
                
                item_data = self.rfid_items_in_area[station_id][sku]
                time_in_area = timestamp - item_data["timestamp"]
                
                # Check if item was scanned while in area
                if not self._was_item_scanned(station_id, sku, item_data["timestamp"], timestamp):
                    alert_key = f"{station_id}_{sku}_{timestamp.isoformat()}"
                    if alert_key not in self.alerts_generated:
                        self.alerts_generated.add(alert_key)
                        return self._generate_scan_avoidance_alert(
                            station_id, sku, item_data["timestamp"], time_in_area.total_seconds()
                        )
                
                del self.rfid_items_in_area[station_id][sku]
        
        return None
    
    def process_pos_event(self, event: Dict[str, Any]) -> None:
        """Process a POS transaction to track scanned items."""
        event_data = event.get("event", {})
        data = event_data.get("data", {})
        station_id = event_data.get("station_id")
        sku = data.get("sku")
        timestamp_str = event_data.get("timestamp")
        
        if not all([station_id, sku, timestamp_str]):
            return
        
        try:
            timestamp = datetime.fromisoformat(timestamp_str)
        except ValueError:
            return
        
        # Record the scan
        scan_event = {
            "sku": sku,
            "timestamp": timestamp,
            "customer_id": data.get("customer_id"),
            "price": data.get("price")
        }
        
        self.recent_scans[station_id].append(scan_event)
        
        # Keep only recent scans (last hour)
        cutoff_time = timestamp - timedelta(hours=1)
        self.recent_scans[station_id] = [
            scan for scan in self.recent_scans[station_id]
            if scan["timestamp"] >= cutoff_time
        ]
        
        # Remove from RFID tracking if scanned
        if (station_id in self.rfid_items_in_area and 
            sku in self.rfid_items_in_area[station_id]):
            del self.rfid_items_in_area[station_id][sku]
    
    def _was_item_scanned(self, station_id: str, sku: str, 
                         start_time: datetime, end_time: datetime) -> bool:
        """Check if item was scanned during the specified time period."""
        if station_id not in self.recent_scans:
            return False
        
        for scan in self.recent_scans[station_id]:
            if (scan["sku"] == sku and 
                start_time <= scan["timestamp"] <= end_time):
                return True
        
        return False
    
    def _generate_scan_avoidance_alert(self, station_id: str, sku: str, 
                                     entry_time: datetime, dwell_seconds: float) -> Dict[str, Any]:
        """Generate a scan avoidance alert event."""
        return {
            "timestamp": datetime.now().isoformat(),
            "event_id": f"SA_{station_id}_{sku}_{int(entry_time.timestamp())}",
            "event_data": {
                "event_name": "Scanner Avoidance",
                "station_id": station_id,
                "product_sku": sku,
                "entry_time": entry_time.isoformat(),
                "dwell_time_seconds": round(dwell_seconds, 1),
                "severity": "HIGH" if dwell_seconds > 30 else "MEDIUM"
            }
        }
    
    def check_timeout_alerts(self) -> List[Dict[str, Any]]:
        """Check for items that have been in scan area too long without scanning."""
        current_time = datetime.now()
        alerts = []
        
        for station_id, items in self.rfid_items_in_area.items():
            for sku, item_data in list(items.items()):
                time_in_area = current_time - item_data["timestamp"]
                
                if time_in_area > self.scan_timeout:
                    alert_key = f"{station_id}_{sku}_timeout_{current_time.isoformat()}"
                    if alert_key not in self.alerts_generated:
                        self.alerts_generated.add(alert_key)
                        
                        alert = self._generate_scan_avoidance_alert(
                            station_id, sku, item_data["timestamp"], time_in_area.total_seconds()
                        )
                        alert["event_data"]["alert_type"] = "TIMEOUT"
                        alerts.append(alert)
                        
                        # Remove from tracking to avoid repeat alerts
                        del items[sku]
        
        return alerts
    
    def get_current_unscanned_items(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get all items currently in scan areas that haven't been scanned."""
        current_items = {}
        current_time = datetime.now()
        
        for station_id, items in self.rfid_items_in_area.items():
            station_items = []
            for sku, item_data in items.items():
                time_in_area = current_time - item_data["timestamp"]
                station_items.append({
                    "sku": sku,
                    "entry_time": item_data["timestamp"].isoformat(),
                    "time_in_area_seconds": time_in_area.total_seconds()
                })
            
            if station_items:
                current_items[station_id] = station_items
        
        return current_items
    
    def cleanup_old_data(self, hours_to_keep: int = 2) -> None:
        """Clean up old tracking data to prevent memory buildup."""
        cutoff_time = datetime.now() - timedelta(hours=hours_to_keep)
        
        # Clean RFID tracking
        for station_id in list(self.rfid_items_in_area.keys()):
            items = self.rfid_items_in_area[station_id]
            for sku in list(items.keys()):
                if items[sku]["timestamp"] < cutoff_time:
                    del items[sku]
            
            if not items:
                del self.rfid_items_in_area[station_id]
        
        # Clean recent scans
        for station_id in list(self.recent_scans.keys()):
            scans = self.recent_scans[station_id]
            recent_scans = [scan for scan in scans if scan["timestamp"] >= cutoff_time]
            if recent_scans:
                self.recent_scans[station_id] = recent_scans
            else:
                del self.recent_scans[station_id]


if __name__ == "__main__":
    # Example usage
    logging.basicConfig(level=logging.DEBUG)
    
    detector = ScanAvoidanceDetector(scan_timeout_seconds=30)
    
    # Simulate RFID event - item enters scan area
    rfid_event = {
        "dataset": "RFID_data",
        "event": {
            "timestamp": "2025-08-13T16:00:01",
            "station_id": "SCC1",
            "data": {
                "sku": "PRD_F_01",
                "location": "IN_SCAN_AREA",
                "epc": "E280116060000000000000001"
            }
        }
    }
    
    alert = detector.process_rfid_event(rfid_event)
    print(f"RFID in area alert: {alert}")
    
    # Simulate item leaving without being scanned
    rfid_out_event = {
        "dataset": "RFID_data", 
        "event": {
            "timestamp": "2025-08-13T16:00:45",
            "station_id": "SCC1",
            "data": {
                "sku": "PRD_F_01",
                "location": "OUT_OF_AREA",
                "epc": "E280116060000000000000001"
            }
        }
    }
    
    alert = detector.process_rfid_event(rfid_out_event)
    print(f"Scan avoidance alert: {alert}")
    
    # Check current unscanned items
    unscanned = detector.get_current_unscanned_items()
    print(f"Current unscanned items: {unscanned}")