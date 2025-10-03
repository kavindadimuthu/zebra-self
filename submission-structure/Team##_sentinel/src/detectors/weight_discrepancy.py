#!/usr/bin/env python3
"""Weight Discrepancy Detection for Project Sentinel.

Detects when the weight of scanned items doesn't match expected weights,
indicating potential fraud, incorrect product scanning, or scale issues.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


class WeightDiscrepancyDetector:
    """Detects weight mismatches between expected and actual weights."""
    
    def __init__(self, tolerance_percentage: float = 10.0):
        self.tolerance_percentage = tolerance_percentage
        self.product_catalog: Dict[str, Dict[str, Any]] = {}
        self.scale_readings: Dict[str, List[Dict[str, Any]]] = {}  # station -> readings
        
    def load_product_catalog(self, catalog: Dict[str, Dict[str, Any]]) -> None:
        """Load product catalog with expected weights."""
        self.product_catalog = catalog
        logger.info(f"Loaded {len(catalog)} products into weight detector")
    
    # @algorithm WeightDiscrepancyDetector | Flag scale weight mismatches
    def process_pos_transaction(self, event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process POS transaction and check for weight discrepancies."""
        event_data = event.get("event", {})
        data = event_data.get("data", {})
        
        station_id = event_data.get("station_id")
        sku = data.get("sku")
        actual_weight = data.get("weight_g")
        customer_id = data.get("customer_id")
        timestamp_str = event_data.get("timestamp")
        
        if not all([station_id, sku, timestamp_str]):
            return None
        
        # Get expected weight from catalog
        if sku not in self.product_catalog:
            logger.warning(f"SKU {sku} not found in product catalog")
            return None
        
        expected_weight = self.product_catalog[sku].get("weight")
        if not expected_weight:
            return None
        
        # If POS doesn't provide weight, try to get from recent scale readings
        if actual_weight is None:
            actual_weight = self._get_recent_scale_reading(station_id, timestamp_str)
        
        if actual_weight is None:
            logger.debug(f"No weight data available for {sku} at {station_id}")
            return None
        
        # Calculate weight discrepancy
        weight_diff = abs(actual_weight - expected_weight)
        percentage_diff = (weight_diff / expected_weight) * 100
        
        if percentage_diff > self.tolerance_percentage:
            try:
                timestamp = datetime.fromisoformat(timestamp_str)
                return self._generate_weight_discrepancy_alert(
                    station_id, customer_id, sku, expected_weight, 
                    actual_weight, percentage_diff, timestamp
                )
            except ValueError:
                logger.error(f"Invalid timestamp: {timestamp_str}")
        
        return None
    
    def process_scale_reading(self, event: Dict[str, Any]) -> None:
        """Process scale reading events for weight tracking."""
        event_data = event.get("event", {})
        data = event_data.get("data", {})
        
        station_id = event_data.get("station_id")
        weight = data.get("weight_g")
        timestamp_str = event_data.get("timestamp")
        
        if not all([station_id, weight, timestamp_str]):
            return
        
        try:
            timestamp = datetime.fromisoformat(timestamp_str)
        except ValueError:
            return
        
        # Store scale reading
        if station_id not in self.scale_readings:
            self.scale_readings[station_id] = []
        
        self.scale_readings[station_id].append({
            "weight": weight,
            "timestamp": timestamp
        })
        
        # Keep only recent readings (last 5 minutes)
        cutoff_time = timestamp - timedelta(minutes=5)
        self.scale_readings[station_id] = [
            reading for reading in self.scale_readings[station_id]
            if reading["timestamp"] >= cutoff_time
        ]
    
    def _get_recent_scale_reading(self, station_id: str, transaction_time_str: str) -> Optional[float]:
        """Get the most recent scale reading for a station near transaction time."""
        if station_id not in self.scale_readings:
            return None
        
        try:
            transaction_time = datetime.fromisoformat(transaction_time_str)
        except ValueError:
            return None
        
        # Find scale reading closest to transaction time (within 30 seconds)
        closest_reading = None
        min_time_diff = timedelta(seconds=30)
        
        for reading in self.scale_readings[station_id]:
            time_diff = abs(reading["timestamp"] - transaction_time)
            if time_diff < min_time_diff:
                min_time_diff = time_diff
                closest_reading = reading
        
        return closest_reading["weight"] if closest_reading else None
    
    def _generate_weight_discrepancy_alert(self, station_id: str, customer_id: Optional[str], 
                                         sku: str, expected_weight: float, actual_weight: float,
                                         percentage_diff: float, timestamp: datetime) -> Dict[str, Any]:
        """Generate a weight discrepancy alert."""
        severity = "HIGH" if percentage_diff > 50 else "MEDIUM"
        
        alert_data = {
            "event_name": "Weight Discrepancies",
            "station_id": station_id,
            "product_sku": sku,
            "expected_weight": expected_weight,
            "actual_weight": actual_weight,
            "weight_difference_g": round(abs(actual_weight - expected_weight), 1),
            "percentage_difference": round(percentage_diff, 1),
            "severity": severity
        }
        
        if customer_id:
            alert_data["customer_id"] = customer_id
        
        return {
            "timestamp": timestamp.isoformat(),
            "event_id": f"WD_{station_id}_{sku}_{int(timestamp.timestamp())}",
            "event_data": alert_data
        }
    
    def analyze_weight_patterns(self, station_id: str, hours: int = 1) -> Dict[str, Any]:
        """Analyze weight discrepancy patterns for a station."""
        # This would analyze historical weight issues
        # For now, return basic statistics
        
        return {
            "station_id": station_id,
            "analysis_period_hours": hours,
            "total_scale_readings": len(self.scale_readings.get(station_id, [])),
            "pattern_analysis": "Weight patterns within normal range"
        }
    
    def get_product_weight_stats(self, sku: str) -> Optional[Dict[str, Any]]:
        """Get weight statistics for a specific product."""
        if sku not in self.product_catalog:
            return None
        
        product = self.product_catalog[sku]
        return {
            "sku": sku,
            "product_name": product.get("product_name"),
            "expected_weight_g": product.get("weight"),
            "tolerance_percentage": self.tolerance_percentage,
            "weight_range_min": product.get("weight", 0) * (1 - self.tolerance_percentage / 100),
            "weight_range_max": product.get("weight", 0) * (1 + self.tolerance_percentage / 100)
        }
    
    def cleanup_old_data(self, hours_to_keep: int = 2) -> None:
        """Clean up old scale readings to prevent memory buildup."""
        cutoff_time = datetime.now() - timedelta(hours=hours_to_keep)
        
        for station_id in list(self.scale_readings.keys()):
            readings = self.scale_readings[station_id]
            recent_readings = [
                reading for reading in readings 
                if reading["timestamp"] >= cutoff_time
            ]
            
            if recent_readings:
                self.scale_readings[station_id] = recent_readings
            else:
                del self.scale_readings[station_id]


if __name__ == "__main__":
    # Example usage
    logging.basicConfig(level=logging.DEBUG)
    
    detector = WeightDiscrepancyDetector(tolerance_percentage=15.0)
    
    # Load sample product catalog
    catalog = {
        "PRD_F_01": {
            "product_name": "Munchee Chocolate Marie (150g)",
            "weight": 150.0,
            "price": 280
        }
    }
    detector.load_product_catalog(catalog)
    
    # Simulate POS transaction with weight discrepancy
    pos_event = {
        "dataset": "POS_Transactions",
        "event": {
            "timestamp": "2025-08-13T16:00:01",
            "station_id": "SCC1",
            "data": {
                "customer_id": "C001",
                "sku": "PRD_F_01",
                "weight_g": 200.0,  # 33% heavier than expected
                "price": 280
            }
        }
    }
    
    alert = detector.process_pos_transaction(pos_event)
    print(f"Weight discrepancy alert: {alert}")
    
    # Get product weight stats
    stats = detector.get_product_weight_stats("PRD_F_01")
    print(f"Product weight stats: {stats}")