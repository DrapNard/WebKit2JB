# Local Instrumented Validation — WebKit 312202

## Latest artifact reinspection — 2026-11-01

This section supersedes the October 31 notes below about absent worktrees and builds; the local lab state later changed.

- Two complete worktrees were present: `before` at parent `e8db86ea1203dcc4109eece64cfe0434d21cf13a` (with the official test and expected output added locally) and `after` at fixed commit `5f0480f771ba1749663a8257eafca70af17b7cec`. The `before` worktree had three untracked items: the test, expected output, and an `artifacts/` directory.
- Only `before` had a `WebKitBuild/GTK/Release` tree (about 1.2 GiB), configured with `ENABLE_SANITIZERS=address`, Release mode, GCC, and roughly 3,410 compile entries containing `-fsanitize=address`. `libjavascriptcoregtk-6.0.so.1.8.1` was an x86-64 ELF linked to `libasan.so.8`. The partial build held 474 JavaScriptCore objects (318 MiB) and 295 WebCore objects (337 MiB), but no object for the unified source file containing `CSSFontFaceSet.cpp`/`FontFaceSet.cpp` was found.
- No `libWebCore`, `libwebkitgtk`, `MiniBrowser`, `WebKitTestRunner`, or `jsc` executable was produced in that tree. `after` had no `WebKitBuild`. System WebKitGTK 2.54.2 is a different, uninstrumented version; no system MiniBrowser or WebKitTestRunner was available.
- `before-target-build.log` and `before-werror-off-build.log` record actual compile failures: incomplete-type errors in JavaScriptCore, then a `-Werror=uninitialized` diagnostic in WebCore. The attempt with Werror disabled was later interrupted when `cc1plus` was killed compiling large unified CSS files. No LayoutTest log, 312202 `*-actual.txt`, or engine ASan report exists. **No vulnerable/fixed ASan result was obtained.**
- The existing build is not reusable from the current path: `CMAKE_HOME_DIRECTORY` and Ninja commands refer to `/workspace`, which no longer exists. A `WebKitTestRunner` dry run fails during CMake regeneration (`mkdir(/workspace): Read-only file system`) and then cannot find expected sources. `gperf` is absent, another blocker to a clean configuration.

**Decision:** no runnable native validation is available without a new configuration/build. A few ASan WebCore objects are insufficient; the official target requires linked WebCore and `WebKitTestRunner`, neither of which exists. Relocating the partial build is not a trivial targeted build; previous attempts already traversed thousands of tasks and failed from compile errors and memory pressure. No further build was started. A theoretical sanitizer comparison would run the same LayoutTest under ASan on the parent and fixed revision, but no sanitizer conclusion follows from the available objects/libraries.

For firmware linkage, the local evidence is limited to [VERSION_PROVENANCE.md](VERSION_PROVENANCE.md): archive `NS2_23.0.0.zip`, WebKit/WKC 3.12.11 source, WebCore/JSC 613.3.9, WKC macro 613.0, and reported Switch User-Agent `AppleWebKit/613.0`. The archive has no browser binary, source revision, or firmware 23.0.1 build ID; WKC delegates User-Agent generation to the Nintendo client. This match is plausible, not engine identification.

## Earlier clone recheck — 2026-10-31

Read-only inspection found that the partial WebKit clone had no usable working tree. `master` had no commit or extracted files although `.git/FETCH_HEAD` listed `5f0480f771ba1749663a8257eafca70af17b7cec` and its parent. `git diff-tree` lists the 312202 changes to `CSSFontFaceSet.cpp`, `CSSFontFaceSet.h`, and `FontFaceSet.cpp`, plus official test `LayoutTests/fast/text/fontface-setstatus-crash.html` and its expected output. That does not make the blob contents available: `GIT_NO_LAZY_FETCH=1 git cat-file -e FETCH_HEAD:CMakeLists.txt` failed, and `rev-list --objects --missing=print` reported **394,142 missing objects**. The remote was configured, but no fetch was attempted.

At that check the host had 12 logical CPUs, 46 GiB RAM (about 12 GiB available), 63 GiB swap (34 GiB free), 106 GiB free on `/home`, and 20 GiB on `/tmp`; `/home` was 88% used. These measurements did not establish that two complete Debug+ASan builds would fit. No large build or configuration estimate was started. Installed WebKitGTK 2.54.2 was not the target commit and provided no instrumented comparison.

Basic tools included CMake 4.4.4, Ninja 1.13.2, Clang 23.1.4 and its ASan runtime, Perl, Python, Bison, Flex, bubblewrap, Xvfb, and D-Bus. `gperf`, Ruby, and `libsoup-2.4` were absent; `libsoup-3.0` was present. Without the target CMake files, only gperf was identified from consulted upstream WebCore configuration as required; Ruby and libsoup 2.4 remained unconfirmed requirements, not established blockers for this commit.

### Isolation and reproducibility boundary

- A bubblewrap smoke command with read-only source, user/PID/UTS/IPC namespaces, and writable temporary output completed with exit code 0. `--unshare-all` failed because this environment denied network-namespace creation (`Failed to create NETLINK_ROUTE socket: Operation not permitted`). File-level isolation was possible, but network confinement was not guaranteed.
- Podman could not start: the default runtime was read-only; a temporary `XDG_RUNTIME_DIR` still failed to start OCI runtime `crun`. No container was created.
- The planned experiment required separate clean parent/fixed source trees and `WebKitBuild` directories, Clang/Debug/ASan, one official test, one or two jobs, sequential builds, and retained logs. It was not executed.

The local clone remains unsuitable for configuration, compilation, or test execution because the required blobs are absent. Restoring complete source for both revisions is the prerequisite; no Switch interaction is required to resume the local PC analysis.
