#!/usr/bin/env python3
"""Quick run script for Project Sentinel demo events.

Simple one-command script to generate and display demo events.
"""

import json
import subprocess
import sys
from pathlib import Path

def main():
    print("🛒 QUICK PROJECT SENTINEL DEMO")
    print("=" * 40)
    
    script_dir = Path(__file__).parent
    demo_events_file = script_dir / "evidence" / "output" / "demo" / "events.json"
    
    # Generate demo events
    print("Generating demo events...")
    try:
        result = subprocess.run([sys.executable, "generate_demo_events.py"], 
                              cwd=script_dir, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Events generated successfully!")
        else:
            print("❌ Error generating events")
            print(result.stderr)
            return
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return
    
    # Display the events
    print()
    print("📄 GENERATED EVENTS:")
    print("=" * 40)
    
    try:
        with open(demo_events_file, 'r') as f:
            data = json.load(f)
        
        print(f"Total Events: {data['total_events']}")
        print(f"Generated At: {data['generated_at']}")
        print()
        
        for i, event in enumerate(data['events'], 1):
            event_data = event['event_data']
            print(f"{i}. {event_data['event_name']}")
            print(f"   Time: {event['timestamp']}")
            print(f"   Station: {event_data.get('station_id', 'N/A')}")
            if 'customer_id' in event_data:
                print(f"   Customer: {event_data['customer_id']}")
            if 'product_sku' in event_data:
                print(f"   Product: {event_data['product_sku']}")
            print()
            
        print(f"📁 Full events file: {demo_events_file}")
        
    except Exception as e:
        print(f"❌ Error reading events file: {e}")

if __name__ == "__main__":
    main()