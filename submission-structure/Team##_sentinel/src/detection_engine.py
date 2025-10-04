#!/usr/bin/env python3
"""Main Detection Engine for Project Sentinel.

Coordinates all detection algorithms and manages the overall event processing pipeline.
"""

import logging
import json
import threading
import time
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from queue import Queue
from pathlib import Path

from data_ingestion import StreamingDataClient, DataBuffer, load_product_catalog, load_customer_data
from event_correlation import EventCorrelator
from detectors.scan_avoidance import ScanAvoidanceDetector
from detectors.weight_discrepancy import WeightDiscrepancyDetector
from detectors.queue_monitor import QueueMonitor
from detectors.barcode_switching import BarcodeSwitchingDetector
from detectors.inventory_discrepancy import InventoryDiscrepancyDetector
from detectors.system_crash import SystemCrashDetector
from detectors.success_operation import SuccessOperationDetector

logger = logging.getLogger(__name__)


class DetectionEngine:
    """Main detection engine that coordinates all detectors."""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.running = False
        
        # Events output file path
        self.events_output_file = self.config.get(
            'events_output_file', 
            '../evidence/output/events/events.json'
        )
        
        # Initialize components
        self.data_client = StreamingDataClient()
        self.data_buffer = DataBuffer()
        self.correlator = EventCorrelator()
        
        # Initialize detectors
        self.scan_avoidance = ScanAvoidanceDetector()
        self.weight_detector = WeightDiscrepancyDetector()
        self.queue_monitor = QueueMonitor()
        self.barcode_detector = BarcodeSwitchingDetector()
        self.inventory_detector = InventoryDiscrepancyDetector()
        self.crash_detector = SystemCrashDetector()
        self.success_detector = SuccessOperationDetector()
        
        # Event queues
        self.alert_queue = Queue()
        self.processed_events = []
        self.saved_events = []  # Track events saved to file
        
        # Data catalogs
        self.product_catalog = {}
        self.customer_data = {}
        
        # Statistics
        self.stats = {
            "events_processed": 0,
            "alerts_generated": 0,
            "start_time": None
        }
    
    def initialize(self, data_dir: str = "../../data/input") -> None:
        """Initialize the detection engine with data catalogs."""
        try:
            # Load product catalog
            self.product_catalog = load_product_catalog(f"{data_dir}/products_list.csv")
            logger.info(f"Loaded {len(self.product_catalog)} products")
            
            # Load customer data
            self.customer_data = load_customer_data(f"{data_dir}/customer_data.csv")
            logger.info(f"Loaded {len(self.customer_data)} customers")
            
            # Configure detectors with catalog data
            self.weight_detector.load_product_catalog(self.product_catalog)
            self.barcode_detector.load_product_catalog(self.product_catalog)
            
            # Register data callbacks
            self._register_data_callbacks()
            
            logger.info("Detection engine initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize detection engine: {e}")
            raise
    
    def _register_data_callbacks(self) -> None:
        """Register callbacks for different data streams."""
        # RFID events
        self.data_client.register_callback("RFID_data", self._process_rfid_event)
        
        # POS transactions
        self.data_client.register_callback("POS_Transactions", self._process_pos_event)
        
        # Queue monitoring
        self.data_client.register_callback("Queue_monitor", self._process_queue_event)
        
        # Product recognition
        self.data_client.register_callback("Product_recognism", self._process_recognition_event)
        
        # Inventory snapshots
        self.data_client.register_callback("Current_inventory_data", self._process_inventory_event)
    
    def start(self) -> None:
        """Start the detection engine."""
        if self.running:
            logger.warning("Detection engine is already running")
            return
        
        self.running = True
        self.stats["start_time"] = datetime.now()
        
        # Start data streaming
        self.data_client.start_streaming()
        
        # Start background tasks
        self._start_background_tasks()
        
        logger.info("Detection engine started")
    
    def stop(self) -> None:
        """Stop the detection engine."""
        self.running = False
        self.data_client.stop_streaming()
        logger.info("Detection engine stopped")
    
    def _start_background_tasks(self) -> None:
        """Start background maintenance tasks."""
        # Periodic cleanup task
        cleanup_thread = threading.Thread(target=self._cleanup_worker, daemon=True)
        cleanup_thread.start()
        
        # Timeout check task
        timeout_thread = threading.Thread(target=self._timeout_worker, daemon=True)
        timeout_thread.start()
    
    def _cleanup_worker(self) -> None:
        """Background worker for periodic cleanup."""
        while self.running:
            try:
                time.sleep(300)  # Run every 5 minutes
                
                # Clean up old data in all detectors
                self.scan_avoidance.cleanup_old_data()
                self.weight_detector.cleanup_old_data()
                self.queue_monitor.cleanup_old_data()
                self.barcode_detector.cleanup_old_data()
                self.inventory_detector.cleanup_old_data()
                self.crash_detector.cleanup_old_data()
                self.correlator.cleanup_old_events()
                
                logger.debug("Completed periodic cleanup")
                
            except Exception as e:
                logger.error(f"Error in cleanup worker: {e}")
    
    def _timeout_worker(self) -> None:
        """Background worker for timeout checks."""
        while self.running:
            try:
                time.sleep(60)  # Check every minute
                
                # Check for scan avoidance timeouts
                timeout_alerts = self.scan_avoidance.check_timeout_alerts()
                for alert in timeout_alerts:
                    self._add_alert(alert)
                
                # Check for system timeouts
                crash_alerts = self.crash_detector.check_station_timeouts()
                for alert in crash_alerts:
                    self._add_alert(alert)
                
                logger.debug("Completed timeout checks")
                
            except Exception as e:
                logger.error(f"Error in timeout worker: {e}")
    
    def _process_rfid_event(self, event: Dict[str, Any]) -> None:
        """Process RFID event through all relevant detectors."""
        try:
            self.stats["events_processed"] += 1
            
            # Add to correlation engine
            self.correlator.add_event(event)
            
            # Process through detectors
            alert = self.scan_avoidance.process_rfid_event(event)
            if alert:
                self._add_alert(alert)
            
            self.inventory_detector.process_rfid_event(event)
            
            # System crash detection
            crash_alert = self.crash_detector.process_station_event(event)
            if crash_alert:
                self._add_alert(crash_alert)
            
        except Exception as e:
            logger.error(f"Error processing RFID event: {e}")
    
    def _process_pos_event(self, event: Dict[str, Any]) -> None:
        """Process POS transaction through all relevant detectors."""
        try:
            self.stats["events_processed"] += 1
            
            # Add to correlation engine
            self.correlator.add_event(event)
            
            # Process through detectors
            self.scan_avoidance.process_pos_event(event)
            
            weight_alert = self.weight_detector.process_pos_transaction(event)
            if weight_alert:
                self._add_alert(weight_alert)
            
            barcode_alert = self.barcode_detector.process_pos_transaction(event)
            if barcode_alert:
                self._add_alert(barcode_alert)
            
            inventory_alert = self.inventory_detector.process_pos_transaction(event)
            if inventory_alert:
                self._add_alert(inventory_alert)
                
            # Success operation detection (generate success events for normal transactions)
            success_alert = self.success_detector.process_pos_transaction(event)
            if success_alert:
                self._add_alert(success_alert)
            
            # System crash detection
            crash_alert = self.crash_detector.process_station_event(event)
            if crash_alert:
                self._add_alert(crash_alert)
            
        except Exception as e:
            logger.error(f"Error processing POS event: {e}")
    
    def _process_queue_event(self, event: Dict[str, Any]) -> None:
        """Process queue monitoring event."""
        try:
            self.stats["events_processed"] += 1
            
            # Add to correlation engine
            self.correlator.add_event(event)
            
            # Process through queue monitor
            alerts = self.queue_monitor.process_queue_event(event)
            for alert in alerts:
                self._add_alert(alert)
            
            # System crash detection
            crash_alert = self.crash_detector.process_station_event(event)
            if crash_alert:
                self._add_alert(crash_alert)
            
        except Exception as e:
            logger.error(f"Error processing queue event: {e}")
    
    def _process_recognition_event(self, event: Dict[str, Any]) -> None:
        """Process product recognition event."""
        try:
            self.stats["events_processed"] += 1
            
            # Add to correlation engine
            self.correlator.add_event(event)
            
            # Process through barcode switching detector
            self.barcode_detector.process_product_recognition(event)
            
            # System crash detection
            crash_alert = self.crash_detector.process_station_event(event)
            if crash_alert:
                self._add_alert(crash_alert)
            
        except Exception as e:
            logger.error(f"Error processing recognition event: {e}")
    
    def _process_inventory_event(self, event: Dict[str, Any]) -> None:
        """Process inventory snapshot event."""
        try:
            self.stats["events_processed"] += 1
            
            # Add to correlation engine
            self.correlator.add_event(event)
            
            # Process through inventory detector
            alerts = self.inventory_detector.process_inventory_snapshot(event)
            for alert in alerts:
                self._add_alert(alert)
            
        except Exception as e:
            logger.error(f"Error processing inventory event: {e}")
    
    def _add_alert(self, alert: Dict[str, Any]) -> None:
        """Add an alert to the queue and save to JSON file."""
        self.alert_queue.put(alert)
        self.stats["alerts_generated"] += 1
        self.saved_events.append(alert)
        
        # Save to JSON file immediately
        self._save_events_to_file()
        
        logger.info(f"Generated alert: {alert['event_data']['event_name']} at {alert.get('event_data', {}).get('station_id', 'UNKNOWN')}")
    
    def _save_events_to_file(self) -> None:
        """Save all events to the JSON output file."""
        try:
            # Create directory if it doesn't exist
            output_path = Path(self.events_output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Save events as JSON array
            with open(self.events_output_file, 'w') as f:
                json.dump(self.saved_events, f, indent=2, default=str)
                
        except Exception as e:
            logger.error(f"Failed to save events to {self.events_output_file}: {e}")
    
    def save_events_jsonl(self, output_file: str = None) -> None:
        """Save events in JSONL format (one JSON object per line)."""
        if output_file is None:
            output_file = self.events_output_file.replace('.json', '.jsonl')
        
        try:
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_file, 'w') as f:
                for event in self.saved_events:
                    f.write(json.dumps(event, default=str) + '\n')
                    
            logger.info(f"Saved {len(self.saved_events)} events to {output_file}")
            
        except Exception as e:
            logger.error(f"Failed to save events to {output_file}: {e}")
    
    def get_alerts(self, max_alerts: int = 10) -> List[Dict[str, Any]]:
        """Get recent alerts from the queue."""
        alerts = []
        count = 0
        while not self.alert_queue.empty() and count < max_alerts:
            alerts.append(self.alert_queue.get())
            count += 1
        return alerts
    
    def get_all_alerts(self) -> List[Dict[str, Any]]:
        """Get all alerts from the queue."""
        alerts = []
        while not self.alert_queue.empty():
            alerts.append(self.alert_queue.get())
        return alerts
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get overall system status."""
        current_time = datetime.now()
        uptime = (current_time - self.stats["start_time"]).total_seconds() if self.stats["start_time"] else 0
        
        return {
            "status": "RUNNING" if self.running else "STOPPED",
            "uptime_seconds": round(uptime, 1),
            "events_processed": self.stats["events_processed"],
            "alerts_generated": self.stats["alerts_generated"],
            "events_per_minute": round(self.stats["events_processed"] / (uptime / 60), 1) if uptime > 0 else 0,
            "pending_alerts": self.alert_queue.qsize(),
            "current_time": current_time.isoformat()
        }
    
    def get_station_summary(self, station_id: str) -> Dict[str, Any]:
        """Get comprehensive status for a specific station."""
        try:
            summary = {
                "station_id": station_id,
                "queue_status": self.queue_monitor.get_queue_analytics(station_id),
                "reliability": self.crash_detector.get_station_reliability_report(station_id),
                "unscanned_items": self.scan_avoidance.get_current_unscanned_items().get(station_id, []),
                "switching_patterns": self.barcode_detector.get_switching_patterns(station_id)
            }
            return summary
        except Exception as e:
            logger.error(f"Error getting station summary for {station_id}: {e}")
            return {"station_id": station_id, "error": str(e)}
    
    def export_events_jsonl(self, output_file: str) -> None:
        """Export all alerts as JSONL format."""
        alerts = self.get_all_alerts()
        
        try:
            with open(output_file, 'w') as f:
                for alert in alerts:
                    f.write(json.dumps(alert) + '\n')
            
            logger.info(f"Exported {len(alerts)} alerts to {output_file}")
            
        except Exception as e:
            logger.error(f"Failed to export events: {e}")
            raise


if __name__ == "__main__":
    # Example usage
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create and initialize detection engine
    engine = DetectionEngine()
    
    try:
        # Initialize with data
        engine.initialize("../../data/input")
        
        # Start detection
        engine.start()
        
        # Run for a test period
        print("Detection engine running... Press Ctrl+C to stop")
        
        # Monitor for a period
        start_time = time.time()
        while time.time() - start_time < 30:  # Run for 30 seconds
            time.sleep(5)
            
            # Get recent alerts
            alerts = engine.get_alerts(5)
            if alerts:
                print(f"\n--- Recent Alerts ({len(alerts)}) ---")
                for alert in alerts:
                    event_data = alert.get('event_data', {})
                    print(f"  {event_data.get('event_name')} at {event_data.get('station_id')} - {event_data.get('severity', 'UNKNOWN')}")
            
            # Show system status
            status = engine.get_system_status()
            print(f"\nSystem Status: {status['events_processed']} events, {status['alerts_generated']} alerts")
    
    except KeyboardInterrupt:
        print("\nStopping detection engine...")
    
    finally:
        engine.stop()
        
        # Export any remaining alerts
        final_alerts = engine.get_all_alerts()
        if final_alerts:
            engine.export_events_jsonl("test_events.jsonl")
            print(f"Exported {len(final_alerts)} final alerts")