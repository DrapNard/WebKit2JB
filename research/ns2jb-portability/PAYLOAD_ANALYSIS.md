# Native payload format analysis

## Evidence available

The upstream `manifest.json` describes a `main` image with `payloadBytes: 4757`, advertised SHA-256 `d590cbfc5d9152c24d5a36f083f8470a2f3164be6b78130129d44132b939701a`, a platform field, a program identifier, and a policy hash. These are upstream metadata values; this audit did not download `main` and therefore did not recompute the hash or inspect its bytes.

The source `start.S` declares an ARM64 startup symbol and a `MOD0`-style module header. The upstream build script source describes an intermediate AArch64 ELF and packages the selected sections into an NSO image. This is source evidence about the build design, not byte-level confirmation of the published `main` artifact.

Consequently, the following claims remain **not independently verified in this laboratory**: the published file's actual magic bytes, ELF/NSO header fields, compressed segment details, symbol table, dynamic dependencies, exact entry metadata, and hash-to-file correspondence. No section dump, disassembly, symbol extraction, or binary execution was performed.

## Format distinctions

| Format | What it denotes | Relation to this review |
|---|---|---|
| ELF | General executable/object format; can describe an AArch64 intermediate image. | Upstream builder source says it creates an AArch64 ELF intermediate. This does not make that intermediate an NRO or NSO. |
| NSO | Nintendo system-module executable container. | Upstream builder source packages the native helper as an NSO. The published file's bytes were not locally verified. |
| NRO | Homebrew executable container used by a homebrew launch environment. | The existing local demo is a separate NRO; its metadata records `NRO0` and AArch64. It is not the NS2JB helper. |
| NPDM | Process metadata/policy accompanying a system module or package. | The manifest carries a policy hash, but this audit did not parse a payload package or verify NPDM bytes. A hash is not itself an NPDM file. |

These formats are not interchangeable. A JavaScript page cannot directly execute any of them. Any actual loading requires an appropriate OS loader and process context, neither of which is provided by the portal.

## Entry and runtime boundary

The sources indicate an AArch64 Horizon module entry rather than a Linux `main()` ABI. The startup assembly sets up the module entry and exposes low-level Horizon wrappers; the C entry then runs as a service process. Calling conventions, relocation behavior, and the published artifact's exact loaded memory layout were not independently inspected here.

## Verdict

- **AArch64 source target:** CONFIRMÉ from source/build metadata.
- **Published `main` is an NSO:** PROBABLE from the upstream packaging source; not byte-verified locally.
- **Published size and SHA match its manifest:** NON DÉMONTRÉ in this lab.
- **ELF, NSO, NRO, and NPDM interchangeability:** INCOMPATIBLE as formats/loader contracts.

Sources: [manifest](https://gitlab.com/pepsipu/ns2jb/-/blob/95f5525089273c5fce0b95047f3600f8442e96ae/engine/switch2/ro/payload/manifest.json), [startup source](https://gitlab.com/pepsipu/ns2jb/-/blob/95f5525089273c5fce0b95047f3600f8442e96ae/engine/switch2/ro/payload/start.S), [builder source](https://gitlab.com/pepsipu/ns2jb/-/blob/95f5525089273c5fce0b95047f3600f8442e96ae/engine/build-payload.cjs), [local NRO build record](../native-demo/build-info.json).
