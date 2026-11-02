# webkit2jb-bridge

Small C11 diagnostic library wired into the portal's local HTTP service.

## Components

- include/webkit2jb_bridge.h and include/w2jb/memory_policy.h: versioned C ABI, bounded request/reply structures, owned-data allocation, and an additive W^X report ABI.
- src/protocol: checks protocol version, request ID alphabet/length, operation and payload bounds before dispatch.
- src/core: lifecycle and backend dispatch.
- src/relay: stable relay ABI for capability discovery and bounded, allow-listed in-process requests. The existing `w2jb_bridge_request` remains as an ABI-compatible entry point and delegates to the relay. `memory-policy` reports read-only permissions for representative code, constant, mutable, heap, and stack regions in the bridge's own process. `NS2JB_STATUS` means only that the read-only unavailable-status probe is wired; it does not mean NS2JB operations are available.
- backends/linux: in-process Linux reference backend and current-process /proc/self/maps inspection.
- backends/mock: deterministic response and injectable failure backend for tests.
- backends/horizon-homebrew: optional libnx homebrew backend. It reports HOS version, supports in-process diagnostics/data echo, and explicitly reports network transport unavailable. Runtime W^X inspection is `UNSUPPORTED`; static NRO inspection does not establish runtime mappings.
- adapters/ns2jb-compatible: a versioned, read-only capability description pinned to the audited NS2JB commit. V1 ABI remains available; V2 explicitly returns zero verified capability flags and `CAPABILITY_UNAVAILABLE`. The Horizon demo calls this probe. The audit found no license-cleared portable NS2JB contract to reuse; no upstream code, wire format, payload, operation layout, or privileged interface is copied.
- `bridge/artifacts.py`: bounded, read-only ELF64/NSO/NRO identification with SHA-256, architecture evidence, container metadata checks, and ELF RWX/executable-stack rejection. It never extracts, loads, or executes artifacts. NSO inspection is deliberately limited to its header marker and minimum length; NRO/NSO architecture is reported as expected from the container convention, not as a parsed machine field.
- `bridge/resources/pc-runner-example.elf`: the 9,248-byte x86-64 example resource from the PC ELF runner, pinned by a manifest and validated read-only. `GET /api/bridge/pc-runner-artifact` and the bridge handshake return its architecture, capacity, size, and SHA-256. This is metadata/format validation only: the HTTP service never extracts or launches it, and the ELF is explicitly not Horizon-compatible.
- `bridge/python/runtime.py`: bounded `ctypes` binding from the HTTP server to the C ABI. The `memory-policy` route invokes the C relay; the Python simulator reports `UNSUPPORTED` instead of inventing mappings. The default server backend is `linux-native`; `linux-mock` selects the C mock, `pc-simulated` selects the Python simulator, and unavailable SDK backends report unavailable. Every response identifies its backend and execution origin and keeps `switchNativeExecution` false.
- `bridge-client.js` and `api-probe.py`: same-origin HTTP v1 client and service. The browser calls the service; the service calls the C library in its own process. This does not provide a native call path from WebKit or WifiWebAuthApplet.

The typed C API is in-process. The browser talks only to the local HTTP server. The C relay does not launch or communicate with a separate native service. There is no browser-to-native loader, no native service on the Switch, and no proof of execution in WifiWebAuthApplet.

## Build and run on Linux

    cmake -S bridge -B bridge/build -DW2JB_BUILD_TESTS=ON
    cmake --build bridge/build
    ctest --test-dir bridge/build --output-on-failure
    ./bridge/build/w2jb-bridge-demo
    python -m unittest discover -s tests -v

The shared library is produced as `bridge/build/libwebkit2jb_bridge.so`. Build it before starting `api-probe.py`; the process loads it with `ctypes`. `NS2_BRIDGE_BACKEND` can select `linux-native`, `linux-mock`, or `pc-simulated`. `NS2_BRIDGE_LIBRARY` overrides the library path, and `NS2_BRIDGE_MOCK_FAIL=1` injects an operational failure in the mock while leaving capability discovery available. The C demo selects linux-local, performs one diagnostic request, and exits. No test uses the WebKit corruption demonstrations or the ELF runner.

The portal's HTTP API is exposed at GET /api/bridge and POST /api/bridge. Operations are restricted to capabilities, diagnostic, in-process backend reachability (no external network probe), bounded echo, a read-only NS2JB compatibility status query, and a read-only memory-policy report. The NS2JB query returns `CAPABILITY_UNAVAILABLE` with zero capability flags; it does not call upstream IPC. Commands, arbitrary memory, process control, executable allocation and payload loading are not protocol operations. The read-only PC runner metadata route does not enter the native operation protocol. The JSON schema is bridge/protocol/bridge-v1.schema.json.

## Optional Horizon homebrew bridge and NRO

    ./bridge/build-horizon.sh

This requires devkitPro's `DEVKITPRO`, `DEVKITA64`, devkitA64 compiler, libnx, `nacptool`, and `elf2nro`. It builds the bridge static library, a minimal `w2jb-horizon-demo.elf`, NACP metadata, and `w2jb-horizon-demo.nro`; a local verifier checks ELF64/AArch64, non-RWX load segments, NRO0, and embedded title/author/version metadata. The example initializes the bridge, queries the relay, requests the W^X report, sends an in-process diagnostic, and requests the read-only NS2JB availability status. It waits for the homebrew applet to exit before shutting the bridge down. It does not use privileged services, install the NRO, or communicate with WebKit. Runtime permission inspection is explicitly `UNSUPPORTED` on Horizon; network transport and NS2JB operations remain unavailable.

A portable devkitPro installation was used without changing host-global configuration. The build completed with devkitA64 GCC 15.2.0 and libnx 4.12.0; the NRO and exact tool versions are recorded in [`HORIZON-BUILD.md`](HORIZON-BUILD.md). No console execution was performed.

## Linux ARM64 cross-check

    ./bridge/build-linux-aarch64.sh

This produces a Linux/AArch64 static archive using Clang's cross target (no Linux ARM64 libc sysroot is bundled) and runs an ABI/protocol/W^X smoke executable under `qemu-aarch64` when available. The smoke binary and every archive object are checked for AArch64; its program headers are checked for RWX segments and executable stack. This is not an execution test of the complete Linux backend under ARM64 and is not a Horizon validation.

## Provenance and upstream boundary

The NS2JB portability notes in this repository classify the audited source at commit 95f5525089273c5fce0b95047f3600f8442e96ae. They identify SmileBASIC/host session contracts and Horizon process-control code, but do not demonstrate a portable, licensed data interface. The original NS2JB source repository remains unmodified. Accordingly, this adapter defines only an unavailable-status seam. It does not reuse NS2JB IPC or payload code.

See the NS2JB portability documents for the documented boundaries and limitations.

libnx is an independent Switch homebrew library; the optional backend uses the documented hosversionGet() utility only. Documentation: https://switchbrew.github.io/libnx/hosversion_8h.html and https://github.com/switchbrew/libnx.
