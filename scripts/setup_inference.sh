#!/usr/bin/env bash
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/.." && pwd)
PYTHON=${IRSEM_PYTHON:-python3}
"$PYTHON" -m venv "$ROOT/.venv-inference"
"$ROOT/.venv-inference/bin/python" -m pip install --index-url "${IRSEM_PIP_INDEX_URL:-https://pypi.org/simple}" -e "$ROOT[inference]"
mkdir -p "$ROOT/.toolchain"
"$ROOT/.venv-inference/bin/python" -m pip freeze > "$ROOT/.toolchain/inference-freeze.txt"
# Downloads no model weights and does not accept any gated-model license.
