# Horizon bridge build record

Date: 2026-11-02

## Toolchain

Build record from a portable devkitPro installation. No host-global configuration was changed.

| Component | Verified version/path |
|---|---|
| devkitPro root | `$DEVKITPRO` |
| devkitA64 compiler | `devkitA64/bin/aarch64-none-elf-gcc`, GCC 15.2.0 (`aarch64-none-elf`) |
| devkitA64 package | `devkitA64 r29.2-1` |
| GCC package | `devkita64-gcc 15.2.0-7` |
| binutils package | `devkita64-binutils 2.45.1-2` |
| libnx | `4.12.0-1` |
| Switch tools | `1.13.1-1` (`elf2nro`, `nacptool`) |

The official `switch.specs` is supplied by libnx. The temporary tool environment was:

```sh
export DEVKITPRO=/path/to/devkitpro
export DEVKITA64="$DEVKITPRO/devkitA64"
export PATH="$DEVKITA64/bin:$DEVKITPRO/tools/bin:$PATH"
```

## Build and verification

From the repository root, the exact command was:

```sh
./bridge/build-horizon.sh
```

The script configured CMake with `aarch64-none-elf-gcc`, `W2JB_BUILD_HORIZON=ON`, libnx's `switch.specs`, then compiled the static bridge and `horizon_bridge_demo.c`, created NACP metadata with `nacptool`, and packaged the NRO with `elf2nro`.

The artifact verifier confirmed ELF64 little-endian AArch64, NRO0 magic, a valid ASET header, the NACP section bounds, exact NACP sidecar embedding, and title `WebKit2JB Bridge Demo`, author `WebKit2JB Lab`, version `0.1.0`. ELF program headers contain RX, R, and RW `PT_LOAD`s without RWX. The ELF has no `GNU_STACK` program header, so this build record makes no claim about effective runtime stack permissions.

The native demo prints an ASCII banner containing `UwU from Nintendo Switch 2`, reports the HOS version when libnx provides it, initializes the Horizon bridge, queries relay ABI v1 capabilities, sends the diagnostic request through the relay, and requests NS2JB compatibility status through the relay. That status is `CAPABILITY_UNAVAILABLE` with zero NS2JB operation flags; it is not an invocation of NS2JB. The app waits for PLUS or B and shuts down the bridge afterward. It prints the initialized state only after successful bridge initialization. The NRO has only been compiled and statically checked; it has not been run on a console.

| Artifact | Path | Size | SHA-256 |
|---|---|---:|---|
| NRO | `bridge/build-horizon/w2jb-horizon-demo.nro` | 233,528 bytes | `9bdc2d13317a85f8e4e7146f08febf00ddfe0dd69e610ddade97ffe630ce0a20` |
| ELF | `bridge/build-horizon/w2jb-horizon-demo.elf` | 2,963,440 bytes | `8f8fdde2b3ae1c57ecd30f491a4fa6b44f56ef572e62e838e208da8d91ad4784` |
| NACP | `bridge/build-horizon/w2jb-horizon-demo.nacp` | 16,384 bytes | `3728518df07cc5b3d669e15e5ef4391f341d0f8ace43886341978ab6cae11bc0` |

No NRO was run on a Switch. Build success is not runtime validation on Horizon hardware.
