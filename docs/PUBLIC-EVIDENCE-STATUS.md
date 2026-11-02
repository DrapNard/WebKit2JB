# Public evidence status

## Confirmed in the local research record

- The portal records JavaScript-visible diagnostics and server acknowledgements. Those observations do not expose native memory state.
- The PC laboratory recorded invalid memory accesses in WebKitGTK 2.52.4 under Memcheck and no corresponding invalid accesses in the tested 2.52.6 run and negative control.
- The Switch-side reports establish JavaScript reentrancy observations, not a native use-after-free in the firmware browser.
- The Nintendo browser binary has not been identified by a matching build ID. A successful Horizon build is not a hardware execution result.
- The bridge is a separate native component. An HTTP request from a browser page does not load or invoke a native process on the Switch.

## Scope of this repository

This repository contains source and safe diagnostic interfaces. It does not contain an exploit chain, privileged process-memory operations, a WebKit-to-native launcher, or a claim of remote code execution. Unsupported NS2JB operations remain explicitly unavailable.

Raw logs, firmware/source archives, generated container layers, crash-trigger variants, and executable build products remain in the private research workspace and are not part of this public candidate.
