# Experimental Results: 312202 Ownership Model

## Source correspondence

The archived Nintendo source is in the private `NS2_23.0.0.zip` archive, under `NS2_23.0.0/webkit_3.12.11/WebCore/css/`:

- `CSSFontFaceSet.h:85` returns `Vector<std::reference_wrapper<CSSFontFace>>`.
- `CSSFontFaceSet.cpp:431-435` builds that vector from raw `CSSFontFace*` values.
- `FontFaceSet.cpp:150-189` keeps the matching result across `load()`, status checks, wrapper creation, and possible promise resolution, repeatedly dereferencing non-owning references.
- `CSSFontFace.cpp:55-64` snapshots clients strongly during callback iteration. This protects client objects but is a separate ownership relation from the matching-face vector.

The local upstream patch changes the matching result and mapper from `std::reference_wrapper<CSSFontFace>` to `Ref<CSSFontFace>`, and changes `FontFaceSet::load()` loops from `.get()` access to local `Ref face` values. Those strong references keep each face alive across reentrant work while the matching result is in scope.

## Experiment

`lifetime_model.cpp` models an active face set owning two faces and a matching result containing either raw pointers (pre-fix) or strong `shared_ptr`s (fixed). The first face synchronously invokes a callback that removes the CSS-connected second face from the active set. The loop then calls `load()` on the second match and inspects its status.

Executed with Clang++ 23.1.4, C++20, `-O1 -g -fno-omit-frame-pointer -fsanitize=address,undefined`:

| Variant | Process result | Sanitizer result |
|---|---|---|
| Non-owning matches | Exited 1 under sanitizer | ASan reports `heap-use-after-free`, a 4-byte read in `Face::load()` on the second matching face. The trace identifies release during reentrant removal and the earlier allocation. |
| Strong matches | Exited 0 | Iteration and status inspection complete with no ASan/UBSan diagnostic. The face is released after the matching-result owner leaves scope. |

The complete ASan trace, stdout/stderr, and built binaries remain in private local results. The local `run.sh` reproduces this model.

## Conclusion and limits

**Confirmed in this model:** a non-owning match list can dangle when reentrant work removes the active set's last owning reference. Strong references in that list prevent the same use-after-free for the same schedule. This experimentally confirms the 312202 ownership hypothesis at the abstract relationship level.

The model substitutes `shared_ptr`/raw pointers for WebKit `Ref`/`reference_wrapper`; it does not run WebCore, JavaScriptCore, the HTML regression test, or Nintendo code. It fixes reentrant timing and match order instead of reproducing engine font matching and promise machinery. It therefore does not establish that a Nintendo binary contains the archived code, reaches this lifetime schedule, or is vulnerable. The combined sanitizer run stops the non-owning process at ASan's first error, so it provides no separate UBSan result for that failing path.
