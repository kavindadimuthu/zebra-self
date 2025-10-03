#!/usr/bin/env python3
"""Inventory Discrepancy Detection for Project Sentinel.

Detects mismatches between RFID-counted inventory and recorded inventory levels,
indicating potential theft, miscounting, or system errors.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from collections import defaultdict

logger = logging.getLogger(__name__)


class InventoryDiscrepancyDetector:
    """Detects inventory level discrepancies using RFID vs recorded counts."""
    
    def __init__(self, discrepancy_threshold_percentage: float = 50.0):
        self.discrepancy_threshold = discrepancy_threshold_percentage
        self.recorded_inventory: Dict[str, int] = {}
        self.rfid_counts: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self.last_inventory_snapshot: Optional[datetime] = None
        # Track if we have sufficient RFID data to make meaningful comparisons
        self.rfid_baseline_established = False
        self.min_rfid_events_for_baseline = 20  # Need more RFID events with 2-state system
        self.pos_transactions: List[Dict[str, Any]] = []
        
    def load_inventory_snapshot(self, snapshot_data: Dict[str, int], timestamp: datetime) -> None:
        """Load inventory snapshot from the system."""
        self.recorded_inventory = snapshot_data.copy()
        self.last_inventory_snapshot = timestamp
        logger.info(f"Loaded inventory snapshot with {len(snapshot_data)} SKUs at {timestamp}")
    
    # @algorithm InventoryTracker | Identify stock discrepancies between RFID and recorded inventory
    def process_inventory_snapshot(self, event: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Process inventory snapshot event and check for discrepancies."""
        event_data = event.get("event", {})
        data = event_data.get("data", {})
        timestamp_str = event_data.get("timestamp")
        
        if not timestamp_str or not data:
            return []
        
        try:
            timestamp = datetime.fromisoformat(timestamp_str)
        except ValueError:
            logger.error(f"Invalid timestamp: {timestamp_str}")
            return []
        
        # Update recorded inventory
        self.recorded_inventory = {sku: int(count) for sku, count in data.items()}
        self.last_inventory_snapshot = timestamp
        
        # Only check for discrepancies if we have sufficient RFID data
        if not self.rfid_baseline_established:
            total_rfid_events = sum(location_counts.values() for location_counts in self.rfid_counts.values())
            if total_rfid_events < self.min_rfid_events_for_baseline:
                logger.debug(f"Insufficient RFID data for inventory comparison: {total_rfid_events} events")
                return []
            self.rfid_baseline_established = True
        
        # Check for discrepancies - with 2-state RFID, we look for unusual patterns
        # RFID counts represent items currently in scan areas, not total inventory
        alerts = []
        for sku, recorded_count in self.recorded_inventory.items():
            rfid_detected = self._get_total_rfid_count(sku)
            
            # Flag discrepancy only if:
            # 1. Items are detected by RFID but not recorded in inventory (impossible scenario)
            # 2. Recorded inventory dropped significantly but no RFID activity (potential theft)
            if rfid_detected > recorded_count:
                # More RFID detections than recorded inventory - suspicious
                discrepancy = self._calculate_discrepancy(recorded_count, rfid_detected)
                if discrepancy and abs(discrepancy["percentage"]) >= self.discrepancy_threshold:
                    alert = self._generate_inventory_discrepancy_alert(
                        sku, recorded_count, rfid_detected, discrepancy, timestamp
                    )
                    alerts.append(alert)
        
        return alerts
    
    def process_rfid_event(self, event: Dict[str, Any]) -> None:
        """Process RFID reading to update real-time inventory counts."""
        event_data = event.get("event", {})
        data = event_data.get("data", {})
        
        sku = data.get("sku")
        location = data.get("location")
        epc = data.get("epc")
        timestamp_str = event_data.get("timestamp")
        
        if not all([sku, epc, timestamp_str, location]):
            return
        
        try:
            timestamp = datetime.fromisoformat(timestamp_str)
        except ValueError:
            return
        
        # Track RFID count with only 2 states: IN_SCAN_AREA and OUT_SCAN_AREA
        if location == "IN_SCAN_AREA":
            # Item detected in scan area - increment count (item present)
            self.rfid_counts["DETECTED"][sku] += 1
        elif location == "OUT_SCAN_AREA":
            # Item left scan area - decrement count (item removed/sold)
            if self.rfid_counts["DETECTED"][sku] > 0:
                self.rfid_counts["DETECTED"][sku] -= 1
    
    def process_pos_transaction(self, event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process POS transaction to update inventory and detect discrepancies."""
        event_data = event.get("event", {})
        data = event_data.get("data", {})
        
        sku = data.get("sku")
        customer_id = data.get("customer_id")
        timestamp_str = event_data.get("timestamp")
        
        if not all([sku, timestamp_str]):
            return None
        
        try:
            timestamp = datetime.fromisoformat(timestamp_str)
        except ValueError:
            return None
        
        # Record transaction
        transaction = {
            "sku": sku,
            "customer_id": customer_id,
            "timestamp": timestamp,
            "quantity": 1  # Assume 1 item per transaction
        }
        self.pos_transactions.append(transaction)
        
        # Clean old transactions (keep last 24 hours)
        cutoff_time = timestamp - timedelta(hours=24)
        self.pos_transactions = [
            t for t in self.pos_transactions if t["timestamp"] >= cutoff_time
        ]
        
        # Update recorded inventory if we have it
        if sku in self.recorded_inventory:
            self.recorded_inventory[sku] = max(0, self.recorded_inventory[sku] - 1)
            
            # Check for immediate discrepancy
            rfid_count = self._get_total_rfid_count(sku)
            recorded_count = self.recorded_inventory[sku]
            
            discrepancy = self._calculate_discrepancy(recorded_count, rfid_count)
            if discrepancy and abs(discrepancy["percentage"]) >= self.discrepancy_threshold:
                return self._generate_inventory_discrepancy_alert(
                    sku, recorded_count, rfid_count, discrepancy, timestamp
                )
        
        return None
    
    def _get_total_rfid_count(self, sku: str) -> int:
        """Get total RFID count for a SKU (items currently detected by RFID)."""
        return self.rfid_counts["DETECTED"].get(sku, 0)
    
    def _calculate_discrepancy(self, recorded: int, rfid: int) -> Optional[Dict[str, Any]]:
        """Calculate discrepancy between recorded and RFID counts."""
        if recorded == 0 and rfid == 0:
            return None
        
        difference = rfid - recorded
        percentage = (difference / max(recorded, 1)) * 100
        
        return {
            "difference": difference,
            "percentage": percentage,
            "type": "OVERAGE" if difference > 0 else "SHORTAGE"
        }
    
    def _generate_inventory_discrepancy_alert(self, sku: str, recorded_count: int, 
                                            rfid_count: int, discrepancy: Dict[str, Any],
                                            timestamp: datetime) -> Dict[str, Any]:
        """Generate inventory discrepancy alert."""
        severity = "HIGH" if abs(discrepancy["percentage"]) > 25 else "MEDIUM"
        
        return {
            "timestamp": timestamp.isoformat(),
            "event_id": f"ID_{sku}_{int(timestamp.timestamp())}",
            "event_data": {
                "event_name": "Inventory Discrepancy",
                "SKU": sku,
                "Expected_Inventory": recorded_count,
                "Actual_Inventory": rfid_count,
                "difference": discrepancy["difference"],
                "percentage_difference": round(discrepancy["percentage"], 1),
                "discrepancy_type": discrepancy["type"],
                "severity": severity
            }
        }
    
    def get_inventory_accuracy_report(self) -> Dict[str, Any]:
        """Generate inventory accuracy report."""
        if not self.recorded_inventory:
            return {"error": "No inventory data available"}
        
        total_skus = len(self.recorded_inventory)
        discrepant_skus = 0
        total_recorded = sum(self.recorded_inventory.values())
        total_rfid = 0
        
        discrepancies = []
        
        for sku, recorded_count in self.recorded_inventory.items():
            rfid_count = self._get_total_rfid_count(sku)
            total_rfid += rfid_count
            
            discrepancy = self._calculate_discrepancy(recorded_count, rfid_count)
            if discrepancy and abs(discrepancy["percentage"]) >= self.discrepancy_threshold:
                discrepant_skus += 1
                discrepancies.append({
                    "sku": sku,
                    "recorded": recorded_count,
                    "rfid": rfid_count,
                    "difference": discrepancy["difference"],
                    "percentage": round(discrepancy["percentage"], 1),
                    "type": discrepancy["type"]
                })
        
        accuracy_percentage = ((total_skus - discrepant_skus) / total_skus) * 100 if total_skus > 0 else 0
        
        return {
            "report_timestamp": datetime.now().isoformat(),
            "last_inventory_snapshot": self.last_inventory_snapshot.isoformat() if self.last_inventory_snapshot else None,
            "total_skus": total_skus,
            "discrepant_skus": discrepant_skus,
            "accuracy_percentage": round(accuracy_percentage, 1),
            "total_recorded_items": total_recorded,
            "total_rfid_items": total_rfid,
            "overall_difference": total_rfid - total_recorded,
            "discrepancies": sorted(discrepancies, key=lambda x: abs(x["percentage"]), reverse=True)[:10]
        }
    
    def get_sku_inventory_status(self, sku: str) -> Dict[str, Any]:
        """Get detailed inventory status for a specific SKU."""
        if sku not in self.recorded_inventory:
            return {"sku": sku, "error": "SKU not found in inventory"}
        
        recorded_count = self.recorded_inventory[sku]
        rfid_count = self._get_total_rfid_count(sku)
        
        # Get RFID count by location
        rfid_by_location = {}
        for location, location_counts in self.rfid_counts.items():
            if sku in location_counts and location_counts[sku] > 0:
                rfid_by_location[location] = location_counts[sku]
        
        # Get recent transactions
        recent_transactions = [
            t for t in self.pos_transactions[-10:] if t["sku"] == sku
        ]
        
        discrepancy = self._calculate_discrepancy(recorded_count, rfid_count)
        
        return {
            "sku": sku,
            "recorded_inventory": recorded_count,
            "rfid_total_count": rfid_count,
            "rfid_by_location": rfid_by_location,
            "discrepancy": discrepancy,
            "recent_transactions": len(recent_transactions),
            "last_transaction": recent_transactions[-1]["timestamp"].isoformat() if recent_transactions else None
        }
    
    def get_location_inventory_summary(self) -> Dict[str, Dict[str, int]]:
        """Get inventory summary by location."""
        summary = {}
        for location, location_counts in self.rfid_counts.items():
            if location_counts:
                summary[location] = dict(location_counts)
        return summary
    
    def cleanup_old_data(self, hours_to_keep: int = 24) -> None:
        """Clean up old transaction data."""
        if not self.pos_transactions:
            return
        
        cutoff_time = datetime.now() - timedelta(hours=hours_to_keep)
        self.pos_transactions = [
            t for t in self.pos_transactions if t["timestamp"] >= cutoff_time
        ]


if __name__ == "__main__":
    # Example usage
    logging.basicConfig(level=logging.DEBUG)
    
    detector = InventoryDiscrepancyDetector(discrepancy_threshold_percentage=15.0)
    
    # Load initial inventory
    initial_inventory = {
        "PRD_F_01": 100,
        "PRD_F_02": 80,
        "PRD_F_03": 120
    }
    detector.load_inventory_snapshot(initial_inventory, datetime.now())
    
    # Simulate RFID readings showing different counts
    for i in range(90):  # Simulate 90 RFID readings for PRD_F_01 (vs 100 recorded)
        rfid_event = {
            "event": {
                "timestamp": datetime.now().isoformat(),
                "data": {
                    "sku": "PRD_F_01",
                    "location": "STORE_FLOOR",
                    "epc": f"EPC00000{i:03d}"
                }
            }
        }
        detector.process_rfid_event(rfid_event)
    
    # Check for discrepancies
    inventory_event = {
        "event": {
            "timestamp": datetime.now().isoformat(),
            "data": initial_inventory
        }
    }
    
    alerts = detector.process_inventory_snapshot(inventory_event)
    print(f"Generated {len(alerts)} inventory alerts")
    
    for alert in alerts:
        print(f"Alert: {alert['event_data']['SKU']} - {alert['event_data']['discrepancy_type']}")
    
    # Get accuracy report
    report = detector.get_inventory_accuracy_report()
    print(f"Inventory accuracy: {report['accuracy_percentage']}%")
    
    # Get SKU status
    sku_status = detector.get_sku_inventory_status("PRD_F_01")
    print(f"SKU PRD_F_01 status: {sku_status}")