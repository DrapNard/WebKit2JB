# Ownership and Lifetime Analysis

## Objects and references

| Object / relationship | Evidence in archived source | Consequence |
|---|---|---|
| `CSSFontFaceSet` owns its active CSS faces | `CSSFontFaceSet.h:123–129`: `m_faces`, `m_facesLookupTable`, and the local-face table contain `Ref<CSSFontFace>`; a constituent lookup map contains raw pointers. | Removing a face can remove an owning reference; these containers establish ownership while an entry is present. |
| Matching result is non-owning | `CSSFontFaceSet.h:85`; the implementation builds `Vector<std::reference_wrapper<CSSFontFace>>` in `CSSFontFaceSet.cpp:431–435`. | The result vector itself does not extend the lifetime of a `CSSFontFace`. |
| `FontFace` wrapper owns its backing object | `FontFace.h:104` declares `Ref<CSSFontFace> m_backing`; `FontFace.cpp` constructs wrappers from the backing object. | A live wrapper can keep the native backing object alive. This does not protect a CSS face before a wrapper is created or when no wrapper exists. |
| `CSSFontFace` wrapper slot is weak | `CSSFontFace.h:188` declares `WeakPtr<FontFace> m_wrapper`; `wrapper()` creates a wrapper if absent (`CSSFontFace.cpp:445–456`). | The native-to-wrapper link does not itself own the wrapper. |
| `CSSFontFace` client registry stores raw client pointers | `CSSFontFace.h:187`; `addClient`/`removeClient` are in `CSSFontFace.cpp:410–419`. `iterateClients` snapshots strong `Ref<Client>` objects in `CSSFontFace.cpp:55–64`. | The callback loop protects the snapshot clients' lifetimes, but the archived code does not recheck whether a client is still registered before invoking its callback. Upstream bug 313577 adds that membership check. |
| `CSSFontFace` has explicit self-protection in selected methods | For example, `CSSFontFace.cpp:370`, `559`, and `653` create `Ref<CSSFontFace> protectedThis(*this)`. | Protection is method-specific and must not be generalized to every call path. |

## Suspected invalidation path and limits

The archive shows a concrete non-owning result: `FontFaceSet::load` retains references returned by `matchingFacesExcludingPreinstalledFonts`, then calls each face's `load()` and later reads status and requests a wrapper (`FontFaceSet.cpp:158–184`). A synchronous callback during `load()` can change CSS rules and remove a CSS-connected face from the set. Upstream bug 312202 changes the returned vector to strong `Ref<CSSFontFace>` references specifically to retain those faces across re-entry. The return type and iteration pattern in the archive match the pre-fix motif.

This establishes a plausible invalidation risk in the archived implementation and a direct correspondence to the upstream fix. It does not prove that the Nintendo runtime used these exact source contents, that a face was destroyed during the observed Switch run, or that the console error was caused by a use-after-free. The on-device wrapper-lifetime observations are compatible with a live backing reference and do not prove native destruction.
