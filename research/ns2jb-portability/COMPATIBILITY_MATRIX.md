# Compatibility matrix

| Component / runtime | Linux x86-64 | ARM64 Linux | Horizon system-module context | Homebrew NRO context | WifiWebAuthApplet |
|---|---|---|---|---|---|
| NS2JB host Node.js orchestration | Host-side code is intended to run on macOS/Linux; target session is still required. | Possible host architecture, not evidence of device-side support. | Not the native payload. | Not an NRO component. | Not called by a web page; no host session bridge is provided. |
| SmileBASIC bootstrap/workers | Not executable as native Linux code. | Not native ARM64 code. | Depends on the SmileBASIC application/runtime. | Not a libnx module. | Not available in the captive browser context. |
| NS2JB native helper source | Incompatible as-is: AArch64 assembly, Horizon SVC/IPC and process handles. | CPU architecture alone is insufficient; Horizon ABI remains missing. | Source is designed for this class of context. | No compatibility demonstrated; NRO loader/process context differs. | Incompatible: a page has no NSO loader or Horizon IPC handle. |
| Existing `ns2-system-dialog-demo.nro` | Not a Linux executable. | Architecture matches CPU only; runtime ABI differs. | Not an NSO/system module. | Built as a libnx homebrew NRO; console execution remains unverified. | Not loadable from the page. |
| Ordinary pure parsing code, if extracted | Potentially unit-testable after separation. | Potentially portable. | Could be called only through an explicit safe wrapper. | Potentially reusable as ordinary library code if licenses/ABI allow. | Only the equivalent data-format logic could be rewritten in JavaScript; no native loading is implied. |

## Why the formats and contexts do not line up

- **Architecture is not a loader contract:** ARM64 describes instruction set, not executable container, ABI, imports, permissions, or process launch rights.
- **NSO is not NRO:** the upstream build source packages a system-module image; the local demo is an NRO intended for a homebrew launch environment.
- **NPDM is metadata, not code:** a policy hash or metadata file does not grant a web document a native process context.
- **WebKit is not Horizon's module loader:** JavaScript executes under the applet's browser process and web security model. The inspected portal interfaces expose HTTP endpoints, not Horizon service handles.
- **No permission equivalence:** NS2JB's helper is explicitly Horizon process-context code. WifiWebAuthApplet's JavaScript permissions do not imply those capabilities.

## Existing NRO verdict

The local NRO is a standalone libnx diagnostic application, not an NS2JB-compatible helper. Its exact metadata and hash are recorded at `research/native-demo/build-info.json`; the bytes start with the expected NRO header marker at the NRO header offset. Its console behavior has not been tested. **Direct NSO/NRO exchange or invocation is INCOMPATIBLE; shared data-only logic is NOT DEMONSTRATED.**
