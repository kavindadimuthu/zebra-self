#!/usr/bin/env python3
"""Project Sentinel Startup Script - Enhanced Version

Simple script to start the Project Sentinel system with the enhanced web dashboard.
This script handles all the setup automatically.

Usage:
    python start_sentinel.py [--port PORT] [--dashboard TYPE] [--data-speed SPEED]
"""

import sys
import time
import subprocess
import threading
import argparse
import logging
from pathlib import Path

# Add src directory to path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def start_data_streaming_server(data_speed=10, port=8765):
    """Start the data streaming server."""
    data_server_path = Path(__file__).parent.parent.parent / "data" / "streaming-server"
    
    print(f"🌊 Starting data streaming server (speed: {data_speed}x, port: {port})...")
    
    try:
        cmd = [
            sys.executable, 
            str(data_server_path / "stream_server.py"),
            "--port", str(port),
            "--speed", str(data_speed),
            "--loop"
        ]
        
        # Start in background
        process = subprocess.Popen(
            cmd,
            cwd=str(data_server_path),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Give it a moment to start
        time.sleep(2)
        
        if process.poll() is None:
            print(f"✅ Data streaming server started on port {port}")
            return process
        else:
            stdout, stderr = process.communicate()
            print(f"❌ Failed to start data server: {stderr.decode()}")
            return None
            
    except Exception as e:
        print(f"❌ Error starting data server: {e}")
        return None

def start_detection_engine():
    """Initialize and start the detection engine."""
    try:
        print("🔧 Initializing detection engine...")
        
        from detection_engine import DetectionEngine
        
        engine = DetectionEngine()
        engine.initialize(data_dir="../data/input")
        
        # Start the engine in a separate thread
        engine_thread = threading.Thread(target=engine.start, daemon=True)
        engine_thread.start()
        
        # Give it time to initialize
        time.sleep(3)
        
        print("✅ Detection engine started")
        return engine
        
    except Exception as e:
        print(f"❌ Error starting detection engine: {e}")
        return None

def start_web_dashboard(engine, port=8080):
    """Start the enhanced web dashboard."""
    try:
        print(f"🎯 Starting enhanced web dashboard on port {port}...")
        
        # Try to use the new modular dashboard first
        try:
            from web_dashboard import DashboardManager
            
            manager = DashboardManager(engine)
            manager.start_web_dashboard(host='localhost', port=port)
            
            print("\n" + "="*60)
            print("🎉 PROJECT SENTINEL - ENHANCED WEB DASHBOARD")
            print("="*60)
            print(f"📊 Dashboard URL: {manager.get_web_url()}")
            print("🔗 Open your browser to view the dashboard")
            print("\n✨ FEATURES:")
            print("  • Real-time monitoring with 5-second updates")
            print("  • Advanced alert management and filtering")  
            print("  • Station analytics and queue monitoring")
            print("  • Interactive charts and visualizations")
            print("  • System health and performance metrics")
            print("  • Modern responsive UI")
            print("\n🔄 Auto-refreshing every 5 seconds")
            print("🛑 Press Ctrl+C to stop")
            print("="*60)
            
            return manager
            
        except ImportError:
            # Fallback to legacy dashboard
            from dashboard import WebDashboard
            
            dashboard = WebDashboard(engine, port=port)
            dashboard.start()
            
            print(f"✅ Web dashboard started at http://localhost:{port}")
            return dashboard
            
    except Exception as e:
        print(f"❌ Error starting web dashboard: {e}")
        return None

def start_console_dashboard(engine):
    """Start console dashboard as backup."""
    try:
        from dashboard import ConsoleDashboard
        
        console = ConsoleDashboard(engine)
        console_thread = threading.Thread(target=console.start, daemon=True)
        console_thread.start()
        
        print("✅ Console dashboard started")
        return console
        
    except Exception as e:
        print(f"⚠️  Console dashboard not available: {e}")
        return None

def main():
    """Main startup function."""
    parser = argparse.ArgumentParser(description="Start Project Sentinel System")
    parser.add_argument("--port", type=int, default=8080, help="Web dashboard port")
    parser.add_argument("--dashboard", choices=['web', 'console', 'both'], default='web', help="Dashboard type")
    parser.add_argument("--data-speed", type=int, default=10, help="Data streaming speed multiplier")
    parser.add_argument("--data-port", type=int, default=8765, help="Data streaming server port")
    
    args = parser.parse_args()
    
    print("🌟 Starting Project Sentinel - Retail Intelligence System")
    print("=" * 60)
    
    data_server = None
    detection_engine = None
    web_dashboard = None
    console_dashboard = None
    
    try:
        # 1. Start data streaming server
        data_server = start_data_streaming_server(args.data_speed, args.data_port)
        if not data_server:
            print("⚠️  Continuing without data server (will use mock data)")
        
        # 2. Start detection engine
        detection_engine = start_detection_engine()
        if not detection_engine:
            print("❌ Failed to start detection engine. Exiting.")
            return
        
        # 3. Start dashboards
        if args.dashboard in ['web', 'both']:
            web_dashboard = start_web_dashboard(detection_engine, args.port)
        
        if args.dashboard in ['console', 'both']:
            console_dashboard = start_console_dashboard(detection_engine)
        
        # 4. Keep running
        print(f"\n🎯 System running! Access dashboard at: http://localhost:{args.port}")
        print("Press Ctrl+C to stop the system")
        
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n🛑 Shutting down...")
            
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        
    finally:
        # Cleanup
        if data_server:
            try:
                data_server.terminate()
                data_server.wait(timeout=5)
                print("✅ Data server stopped")
            except:
                pass
        
        if web_dashboard and hasattr(web_dashboard, 'stop_all'):
            try:
                web_dashboard.stop_all()
                print("✅ Web dashboard stopped")
            except:
                pass
        
        print("✅ System shutdown complete")

if __name__ == "__main__":
    main()