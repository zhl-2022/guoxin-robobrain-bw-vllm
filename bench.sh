#!/usr/bin/env bash
set -euo pipefail
REPOSITORY_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
source "$REPOSITORY_ROOT/env.sh"
exec "$PYTHON_BIN" "$REPOSITORY_ROOT/scripts/bench_robo_native025.py" "$@"
