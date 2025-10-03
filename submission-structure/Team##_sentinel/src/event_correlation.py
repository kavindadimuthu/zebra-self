#!/usr/bin/env python3
"""Event correlation engine for Project Sentinel.

Correlates events across different data streams based on:
- Temporal proximity (time windows)
- Station ID matching
- Customer ID tracking
- Product SKU relationships
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from collections import defaultdict
import threading

logger = logging.getLogger(__name__)


class EventCorrelator:
    """Correlates events across multiple data streams."""
    
    def __init__(self, time_window_seconds: int = 30):
        self.time_window = timedelta(seconds=time_window_seconds)
        self.events_by_station: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self.events_by_customer: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self.lock = threading.RLock()
        self.max_events_per_key = 100
        
    def add_event(self, event: Dict[str, Any]) -> None:
        """Add an event to the correlation engine."""
        with self.lock:
            # Extract key information
            event_data = event.get("event", {})
            timestamp_str = event_data.get("timestamp")
            station_id = event_data.get("station_id")
            customer_id = event_data.get("data", {}).get("customer_id")
            
            if not timestamp_str:
                logger.warning("Event missing timestamp, skipping correlation")
                return
            
            try:
                timestamp = datetime.fromisoformat(timestamp_str)
                enriched_event = {
                    **event,
                    "parsed_timestamp": timestamp,
                    "station_id": station_id,
                    "customer_id": customer_id
                }
                
                # Store by station
                if station_id:
                    self._add_to_buffer(self.events_by_station[station_id], enriched_event)
                
                # Store by customer
                if customer_id:
                    self._add_to_buffer(self.events_by_customer[customer_id], enriched_event)
                    
            except ValueError as e:
                logger.error(f"Invalid timestamp format: {timestamp_str}, error: {e}")
    
    def _add_to_buffer(self, buffer: List[Dict[str, Any]], event: Dict[str, Any]) -> None:
        """Add event to buffer with size limiting."""
        buffer.append(event)
        if len(buffer) > self.max_events_per_key:
            buffer[:] = buffer[-self.max_events_per_key:]
    
    def find_related_events(self, reference_event: Dict[str, Any], 
                          dataset_types: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Find events related to a reference event within the time window."""
        with self.lock:
            ref_timestamp = reference_event.get("parsed_timestamp")
            ref_station = reference_event.get("station_id") 
            ref_customer = reference_event.get("customer_id")
            
            if not ref_timestamp:
                return []
            
            related_events = []
            start_time = ref_timestamp - self.time_window
            end_time = ref_timestamp + self.time_window
            
            # Search by station
            if ref_station and ref_station in self.events_by_station:
                for event in self.events_by_station[ref_station]:
                    if self._is_event_in_window(event, start_time, end_time, dataset_types):
                        related_events.append(event)
            
            # Search by customer
            if ref_customer and ref_customer in self.events_by_customer:
                for event in self.events_by_customer[ref_customer]:
                    if self._is_event_in_window(event, start_time, end_time, dataset_types):
                        related_events.append(event)
            
            # Remove duplicates and reference event itself
            seen = set()
            unique_events = []
            ref_id = id(reference_event)
            
            for event in related_events:
                event_id = id(event)
                if event_id != ref_id and event_id not in seen:
                    seen.add(event_id)
                    unique_events.append(event)
            
            return sorted(unique_events, key=lambda e: e.get("parsed_timestamp", datetime.min))
    
    def _is_event_in_window(self, event: Dict[str, Any], start_time: datetime, 
                           end_time: datetime, dataset_types: Optional[List[str]]) -> bool:
        """Check if event is within time window and matches dataset filter."""
        event_time = event.get("parsed_timestamp")
        if not event_time or not (start_time <= event_time <= end_time):
            return False
        
        if dataset_types:
            event_dataset = event.get("dataset")
            return event_dataset in dataset_types
        
        return True
    
    def find_sequence_patterns(self, station_id: str, pattern_length: int = 3) -> List[List[Dict[str, Any]]]:
        """Find common event sequences at a station."""
        with self.lock:
            if station_id not in self.events_by_station:
                return []
            
            events = sorted(self.events_by_station[station_id], 
                          key=lambda e: e.get("parsed_timestamp", datetime.min))
            
            sequences = []
            for i in range(len(events) - pattern_length + 1):
                sequence = events[i:i+pattern_length]
                # Check if sequence occurs within reasonable time
                if self._is_valid_sequence(sequence):
                    sequences.append(sequence)
            
            return sequences
    
    def _is_valid_sequence(self, sequence: List[Dict[str, Any]], max_duration_minutes: int = 10) -> bool:
        """Check if a sequence is valid (events are close in time)."""
        if len(sequence) < 2:
            return True
        
        first_time = sequence[0].get("parsed_timestamp")
        last_time = sequence[-1].get("parsed_timestamp")
        
        if not first_time or not last_time:
            return False
        
        duration = last_time - first_time
        return duration <= timedelta(minutes=max_duration_minutes)
    
    def get_station_activity_summary(self, station_id: str, hours: int = 1) -> Dict[str, Any]:
        """Get activity summary for a station over the last N hours."""
        with self.lock:
            if station_id not in self.events_by_station:
                return {"station_id": station_id, "events": 0, "datasets": {}}
            
            cutoff_time = datetime.now() - timedelta(hours=hours)
            recent_events = [
                event for event in self.events_by_station[station_id]
                if event.get("parsed_timestamp", datetime.min) >= cutoff_time
            ]
            
            dataset_counts = defaultdict(int)
            for event in recent_events:
                dataset = event.get("dataset", "unknown")
                dataset_counts[dataset] += 1
            
            return {
                "station_id": station_id,
                "events": len(recent_events),
                "datasets": dict(dataset_counts),
                "time_span_hours": hours
            }
    
    def cleanup_old_events(self, hours_to_keep: int = 2) -> None:
        """Remove events older than specified hours to prevent memory buildup."""
        with self.lock:
            cutoff_time = datetime.now() - timedelta(hours=hours_to_keep)
            
            # Clean station events
            for station_id in list(self.events_by_station.keys()):
                events = self.events_by_station[station_id]
                recent_events = [
                    event for event in events
                    if event.get("parsed_timestamp", datetime.max) >= cutoff_time
                ]
                if recent_events:
                    self.events_by_station[station_id] = recent_events
                else:
                    del self.events_by_station[station_id]
            
            # Clean customer events
            for customer_id in list(self.events_by_customer.keys()):
                events = self.events_by_customer[customer_id]
                recent_events = [
                    event for event in events
                    if event.get("parsed_timestamp", datetime.max) >= cutoff_time
                ]
                if recent_events:
                    self.events_by_customer[customer_id] = recent_events
                else:
                    del self.events_by_customer[customer_id]


