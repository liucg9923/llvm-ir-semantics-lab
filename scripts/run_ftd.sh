#!/usr/bin/env bash
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/.." && pwd)
cd "$ROOT"
case "${1:-}" in
 dev)
  bash scripts/run_model.sh generate --backend gguf --model compiler-ftd --split dev --smoke --out results/compiler-ftd-dev-v1
  .venv/bin/irsem evaluate --run results/compiler-ftd-dev-v1
  ;;
 formal)
  bash scripts/run_model.sh generate --backend gguf --model compiler-ftd --out results/compiler-ftd-v1
  .venv/bin/irsem evaluate --run results/compiler-ftd-v1
  ;;
 feedback)
  bash scripts/run_model.sh feedback --parent results/compiler-ftd-v1 --out results/compiler-ftd-feedback-v1
  .venv/bin/irsem evaluate --run results/compiler-ftd-feedback-v1
  ;;
 *) echo 'Usage: bash scripts/run_ftd.sh dev|formal|feedback' >&2;exit 2;;
esac
