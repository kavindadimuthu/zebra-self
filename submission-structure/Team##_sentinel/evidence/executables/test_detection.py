#!/usr/bin/env python3
"""Quick test of the detection system."""

import sys
import time
import json
from pathlib import Path

# Add src to path
src_path = str(Path(__file__).parent.parent.parent / "src")
sys.path.insert(0, src_path)

print(f"Added to path: {src_path}")

try:
    from detection_engine import DetectionEngine
    print("✓ Import successful")
except ImportError as e:
    print(f"✗ Import failed: {e}")
    sys.exit(1)

def main():
    print("Testing Project Sentinel Detection Engine...")
    
    # Create detection engine
    engine = DetectionEngine()
    
    # Initialize with minimal data
    data_dir = Path(__file__).parent.parent.parent.parent.parent / "data" / "input"
    
    try:
        engine.initialize(str(data_dir))
        print("✓ Detection engine initialized")
        
        # Start the engine
        engine.start()
        print("✓ Detection engine started")
        
        # Let it run for a short time
        print("Running detection for 15 seconds...")
        time.sleep(15)
        
        # Get results
        alerts = engine.get_all_alerts()
        print(f"✓ Generated {len(alerts)} alerts")
        
        # Export to test file
        if alerts:
            with open("test_events.jsonl", "w") as f:
                for alert in alerts:
                    f.write(json.dumps(alert) + "\n")
            print("✓ Exported events to test_events.jsonl")
        
        # Show system status
        status = engine.get_system_status()
        print(f"✓ Processed {status['events_processed']} events")
        
        return True
        
    except Exception as e:
        print(f"✗ Error: {e}")
        return False
    
    finally:
        engine.stop()
        print("✓ Detection engine stopped")

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)