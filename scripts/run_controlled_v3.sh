#!/usr/bin/env bash
# Reproduce the final B protocol in a fresh prepared cloud checkout.
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/.." && pwd)
cd "$ROOT"
for prior in results/v3b-pilot-* results/v3b-formal-*; do
 [ ! -e "$prior" ] || { echo 'Existing run evidence found; use a fresh checkout/run namespace.' >&2; exit 2; }
done
export HF_HOME="$ROOT/.cache/huggingface" HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 TOKENIZERS_PARALLELISM=false CUBLAS_WORKSPACE_CONFIG=:4096:8
[ -f results/model-downloads/qwen-verified.json ] && [ -f results/model-downloads/compiler-ftd-verified.json ]
if [ ! -f results/campaign-v3/hints.json ]; then .venv/bin/python scripts/build_v3_hints.py; fi
.venv/bin/python scripts/accept_v3.py
if [ ! -f results/campaign-v3/frozen.json ]; then
 .venv/bin/python -c 'from pathlib import Path;from irsem.v3.control import freeze;freeze(Path.cwd())'
fi
stage() {
 local model=$1 phase=$2 name=$3 out=$4
 .venv/bin/python scripts/run_stage.py --campaign campaign-v3 --name "$name" --timeout 5400 --profile-gpu -- flock .cache/gpu.lock .venv-inference/bin/python -m irsem.v3.runner --model "$model" --phase "$phase" --profile native_bounded_v1 --out "results/$out"
}
for model in compiler-ftd qwen; do stage "$model" pilot "reproduction-pilot-$model" "v3b-pilot-$model"; done
.venv/bin/python - <<'PY'
from pathlib import Path
from irsem.v3.selection import select
r=select(Path.cwd(),['v3b-pilot-compiler-ftd','v3b-pilot-qwen'])
if not r['primary_passed']:raise SystemExit('STOP: no formal comparison while primary gate fails')
PY
for model in compiler-ftd qwen; do stage "$model" hint_pilot "reproduction-hintpilot-$model" "v3b-hintpilot-$model"; done
.venv/bin/python - <<'PY'
from pathlib import Path
from irsem.v3.selection import select
select(Path.cwd(),['v3b-pilot-compiler-ftd','v3b-pilot-qwen'],['v3b-hintpilot-compiler-ftd','v3b-hintpilot-qwen'])
PY
for model in opt identity compiler-ftd qwen; do stage "$model" formal "reproduction-formal-$model" "v3b-formal-$model"; done
if .venv/bin/python -c 'import json;raise SystemExit(0 if json.load(open("results/campaign-v3/selected-profile.json"))["hint_passed"] else 1)'; then
 for model in compiler-ftd qwen; do stage "$model" hint "reproduction-hint-$model" "v3b-hint-$model"; done
fi
