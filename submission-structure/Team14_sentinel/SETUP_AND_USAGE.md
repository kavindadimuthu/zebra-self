# Project Sentinel - Setup and Usage Guide

## Overview

Project Sentinel is a comprehensive retail intelligence system that detects fraud, monitors queues, and optimizes store operations in real-time. The system has been streamlined to run with a single command.

## Quick Start

Run the complete system with one command:

```bash
cd submission-structure/Team##_sentinel/evidence/executables
python3 run_demo.py
```

This will:
- ✅ Start the detection engine
- ✅ Start the web dashboard on http://localhost:8080
- ✅ Process events and save to `evidence/output/events/`
- ✅ Run for 120 seconds (default duration)

## Command-Line Options

### Basic Usage

```bash
python3 run_demo.py [OPTIONS]
```

### Available Options

| Option | Values | Default | Description |
|--------|--------|---------|-------------|
| `--mode` | `both`, `web-only`, `detection-only` | `both` | Execution mode |
| `--duration` | Integer (seconds) | `120` | How long to run |
| `--output-subdir` | `events`, `final`, `test` | `events` | Output subdirectory |
| `--dashboard` | `web`, `console`, `none` | `web` | Dashboard type |
| `--data-dir` | Path | Auto-detect | Data directory location |

### Output Locations

All events are saved **ONLY** to the centralized location:

```
submission-structure/Team##_sentinel/evidence/output/{subdir}/
```

Where `{subdir}` can be:
- `events/` - Default location
- `final/` - For final submission
- `test/` - For testing runs

Each run creates:
- `events.json` - Event data in JSON array format
- `events.jsonl` - Event data in JSONL format (one per line)
- `summary.json` - Run summary with statistics

## Usage Examples

### 1. Default Run (Detection + Web Dashboard)

```bash
python3 run_demo.py
```

- Runs both detection engine and web dashboard
- Outputs to `evidence/output/events/`
- Duration: 120 seconds
- Dashboard: http://localhost:8080

### 2. Quick Test Run

```bash
python3 run_demo.py --duration 30 --output-subdir test
```

- 30-second test run
- Outputs to `evidence/output/test/`

### 3. Final Submission Run

```bash
python3 run_demo.py --duration 300 --output-subdir final
```

- 5-minute production run
- Outputs to `evidence/output/final/`

### 4. Detection Only (No Dashboard)

```bash
python3 run_demo.py --mode detection-only --dashboard none
```

- Runs only detection engine
- No dashboard/UI overhead
- Faster processing

### 5. Web Dashboard Only

```bash
python3 run_demo.py --mode web-only
```

- Runs standalone monitoring dashboard
- Shows server status diagnostics
- Useful for testing dashboard independently

### 6. Console Dashboard

```bash
python3 run_demo.py --dashboard console
```

- Uses terminal-based dashboard
- Lower resource usage
- Good for headless environments

## System Architecture

### Components

1. **Data Streaming Server**
   - Replays real retail data events
   - Port: 8765 (TCP)
   - 10x speed by default

2. **Detection Engine**
   - Processes events in real-time
   - Runs multiple detection algorithms:
     - Scan avoidance detection
     - Weight discrepancy detection
     - Barcode switching detection
     - Queue monitoring
     - Inventory discrepancy detection
     - System crash detection
     - Success operation tracking

3. **Web Dashboard** (Optional)
   - Real-time monitoring interface
   - Port: 8080 (HTTP)
   - Auto-refreshes every 5 seconds
   - Shows alerts, metrics, and system status

### Data Flow

```
Data Server (8765) → Detection Engine → Events Output
                            ↓
                     Web Dashboard (8080)
```

## Output Files

### events.json

JSON array format containing all detected events:

```json
[
  {
    "timestamp": "2025-08-13T16:00:25",
    "event_id": "SN_SCC1_1755081025",
    "event_data": {
      "event_name": "Staffing Needs",
      "station_id": "SCC1",
      "Staff_type": "Cashier",
      "reason": "High queue length with slow service",
      "customer_count": 4,
      "avg_dwell_time": 274.6
    }
  }
]
```

### events.jsonl

JSONL format (one JSON object per line) - easier for streaming/processing:

```jsonl
{"timestamp": "2025-08-13T16:00:25", "event_id": "SN_SCC1_1755081025", "event_data": {...}}
{"timestamp": "2025-08-13T16:01:30", "event_id": "SN_SCC2_1755081090", "event_data": {...}}
```

### summary.json

Run statistics and metrics:

```json
{
  "run_timestamp": "2025-10-04T14:14:31.123456",
  "duration_seconds": 120,
  "system_status": {
    "events_processed": 1234,
    "alerts_generated": 16,
    "uptime_seconds": 120.5,
    "events_per_minute": 123.4
  },
  "total_alerts": 16,
  "alerts_by_type": {
    "Staffing Needs": 8,
    "Scan Avoidance": 3,
    "Weight Discrepancy": 5
  },
  "high_severity_alerts": 3,
  "output_files": ["events.jsonl", "summary.json"]
}
```

## Troubleshooting

### Port Already in Use

If you see "Address already in use" errors:

```bash
# Kill streaming server (port 8765)
pkill -f stream_server.py

# Kill web dashboard (port 8080)
lsof -i :8080 | grep python | awk '{print $2}' | xargs kill
```

### Failed to Load Product Catalog

This warning can be ignored - it doesn't affect event detection. The system will still work correctly.

### No Events Generated

This is normal for very short runs (< 10 seconds). The system needs time to:
1. Connect to data stream
2. Process events
3. Correlate data across sensors

Try running for at least 30 seconds.

### Web Dashboard Not Loading

1. Check the dashboard URL in the output
2. Ensure port 8080 is not blocked by firewall
3. Try console dashboard instead: `--dashboard console`

## Performance Tips

1. **Faster Processing**: Use `--dashboard none` to reduce overhead
2. **Longer Runs**: Increase `--duration` for more comprehensive results
3. **Clean Environment**: Kill old processes before starting new runs

## Directory Structure

```
Team##_sentinel/
├── evidence/
│   ├── executables/
│   │   └── run_demo.py          # Main entry point
│   └── output/
│       ├── events/              # Default output (--output-subdir events)
│       ├── final/               # Final submission (--output-subdir final)
│       └── test/                # Test runs (--output-subdir test)
├── src/
│   ├── detection_engine.py      # Core detection engine
│   ├── dashboard.py             # Console dashboard
│   ├── data_ingestion.py        # Data streaming client
│   ├── event_correlation.py     # Event correlation
│   ├── detectors/               # Individual detection algorithms
│   └── web_dashboard/           # Web dashboard components
└── start_sentinel.py            # Alternative startup script
```

## Integration with Submission

For your final submission, use:

```bash
python3 run_demo.py --duration 300 --output-subdir final
```

This will create all outputs in:
```
submission-structure/Team##_sentinel/evidence/output/final/
```

Zip these files with your submission according to the hackathon guidelines.

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review the console output for error messages
3. Try a shorter test run first: `python3 run_demo.py --duration 10 --output-subdir test`

---

**Last Updated**: October 4, 2025
**Version**: 2.0 - Streamlined Single Command Edition
