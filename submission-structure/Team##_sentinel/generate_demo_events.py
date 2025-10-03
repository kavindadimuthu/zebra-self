#!/usr/bin/env python3
"""Simple script to generate demo events for Project Sentinel.

This script creates sample detection events in the expected format
and saves them to the demo folder for easy checking and verification.
"""

import json
from datetime import datetime, timedelta
from pathlib import Path

def generate_sample_events():
    """Generate sample events in the expected format."""
    base_time = datetime.now()
    events = []
    
    # Sample events covering all 7 detection scenarios
    sample_events = [
        {
            "timestamp": (base_time).isoformat(),
            "event_id": "E001",
            "event_data": {
                "event_name": "Scanner Avoidance",
                "station_id": "SCC1",
                "customer_id": "C004",
                "product_sku": "PRD_S_04"
            }
        },
        {
            "timestamp": (base_time + timedelta(minutes=2)).isoformat(),
            "event_id": "E002",
            "event_data": {
                "event_name": "Barcode Switching",
                "station_id": "SCC1",
                "customer_id": "C009",
                "actual_sku": "PRD_F_08",
                "scanned_sku": "PRD_F_07"
            }
        },
        {
            "timestamp": (base_time + timedelta(minutes=3)).isoformat(),
            "event_id": "E003",
            "event_data": {
                "event_name": "Weight Discrepancies",
                "station_id": "SCC2",
                "customer_id": "C007",
                "product_sku": "PRD_F_09",
                "expected_weight": 425,
                "actual_weight": 680
            }
        },
        {
            "timestamp": (base_time + timedelta(minutes=5)).isoformat(),
            "event_id": "E004",
            "event_data": {
                "event_name": "Unexpected Systems Crash",
                "station_id": "SCC3",
                "duration_seconds": 180
            }
        },
        {
            "timestamp": (base_time + timedelta(minutes=8)).isoformat(),
            "event_id": "E005",
            "event_data": {
                "event_name": "Long Queue Length",
                "station_id": "SCC1",
                "num_of_customers": 6
            }
        },
        {
            "timestamp": (base_time + timedelta(minutes=10)).isoformat(),
            "event_id": "E006",
            "event_data": {
                "event_name": "Long Wait Time",
                "station_id": "SCC2",
                "customer_id": "C015",
                "wait_time_seconds": 350
            }
        },
        {
            "timestamp": (base_time + timedelta(minutes=12)).isoformat(),
            "event_id": "E007",
            "event_data": {
                "event_name": "Inventory Discrepancy",
                "SKU": "PRD_F_03",
                "Expected_Inventory": 150,
                "Actual_Inventory": 120
            }
        },
        {
            "timestamp": (base_time + timedelta(minutes=15)).isoformat(),
            "event_id": "E008",
            "event_data": {
                "event_name": "Staffing Needs",
                "station_id": "SCC1",
                "Staff_type": "Cashier"
            }
        },
        {
            "timestamp": (base_time + timedelta(minutes=18)).isoformat(),
            "event_id": "E009",
            "event_data": {
                "event_name": "Checkout Station Action",
                "station_id": "SCC3",
                "Action": "Open"
            }
        }
    ]
    
    return sample_events

def main():
    print("🛒 PROJECT SENTINEL - DEMO EVENT GENERATOR")
    print("=" * 50)
    
    # Set up paths
    script_dir = Path(__file__).parent
    demo_output_dir = script_dir / "evidence" / "output" / "demo"
    demo_events_file = demo_output_dir / "events.json"
    
    # Create demo output directory if it doesn't exist
    demo_output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"Generating sample events...")
    print(f"Output will be saved to: {demo_events_file}")
    print()
    
    try:
        # Generate sample events
        events = generate_sample_events()
        
        # Create the output structure
        output_data = {
            "total_events": len(events),
            "generated_at": datetime.now().isoformat(),
            "description": "Sample Project Sentinel detection events covering all 7 scenarios",
            "scenarios_covered": [
                "Scanner Avoidance",
                "Barcode Switching", 
                "Weight Discrepancies",
                "Unexpected Systems Crash",
                "Long Queue Length",
                "Long Wait Time",
                "Inventory Discrepancy",
                "Staffing Needs",
                "Checkout Station Action"
            ],
            "events": events
        }
        
        # Write to demo events.json file
        with open(demo_events_file, 'w') as f:
            json.dump(output_data, f, indent=2)
        
        print(f"✅ Generated {len(events)} sample events")
        print(f"✅ Events saved to: {demo_events_file}")
        print()
        print("📊 Event Summary:")
        
        # Show event types
        event_types = {}
        for event in events:
            event_name = event.get('event_data', {}).get('event_name', 'Unknown')
            event_types[event_name] = event_types.get(event_name, 0) + 1
        
        for event_type, count in event_types.items():
            print(f"   - {event_type}: {count}")
            
    except Exception as e:
        print(f"❌ Error generating demo events: {e}")
        
        # Create empty events file as fallback
        with open(demo_events_file, 'w') as f:
            json.dump({
                "total_events": 0,
                "generated_at": datetime.now().isoformat(),
                "error": str(e),
                "events": []
            }, f, indent=2)
        print(f"✅ Created fallback events file: {demo_events_file}")

    print()
    print("✅ Demo event generation complete!")
    print(f"Check the file: {demo_events_file}")

if __name__ == "__main__":
    main()