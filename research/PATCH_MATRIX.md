# Upstream FontFace Patch Matrix

## Scope and comparison status

This matrix records three upstream changes using official WebKit commits, the local 312202 reference patch, and the inspected archive identified in [SOURCE_INVENTORY.md](SOURCE_INVENTORY.md). The reference patch matches commit `5f0480f771ba1749663a8257eafca70af17b7cec` by its embedded `From` header and diff. The archived WebKit 3.12.11 source contains pre-fix motifs for all three changes.

The companion WKC tree was scanned separately. It has no `CSSFontFace*` or `FontFaceSet*` source path and no exact text occurrences of the four audited WebCore symbols. No alternate implementation was found in WKC. This does not rule out firmware-only builds, patches, or binary changes. Public source labels do not prove the exact revision used by the shipped firmware.

**CVE attribution:** CVE-2026-43715 maps to WebKit bug 313577 in the official WSA-2026-0004 advisory. It does not identify bug 312202 (`5f0480f`, canonical `313821@main`), which is a separate lifetime fix. Keep these identifiers distinct even though both concern CSSFontFace lifetime behavior.

## Matrix

| Upstream issue/change | Behavior changed upstream | Relevant files/functions | Nintendo/WKC status | Evidence and confidence |
|---|---|---|---|---|
| Bug 312202; commit `5f0480f771ba1749663a8257eafca70af17b7cec`; canonical `313821@main` | `CSSFontFaceSet::matchingFacesExcludingPreinstalledFonts` returns `Vector<Ref<CSSFontFace>>` instead of `Vector<std::reference_wrapper<CSSFontFace>>`. `FontFaceSet::load` consumes owning `Ref` values while starting loads and inspecting status, source, and wrappers. The matches stay alive across synchronous script reentrancy that may remove their CSS rule. | Upstream: `Source/WebCore/css/CSSFontFaceSet.cpp`, `.h`, and `Source/WebCore/css/FontFaceSet.cpp`. Archive: `CSSFontFaceSet.h:85` and `.cpp:384-435` retain the `reference_wrapper` pattern. Regression: `LayoutTests/fast/text/fontface-setstatus-crash.html`. | **Pre-fix motif present** in the inspected WebKit 3.12.11 archive. No alternate WKC implementation found; firmware mapping remains unknown. | Official commit and diff plus local archive inspection. The upstream test describes a thenable getter removing an `@font-face` rule during `FontFaceSet.load`; the commit references ASan/assertion safety. Archive evidence does not prove shipped firmware identity. |
| Bug 313577; CVE-2026-43715; commit `5aedb82710ba578f61501106e78f6b25b7f7a558`; canonical `316482@main` | `iterateClients` snapshots clients as `Ref<CSSFontFaceClient>` and checks `clients.contains(client)` before each callback. A client removed from the live weak set by an earlier reentrant callback is skipped even though the snapshot retains it. | Upstream: `Source/WebCore/css/CSSFontFace.cpp` (`iterateClients`). Archive: `CSSFontFace.cpp:55-64` snapshots strong references but lacks the live-membership check. Regression: `LayoutTests/fonts/font-face-load-crash.html`. | **Pre-fix motif present** in the inspected archive (no live membership guard). No alternate WKC implementation found; firmware mapping remains unknown. | Official WebKitGTK advisory WSA-2026-0004 maps CVE-2026-43715 to bug 313577. The commit describes a UAF in `CSSFontFace::setStatus` via `CSSFontFace::load`; its diff adds membership validation around callbacks. The test removes a style element from a `FontFace.prototype.then` getter during `face.load()`. This does not prove the firmware uses the same code. |
| Bug 322233; commit `64a55fd574c40d8fda92b4f114d2a2afb9f0ec71`; canonical `319575@main` | `CSSFontFace::setStatus` updates `m_status` before client callbacks using `std::exchange`, passes captured old/new status values, and removes the post-callback assignment. Reentrant `pump()` sees committed state and avoids a duplicate transition. | Upstream: `Source/WebCore/css/CSSFontFace.cpp` (`CSSFontFace::setStatus`). Archive: `CSSFontFace.cpp:498-523` calls clients before assigning `m_status = newStatus`. Regression: `LayoutTests/fast/text/font-face/css-font-face-setstatus-reentrancy-crash.html`. | **Pre-fix motif present** in the inspected archive. No alternate WKC implementation found; firmware mapping remains unknown. | Official commit message describes the two-client sequence and assertion; the diff makes state-write order explicit. The test uses synchronous `local()` loading and `OffscreenCanvas.measureText()` to reenter. Archive evidence does not prove shipped firmware identity. |

## Interpretation

These changes address related but distinct correctness hazards:

1. **Object lifetime:** 312202 makes the matching-face collection retain `CSSFontFace` objects while author script can mutate stylesheets.
2. **Client-set mutation:** 313577 avoids notifying a snapshotted client that has since been removed from the live client set.
3. **State-transition reentrancy:** 322233 commits status before callbacks so clients observe consistent old/new state and nested pumping sees the completed transition.

They should not be collapsed into one “reentrancy fix.” One change does not establish that the others are present. A port may implement equivalent safeguards differently; compare behavior and ownership semantics, not only matching text.

The upstream regression tests describe public WebKit source and its stated failure conditions. The inspected 3.12.11 source matches the pre-fix implementation patterns, but this alone does not prove that the Nintendo browser contains that exact source or that its reported error has the same cause. A crash does not demonstrate memory corruption or code execution.

## References

- [WebKit commit 5f0480f / bug 312202](https://github.com/WebKit/WebKit/commit/5f0480f771ba1749663a8257eafca70af17b7cec)
- [WebKit commit 5aedb82 / bug 313577](https://github.com/WebKit/WebKit/commit/5aedb82710ba578f61501106e78f6b25b7f7a558)
- [WebKitGTK advisory WSA-2026-0004 / CVE-2026-43715](https://webkitgtk.org/security/WSA-2026-0004.html)
- [WebKit commit 64a55fd / bug 322233](https://github.com/WebKit/WebKit/commit/64a55fd574c40d8fda92b4f114d2a2afb9f0ec71)
- Local 312202 patch artifact (not included): upstream commit `5f0480f` only.
