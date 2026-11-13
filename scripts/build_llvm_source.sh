#!/usr/bin/env bash
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/.." && pwd)
BUILD=${IRSEM_BUILD_DIR:-$ROOT/.build}
JOBS=${IRSEM_BUILD_JOBS:-4}
mkdir -p "$BUILD"
if [ "${IRSEM_USE_PROVIDER_PROXY:-0}" = 1 ] && [ -f /etc/network_turbo ]; then
 source /etc/network_turbo >/dev/null 2>&1
fi
if [ ! -d "$BUILD/llvm-project/.git" ]; then
 git clone --depth 1 --branch llvmorg-17.0.6 https://github.com/llvm/llvm-project.git "$BUILD/llvm-project"
fi
[ "$(git -C "$BUILD/llvm-project" describe --tags --exact-match)" = llvmorg-17.0.6 ]
[ "$(git -C "$BUILD/llvm-project" rev-parse HEAD)" = 6009708b4367171ccdbf4b5905cb6a803753fe18 ]
cmake -S "$BUILD/llvm-project/llvm" -B "$BUILD/llvm17-build" -G Ninja \
 -DCMAKE_BUILD_TYPE=Release -DLLVM_TARGETS_TO_BUILD=X86 -DLLVM_ENABLE_PROJECTS="" \
 -DLLVM_ENABLE_EH=ON -DLLVM_ENABLE_RTTI=ON -DLLVM_ENABLE_ASSERTIONS=ON \
 -DLLVM_INCLUDE_TESTS=OFF -DLLVM_INCLUDE_BENCHMARKS=OFF
cmake --build "$BUILD/llvm17-build" --target opt llvm-as llvm-dis llvm-config --parallel "$JOBS"
bash "$ROOT/scripts/build_alive2.sh" "$BUILD/llvm17-build/lib/cmake/llvm"
printf 'Use LLVM_BIN=%s\n' "$BUILD/llvm17-build/bin"
