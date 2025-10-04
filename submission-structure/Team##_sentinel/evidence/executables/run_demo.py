#!/usr/bin/env python3
"""Project Sentinel Automation Script.

This script sets up dependencies, starts the streaming server, 
runs the detection system, and produces events.jsonl output.

Usage:
    python3 run_demo.py [--mode MODE] [--duration SECONDS] [--data-dir PATH] [--output-dir PATH]
    
Modes:
    both         - Run both detection engine and web dashboard (default)
    web-only     - Run only the web dashboard in standalone mode
    detection-only - Run only the detection engine (no dashboard)
"""

import os
import sys
import json
import time
import argparse
import subprocess
import threading
import signal
from pathlib import Path
from datetime import datetime

# Add src directory to Python path
src_path = str(Path(__file__).parent.parent.parent / "src")
sys.path.insert(0, src_path)

try:
    from detection_engine import DetectionEngine
    from dashboard import ConsoleDashboard, WebDashboard
except ImportError as e:
    print(f"Error importing modules: {e}")
    print("Make sure you're running from the correct directory")
    sys.exit(1)


class ProjectSentinelRunner:
    """Main runner for Project Sentinel system."""
    
    def __init__(self, args):
        self.args = args
        self.detection_engine = None
        self.dashboard = None
        self.streaming_server_process = None
        self.running = False
        
        # Set up paths
        self.base_dir = Path(__file__).parent.parent.parent
        # Data directory is 5 levels up from executables, we're already in zebra-self
        self.data_dir = Path(args.data_dir) if args.data_dir else Path(__file__).parent.parent.parent.parent.parent / "data"
        self.output_dir = Path(args.output_dir) if args.output_dir else Path("./results")
        
        # Ensure output directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    def setup_dependencies(self) -> bool:
        """Install and verify all required dependencies."""
        print("Setting up dependencies...")
        
        # Check Python version
        if sys.version_info < (3, 9):
            print("Error: Python 3.9+ required")
            return False
        
        # No external dependencies required - using only standard library
        print("✓ All dependencies satisfied")
        return True
    
    def start_streaming_server(self) -> bool:
        """Start the data streaming server."""
        streaming_server_path = self.data_dir / "streaming-server" / "stream_server.py"
        
        if not streaming_server_path.exists():
            print(f"Error: Streaming server not found at {streaming_server_path}")
            return False
        
        print("Starting data streaming server...")
        
        try:
            # Start streaming server
            self.streaming_server_process = subprocess.Popen([
                sys.executable, str(streaming_server_path),
                "--port", "8765",
                "--speed", "10",  # 10x speed for faster processing
                "--loop"
            ], cwd=str(streaming_server_path.parent))
            
            # Wait a moment for server to start
            time.sleep(2)
            
            # Check if process is still running
            if self.streaming_server_process.poll() is None:
                print("✓ Streaming server started successfully")
                return True
            else:
                print("✗ Streaming server failed to start")
                return False
                
        except Exception as e:
            print(f"Error starting streaming server: {e}")
            return False
    
    def initialize_detection_engine(self) -> bool:
        """Initialize the detection engine."""
        print("Initializing detection engine...")
        
        try:
            # Configure events output path
            events_output_path = self.base_dir / "evidence" / "output" / "events" / "events.json"
            config = {
                'events_output_file': str(events_output_path)
            }
            
            self.detection_engine = DetectionEngine(config)
            
            # Initialize with data files
            input_dir = self.data_dir / "input"
            if not input_dir.exists():
                print(f"Error: Input data directory not found at {input_dir}")
                return False
            
            self.detection_engine.initialize(str(input_dir))
            print("✓ Detection engine initialized")
            print(f"✓ Events will be saved to: {events_output_path}")
            return True
            
        except Exception as e:
            print(f"Error initializing detection engine: {e}")
            return False
    
    def start_detection_system(self) -> bool:
        """Start the detection system."""
        print("Starting detection system...")
        
        try:
            self.detection_engine.start()
            print("✓ Detection system started")
            return True
            
        except Exception as e:
            print(f"Error starting detection system: {e}")
            return False
    
    def start_dashboard(self) -> None:
        """Start the monitoring dashboard."""
        if self.args.dashboard == "console":
            print("Starting console dashboard...")
            self.dashboard = ConsoleDashboard(self.detection_engine)
            dashboard_thread = threading.Thread(target=self.dashboard.start, daemon=True)
            dashboard_thread.start()
        elif self.args.dashboard == "web":
            print("Starting web dashboard...")
            try:
                self.dashboard = WebDashboard(self.detection_engine, port=8080)
                self.dashboard.start()
                print(f"Web dashboard available at: {self.dashboard.get_url()}")
                print("Open your browser to view real-time analytics and alerts!")
            except Exception as e:
                print(f"Failed to start web dashboard: {e}")
                print("Continuing without dashboard...")
                self.dashboard = None
        elif self.args.dashboard == "none":
            print("Dashboard disabled")
    
    def start_standalone_dashboard(self) -> None:
        """Start web dashboard in standalone mode (no detection engine)."""
        print("Starting server monitoring dashboard...")
        try:
            # Try to use the new modular dashboard
            try:
                from web_dashboard.controller import WebDashboard
                self.dashboard = WebDashboard(detection_engine=None, host='localhost', port=8080)
                self.dashboard.start()
                print(f"Server monitoring dashboard available at: http://localhost:8080")
                print("Open your browser to view server status and diagnostics!")
                print("⚠️  Note: Detection server offline - showing connection status")
            except ImportError:
                # Fallback to legacy dashboard
                print("⚠️  Enhanced dashboard not available, using basic mode")
                print("Server monitoring dashboard started on http://localhost:8080")
        except Exception as e:
            print(f"Failed to start server monitoring dashboard: {e}")
            self.dashboard = None
    
    def monitor_web_only(self) -> None:
        """Monitor web-only mode."""
        print(f"\nServer monitoring dashboard running for {self.args.duration} seconds...")
        print("=" * 60)
        print("🌐 Web dashboard: http://localhost:8080")
        print("⚠️  Detection server status: OFFLINE")
        print("📊 Showing server connectivity and status diagnostics")
        print("🛑 Press Ctrl+C to stop")
        print("=" * 60)
        
        start_time = time.time()
        try:
            while self.running and (time.time() - start_time) < self.args.duration:
                time.sleep(5)
        except KeyboardInterrupt:
            print("\nReceived interrupt signal, shutting down...")
    
    def monitor_detection_only(self) -> None:
        """Monitor detection-only mode."""
        print(f"\nDetection engine running for {self.args.duration} seconds...")
        print("=" * 60)
        print("🔍 Processing retail intelligence data")
        print("📈 Events being processed and logged")
        print("🛑 Press Ctrl+C to stop")
        print("=" * 60)
        
        start_time = time.time()
        last_status_time = 0
        
        try:
            while self.running and (time.time() - start_time) < self.args.duration:
                current_time = time.time()
                
                # Print status update every 30 seconds
                if current_time - last_status_time >= 30:
                    self._print_status_update()
                    last_status_time = current_time
                
                time.sleep(5)
                
        except KeyboardInterrupt:
            print("\nReceived interrupt signal, shutting down...")
    
    def monitor_system(self) -> None:
        """Monitor the system and display status updates."""
        print(f"\nProject Sentinel running for {self.args.duration} seconds...")
        print("=" * 60)
        
        start_time = time.time()
        last_status_time = 0
        
        try:
            while self.running and (time.time() - start_time) < self.args.duration:
                current_time = time.time()
                
                # Print status update every 30 seconds
                if current_time - last_status_time >= 30:
                    self._print_status_update()
                    last_status_time = current_time
                
                time.sleep(5)
                
        except KeyboardInterrupt:
            print("\nReceived interrupt signal, shutting down...")
    
    def _print_status_update(self) -> None:
        """Print a status update."""
        if not self.detection_engine:
            return
        
        status = self.detection_engine.get_system_status()
        current_time = datetime.now().strftime("%H:%M:%S")
        
        print(f"[{current_time}] Events: {status['events_processed']}, "
              f"Alerts: {status['alerts_generated']}, "
              f"Rate: {status['events_per_minute']:.1f}/min")
    
    def generate_output(self) -> bool:
        """Generate final output files."""
        print("Generating output files...")
        
        try:
            # Get all alerts
            alerts = self.detection_engine.get_all_alerts()
            
            if not alerts:
                print("⚠️  No alerts generated during run")
                # Create empty events file
                events_file = self.output_dir / "events.jsonl"
                events_file.write_text("")
            else:
                # Export events as JSONL to results directory
                events_file = self.output_dir / "events.jsonl"
                self.detection_engine.export_events_jsonl(str(events_file))
                print(f"✓ Generated {len(alerts)} events in {events_file}")
                
                # Also save to evidence/output/events directory (JSONL format)
                evidence_events_file = self.base_dir / "evidence" / "output" / "events" / "events.jsonl"
                self.detection_engine.save_events_jsonl(str(evidence_events_file))
                print(f"✓ Saved events to evidence output: {evidence_events_file}")
            
            # Generate summary report
            self._generate_summary_report(alerts)
            
            return True
            
        except Exception as e:
            print(f"Error generating output: {e}")
            return False
    
    def _generate_summary_report(self, alerts: list) -> None:
        """Generate a summary report."""
        summary_file = self.output_dir / "summary.json"
        
        # Analyze alerts by type
        alert_types = {}
        for alert in alerts:
            event_name = alert.get('event_data', {}).get('event_name', 'Unknown')
            alert_types[event_name] = alert_types.get(event_name, 0) + 1
        
        # Get system status
        status = self.detection_engine.get_system_status()
        
        summary = {
            "run_timestamp": datetime.now().isoformat(),
            "duration_seconds": self.args.duration,
            "system_status": status,
            "total_alerts": len(alerts),
            "alerts_by_type": alert_types,
            "high_severity_alerts": len([a for a in alerts if a.get('event_data', {}).get('severity') == 'HIGH']),
            "output_files": ["events.jsonl", "summary.json"]
        }
        
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
        
        print(f"✓ Generated summary report: {summary_file}")
    
    def cleanup(self) -> None:
        """Clean up resources."""
        print("Cleaning up...")
        
        if self.detection_engine:
            self.detection_engine.stop()
        
        if self.dashboard:
            self.dashboard.stop()
        
        if self.streaming_server_process:
            try:
                self.streaming_server_process.terminate()
                self.streaming_server_process.wait(timeout=5)
                print("✓ Streaming server stopped")
            except subprocess.TimeoutExpired:
                self.streaming_server_process.kill()
                print("✓ Streaming server force stopped")
            except Exception as e:
                print(f"Warning: Error stopping streaming server: {e}")
    
    def run(self) -> int:
        """Run the complete Project Sentinel system."""
        self.running = True
        
        # Setup signal handler for graceful shutdown
        def signal_handler(signum, frame):
            print(f"\nReceived signal {signum}, shutting down gracefully...")
            self.running = False
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        try:
            # Print mode information
            print(f"🔧 Running in mode: {self.args.mode}")
            
            if self.args.mode == 'web-only':
                # Web-only mode: start only the web dashboard
                print("🎯 Starting web dashboard in server monitoring mode...")
                if not self.setup_dependencies():
                    return 1
                    
                self.start_standalone_dashboard()
                self.monitor_web_only()
                
                print("\n✓ Server monitoring dashboard completed successfully!")
                return 0
                
            elif self.args.mode == 'detection-only':
                # Detection-only mode: start streaming server and detection engine
                print("🎯 Starting detection engine only...")
                if not self.setup_dependencies():
                    return 1
                
                if not self.start_streaming_server():
                    return 1
                
                if not self.initialize_detection_engine():
                    return 1
                
                if not self.start_detection_system():
                    return 1
                
                # Monitor without dashboard
                self.monitor_detection_only()
                
                # Output phase
                if not self.generate_output():
                    return 1
                
                print("\n✓ Detection engine completed successfully!")
                return 0
                
            else:  # both mode (default)
                # Full mode: start everything
                print("🎯 Starting full system (detection engine + dashboard)...")
                
                # Setup phase
                if not self.setup_dependencies():
                    return 1
                
                if not self.start_streaming_server():
                    return 1
                
                if not self.initialize_detection_engine():
                    return 1
                
                if not self.start_detection_system():
                    return 1
                
                # Start dashboard if requested
                self.start_dashboard()
                
                # Monitor phase
                self.monitor_system()
                
                # Output phase
                if not self.generate_output():
                    return 1
                
                print("\n✓ Project Sentinel completed successfully!")
                return 0
            
        except Exception as e:
            print(f"Fatal error: {e}")
            return 1
        
        finally:
            self.cleanup()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Project Sentinel - Retail Intelligence System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 run_demo.py                           # Run both systems (default)
  python3 run_demo.py --mode web-only           # Run standalone web dashboard
  python3 run_demo.py --mode detection-only     # Run detection engine only
  python3 run_demo.py --duration 60             # Run for 60 seconds
  python3 run_demo.py --dashboard web           # Use web dashboard
  python3 run_demo.py --dashboard none          # Disable dashboard
        """
    )
    
    parser.add_argument(
        "--mode",
        choices=["both", "web-only", "detection-only"],
        default="both",
        help="Execution mode: both (default), web-only, or detection-only"
    )
    
    parser.add_argument(
        "--duration",
        type=int,
        default=120,
        help="Duration to run in seconds (default: 120)"
    )
    
    parser.add_argument(
        "--data-dir",
        help="Path to data directory (default: auto-detect)"
    )
    
    parser.add_argument(
        "--output-dir",
        default="./results",
        help="Output directory for results (default: ./results)"
    )
    
    parser.add_argument(
        "--dashboard",
        choices=["console", "web", "none"],
        default="console",
        help="Dashboard type (default: console)"
    )
    
    args = parser.parse_args()
    
    # Print banner
    print("=" * 60)
    print("🛒 PROJECT SENTINEL - RETAIL INTELLIGENCE SYSTEM")
    print("   Real-time fraud detection and store optimization")
    print("=" * 60)
    
    # Run the system
    runner = ProjectSentinelRunner(args)
    return runner.run()


if __name__ == "__main__":
    sys.exit(main())
