import argparse

from shop_api.shop_api import run_server


def parse_args():
    """Parse command-line arguments for server startup."""
    parser = argparse.ArgumentParser(description="Start Shop API server")
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Network port for the HTTP server (default: 8000)",
    )
    parser.add_argument(
        "--host",
        default="localhost",
        help="Network host/interface for the HTTP server (default: localhost)",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    run_server(host=args.host, port=args.port)
