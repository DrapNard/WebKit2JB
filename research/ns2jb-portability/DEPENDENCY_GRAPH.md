# Dependency graph (architectural only)

The graph is based on upstream source roles, not a runtime trace. The privileged payload's operation-level IPC and process-control edges are intentionally abstracted.

```mermaid
flowchart LR
  subgraph NS2JB[Public NS2JB system]
    BASIC[SmileBASIC bootstrap and app-side workers]
    HOST[Host Node.js session/orchestration]
    ENGINE[JavaScript engine modules]
    NATIVE[ARM64 native helper: main.c + process.c + start.S]
    HOS[Horizon kernel and service environment]
    BASIC <-- session/RPC --> HOST
    HOST --> ENGINE
    ENGINE --> BASIC
    ENGINE --> NATIVE
    NATIVE --> HOS
  end

  subgraph TARGETS[Separate runtime environments]
    WIFI[WifiWebAuthApplet WebKit page]
    HBL[Homebrew launcher / libnx]
    NRO[Existing NS2 system-dialog demo NRO]
    WIFI -->|HTML / JavaScript only; no native-module loader evidenced| WIFI
    HBL --> NRO
    NRO -->|libnx application services| HOS
  end

  WIFI -. no documented loader or shared native ABI .-> NATIVE
  NRO -. no NS2JB service contract demonstrated .-> NATIVE
```

## Evidence notes

- The upstream README distinguishes the SmileBASIC bootstrap, host Node entrypoint, engine, and native helper, and names Zig 0.15.2 as the advertised payload build toolchain.
- Upstream `main.c` and `start.S` are Horizon/AArch64-specific. `process.c` belongs to a privileged process-control boundary. This graph deliberately does not expand its request formats or operations.
- The local NRO README/build record describes a standalone libnx homebrew program. Its NRO header is confirmed locally; console launch is not.
- Dashed edges are **not supported by evidence** and are shown to make the missing integration boundary explicit.

Sources: [NS2JB README](https://gitlab.com/pepsipu/ns2jb/-/blob/95f5525089273c5fce0b95047f3600f8442e96ae/README.md), [payload sources](https://gitlab.com/pepsipu/ns2jb/-/tree/95f5525089273c5fce0b95047f3600f8442e96ae/engine/switch2/ro/payload), [local NRO record](../native-demo/README.md).
