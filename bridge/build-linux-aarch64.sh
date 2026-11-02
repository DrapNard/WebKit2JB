#!/bin/sh
set -eu
BRIDGE_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
BUILD_DIR="${W2JB_AARCH64_BUILD_DIR:-$BRIDGE_DIR/build-aarch64}"
for tool in clang llvm-ar llvm-readelf ld.lld; do
    if ! command -v "$tool" >/dev/null 2>&1; then
        echo "$tool is required for the AArch64 cross build." >&2
        exit 2
    fi
done

cmake -S "$BRIDGE_DIR" -B "$BUILD_DIR" \
    -DCMAKE_TOOLCHAIN_FILE="$BRIDGE_DIR/cmake/aarch64-linux-clang.cmake" \
    -DW2JB_BUILD_TESTS=OFF
cmake --build "$BUILD_DIR" --target webkit2jb_bridge --parallel 2

ABI_DIR="$BUILD_DIR/abi-smoke"
mkdir -p "$ABI_DIR"
clang --target=aarch64-linux-gnu -ffreestanding -fno-stack-protector -fno-pic \
    -I"$BRIDGE_DIR/compat/aarch64-linux/include" -I"$BRIDGE_DIR/include" -I"$BRIDGE_DIR/src/core" \
    -c "$BRIDGE_DIR/src/protocol/protocol.c" -o "$ABI_DIR/protocol.o"
clang --target=aarch64-linux-gnu -ffreestanding -fno-stack-protector -fno-pic \
    -I"$BRIDGE_DIR/compat/aarch64-linux/include" -I"$BRIDGE_DIR/include" \
    -c "$BRIDGE_DIR/src/core/memory_policy_contract.c" -o "$ABI_DIR/memory_policy.o"
clang --target=aarch64-linux-gnu -ffreestanding -fno-stack-protector -fno-pic \
    -I"$BRIDGE_DIR/compat/aarch64-linux/include" -I"$BRIDGE_DIR/include" \
    -I"$BRIDGE_DIR/adapters/ns2jb-compatible" -I"$BRIDGE_DIR/src/core" \
    -c "$BRIDGE_DIR/tests/arm64_abi_smoke.c" -o "$ABI_DIR/test.o"
clang --target=aarch64-linux-gnu -c "$BRIDGE_DIR/tests/arm64_start.S" -o "$ABI_DIR/start.o"
ld.lld -m aarch64elf -static -e _start -o "$ABI_DIR/w2jb-arm64-abi-smoke" \
    "$ABI_DIR/start.o" "$ABI_DIR/test.o" "$ABI_DIR/protocol.o" "$ABI_DIR/memory_policy.o"
llvm-readelf -h "$ABI_DIR/w2jb-arm64-abi-smoke" | rg -q 'Machine:.*AArch64'
ARCHIVE_MEMBERS=$(llvm-ar t "$BUILD_DIR/libwebkit2jb_bridge.a" | wc -l)
ARCHIVE_AARCH64_MEMBERS=$(llvm-readelf -h "$BUILD_DIR/libwebkit2jb_bridge.a" | rg -c 'Machine:.*AArch64')
if [ "$ARCHIVE_MEMBERS" -eq 0 ] || [ "$ARCHIVE_MEMBERS" -ne "$ARCHIVE_AARCH64_MEMBERS" ]; then
    echo "The Linux ARM64 archive contains a non-AArch64 object." >&2
    exit 1
fi
python3 "$BRIDGE_DIR/verify-linux-elf.py" "$ABI_DIR/w2jb-arm64-abi-smoke" AArch64
if command -v qemu-aarch64 >/dev/null 2>&1; then
    qemu-aarch64 "$ABI_DIR/w2jb-arm64-abi-smoke"
    echo "ARM64 ABI/protocol/W^X smoke under QEMU: PASS"
else
    echo "qemu-aarch64 unavailable; produced ARM64 ABI smoke binary without execution."
fi

echo "Linux ARM64 static archive: $BUILD_DIR/libwebkit2jb_bridge.a"
llvm-readelf -h "$BUILD_DIR/libwebkit2jb_bridge.a" | rg 'Machine:.*AArch64' | head -1
