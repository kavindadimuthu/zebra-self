# Submission Guide

Complete this template before zipping your submission. Keep the file at the
project root.

## Team details
- Team name: Team Sentinel Alpha
- Members: AI Assistant (GitHub Copilot)
- Primary contact email: contact@projectsentinel.example

## Judge run command
Judges will `cd evidence/executables/` and run **one command** on Ubuntu 24.04:

```
python3 run_demo.py --duration 60 --dashboard none
```

This command will:
1. Verify Python 3.9+ is available (no additional dependencies required)
2. Start the data streaming server from the data directory
3. Initialize the detection engine with product catalogs
4. Run all 7 detection algorithms on the live data stream
5. Generate events.jsonl in ./results/ directory

## Checklist before zipping and submitting
- Algorithms tagged with `# @algorithm Name | Purpose` comments: ✓ All 7 detectors have proper tags
- Evidence artefacts present in `evidence/`: ✓ Complete executables and output structure ready
- Source code complete under `src/`: ✓ Full detection engine with all modules implemented
