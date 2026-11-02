# IPC interface inventory (high-level)

This document records boundaries and responsibilities only. It does not reproduce message IDs, binary descriptors, argument layouts, syscall numbers, service-registration sequences, or process-control request recipes.

## Boundaries visible in the reviewed source

| Boundary | Producer / consumer | Contract category | Portability |
|---|---|---|---|
| Host ↔ SmileBASIC session | Node.js host and BASIC-side workers | Network/session framing and RPC orchestration | Host code can run on Linux, but its peer and state machine are SmileBASIC-specific. |
| Engine ↔ Horizon service manager | Native helper and Horizon | Service registration, session acceptance, request/reply, handle lifecycle | Horizon-only. Linux can only mock a neutral abstract interface; it cannot implement Horizon kernel semantics. |
| Engine ↔ process handle | Native helper and a Horizon process handle received through IPC | Process metadata, memory-region inspection, and privileged process-control operations | Horizon-only and security-sensitive. Exact request contract intentionally not documented here. |
| WifiWebAuthApplet ↔ portal server | Browser JavaScript and local HTTP APIs | Ordinary HTTP diagnostics/reporting | No NS2JB native IPC or NSO loader is evidenced at this boundary. |
| Existing NRO ↔ Horizon | libnx homebrew application | Homebrew application services and applet APIs | Separate process context and API surface; no adapter to the NS2JB helper is present. |

## Source-level separation

- `main.c` owns the Horizon-facing request loop and delegates process-oriented requests.
- `process.c` contains the sensitive process-handle boundary and platform-specific operations. It is not a pure portable C library.
- `start.S` supplies the AArch64 entry and low-level Horizon wrappers.
- The SmileBASIC/Node RPC is a separate host/session layer. It cannot be inferred to be compatible with WebKit HTTP just because both carry messages.

## Mocking boundary

A Linux unit-test seam could be created only for pure validation/parsing functions that have no Horizon types, handles, or side effects. The reviewed sources do not currently prove a clean such seam. This audit did not create mocks or tests. Any mock must exclude remote process-memory, permission, or instruction-modification behavior; those are not needed for a benign serialization test and must not be represented as ordinary portable IPC.

Sources: [main.c](https://gitlab.com/pepsipu/ns2jb/-/blob/95f5525089273c5fce0b95047f3600f8442e96ae/engine/switch2/ro/payload/main.c), [process.c](https://gitlab.com/pepsipu/ns2jb/-/blob/95f5525089273c5fce0b95047f3600f8442e96ae/engine/switch2/ro/payload/process.c), [start.S](https://gitlab.com/pepsipu/ns2jb/-/blob/95f5525089273c5fce0b95047f3600f8442e96ae/engine/switch2/ro/payload/start.S), [local NRO source](../native-demo/source/main.c).
