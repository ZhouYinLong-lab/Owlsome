#!/usr/bin/env python3
"""
MinerU WebUI — Entry Point

Usage:
    python run.py              # Start server at http://127.0.0.1:7861
    python run.py --port 8080  # Custom port
    python run.py --host 0.0.0.0 --port 7861  # Expose on LAN
"""

import argparse
import sys
from pathlib import Path

# Ensure the project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

import uvicorn


def main():
    parser = argparse.ArgumentParser(description="MinerU WebUI Server")
    parser.add_argument("--host", default="127.0.0.1", help="Bind address (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=7861, help="Port (default: 7861)")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload (dev mode)")
    args = parser.parse_args()

    print(f"\n  MinerU WebUI")
    print(f"  ─────────────")
    print(f"  http://{args.host}:{args.port}\n")

    uvicorn.run(
        "webui.app:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level="info",
    )


if __name__ == "__main__":
    main()
