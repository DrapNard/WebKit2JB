# PC WebKitGTK experimental results

This report consolidates the separate x86-64 Podman laboratory. It does not transfer its results to Nintendo WebKit/WKC.

## Environment and provenance

The laboratory used rootless Podman 6.1.4 with `crun`, separate Arch Linux images, and network-disabled browser executions. The WebKit packages came from signed Arch archives; their signatures were checked with the configured Arch keyring. The WebKitGTK sources and package build scripts were inspected to classify the fix by source content, not by release date.

| WebKitGTK package | Source classification for 312202 | Checked source behavior | MiniBrowser smoke |
|---|---|---|---|
| 2.52.3-1 | Pre-fix | Non-owning `reference_wrapper<CSSFontFace>` results and iteration through `face.get()`. | PASS |
| 2.52.4-2 | Fixed | `Ref<CSSFontFace>` results and retained `Ref` values across operations that can re-enter. | PASS |
| 2.52.6-1 | Fixed | Same strong-ownership pattern. | PASS |

Arch package signatures and exact source hashes are recorded in the local PC lab's manifest. The packages, full image storage, and raw runtime logs are intentionally not copied into this repository.

## WebKit 313577 comparison under Memcheck

The official test `LayoutTests/fonts/font-face-load-crash.html` was served unchanged and its SHA-256 was checked: `47e8d5aa4263b5c3be4a923fc3d43e10c21f4c3a0a39a6933a3f67dff60b052b`. HTTP acknowledgements confirmed the test document was present. WebKitWebProcess was instrumented; the glycin child exclusion did not exclude WebKit processes. Container restrictions and WebKit/glycin sandboxes remained enabled.

| Run | Invalid accesses captured in WebKitWebProcess | Process end | Interpretation boundary |
|---|---|---|---|
| WebKitGTK 2.52.4-2, official test | Five invalid reads and one invalid write in the same 200-byte block already reported as freed. | No spontaneous termination was seen; MiniBrowser was stopped deliberately after the HTTP acknowledgement. | Supports an invalid-access observation for this exact Linux run; stripped symbols prevent source-level attribution. |
| WebKitGTK 2.52.6-1, official test | Zero invalid read/write/free reports captured. | Controlled stop after acknowledgement. | This run did not report the same invalid accesses; it is not proof of general memory safety. |
| WebKitGTK 2.52.4-2, negative control | Zero invalid read/write/free reports captured. | Controlled stop after acknowledgement. | The negative control kept normal font loading but omitted the test's reentrant mutation path; association is supported, not a line-by-line cause proof. |

The six invalid accesses were absent in the single negative-control run and the corrected-version run. Generic uninitialized-value/conditional-branch diagnostics appeared separately and were not counted as invalid accesses. The WebKit binaries were stripped; Memcheck did not identify a CSSFontFace source line. These results do not prove a controlled write primitive, arbitrary memory access, or code execution.

An earlier 312202 Memcheck attempt on 2.52.3 recorded 41 errors in 14 contexts, including four invalid reads, and a process crash. That attempt did not confirm the CSS rule removal in the same execution. It remains inconclusive for 312202 and must not be merged with the 313577 comparison above.

## 312202 browser-level observations on PC

The official 312202 HTML was kept unchanged (SHA-256 `a1778b176505b607d7d3b964b488756eadf64d0c9b8de11a82aa7031468768c2`). Without a recognized local Helvetica face, `local(Helvetica)` failed and the CSS rule remained. A legally modified local test font with internal family name `Helvetica` satisfied that prerequisite in the isolated images. With that prerequisite, the wrapper could inspect the same-origin iframe and observed `cssRules.length === 0` in both WebKitGTK 2.52.3 and 2.52.4. Neither browser spontaneously terminated during the bounded observation.

This confirms the CSS-side action was observed in both tested Release binaries. Release binaries under Memcheck are not ASan builds, and process survival does not show that no invalid access occurred. The observation also does not establish a differential result for the memory-safety fix.

## Separate educational native programs

### ASan ownership model

A small standalone C++ ownership exercise produced AddressSanitizer `heap-use-after-free` reports for its deliberately invalid read and write variants; the corrected ownership case and a control case passed. This toy program is independent of WebKit, CSSFontFace, and the Switch.

### Fixed-capacity ELF runner

The independent Linux x86-64 runner reserves 65,536 bytes for an embedded resource. The sample ELF is 9,248 bytes with SHA-256 `543e3c76b417585f8f30bb174d8d7dc276c242aa33b1c7ab028e03bdf97cf54e`. In an isolated rootless container, its ordinary explicit launch printed `UwU from x86-64 lab` and returned exit code 23. This was a normal runner operation. It was not invoked from WebKit, from a UAF, or from memory corruption.

The release snapshot includes only a small fixed ELF validation fixture where needed; it does not include the old launch/experiment bundles or connect the runner to the browser portal.

## Reproducibility records kept locally

The PC lab retains separate run bundles and checksums for the 313577 official and negative-control comparisons. For example, the later bounded rerun bundles are recorded as:

| Bundle | SHA-256 |
|---|---|
| 2.52.4 official | `83c4786a983a1f5949d976692ddbadb7378dd0130b26489f5a992495b2b46bf2` |
| 2.52.6 official | `2f9627f47b477505fe104bfa0bcf39962ccdb36f54c4b310e364b0279a78654f` |
| 2.52.4 negative control | `e0e16160746edf5a901ca4efb86360e86a95e110957e4e9ee5436265eb53cbb5` |

The bundles and original per-process logs remain in the local PC laboratory and are not duplicated here. Hashes identify those specific local artifacts; they do not make the excluded bundles available from this repository.

## Overall PC conclusion

The strongest result is a reproducible, bounded Memcheck observation on WebKitGTK 2.52.4 that was not captured in one corrected-version run or one negative-control run. The exact native function and causal object lifetime remain unresolved. The Switch browser binary is a different, unidentified build. No WebKitGTK result demonstrates the vulnerability on Switch 2 or a UAF-to-native-execution chain.
