# AddressSanitizer Findings — Local WebKit 312202 Validation

## Environment recheck — 2026-10-31

WebKit was **not executed**. A Git check with lazy fetching disabled found 394,142 missing objects. The commit and trees list the official test and target CSS files, but their contents are not available in the local clone and there is no checked-out branch. The test runner, engine, and HTML/expected files therefore cannot be run from the local disk.

Clang 23.1.4 and its `libclang_rt.asan-x86_64.so` runtime are present. This is not a WebKit build or run. No new WebKit compilation, regression test, or engine ASan trace was produced during this recheck. The earlier minimal C++ diagnostic only checked that the runtime starts.

The host had 12 logical CPUs, about 12 GiB of available RAM, 34 GiB free swap, 106 GiB free on the home filesystem, and 20 GiB free under `/tmp`. `gperf`, Ruby, and `libsoup-2.4` were absent. Their exact requirement for the target commit cannot be confirmed without the missing CMake blobs. The other inspected GTK dependencies were present. Available disk and memory did not justify starting two Debug+ASan builds before the source checkout and expected build size were restored.

The Git trees confirm that 312202 changes `CSSFontFaceSet.cpp`, `CSSFontFaceSet.h`, and `FontFaceSet.cpp`, and adds the official test `fast/text/fontface-setstatus-crash.html` with expected output. These are tree entries, not execution results. Before/after behavior and engine ASan output remain unavailable.

## Summary

**No instrumented WebKit result was obtained.** The build and regression test are not runnable in the current environment: the clone is partial, has no working tree, and is missing 394,142 accessible objects. WebCore source blobs, GTK build configuration, build/test scripts, and the official 312202 test are unavailable. There is no engine ASan trace and no before/after result. This means “not run,” not “passed.”

## Diagnostics actually run

| Diagnostic | Result | Scope |
|---|---|---|
| Clang 23.1.4: compile and run a minimal C++ program with `-fsanitize=address -fno-omit-frame-pointer` | Exit code 0; no ASan output | Confirms the basic Clang ASan runtime on this host only. |
| GCC 16.2.1: same minimal diagnostic | Exit code 0; no ASan output | Independent runtime check; not used for the proposed WebKit comparison. |
| Runtime and tools | Clang 23.1.4 and `libclang_rt.asan-x86_64.so` present; CMake 4.4.4, Ninja 1.13.2; `gperf` absent | Consultable upstream WebKit CMake requires gperf >= 3.0.1 when WebCore is enabled. The target commit's build files are missing; confirm the exact list after source restoration. |
| Test runner search | `Tools/Scripts/run-webkit-tests` is absent, along with the rest of the working tree | No WebKit test can be launched. |
| Official 312202 test | Not run | `LayoutTests/fast/text/fontface-setstatus-crash.html`, expected output, engine, and tools are not available as usable blobs. |

The earlier minimal diagnostic used `ASAN_OPTIONS=detect_leaks=0`; it does not test LeakSanitizer, WebCore, WebKit's allocator, or the regression scenario. No false “ASan clean” claim is made.

## Before/after results

| Revision | Official test | Result | ASan trace |
|---|---|---|---|
| Before: parent `e8db86ea1203dcc4109eece64cfe0434d21cf13a` | Not run | Unavailable | None collected |
| After: commit `5f0480f771ba1749663a8257eafca70af17b7cec` | Not run | Unavailable | None collected |

Metadata and the reference patch confirm the upstream 312202 change: matching-face results and `FontFaceSet::load()` locals use `Ref<CSSFontFace>` instead of `std::reference_wrapper`. The official test still needs to establish behavior; no runtime difference was measured.

## Why the test was not launched

1. The local WebKit clone has no `HEAD` or working files. With `GIT_NO_LAZY_FETCH=1`, blobs for `CMakeLists.txt`, CSSFontFace/FontFaceSet sources, `Tools/Scripts/build-webkit`, `OptionsGTK.cmake`, `run-webkit-tests`, and the official test are missing. Commit and tree metadata alone are insufficient.
2. A previously recorded remote `git ls-remote` attempt failed because `github.com` could not be resolved. No fetch was attempted.
3. `gperf` is missing. Ruby is missing too, but whether it is required for this target build was not established. GTK3 and inspected pkg-config dependencies are present; `libsoup-2.4` is absent while `libsoup-3.0` is present. See [LOCAL_REPRODUCTION.md](LOCAL_REPRODUCTION.md) for the recorded environment.
4. At the last resource check there were 105.5 GiB free on the home filesystem, 12.2 GiB available RAM, 12 logical CPUs, and 19.1 GiB free under `/tmp`. No large build was started; disk needs for two Debug+ASan builds were not measured for this revision.
5. Installed WebKitGTK 2.54.2 is neither the target commit nor an ASan-instrumented build; it cannot substitute for the required binaries.
6. A local bubblewrap test with a read-only filesystem and user/PID/UTS/IPC namespaces passed. Network namespace isolation (`--unshare-all`) was denied by the environment. Podman could not start because no usable OCI runtime was available; no container was created.

## Requirements for obtaining traces

First restore complete source blobs for both commits, or provide complete checkouts. Install gperf through the normal package manager and verify exact dependencies during configuration. Recheck resources, use two separate GTK Debug+ASan build directories sequentially with one or two jobs, then run only the official `fast/text/fontface-setstatus-crash.html` test. Capture test logs, `*-actual.txt`, exit status, and ASan reports to replace the “not run” results above.

No Switch action, local Nintendo browser test, or RCE payload was produced.
