#!/usr/bin/env bash
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/.." && pwd)
cd "$ROOT"
mkdir -p "$ROOT/.cache"
exec 9> "$ROOT/.cache/gpu.lock"
flock -n 9 || { echo "Another project model process holds the GPU lock" >&2; exit 2; }
export HF_HOME=${HF_HOME:-$ROOT/.cache/huggingface}
export TOKENIZERS_PARALLELISM=false
export CUBLAS_WORKSPACE_CONFIG=:4096:8
exec "$ROOT/.venv-inference/bin/irsem" "$@"
