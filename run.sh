#!/usr/bin/env bash
set -euo pipefail
REPOSITORY_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
source "$REPOSITORY_ROOT/env.sh"
_ROBO_MODEL_PREP_ARGS=()
for _ROBO_ARG in "$@"; do
  if [[ "$_ROBO_ARG" == "--dry-run" ]]; then _ROBO_MODEL_PREP_ARGS=(--plan-only); fi
done
"$ROBOBRAIN_PYTHON_BIN" "$REPOSITORY_ROOT/scripts/prepare_image_model030.py" "${_ROBO_MODEL_PREP_ARGS[@]}" >&2
exec bash "$REPOSITORY_ROOT/tasks/robobrain-bw-vllm/run.sh" "$@"
