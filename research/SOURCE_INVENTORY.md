# Source Inventory

Inspection date: 2026-10-31. Sources were inspected read-only; nothing was extracted.

## Nintendo / ACCESS source archive

- **Local path:** withheld from this copy; the archive remains in the private workspace.
- **SHA-256:** `a2bcdfb7ec695d1ac5c790317a1239ccdb40e0ba8e052891c2ebba1314200f90`
- **Size:** 197,123,071 bytes; `unzip -l` reports 40,478 entries and 728,410,973 uncompressed bytes.
- **Embedded roots:** `NS2_23.0.0/webkit_3.12.11/` (19,063 entries, 357,697,990 uncompressed bytes) and `NS2_23.0.0/WKC_3.12.11/` (715 entries, 3,898,165 uncompressed bytes). The archive also contains an older `webkit_0.12.2/` tree with WebKit 601.7.4.
- **Version signals:** archive/folder labels `NS2_23.0.0` and `webkit_3.12.11`; `WebCore/Configurations/Version.xcconfig` in the 3.12.11 tree reports WebKit 613.3.9. These labels do not prove exact firmware code identity.
- **Metadata:** `NS2_23.0.0/NetFrontBrowserNX_OSSCopyright.txt` identifies NetFront Browser NX copyright for ACCESS Co., Ltd. (2023–2026) and says some files were modified by ACCESS.
- **Member timestamps:** September 8, 2026, 11:58:34 through 13:09:34 (ZIP timestamps; timezone unspecified). These are archive metadata, not reliable per-file source-change dates.
- **Relevant source members:**
  - `NS2_23.0.0/webkit_3.12.11/WebCore/css/CSSFontFaceSet.h`
  - `NS2_23.0.0/webkit_3.12.11/WebCore/css/CSSFontFaceSet.cpp`
  - `NS2_23.0.0/webkit_3.12.11/WebCore/css/FontFaceSet.cpp`
  - `NS2_23.0.0/webkit_3.12.11/WebCore/css/CSSFontFace.h`
  - `NS2_23.0.0/webkit_3.12.11/WebCore/css/CSSFontFace.cpp`
- **WKC version metadata:** `WKCVersion.h:26-35` declares WKC 7.0.0, customer release 3.12.11, and `WKC_WEBKIT_VERSION` 613.0. `WKCVersion.cpp:25-27` returns the customer release. The WebKit macro is only defined, not used, in this archive. `FrameLoaderClientWKC.cpp:1131-1137` obtains User-Agent from the host application's `userAgent(uri)` callback; the interface is `FrameLoaderClientIf.h:852`. Thus the observed `AppleWebKit/613.0` string does not prove this macro supplied it. The Nintendo applet source is absent.
- **WKC cross-check:** the 715-entry WKC tree contains no `CSSFontFace*` or `FontFaceSet*` members, and static scans found none of the four audited WebCore method symbols. WKC-specific source does not expose an alternate implementation of these functions.
- **Build outputs:** no `.nso`, `.nro`, `.nsp`, `.elf`, `.so`, `.dll`, `.dylib`, `.a`, `.o`, or `.bin` members were found. The archive supplies source, not the built browser binary or a build-ID mapping.
- **Modifications:** archive metadata attributes the contents to the package. Local modifications cannot be assessed without a trusted original-release checksum/manifest. No archive member was modified.

## Other candidate locations

- A local WebKit 312202 clone had no working tree, but its partial Git repository listed `FETCH_HEAD=5f0480f771ba1749663a8257eafca70af17b7cec` (upstream 312202 fix, 2026-05-24; parent `e8db86ea1203dcc4109eece64cfe0434d21cf13a`). It is shallow with `blob:none`; the four audited WebCore blobs are absent. This is fixed-baseline commit metadata, not a usable source checkout.
- No extracted `CSSFontFaceSet.cpp`, `FontFaceSet.cpp`, or `CSSFontFace.cpp` was found in the project or the development/download trees during the tree-only search. The prior search did not inspect archive members, which explains its empty result.
- The replacement scanner supports ZIP and TAR-family formats. It scanned 164 archives in the configured roots and found FontFace source members only in `NS2_23.0.0.zip`; 163 others had no matches. 7z/RAR archives are not parsed.
- The lab's `webkit-audit/bug-312202/312202.patch` is a patch reference, not a WebKit source tree.

## Inventory limits

The archive establishes that version-labeled source files were available locally. It does not establish byte-for-byte identity with Nintendo Switch 2 firmware 23.0.1, the exact `WifiWebAuthApplet` binary, or binary-only backports.
