#!/usr/bin/env sh
set -eu

docker compose exec backend python scripts/bridge_launch.py "$@"
