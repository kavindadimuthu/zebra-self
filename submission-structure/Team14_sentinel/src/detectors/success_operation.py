#!/usr/bin/env python3
"""Success Operation Detection for Project Sentinel.

Tracks successful transactions and operations to provide positive indicators
and baseline metrics for normal system operation.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


class SuccessOperationDetector:
    """Tracks successful operations and normal transactions."""
    
    def __init__(self):
        self.successful_transactions = []
        self.last_success_per_station = {}
        
    # @algorithm SuccessOperationDetector | Track successful transactions and normal operations
    def process_pos_transaction(self, event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process POS transaction and generate success operation if appropriate."""
        try:
            # Handle both formats: direct event format and wrapped event format
            if "event" in event:
                event_data = event.get("event", {})
                data = event_data.get("data", {})
                station_id = event_data.get("station_id")
                timestamp_str = event_data.get("timestamp")
                status = event_data.get("status", "")
            else:
                # Direct format (current streaming format)
                event_data = event
                data = event_data.get("data", {})
                station_id = event_data.get("station_id")
                timestamp_str = event_data.get("timestamp")
                status = event_data.get("status", "")
            
            if not all([station_id, timestamp_str]):
                return None
                
            # Only process "Active" status transactions
            if status != "Active":
                return None
            
            try:
                timestamp = datetime.fromisoformat(timestamp_str)
            except ValueError:
                logger.error(f"Invalid timestamp: {timestamp_str}")
                return None
            
            customer_id = data.get("customer_id")
            sku = data.get("sku")
            product_name = data.get("product_name")
            
            if not all([customer_id, sku]):
                return None
            
            # Generate success operation for every few transactions to show normal operations
            # This simulates successful checkout completion
            success_alert = self._generate_success_operation_alert(
                station_id, customer_id, sku, timestamp
            )
            
            # Track this as a successful transaction
            self.successful_transactions.append({
                "station_id": station_id,
                "customer_id": customer_id,
                "sku": sku,
                "timestamp": timestamp
            })
            
            # Keep only recent transactions (last hour)
            cutoff_time = timestamp - timedelta(hours=1)
            self.successful_transactions = [
                tx for tx in self.successful_transactions
                if tx["timestamp"] >= cutoff_time
            ]
            
            self.last_success_per_station[station_id] = timestamp
            
            return success_alert
            
        except Exception as e:
            logger.error(f"Error processing success operation: {e}")
            return None
    
    def _generate_success_operation_alert(self, station_id: str, customer_id: str, 
                                        product_sku: str, timestamp: datetime) -> Dict[str, Any]:
        """Generate success operation alert."""
        
        return {
            "timestamp": timestamp.isoformat(),
            "event_id": f"SO_{station_id}_{customer_id}_{int(timestamp.timestamp())}",
            "event_data": {
                "event_name": "Success Operation",
                "station_id": station_id,
                "customer_id": customer_id,
                "product_sku": product_sku
            }
        }
    
    def get_success_rate(self, station_id: str, hours: int = 1) -> Dict[str, Any]:
        """Calculate success rate for a station."""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        recent_transactions = [
            tx for tx in self.successful_transactions
            if tx["station_id"] == station_id and tx["timestamp"] >= cutoff_time
        ]
        
        return {
            "station_id": station_id,
            "period_hours": hours,
            "successful_transactions": len(recent_transactions),
            "transactions_per_hour": len(recent_transactions) / hours if hours > 0 else 0,
            "last_success": self.last_success_per_station.get(station_id)
        }


if __name__ == "__main__":
    # Example usage
    logging.basicConfig(level=logging.DEBUG)
    
    detector = SuccessOperationDetector()
    
    # Test with sample POS transaction
    sample_event = {
        "timestamp": "2025-08-13T16:00:00",
        "station_id": "SCC1",
        "status": "Active",
        "data": {
            "customer_id": "C001",
            "sku": "PRD_F_03",
            "product_name": "Coca Cola (330ml)",
            "price": 150.0
        }
    }
    
    result = detector.process_pos_transaction(sample_event)
    if result:
        print("Success Operation Generated:")
        print(result)