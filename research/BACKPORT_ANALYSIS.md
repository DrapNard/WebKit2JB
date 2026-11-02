# Structural Backport Analysis

## Method and scope

The WebKit functions in `NS2_23.0.0.zip` were compared with the official upstream diffs for bugs 312202, 313577, and 322233. All three upstream commits predate the package's September 8, 2026 archive timestamps. Source line references below point to members listed in [VERSION_PROVENANCE.md](VERSION_PROVENANCE.md).

| Upstream change | Upstream diff | WebKit 3.12.11 source | Equivalent backport indicator | Archive-level conclusion |
|---|---|---|---|
| 312202 — commit `5f0480f771ba1749663a8257eafca70af17b7cec`, May 24, 2026 | Selection returns `Ref<CSSFontFace>` rather than `std::reference_wrapper<CSSFontFace>`. `FontFaceSet::load` retains strong references while starting loads, checking status, and accessing wrappers. [Upstream diff](https://github.com/WebKit/WebKit/commit/5f0480f771ba1749663a8257eafca70af17b7cec) | `CSSFontFaceSet.h:85` declares a vector of `reference_wrapper`; `CSSFontFaceSet.cpp:384-435` builds that vector from pointers; `FontFaceSet.cpp:150-184` iterates over `face.get()` without creating a local strong reference. | `m_faces` and the `CSSFontFaceSet` tables hold `Ref`s, but do not keep a face alive after reentrant removal from those structures. No equivalent strong references appear in the result list and `load` loops. | **Pre-fix motif present.** No equivalent backport is visible in these functions. |
| 313577 — CVE-2026-43715; commit `5aedb82710ba578f61501106e78f6b25b7f7a558`, July 3, 2026 | After copying clients into strong references, iteration still checks `clients.contains(client)` before the callback. This skips a client detached by an earlier callback. [Upstream diff](https://github.com/WebKit/WebKit/commit/5aedb82710ba578f61501106e78f6b25b7f7a558.patch) | `CSSFontFace.cpp:55-64` copies `HashSet<Client*>` pointers into `Vector<Ref<Client>>`, then invokes each callback without rechecking membership in the set. | **Partial protection exists:** the snapshot retains each client's lifetime. **Mutation protection is absent:** a callback is still invoked after that client was removed from the live set. The snapshot alone is not equivalent to the upstream membership check. | **Pre-fix motif present**, although part of the client-lifetime mechanism already exists. |
| 322233 — commit `64a55fd574c40d8fda92b4f114d2a2afb9f0ec71`, August 20, 2026 | `std::exchange(m_status, newStatus)` saves the old status and publishes the new status before callbacks; clients receive a stable old/new pair. [Upstream diff](https://github.com/WebKit/WebKit/commit/64a55fd574c40d8fda92b4f114d2a2afb9f0ec71) | `CSSFontFace.cpp:498-523` calls `fontStateChanged(*this, m_status, newStatus)` during iteration and assigns `m_status = newStatus` only after callbacks. | `setStatus` has no pre-callback state update or `std::exchange` equivalent; reentrant callbacks can still observe the old `m_status`. | **Pre-fix motif present.** |

The partial local Git repository lists the 312202 commit as `FETCH_HEAD`, but the required source blobs are unavailable offline. Bugs 313577 and 322233 were compared using their official diffs. This table describes the archived 3.12.11 source; it does not establish the contents of the firmware 23.0.1 binary.

## Search for other backports

- The four inspected WebCore sources contain none of the markers `PLATFORM(WKC)`, `WTF_PLATFORM_WKC`, `WKC_`, `ACCESS`, or `Nintendo`. This does not prove that ACCESS left those files unchanged: the package copyright notice says some files were modified but does not enumerate them.
- `WKC_WEBKIT_VERSION` is defined as 613.0 and has no other occurrence in the archive. `FrameLoaderClientWKC::userAgent` delegates the value to a host-application callback (`WKC/WebCoreSupport/FrameLoaderClientWKC.cpp:1131-1137`; interface `WKC/helpers/FrameLoaderClientIf.h:852`). The observed User-Agent may therefore come from `WifiWebAuthApplet`, whose source is not included. A matching `613.0` suffix is not proof of provenance.
- The WKC source tree contains no `CSSFontFace*` or `FontFaceSet*` source file and no occurrences of the four audited symbols. It provides no second implementation that would prove a backport outside WebCore.
- The protections found in owning containers or in the strong client snapshot do not implement the specific upstream changes: the result list remains non-owning, removed clients are still called, and status remains stale during callbacks.
- The upstream changes predate the package archive timestamps (312202: May 24; 313577: July 3; 322233: August 20; archive: September 8, 2026). The later archive timestamp plus the retained motifs suggests this shipped source branch did not incorporate those changes. The archive timestamp does not prove when the code was built.

## Feasibility of a local instrumented reproduction

### Available tools

- `clang++` 23.1.4, `g++`, CMake 4.4.4, Ninja 1.13.2, and GTK/GLib dependencies are installed.
- A minimal C++ program compiles with ASan+UBSan under Clang and GCC and runs with `ASAN_OPTIONS=detect_leaks=0`. LeakSanitizer initialization fails in the current environment; this does not block the ASan/UBSan smoke check, but no instrumented WebKit build was made.
- WebKitGTK 2.54.2 is installed. Its libraries are not linked with ASan/UBSan and are not the WKC code under review, so they are not an instrumented reproduction.

### Concrete blockers

- The archive contains component source, but not the WebKit build root, `Tools/Scripts/build-webkit`, `Source/cmake/OptionsGTK.cmake`, or top-level `CMakeLists.txt` files. The available CMake files belong to subcomponents.
- The local repository pointing at commit 312202 is a partial `blob:none` clone; the required WebCore blobs are not cached. No configured `WebKitBuild` tree was found.
- The archive includes neither a runnable browser binary nor an ASan/UBSan configuration for the WKC port.

**Verdict:** the native compiler toolchain and basic sanitizers work, but these WebCore paths cannot be reproduced with the currently available sources and metadata. A complete WebKit checkout and build tools would be required; any resulting build would still represent a local port, not proof about Nintendo's binary.

## Evidence levels

**Confirmed:** all three pre-fix motifs appear in the archived 3.12.11 code. The 313577 change retains a strong client snapshot but does not revalidate membership. The local upstream clone has the 312202 commit metadata but not its source blobs.

**Probable:** the 3.12.11 source belongs to the release family suggested by matching package/client labels. The inspected archive likely does not include the three targeted backports. This conclusion is limited to the archive source, not the firmware binary.

**Unknown:** whether firmware 23.0.1 uses this exact source, whether a build-time or out-of-tree patch was applied, and whether console error 2168-0002 resulted from any of these defects. No firmware dump or matching symbol set is available.
