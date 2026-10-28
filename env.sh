#!/usr/bin/env bash
_TASK_REPOSITORY_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# Match the DTK26.04 environment and service profile used by the full200 run
# and the original native performance matrix. Model/driver bytes are unchanged.
export ROBOBRAIN_PYTHON_BIN="${ROBOBRAIN_PYTHON_BIN:-/usr/bin/python3}"
export ROBOBRAIN_MAX_RUNTIME_SECONDS="${ROBOBRAIN_MAX_RUNTIME_SECONDS:-43200}"
export ROBOBRAIN_SERVED_NAME="${ROBOBRAIN_SERVED_NAME:-${ROBOBRAIN_MODEL_PATH:-/root/private_data/SothisAI/model/Aihub/RoboBrain2.5-8B-NV/main/RoboBrain2.5-8B-NV}}"
export ROCM_PATH="${ROCM_PATH:-/opt/dtk}"
export HIP_PATH="${HIP_PATH:-/opt/dtk/hip}"
for _ROBO_PATH in /opt/hyhal/bin /opt/dtk/hip/bin /opt/dtk/llvm/bin /opt/dtk/bin /opt/ucx/bin; do
  case ":$PATH:" in *":$_ROBO_PATH:"*) ;; *) export PATH="$_ROBO_PATH:$PATH" ;; esac
done
for _ROBO_PATH in /opt/hwloc/lib /opt/mpi/lib /opt/dtk/opencl/lib /opt/dtk/dushmem/lib /opt/hyhal/lib64 /opt/hyhal/lib /opt/dtk/lib64 /opt/dtk/lib /opt/dtk/llvm/lib /opt/dtk/hip/lib /opt/dtk/dcc/gcvm/lib /opt/ucx/lib; do
  case ":${LD_LIBRARY_PATH:-}:" in *":$_ROBO_PATH:"*) ;; *) export LD_LIBRARY_PATH="$_ROBO_PATH${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}" ;; esac
done
source "$_TASK_REPOSITORY_ROOT/tasks/robobrain-bw-vllm/env.sh"
unset _TASK_REPOSITORY_ROOT _ROBO_PATH
