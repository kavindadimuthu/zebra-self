# Project Sentinel - Decoupled Architecture Guide

## Overview

Project Sentinel now supports **decoupled execution modes**, allowing you to run the web dashboard and detection engine independently or together. This is useful for different deployment scenarios and development purposes.

## Execution Modes

### 1. **Web-Only Mode** (`--mode web-only`)
Runs only the web dashboard in standalone demonstration mode.

**Use Cases:**
- Demo/presentation purposes
- Development of dashboard UI without data processing
- Shop system monitoring interface when detection engine is offline
- Testing dashboard responsiveness and features

**Features:**
- Simulated retail analytics data
- Randomized demo metrics that change over time
- All dashboard features functional with mock data
- No detection engine or data streaming required
- Lightweight and fast startup

**Usage:**
```bash
# Start standalone web dashboard
python start_sentinel.py --mode web-only --port 8080

# Using run_demo.py
python3 run_demo.py --mode web-only --duration 60
```

### 2. **Detection-Only Mode** (`--mode detection-only`)
Runs only the detection engine and data processing without any dashboard.

**Use Cases:**
- Production environments where dashboard runs separately
- Batch processing and data analysis
- Headless server deployments
- Event generation and logging focus

**Features:**
- Full detection engine with all 7 algorithms
- Data streaming server integration
- Event processing and alert generation
- JSON output file generation
- No UI overhead

**Usage:**
```bash
# Start detection engine only
python start_sentinel.py --mode detection-only --data-speed 10

# Using run_demo.py
python3 run_demo.py --mode detection-only --duration 120
```

### 3. **Both Mode** (`--mode both` - Default)
Runs both detection engine and web dashboard in fully integrated mode.

**Use Cases:**
- Complete system demonstration
- Development and testing
- Full-featured deployments
- Real-time monitoring with live data

**Features:**
- Full detection engine + live web dashboard
- Real-time data flow between components
- Complete Project Sentinel experience
- All features enabled

**Usage:**
```bash
# Start full system (default)
python start_sentinel.py
python start_sentinel.py --mode both --port 8080

# Using run_demo.py
python3 run_demo.py --duration 120 --dashboard web
```

## Command Line Options

### `start_sentinel.py`
```bash
python start_sentinel.py [OPTIONS]

Options:
  --mode {both,web-only,detection-only}  Execution mode (default: both)
  --port INT                            Web dashboard port (default: 8080)
  --dashboard {web,console,both}        Dashboard type (default: web)
  --data-speed INT                      Data streaming speed multiplier (default: 10)
  --data-port INT                       Data streaming server port (default: 8765)
```

### `run_demo.py`
```bash
python3 run_demo.py [OPTIONS]

Options:
  --mode {both,web-only,detection-only}  Execution mode (default: both)
  --duration INT                        Duration to run in seconds (default: 120)
  --dashboard {console,web,none}        Dashboard type (default: console)
  --data-dir PATH                       Path to data directory (default: auto-detect)
  --output-dir PATH                     Output directory for results (default: ./results)
```

## Examples

### Development Scenarios

```bash
# Work on dashboard UI without data complexity
python start_sentinel.py --mode web-only

# Test detection algorithms without UI
python start_sentinel.py --mode detection-only --data-speed 50

# Full integration testing
python start_sentinel.py --mode both --dashboard web
```

### Production Scenarios

```bash
# Distributed deployment - Dashboard server
python start_sentinel.py --mode web-only --port 80

# Distributed deployment - Processing server
python start_sentinel.py --mode detection-only --data-speed 1

# Single server deployment
python start_sentinel.py --mode both --port 8080
```

### Demo and Testing

```bash
# Quick dashboard demo
python3 run_demo.py --mode web-only --duration 30

# Algorithm testing and validation
python3 run_demo.py --mode detection-only --duration 300

# Complete system demonstration
python3 run_demo.py --mode both --duration 180 --dashboard web
```

## Technical Details

### Web Dashboard Standalone Mode
- Uses demo data generators with randomized realistic values
- All API endpoints functional with mock responses
- Maintains same UI/UX as connected mode
- Shows clear indicators when running in demo mode
- No external dependencies required

### Detection Engine Standalone Mode
- Full event processing pipeline
- All 7 detection algorithms active
- Data streaming server integration
- Event correlation and alert generation
- Output file generation (events.jsonl, summary.json)

### Architecture Benefits
- **Scalability**: Components can be scaled independently
- **Development**: Easier to work on specific components
- **Deployment**: Flexible deployment options
- **Testing**: Isolated testing of individual components
- **Maintenance**: Independent updates and maintenance

## Files Modified

- `src/web_dashboard/api/endpoints.py` - Added standalone mode support
- `src/web_dashboard/controller.py` - Added detection engine optional parameter
- `start_sentinel.py` - Added mode-based execution logic
- `evidence/executables/run_demo.py` - Added mode support for demo script

## Compatibility

All existing functionality remains fully compatible. The default behavior (`--mode both`) provides the same experience as before the decoupling.