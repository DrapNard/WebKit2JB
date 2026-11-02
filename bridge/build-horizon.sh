#!/bin/sh
set -eu
if [ -z "${DEVKITPRO:-}" ] || [ -z "${DEVKITA64:-}" ]; then
    echo "DEVKITPRO and DEVKITA64 are required; no Horizon SDK build was attempted." >&2
    exit 2
fi
if [ ! -f "$DEVKITPRO/libnx/include/switch.h" ] || [ ! -f "$DEVKITPRO/libnx/switch.specs" ]; then
    echo "DEVKITPRO does not point to a libnx installation: $DEVKITPRO" >&2
    exit 2
fi
if [ ! -x "$DEVKITA64/bin/aarch64-none-elf-gcc" ]; then
    echo "DEVKITA64 does not contain aarch64-none-elf-gcc: $DEVKITA64" >&2
    exit 2
fi
for tool in "$DEVKITPRO/tools/bin/nacptool" "$DEVKITPRO/tools/bin/elf2nro"; do
    if [ ! -x "$tool" ]; then
        echo "Required devkitPro tool is unavailable: $tool" >&2
        exit 2
    fi
done
cmake -S "$(dirname "$0")" -B "$(dirname "$0")/build-horizon" \
    -DW2JB_BUILD_HORIZON=ON -DW2JB_BUILD_TESTS=OFF \
    -DCMAKE_SYSTEM_NAME=Generic -DCMAKE_SYSTEM_PROCESSOR=aarch64 \
    -DCMAKE_TRY_COMPILE_TARGET_TYPE=STATIC_LIBRARY \
    -DCMAKE_C_COMPILER="$DEVKITA64/bin/aarch64-none-elf-gcc" \
    -DCMAKE_C_FLAGS="-I${DEVKITPRO}/libnx/include"
cmake --build "$(dirname "$0")/build-horizon" --target w2jb-horizon-nro --parallel 2
python3 "$(dirname "$0")/verify-horizon-artifact.py" \
    "$(dirname "$0")/build-horizon/w2jb-horizon-demo.elf" \
    "$(dirname "$0")/build-horizon/w2jb-horizon-demo.nro" \
    "$(dirname "$0")/build-horizon/w2jb-horizon-demo.nacp" \
    "$(dirname "$0")/build-horizon/build-info.json"
