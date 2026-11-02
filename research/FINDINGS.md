# Findings

## Established by local source inspection

1. `NS2_23.0.0.zip` contains `webkit_3.12.11` and `WKC_3.12.11`. The archive was not extracted. Its SHA-256 and embedded version signals are recorded in [SOURCE_INVENTORY.md](SOURCE_INVENTORY.md).
2. In the archived WebKit source, `matchingFacesExcludingPreinstalledFonts` returns `reference_wrapper<CSSFontFace>` values, and `FontFaceSet::load` retains that result while invoking face loading. The upstream 312202 fix changes these to strong `Ref` ownership. See [PATCH_MATRIX.md](PATCH_MATRIX.md), source paths `WebCore/css/CSSFontFaceSet.h:85`, `CSSFontFaceSet.cpp:384-435`, and `FontFaceSet.cpp:150-184`.
3. Archived `iterateClients` retains clients in a snapshot but does not skip a client detached during an earlier callback; 313577 adds a membership check. Source path: `WebCore/css/CSSFontFace.cpp:55-64`.
4. Archived `CSSFontFace::setStatus` notifies clients before updating `m_status`; 322233 moves the state update before notification. Source path: `WebCore/css/CSSFontFace.cpp:498-523`.
5. The replacement audit scanned the lab, the development directory, and the downloads directory; it found 164 ZIP/TAR archives and source members in exactly two groups, both in `NS2_23.0.0.zip`. The 3.12.11 group contains all four audit targets and all three pre-fix indicators; the 0.12.2 group is partial. The original reproducible outputs are private local artifacts and are not included in this repository.
6. A second WKC pass scanned all 656 files and found no FontFace source path or exact source-text match for the audited methods. No compiled browser artifact was found in that package. This answers the local package question as “no alternate WKC implementation found”; it does not rule out firmware-only code or patches.

## Established by local report artifacts

The safe FontFace survey records a getter callback while `document.fonts.load()` is active and reports `matchingFaces: 2`. Other survey reports show CSS rule removal updating set membership and a removed CSS face retaining a readable JavaScript wrapper. These are JavaScript-observable behavior and reentrancy, not proof of native deallocation.

For the crash-associated run, the recorded server acknowledgement is for the `armed` phase. A later `returned` or `finished` record is absent. The exact termination point is therefore unknown.

## Assessment

The archived implementation matches the three targeted pre-fix source motifs, and the official upstream changes address the corresponding risk classes. This is a strong source-level correspondence but only a moderate indicator about the Nintendo runtime: archive version labels do not prove identity with firmware code. There is insufficient evidence to conclude that the reported console error was a use-after-free or memory corruption. There is no evidence of controlled control flow or code execution.

The archive's WKC header defines `WKC_WEBKIT_VERSION` as 613.0, while its frame-loader code gets the User-Agent through an application-client callback. The matching `AppleWebKit/613.0` substring is not independent proof that the archive produced the observed runtime string or that the firmware uses this exact source tree. See [VERSION_PROVENANCE.md](VERSION_PROVENANCE.md).

The missing evidence is listed in [UNRESOLVED_QUESTIONS.md](UNRESOLVED_QUESTIONS.md).
