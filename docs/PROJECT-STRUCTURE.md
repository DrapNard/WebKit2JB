# Project structure

## Runtime layers

1. **Browser portal** — HTML and JavaScript run inside the browser and submit bounded diagnostic reports to the local Python service. They do not gain native process access.
2. **HTTP service** — validates request sizes and schemas, persists local reports, and routes bridge requests.
3. **C bridge** — provides a stable API and versioned protocol with Linux, mock, and Horizon-homebrew backends. Unsupported capabilities return explicit errors.
4. **Horizon demo** — a separately built NRO exercises the bridge from a homebrew process. It is not launched by WebKit.

## Evidence categories

- **Browser-observable:** JavaScript API availability, FontFace status, event ordering, and server acknowledgement.
- **Host-native:** WebKitGTK diagnostics collected by the local PC lab.
- **Compiled-only:** ARM64 and Horizon artifacts whose runtime has not been observed on hardware.
- **Unavailable:** operations requiring privileged NS2JB capabilities or access not provided to this bridge.

## Local-only material

Raw reports, Memcheck logs, container storage, firmware archives, generated binaries, and historical trigger variants stay outside this public-source snapshot. Keep their original hashes and provenance in the private workspace.