class TransactionSession:
    """Represents a customer's checkout session."""
    
    def __init__(self, customer_id: str, station_id: str, start_time: datetime):
        self.customer_id = customer_id
        self.station_id = station_id
        self.start_time = start_time
        self.events: List[Dict[str, Any]] = []
        self.rfid_items: List[str] = []
        self.scanned_items: List[str] = []
        self.total_amount = 0.0
        self.is_active = True
    
    def add_event(self, event: Dict[str, Any]) -> None:
        """Add an event to this session."""
        self.events.append(event)
        
        dataset = event.get("dataset", "")
        event_data = event.get("event", {}).get("data", {})
        
        if dataset == "RFID_data":
            sku = event_data.get("sku")
            if sku and sku not in self.rfid_items:
                self.rfid_items.append(sku)
        
        elif dataset == "POS_Transactions":
            sku = event_data.get("sku")
            price = event_data.get("price", 0)
            if sku:
                self.scanned_items.append(sku)
                self.total_amount += price
    
    def get_unscanned_items(self) -> List[str]:
        """Get items detected by RFID but not scanned."""
        return [item for item in self.rfid_items if item not in self.scanned_items]
    
    def get_duration_seconds(self) -> float:
        """Get session duration in seconds."""
        if not self.events:
            return 0.0
        
        last_event_time = max(
            event.get("parsed_timestamp", self.start_time) 
            for event in self.events
        )
        return (last_event_time - self.start_time).total_seconds()


if __name__ == "__main__":
    # Example usage
    logging.basicConfig(level=logging.INFO)
    
    correlator = EventCorrelator(time_window_seconds=60)
    
    # Simulate some events
    test_events = [
        {
            "dataset": "RFID_data",
            "event": {
                "timestamp": "2025-08-13T16:00:01",
                "station_id": "SCC1",
                "data": {"sku": "PRD_F_01", "location": "IN_SCAN_AREA"}
            }
        },
        {
            "dataset": "POS_Transactions", 
            "event": {
                "timestamp": "2025-08-13T16:00:05",
                "station_id": "SCC1",
                "data": {"customer_id": "C001", "sku": "PRD_F_01", "price": 280}
            }
        }
    ]
    
    for event in test_events:
        correlator.add_event(event)
    
    # Find related events
    related = correlator.find_related_events(test_events[0])
    print(f"Found {len(related)} related events")
    
    # Get station summary
    summary = correlator.get_station_activity_summary("SCC1")
    print(f"Station activity: {summary}")