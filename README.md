# WebKit2JB

A local captive-portal research lab with safe browser diagnostics and a non-privileged native bridge for Linux and Horizon homebrew. The project separates browser observations, host-side tooling, and Horizon build artifacts.

## Project map

- `api-probe.py`, `index.html`, `portal.js`, `diagnostics.js` — local portal and report endpoints.
- `shared/` and `schemas/` — platform-neutral browser reporting and JSON contracts.
- `bridge/` — C API, versioned protocol, Linux/mock/Horizon backends, read-only memory-policy reporting, and build/verification scripts.
- `research/ns2jb-portability/` — source-level portability notes; no NS2JB payload source is copied.
- `history/legacy-backup-inventory.json` — hashes for historical backup files retained in the private workspace.

## Evidence boundary

Linux WebKitGTK Memcheck results are not evidence of a Nintendo firmware binary. A successful Horizon build is not evidence that the NRO ran on a Switch. This project does not claim a WebKit-to-native execution chain; the bridge is not reachable from a web page as a native process interface.

## Build and test

See [`bridge/README.md`](bridge/README.md), [`bridge/HORIZON-BUILD.md`](bridge/HORIZON-BUILD.md), and [`research/ns2jb-portability/PORTABILITY_AUDIT.md`](research/ns2jb-portability/PORTABILITY_AUDIT.md). The portal uses Python's standard library. Run the documented unit suites locally before deployment.

## Public-release scope

This source snapshot intentionally excludes private run reports, firmware archives, WebKit source archives, generated container layers, large build outputs, firmware/source archives, legacy crash-trigger experiments, and historical private reports. A tiny fixed x86-64 example ELF remains only as a read-only metadata-validation fixture; the portal does not extract or execute it. Original research artifacts remain unchanged in the local workspace. The inventory records backup hashes without disclosing their contents.

## Licensing

No blanket license is asserted here. Each imported component retains its original authorship and licensing terms. The NS2JB audit is analysis only and does not copy NS2JB code. Check third-party notices before reusing any component.
