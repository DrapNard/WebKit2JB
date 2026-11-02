# WebKit2JB

**A local research lab for captive-browser behavior, WebKit font-lifetime bugs, and a non-privileged C/Horizon bridge.**

WebKit2JB brings the portal, reporting service, native bridge, and carefully bounded research notes together in one repository. It compares browser-visible behavior with native observations while keeping those evidence types separate.

> [!IMPORTANT]
> **This repository does not provide a WebKit-to-native exploit chain.** The browser page talks to a local HTTP service; that service invokes the C bridge in its own host process. It does not load native code into WifiWebAuthApplet or launch a program on the Switch.

## Research targets

| Reference | What the upstream change addresses | What this project has observed |
|---|---|---|
| **[CVE-2026-43715](https://support.apple.com/en-us/149041) · [WebKit bug 313577](https://github.com/WebKit/WebKit/commit/5aedb82710ba578f61501106e78f6b25b7f7a558)** | A use-after-free in `CSSFontFace::setStatus` reached through `CSSFontFace::load`; the fix checks whether a snapshotted client is still registered before notifying it. Apple maps this CVE to WebKit bug 313577. | In the isolated PC lab, WebKitGTK 2.52.4 produced five invalid reads and one invalid write under Memcheck; 2.52.6 and one negative control produced none. This is Linux evidence, not Switch evidence. |
| **[WebKit bug 312202](https://github.com/WebKit/WebKit/commit/5f0480f771ba1749663a8257eafca70af17b7cec)** | A separate face-lifetime issue; the fix retains strong `Ref<CSSFontFace>` ownership across operations that can re-enter. | The official test’s CSS rule removal was observed in WebKitGTK 2.52.3 and 2.52.4 after satisfying its local-font prerequisite. Both Release builds survived the bounded observation; that does not establish memory safety. No CVE is assigned to 312202 in this project. |
| **[WebKit bug 322233](https://github.com/WebKit/WebKit/commit/64a55fd574c40d8fda92b4f114d2a2afb9f0ec71)** | A separate re-entrant status-ordering issue; the fix commits the new status before client notification. | Source-level comparison only. It is not the same issue as 312202 or 313577, and this project does not assign it a CVE. |

The CVE mapping for 313577 is confirmed in [Apple’s security advisory](https://support.apple.com/en-us/149041) and the [upstream WebKit commit](https://github.com/WebKit/WebKit/commit/5aedb82710ba578f61501106e78f6b25b7f7a558). The source review does **not** identify the WebKit binary used by Switch firmware 23.0.1. Browser-side JavaScript observations and WebKitGTK results do not prove a native UAF on the console.

## What is in the lab

```text
WebKit2JB
├── api-probe.py, index.html, portal.js, diagnostics.js   captive portal and report API
├── bridge/                                               C API, protocol, Linux/mock/Horizon backends
├── shared/, schemas/                                     browser reporting and JSON contracts
├── fonts/                                                attributed test-font fixture
├── research/                                             English evidence dossier and redacted data
└── tests/                                                portal, protocol, artifact, and report tests
```

The bridge exposes a bounded, versioned API for capability discovery and local diagnostics. The Linux backend is usable by the local service; the mock backend supports deterministic tests. The optional Horizon backend is for a separately launched homebrew process. NS2JB operations remain `CAPABILITY_UNAVAILABLE`; no NS2JB payload or privileged interface is included.

## Evidence at a glance

- **PC / WebKitGTK:** the 313577 Memcheck comparison recorded invalid accesses in 2.52.4, but not in one tested 2.52.6 run or one 2.52.4 negative control. The stripped binaries prevent attribution to an exact source line.
- **Switch browser:** saved reports show JavaScript-visible font loading and synchronous re-entry in some reported runs. They do not reveal native object ownership, freeing, or invalid access.
- **Nintendo source archive:** the reviewed package is labeled `NS2_23.0.0` and contains WebKit/WKC 3.12.11 source. It has no WifiWebAuthApplet binary or trusted firmware Build-ID mapping; firmware under study is reported as 23.0.1.
- **Horizon bridge:** an AArch64 NRO was compiled and statically checked. It has not been run on a Switch.
- **Native execution:** the PC ELF sample ran through its ordinary isolated runner. It was never launched by WebKit or by a UAF.

See the [research dossier](research/README.md), [PC results](research/PC_WEBKITGTK_RESULTS.md), [evidence matrix](research/EVIDENCE_MATRIX.md), and [redacted data catalog](research/DATA_CATALOG.md) for methods, hashes, and limitations. Raw Switch reports, Memcheck logs, firmware/source archives, and Podman storage are kept outside this repository.

## Build and test on Linux

Requirements: Python 3, CMake, a C11 compiler, and Node.js for JavaScript syntax checks.

```sh
cmake -S bridge -B bridge/build -DW2JB_BUILD_TESTS=ON
cmake --build bridge/build
ctest --test-dir bridge/build --output-on-failure
python3 -m unittest discover -s tests -v
```

Run the local portal with the C shared library built first:

```sh
NS2_HOST=127.0.0.1 NS2_PORT=8081 NS2_OUT="$PWD/runs" python3 api-probe.py
```

Open `http://127.0.0.1:8081/`. The browser’s bridge client calls the HTTP service; the service loads the C library locally. Responses identify the actual backend and never report Switch-native execution based on a PC response. See [bridge documentation](bridge/README.md) for protocol operations and backend selection.

## Optional Horizon homebrew build

With devkitPro, devkitA64, and libnx configured:

```sh
./bridge/build-horizon.sh
```

The build creates an NRO and checks its ELF/NRO metadata and static load-segment permissions. **Build success is not evidence that the NRO ran on hardware.** Runtime W^X inspection and NS2JB operations remain unavailable in the current Horizon backend. See [Horizon build details](bridge/HORIZON-BUILD.md).

## Project boundaries

- No full WebKit build is required for the included portal or C bridge.
- No Switch diagnostic is started automatically; this repository does not claim a current hardware validation.
- The bridge has no arbitrary memory read/write, command execution, process-control, or payload-loading operation.
- ELF, NSO, and NRO inspection is bounded and read-only; Linux ELF execution is separate from the browser and bridge.
- The raw Switch and PC evidence remains in the local research workspaces. This repository contains summaries and privacy-redacted aggregate metadata, not the raw corpus.
- No blanket project license is asserted. Review [third-party notices](THIRD-PARTY-NOTICES.md) before reuse; the NS2JB section is analysis and includes no NS2JB source.

## Documentation

- [Research index](research/README.md)
- [Original source and provenance manifest](research/data/ORIGINAL_SOURCE_MANIFEST.json)
- [Switch report aggregate](research/data/SWITCH_REPORT_AGGREGATE.json)
- [Project structure](docs/PROJECT-STRUCTURE.md)
- [Public evidence status](docs/PUBLIC-EVIDENCE-STATUS.md)
- [Translation and history policy](docs/TRANSLATION-AND-HISTORY.md)
