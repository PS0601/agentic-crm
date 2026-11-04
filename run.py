#!/usr/bin/env python3
"""
Quick start script for AI-Powered CRM
Runs the FastAPI server with hot reload
"""

import uvicorn
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    print("=" * 70)
    print("  🤖 AI-Powered CRM - Starting Server")
    print("=" * 70)
    print()
    print("  Dashboard:  http://localhost:8000/dashboard")
    print("  API Server: http://localhost:8000")
    print("  API Docs:   http://localhost:8000/docs")
    print("  Health:     http://localhost:8000/health")
    print()
    print("  Press CTRL+C to stop")
    print("=" * 70)
    print()

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
        access_log=True
    )
