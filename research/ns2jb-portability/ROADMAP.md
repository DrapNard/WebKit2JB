# Remaining work and blockers

## Completed safely

- Read the public upstream README, source entry points, manifest, and build-script source at commit `95f55250`.
- Classified the host, SmileBASIC, native helper, Horizon, WebKit portal, and existing NRO boundaries.
- Confirmed the existing NRO artifact's local hash/build record without launching it.
- Preserved the original `ns2-webkit-lab` working tree and its pre-existing uncommitted changes.

## Not performed

- Download or byte-parse the published `main` binary.
- Build the NSO or compare the output with the manifest hash.
- Recreate the payload's IPC layouts or syscall contracts.
- Create Linux mocks of privileged process operations.
- Adapt, wrap, load, or install the NSO/NRO from WebKit or Horizon.
- Test anything on a Switch.

These steps remain blocked in this audit because the payload implements process-memory/executable-page operations. Rebuilding it and extracting precise contracts for a separate Horizon port would materially support operational reuse. The exact on-console module metadata, runtime identity, rights, and compatibility of any alternate Horizon development environment also remain unverified.

## Safe path for future work

1. Obtain a clear license/permission basis before copying or redistributing any upstream component; the project API did not provide license metadata.
2. If the goal is Linux unit testing, limit a future extraction to demonstrably pure, side-effect-free parsing or serialization helpers and mock only neutral data structures.
3. Keep tests independent from the exploit, process handles, memory mappings, permission changes, code patching, module loading, and Switch interaction.
4. Treat the existing NRO as a separate libnx app. A benign shared-data protocol could be specified separately, but no NS2JB protocol adapter is evidenced or implemented.

## Verdict

The source tree has a native helper that is syntactically separate from SmileBASIC but architecturally tied to Horizon. That separation is insufficient to call the helper portable. Exact build reproducibility, artifact format bytes, and integration with the existing NRO are **NOT DEMONSTRATED** here. Direct loading from WifiWebAuthApplet is **INCOMPATIBLE** with the interfaces evidenced in this repository.
