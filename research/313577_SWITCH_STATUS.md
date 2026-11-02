# WebKit 313577 — Consolidated Status for WifiWebAuthApplet 23.0.1

## Decision

**INDETERMINATE for the Nintendo browser on firmware 23.0.1.** Existing data establish JavaScript reentrancy on Switch and a pre-fix source motif in the inspected WebKit/WKC archive. They do not identify the binary loaded by firmware 23.0.1 and do not demonstrate invalid native memory access on the console.

This note summarizes existing reports and does not replace them. Switch JSON, Memcheck logs, upstream tests, hashes, and other raw artifacts remain in their original private locations.

## Existing results

- **PC, WebKitGTK:** under Memcheck, the official 313577 scenario produced five invalid reads and one invalid write in pre-fix 2.52.4. The tested corrected 2.52.6 run reported no invalid access; the 2.52.4 negative control reported none either. This strongly associates those errors with the reentrancy/mutation path in those GTK binaries. Native source attribution remains incomplete, and these results do not transfer to the Nintendo port.
- **Switch, JavaScript:** existing `safe-v2` reports record `getter-A` during `document.fonts.load()`, with `insideLoad: true`, loading state, and normal resolution. This confirms observable reentrancy in that specific path, not removal of a C++ client or a native use-after-free.
- **Archived source:** `NS2_23.0.0.zip` contains the 313577 pre-fix motif in WebKit 3.12.11. This proves source content under that archive label; it does not establish provenance for the engine executed by WifiWebAuthApplet on firmware 23.0.1.
- **Optional `fontface-313577-safe.html` page:** not required for the current validation and should not trigger another Switch campaign. Its implementation and schema remain in the original local lab only.

Detailed source references are in [PATCH_MATRIX.md](PATCH_MATRIX.md) and [VERSION_PROVENANCE.md](VERSION_PROVENANCE.md). Raw PC and Switch artifacts remain in the private research workspaces.

## Missing information and current accessibility

| Needed information | Why it blocks a conclusion | Accessible now? | Status |
|---|---|---|---|
| Exact WebKit/WKC identity loaded by WifiWebAuthApplet on 23.0.1 and a verifiable map to 3.12.11 sources (revision, build ID, any backports) | Without the mapping, the archive's source motif cannot be attributed to the 23.0.1 binary. `AppleWebKit/613.0` is not a build ID. | No. The examined artifacts contain no browser binary or matching build manifest. | **Blocked** — a reliable build record or legally supplied binary with matching provenance is missing. |
| Native observation of the `CSSFontFace` client set and any invalid access in the identified Nintendo binary | JavaScript APIs expose neither C++ references nor live-set membership nor allocation/free state. GTK Memcheck results concern a different port, binary, allocator, and environment. | No. The portal can collect Web API observations and JavaScript reports only. No symbolized native log, dump, or Nintendo-process instrumentation is available. | **Blocked** — native evidence from the identified Nintendo binary is absent. |

Switch reports also have provenance limits: User-Agent and JavaScript events are page-reported; server receipt proves only that the JSON was stored.

## Actual WebKit access capability

The lab can serve a page to the captive browser, observe Web APIs exposed to JavaScript, and store local reports with provenance for served resources. It cannot identify the firmware WebKit/WKC binary from those observations, inspect internal WebCore structures, or prove a native use-after-free. The archived source is compatible with the 313577 pre-fix pattern, but its presence and memory effect in the firmware 23.0.1 browser remain **indeterminate**.
