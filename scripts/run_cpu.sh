#!/usr/bin/env bash
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/.." && pwd)
cd "$ROOT"
if [ -x "$ROOT/.toolchain/bin/opt" ]; then
 export LLVM_BIN=${LLVM_BIN:-$ROOT/.toolchain/bin}
else
 export LLVM_BIN=${LLVM_BIN:-/usr/lib/llvm-17/bin}
fi
export ALIVE_TV=${ALIVE_TV:-$ROOT/.toolchain/bin/alive-tv}
# Drop model-auth environment variables from the CPU evaluation process.
unset HF_TOKEN HUGGING_FACE_HUB_TOKEN OPENAI_API_KEY ANTHROPIC_API_KEY
exec "$ROOT/.venv/bin/irsem" "$@"
