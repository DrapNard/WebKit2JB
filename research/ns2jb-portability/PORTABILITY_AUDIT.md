# NS2JB native payload portability audit

## Scope and evidence boundary

This is a source-level architecture review of the public upstream repository `pepsipu/ns2jb` at GitLab `main`, commit `95f5525089273c5fce0b95047f3600f8442e96ae` (short `95f55250`, observed through the GitLab branch API on 2026-11-01). The source pages reviewed were the project README and `engine/switch2/ro/payload/{main.c,process.c,start.S}`, the payload manifest, and the builder source. No upstream checkout or binary was added to this laboratory. No payload was downloaded, built, run, or installed; no Switch interaction was performed. No NS2JB source or license text was copied.

The payload source contains privileged Horizon IPC and process-memory / executable-page operations. This report therefore records only the architectural separation and compatibility boundary. It deliberately omits wire-level IPC encodings, operation IDs, invocation recipes, binary layout reconstruction steps, and a recipe for rebuilding or porting the privileged payload. Those details would turn this review into an operational porting guide.

## Findings

| Question | Finding | Classification |
|---|---|---|
| Is the small C/assembly payload source separate from SmileBASIC syntax? | Yes. `main.c`, `process.c`, and `start.S` are native source files, and the upstream README identifies Zig 0.15.2 as its reproduction toolchain. That separation does not make the program platform-independent. | CONFIRMED |
| Does the payload itself depend on Horizon? | Yes. Its assembly startup layer contains AArch64 system-call wrappers and its C sources depend on Horizon IPC/process semantics. It is built for the Horizon module environment rather than a Linux process ABI. | CONFIRMED |
| Does the full NS2JB execution path depend on SmileBASIC? | Yes. The README identifies a SmileBASIC program and host-side Node orchestration. The native helper is one component in a larger loader/orchestration path, not a standalone WebKit artifact. | CONFIRMED |
| Are pure C routines reusable? | Only routines proven free of Horizon types, handles, service state, and side effects could be extracted for ordinary unit tests. No such isolated library boundary or Linux test suite was demonstrated by the reviewed payload files. | PROBABLE / NOT DEMONSTRATED |
| Can the payload be loaded directly by WifiWebAuthApplet? | No such loader or ABI is exposed by the browser page. A web document executing JavaScript is not an ELF/NSO/NRO loader. | INCOMPATIBLE |
| Is the existing NRO compatible with NS2JB's native helper interface? | No direct compatibility is demonstrated. The NRO is an independent libnx homebrew application using a homebrew launch context; it does not implement the payload's Horizon service contract. | NOT DEMONSTRATED; direct loading is INCOMPATIBLE |
| Is the shipped native image byte-for-byte reproducible here? | Not tested. The upstream manifest advertises a 4,757-byte payload and a SHA-256, while the README says Zig 0.15.2 is used for reproduction. The exact binary bytes were not acquired and compared. | NOT DEMONSTRATED |
| Are reuse rights established? | The project API response exposed no license metadata. No license was independently established for reuse. | NOT DEMONSTRATED |

## Component boundary

- **SmileBASIC-facing layer:** the BASIC bootstrap and the host-to-console orchestration described by the README. This supplies the project-specific entry/session path; it is not a native API that WifiWebAuthApplet can call.
- **Host layer:** Node.js transport and orchestration. It coordinates a session with the BASIC program and consumes the native helper's results. It is host software, not part of the ARM64 payload.
- **Native helper:** `main.c` implements the helper's long-running Horizon service loop; `process.c` handles privileged process-oriented requests; `start.S` supplies the low-level AArch64/Horizon entry and syscall glue. These are Horizon-coupled, not Linux-portable as-is.
- **Horizon boundary:** the helper expects Horizon kernel IPC, service registration, handles, memory metadata, and process control semantics. Those are not web APIs and are not proven available to WifiWebAuthApplet.
- **Existing NRO:** a separate libnx homebrew test application. Its local artifact is `research/native-demo/build/ns2-system-dialog-demo.nro`, 208,952 bytes, SHA-256 `c1ceb5084dddc2d44625997b535f0e35a8ef7fdfaae19da3fbcd108301e29fc8`; its existing build record identifies `NRO0` and AArch64. It has not been run on the console and does not establish any NS2JB IPC integration.

## Reuse conclusion

The only reasonable reuse boundary for ordinary Linux tests is newly documented, side-effect-free parsing or validation code after it has been separated from Horizon headers, handles, and privileged operations. The reviewed payload does not currently establish that boundary. The native service loop and process-control functionality are not suitable for transplantation into WebKit2JB, and no code was copied or modified here.

## Source references

- [Upstream README](https://gitlab.com/pepsipu/ns2jb/-/blob/95f5525089273c5fce0b95047f3600f8442e96ae/README.md)
- [Payload `main.c`](https://gitlab.com/pepsipu/ns2jb/-/blob/95f5525089273c5fce0b95047f3600f8442e96ae/engine/switch2/ro/payload/main.c)
- [Payload `process.c`](https://gitlab.com/pepsipu/ns2jb/-/blob/95f5525089273c5fce0b95047f3600f8442e96ae/engine/switch2/ro/payload/process.c)
- [Payload `start.S`](https://gitlab.com/pepsipu/ns2jb/-/blob/95f5525089273c5fce0b95047f3600f8442e96ae/engine/switch2/ro/payload/start.S)
- [Payload manifest](https://gitlab.com/pepsipu/ns2jb/-/blob/95f5525089273c5fce0b95047f3600f8442e96ae/engine/switch2/ro/payload/manifest.json)
