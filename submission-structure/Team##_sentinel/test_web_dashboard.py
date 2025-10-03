#!/usr/bin/env python3
"""Test script for the Project Sentinel Web Dashboard.

This script starts the system with web dashboard enabled and provides
instructions for testing the interactive features.
"""

import sys
import time
import subprocess
import webbrowser
from pathlib import Path

def main():
    print("🛒 PROJECT SENTINEL WEB DASHBOARD TEST")
    print("=" * 50)
    print()
    
    # Get the script directory
    script_dir = Path(__file__).parent
    executables_dir = script_dir / "evidence" / "executables"
    
    print(f"Starting Project Sentinel with Web Dashboard...")
    print(f"Working directory: {executables_dir}")
    print()
    
    # Start the system with web dashboard
    try:
        print("🚀 Starting system with web dashboard...")
        print("   Duration: 120 seconds (2 minutes)")
        print("   Dashboard: Web interface at http://localhost:8080")
        print()
        
        # Run the system
        result = subprocess.run([
            sys.executable, "run_demo.py", 
            "--duration", "120", 
            "--dashboard", "web"
        ], cwd=executables_dir, capture_output=False)
        
        if result.returncode == 0:
            print("✅ System completed successfully!")
        else:
            print(f"❌ System exited with error code: {result.returncode}")
            
    except KeyboardInterrupt:
        print("\n🛑 Test interrupted by user")
    except Exception as e:
        print(f"❌ Error running test: {e}")

if __name__ == "__main__":
    main()