#!/usr/bin/env bash
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/.." && pwd)
BUILD=${IRSEM_BUILD_DIR:-$ROOT/.build}
mkdir -p "$BUILD"
[ "$(id -u)" -eq 0 ] || { echo 'Use the validator Dockerfile or install system prerequisites separately.' >&2; exit 2; }
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y --no-install-recommends ca-certificates curl gnupg git cmake ninja-build g++ re2c python3 python3-venv python3-pip libz3-dev libseccomp-dev libzstd-dev zlib1g-dev
curl --fail --location --retry 3 --connect-timeout 15 --max-time 120 https://apt.llvm.org/llvm-snapshot.gpg.key -o "$BUILD/llvm-key.asc"
gpg --batch --yes --dearmor -o /usr/share/keyrings/irsem-llvm.gpg "$BUILD/llvm-key.asc"
printf '%s\n' "deb [signed-by=/usr/share/keyrings/irsem-llvm.gpg] ${IRSEM_LLVM_APT_BASE:-https://apt.llvm.org}/jammy/ llvm-toolchain-jammy-17 main" > /etc/apt/sources.list.d/irsem-llvm17.list
apt-get update
apt-get install -y --no-install-recommends clang-17 llvm-17 llvm-17-dev
LLVM_CONFIG=/usr/lib/llvm-17/bin/llvm-config
[ "$("$LLVM_CONFIG" --version)" = 17.0.6 ] || { echo 'Unexpected LLVM version' >&2; exit 3; }
LLVM_CMAKE=$("$LLVM_CONFIG" --cmakedir)
if ! grep -Eq 'set\(LLVM_ENABLE_EH (ON|1)\)' "$LLVM_CMAKE/LLVMConfig.cmake"; then
 echo 'LLVM package lacks EH. Run build_llvm_source.sh, then build_alive2.sh with that LLVM cmake directory.' >&2; exit 4
fi
bash "$ROOT/scripts/build_alive2.sh" "$LLVM_CMAKE"
