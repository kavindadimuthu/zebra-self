#!/usr/bin/env python3
"""Barcode Switching Detection for Project Sentinel.

Detects when customers scan cheaper items instead of more expensive ones,
by correlating product recognition with POS scans and price differences.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Set
from collections import defaultdict

logger = logging.getLogger(__name__)


class BarcodeSwitchingDetector:
    """Detects barcode switching fraud attempts."""
    
    def __init__(self, time_window_seconds: int = 60, min_price_difference: float = 50.0):
        self.time_window = timedelta(seconds=time_window_seconds)
        self.min_price_difference = min_price_difference
        self.product_catalog: Dict[str, Dict[str, Any]] = {}
        self.recognition_events: Dict[str, List[Dict[str, Any]]] = defaultdict(list)  # station -> events
        self.pos_events: Dict[str, List[Dict[str, Any]]] = defaultdict(list)  # station -> events
        self.alerts_generated: Set[str] = set()
        
    def load_product_catalog(self, catalog: Dict[str, Dict[str, Any]]) -> None:
        """Load product catalog with prices."""
        self.product_catalog = catalog
        logger.info(f"Loaded {len(catalog)} products into barcode switching detector")
    
    # @algorithm BarcodeSwitchingDetector | Detect price/weight mismatches between recognition and POS
    def process_product_recognition(self, event: Dict[str, Any]) -> None:
        """Process product recognition event."""
        # Handle both formats: direct event format and wrapped event format
        if "event" in event:
            event_data = event.get("event", {})
            data = event_data.get("data", {})
            station_id = event_data.get("station_id")
            timestamp_str = event_data.get("timestamp")
        else:
            # Direct format (current streaming format)
            event_data = event
            data = event_data.get("data", {})
            station_id = event_data.get("station_id")
            timestamp_str = event_data.get("timestamp")
        
        predicted_product = data.get("predicted_product")
        accuracy = data.get("accuracy", 0.0)
        
        if not all([station_id, predicted_product, timestamp_str]):
            return
        
        try:
            timestamp = datetime.fromisoformat(timestamp_str)
        except ValueError:
            logger.error(f"Invalid timestamp: {timestamp_str}")
            return
        
        # Only consider high-confidence predictions
        if accuracy < 0.6:
            logger.debug(f"Low confidence prediction ({accuracy}) for {predicted_product}, skipping")
            return
        
        # Store recognition event
        recognition_data = {
            "predicted_sku": predicted_product,
            "accuracy": accuracy,
            "timestamp": timestamp,
            "station_id": station_id
        }
        
        self.recognition_events[station_id].append(recognition_data)
        
        # Keep only recent events
        cutoff_time = timestamp - timedelta(hours=1)
        self.recognition_events[station_id] = [
            event for event in self.recognition_events[station_id]
            if event["timestamp"] >= cutoff_time
        ]
    
    def process_pos_transaction(self, event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process POS transaction and check for barcode switching."""
        # Handle both formats: direct event format and wrapped event format
        if "event" in event:
            event_data = event.get("event", {})
            data = event_data.get("data", {})
            station_id = event_data.get("station_id")
            timestamp_str = event_data.get("timestamp")
        else:
            # Direct format (current streaming format)
            event_data = event
            data = event_data.get("data", {})
            station_id = event_data.get("station_id")
            timestamp_str = event_data.get("timestamp")
        
        scanned_sku = data.get("sku")
        customer_id = data.get("customer_id")
        
        if not all([station_id, scanned_sku, timestamp_str]):
            return None
        
        try:
            timestamp = datetime.fromisoformat(timestamp_str)
        except ValueError:
            logger.error(f"Invalid timestamp: {timestamp_str}")
            return None
        
        # Store POS event
        pos_data = {
            "scanned_sku": scanned_sku,
            "customer_id": customer_id,
            "timestamp": timestamp,
            "station_id": station_id
        }
        
        self.pos_events[station_id].append(pos_data)
        
        # Keep only recent events
        cutoff_time = timestamp - timedelta(hours=1)
        self.pos_events[station_id] = [
            event for event in self.pos_events[station_id]
            if event["timestamp"] >= cutoff_time
        ]
        
        # Check for barcode switching
        return self._check_barcode_switching(pos_data)
    
    def _check_barcode_switching(self, pos_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Check if this POS transaction indicates barcode switching."""
        station_id = pos_data["station_id"]
        scanned_sku = pos_data["scanned_sku"]
        timestamp = pos_data["timestamp"]
        
        # Find recent recognition events at this station
        start_time = timestamp - self.time_window
        end_time = timestamp + timedelta(seconds=30)  # Allow small delay after recognition
        
        relevant_recognitions = [
            event for event in self.recognition_events.get(station_id, [])
            if start_time <= event["timestamp"] <= end_time
        ]
        
        if not relevant_recognitions:
            logger.debug(f"No recent recognition events for station {station_id}")
            return None
        
        # Find the most recent recognition event
        latest_recognition = max(relevant_recognitions, key=lambda e: e["timestamp"])
        predicted_sku = latest_recognition["predicted_sku"]
        
        # If recognition matches scan, no switching detected
        if predicted_sku == scanned_sku:
            return None
        
        # Check if both products exist in catalog
        if predicted_sku not in self.product_catalog or scanned_sku not in self.product_catalog:
            logger.debug(f"Missing catalog data for {predicted_sku} or {scanned_sku}")
            return None
        
        predicted_price = self.product_catalog[predicted_sku].get("price", 0)
        scanned_price = self.product_catalog[scanned_sku].get("price", 0)
        
        price_difference = predicted_price - scanned_price
        
        # Only alert if customer scanned significantly cheaper item
        if price_difference >= self.min_price_difference:
            alert_key = f"{station_id}_{predicted_sku}_{scanned_sku}_{timestamp.isoformat()}"
            if alert_key not in self.alerts_generated:
                self.alerts_generated.add(alert_key)
                return self._generate_barcode_switching_alert(
                    station_id, pos_data["customer_id"], predicted_sku, scanned_sku,
                    predicted_price, scanned_price, latest_recognition["accuracy"], timestamp
                )
        
        return None
    
    def _generate_barcode_switching_alert(self, station_id: str, customer_id: Optional[str],
                                        predicted_sku: str, scanned_sku: str,
                                        predicted_price: float, scanned_price: float,
                                        recognition_accuracy: float, timestamp: datetime) -> Dict[str, Any]:
        """Generate barcode switching alert."""
        price_difference = predicted_price - scanned_price
        percentage_savings = (price_difference / predicted_price) * 100
        
        severity = "HIGH" if price_difference > 200 else "MEDIUM"
        
        alert_data = {
            "event_name": "Barcode Switching",
            "station_id": station_id,
            "actual_sku": predicted_sku,
            "scanned_sku": scanned_sku,
            "expected_price": predicted_price,
            "scanned_price": scanned_price,
            "price_difference": round(price_difference, 2),
            "percentage_savings": round(percentage_savings, 1),
            "recognition_confidence": round(recognition_accuracy, 2),
            "severity": severity
        }
        
        if customer_id:
            alert_data["customer_id"] = customer_id
        
        return {
            "timestamp": timestamp.isoformat(),
            "event_id": f"BS_{station_id}_{predicted_sku}_{scanned_sku}_{int(timestamp.timestamp())}",
            "event_data": alert_data
        }
    
    def get_switching_patterns(self, station_id: str, hours: int = 4) -> Dict[str, Any]:
        """Analyze barcode switching patterns for a station."""
        if station_id not in self.recognition_events:
            return {"station_id": station_id, "error": "No recognition data"}
        
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        recent_recognitions = [
            event for event in self.recognition_events[station_id]
            if event["timestamp"] >= cutoff_time
        ]
        
        recent_pos = [
            event for event in self.pos_events.get(station_id, [])
            if event["timestamp"] >= cutoff_time
        ]
        
        # Calculate match rate
        matches = 0
        potential_switches = 0
        
        for pos_event in recent_pos:
            # Find corresponding recognition
            pos_time = pos_event["timestamp"]
            relevant_recognitions = [
                rec for rec in recent_recognitions
                if abs((rec["timestamp"] - pos_time).total_seconds()) <= self.time_window.total_seconds()
            ]
            
            if relevant_recognitions:
                latest_rec = max(relevant_recognitions, key=lambda e: e["timestamp"])
                if latest_rec["predicted_sku"] == pos_event["scanned_sku"]:
                    matches += 1
                else:
                    potential_switches += 1
        
        total_correlated = matches + potential_switches
        match_rate = (matches / total_correlated * 100) if total_correlated > 0 else 0
        
        return {
            "station_id": station_id,
            "analysis_period_hours": hours,
            "total_recognitions": len(recent_recognitions),
            "total_pos_transactions": len(recent_pos),
            "correlated_events": total_correlated,
            "matches": matches,
            "potential_switches": potential_switches,
            "match_rate_percentage": round(match_rate, 1),
            "switching_rate_percentage": round(100 - match_rate, 1) if total_correlated > 0 else 0
        }
    
    def get_high_risk_products(self) -> List[Dict[str, Any]]:
        """Get products most frequently involved in switching attempts."""
        # Analyze which expensive products are most often "switched" with cheaper ones
        product_risks = []
        
        for sku, product in self.product_catalog.items():
            price = product.get("price", 0)
            if price > 100:  # Only consider moderately expensive items
                # Count how often this product was recognized but something cheaper was scanned
                # This is a simplified analysis - in practice you'd track this over time
                risk_score = price / 100  # Simple heuristic
                
                product_risks.append({
                    "sku": sku,
                    "product_name": product.get("product_name"),
                    "price": price,
                    "risk_score": round(risk_score, 1),
                    "reason": "High-value item susceptible to switching"
                })
        
        return sorted(product_risks, key=lambda x: x["risk_score"], reverse=True)[:10]
    
    def cleanup_old_data(self, hours_to_keep: int = 4) -> None:
        """Clean up old recognition and POS data."""
        cutoff_time = datetime.now() - timedelta(hours=hours_to_keep)
        
        # Clean recognition events
        for station_id in list(self.recognition_events.keys()):
            events = self.recognition_events[station_id]
            recent_events = [event for event in events if event["timestamp"] >= cutoff_time]
            
            if recent_events:
                self.recognition_events[station_id] = recent_events
            else:
                del self.recognition_events[station_id]
        
        # Clean POS events
        for station_id in list(self.pos_events.keys()):
            events = self.pos_events[station_id]
            recent_events = [event for event in events if event["timestamp"] >= cutoff_time]
            
            if recent_events:
                self.pos_events[station_id] = recent_events
            else:
                del self.pos_events[station_id]


if __name__ == "__main__":
    # Example usage
    logging.basicConfig(level=logging.DEBUG)
    
    detector = BarcodeSwitchingDetector(time_window_seconds=30, min_price_difference=20.0)
    
    # Load sample catalog
    catalog = {
        "PRD_F_01": {"product_name": "Expensive Product", "price": 500.0},
        "PRD_F_02": {"product_name": "Cheap Product", "price": 100.0}
    }
    detector.load_product_catalog(catalog)
    
    # Simulate product recognition
    recognition_event = {
        "dataset": "Product_recognism",
        "event": {
            "timestamp": "2025-08-13T16:00:01",
            "station_id": "SCC1",
            "data": {
                "predicted_product": "PRD_F_01",
                "accuracy": 0.85
            }
        }
    }
    
    detector.process_product_recognition(recognition_event)
    
    # Simulate POS scan of different (cheaper) product
    pos_event = {
        "dataset": "POS_Transactions",
        "event": {
            "timestamp": "2025-08-13T16:00:15",
            "station_id": "SCC1",
            "data": {
                "customer_id": "C001",
                "sku": "PRD_F_02",
                "price": 100.0
            }
        }
    }
    
    alert = detector.process_pos_transaction(pos_event)
    print(f"Barcode switching alert: {alert}")
    
    # Get switching patterns
    patterns = detector.get_switching_patterns("SCC1")
    print(f"Switching patterns: {patterns}")
    
    # Get high-risk products
    high_risk = detector.get_high_risk_products()
    print(f"High-risk products: {high_risk}")