#!/usr/bin/env python3
"""Data ingestion module for Project Sentinel streaming data.

Connects to the TCP streaming server and parses incoming JSONL events from:
- RFID readings
- Queue monitoring
- POS transactions  
- Product recognition
- Inventory snapshots
"""

import json
import socket
import logging
import threading
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime
import queue

logger = logging.getLogger(__name__)


class StreamingDataClient:
    """TCP client for consuming Project Sentinel data streams."""
    
    def __init__(self, host: str = "127.0.0.1", port: int = 8765):
        self.host = host
        self.port = port
        self.running = False
        self.events_queue = queue.Queue()
        self.callbacks: Dict[str, List[Callable]] = {}
        
    def register_callback(self, dataset_type: str, callback: Callable[[Dict[str, Any]], None]):
        """Register a callback function for specific dataset events."""
        if dataset_type not in self.callbacks:
            self.callbacks[dataset_type] = []
        self.callbacks[dataset_type].append(callback)
    
    def start_streaming(self) -> None:
        """Start the streaming client in a separate thread."""
        self.running = True
        thread = threading.Thread(target=self._stream_worker, daemon=True)
        thread.start()
        logger.info(f"Started streaming client for {self.host}:{self.port}")
    
    def stop_streaming(self) -> None:
        """Stop the streaming client."""
        self.running = False
        logger.info("Stopping streaming client")
    
    def get_event(self, timeout: Optional[float] = None) -> Optional[Dict[str, Any]]:
        """Get next event from the queue."""
        try:
            return self.events_queue.get(timeout=timeout)
        except queue.Empty:
            return None
    
    def _stream_worker(self) -> None:
        """Worker thread that connects and processes stream events."""
        while self.running:
            try:
                with socket.create_connection((self.host, self.port)) as conn:
                    logger.info("Connected to streaming server")
                    with conn.makefile("r", encoding="utf-8") as stream:
                        for line in stream:
                            if not self.running:
                                break
                            if not line.strip():
                                continue
                            
                            try:
                                event = json.loads(line)
                                self._process_event(event)
                            except json.JSONDecodeError as e:
                                logger.error(f"Failed to parse JSON: {e}")
                                continue
                                
            except ConnectionError as e:
                logger.error(f"Connection failed: {e}")
                if self.running:
                    logger.info("Retrying connection in 5 seconds...")
                    threading.Event().wait(5)
            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                break
    
    def _process_event(self, event: Dict[str, Any]) -> None:
        """Process a single event from the stream."""
        # Add to queue
        self.events_queue.put(event)
        
        # Call registered callbacks
        dataset = event.get("dataset", "unknown")
        if dataset in self.callbacks:
            for callback in self.callbacks[dataset]:
                try:
                    callback(event)
                except Exception as e:
                    logger.error(f"Callback error for {dataset}: {e}")


class DataBuffer:
    """Thread-safe buffer for storing recent events by type."""
    
    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self.buffers: Dict[str, List[Dict[str, Any]]] = {}
        self.lock = threading.RLock()
    
    def add_event(self, dataset: str, event: Dict[str, Any]) -> None:
        """Add an event to the appropriate buffer."""
        with self.lock:
            if dataset not in self.buffers:
                self.buffers[dataset] = []
            
            self.buffers[dataset].append(event)
            
            # Keep buffer size limited
            if len(self.buffers[dataset]) > self.max_size:
                self.buffers[dataset] = self.buffers[dataset][-self.max_size:]
    
    def get_recent_events(self, dataset: str, count: int = 10) -> List[Dict[str, Any]]:
        """Get recent events for a dataset."""
        with self.lock:
            if dataset not in self.buffers:
                return []
            return self.buffers[dataset][-count:]
    
    def get_events_in_timeframe(self, dataset: str, start_time: datetime, end_time: datetime) -> List[Dict[str, Any]]:
        """Get events within a specific timeframe."""
        with self.lock:
            if dataset not in self.buffers:
                return []
            
            filtered_events = []
            for event in self.buffers[dataset]:
                try:
                    event_time = datetime.fromisoformat(event.get("event", {}).get("timestamp", ""))
                    if start_time <= event_time <= end_time:
                        filtered_events.append(event)
                except (ValueError, KeyError):
                    continue
            
            return filtered_events


def load_product_catalog(csv_path: str) -> Dict[str, Dict[str, Any]]:
    """Load product catalog from CSV file."""
    import csv
    
    catalog = {}
    try:
        with open(csv_path, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                sku = row['SKU']
                catalog[sku] = {
                    'product_name': row['product_name'],
                    'quantity': int(row['quantity']),
                    'barcode': row['barcode'],
                    'weight': float(row['weight']),
                    'price': float(row['price']),
                    'epc_range': row['EPC_range']
                }
    except Exception as e:
        logger.error(f"Failed to load product catalog: {e}")
    
    return catalog


def load_customer_data(csv_path: str) -> Dict[str, Dict[str, Any]]:
    """Load customer data from CSV file."""
    import csv
    
    customers = {}
    try:
        with open(csv_path, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                customer_id = row['Customer_ID']
                customers[customer_id] = {
                    'name': row['Name'],
                    'age': int(row['Age']),
                    'address': row['Address'],
                    'phone': row['TP']
                }
    except Exception as e:
        logger.error(f"Failed to load customer data: {e}")
    
    return customers


if __name__ == "__main__":
    # Example usage
    logging.basicConfig(level=logging.INFO)
    
    client = StreamingDataClient()
    buffer = DataBuffer()
    
    # Register callbacks for different data types
    client.register_callback("POS_Transactions", lambda event: buffer.add_event("pos", event))
    client.register_callback("RFID_data", lambda event: buffer.add_event("rfid", event))
    client.register_callback("Queue_monitor", lambda event: buffer.add_event("queue", event))
    client.register_callback("Product_recognism", lambda event: buffer.add_event("product_recognition", event))
    client.register_callback("Current_inventory_data", lambda event: buffer.add_event("inventory", event))
    
    client.start_streaming()
    
    try:
        # Process events for testing
        for _ in range(10):
            event = client.get_event(timeout=5)
            if event:
                print(f"Received event from {event.get('dataset')}: {event.get('sequence')}")
            else:
                print("No events received")
    except KeyboardInterrupt:
        pass
    finally:
        client.stop_streaming()