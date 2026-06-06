#!/bin/bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ "${1:-}" == "-a" ]]; then
	echo "Running full clean via git..."
	git -C "$ROOT_DIR" clean -xfd
	exit 0
fi

echo "Cleaning logs and database files..."
rm -f "$ROOT_DIR"/shop_api.log
rm -f "$ROOT_DIR"/shop.db

echo "Done."