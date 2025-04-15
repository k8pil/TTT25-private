#!/usr/bin/env python

"""
Run Interview Advisor

This script launches the Interview Advisor application.
"""

import os
import sys
import argparse
from interview_advisor.main import main
from interview_advisor.api import run_api

if __name__ == "__main__":
    # Check if Python version is at least 3.8
    if sys.version_info < (3, 8):
        print("Error: Python 3.8 or higher is required.")
        sys.exit(1)

    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Run Interview Advisor")
    parser.add_argument("--api", action="store_true",
                        help="Run in API server mode")
    parser.add_argument("--port", type=int, default=5000,
                        help="Port for API server")
    parser.add_argument("--debug", action="store_true",
                        help="Run in debug mode")
    parser.add_argument("--no-database", action="store_true",
                        help="Run without database functionality")
    args = parser.parse_args()

    if args.api:
        # Run in API server mode
        run_api(port=args.port, debug=args.debug, no_database=args.no_database)
    else:
        # Run in interactive mode
        main(no_database=args.no_database)
