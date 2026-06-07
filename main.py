#!/usr/bin/env python3
"""CLI entrypoint for running the shop API server."""

import argparse

from shop_api.shop_api import run_server


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments for host and port."""
    parser = argparse.ArgumentParser(description="Run the shop API server")
    parser.add_argument(
        "--host",
        default="localhost",
        help="Host address to bind the server to (default: localhost)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to bind the server to (default: 8000)",
    )

    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error("--port must be between 1 and 65535")
    return args


def main() -> None:
    """Run the shop API server using CLI arguments."""
    args = parse_args()
    run_server(host=args.host, port=args.port)


if __name__ == "__main__":
    main()
