# WebKit/WKC Version Provenance

## Package examined

- Archive: the local `NS2_23.0.0.zip` source archive (its filesystem path is withheld).
- SHA-256: `a2bcdfb7ec695d1ac5c790317a1239ccdb40e0ba8e052891c2ebba1314200f90`
- Size: 197,123,071 bytes; 40,478 ZIP entries.
- Roots: `NS2_23.0.0/webkit_3.12.11/` (19,063 entries) and `NS2_23.0.0/WKC_3.12.11/` (715 entries). The package also contains WebKit 0.12.2 / 601.7.4.
- ZIP member timestamps span September 8, 2026, 11:58:34 to 13:09:34. The ZIP's DOS timezone is unspecified; the archive file itself had a local modification date of October 30, 2026.
- `NS2_23.0.0/NetFrontBrowserNX_OSSCopyright.txt` identifies ACCESS Co., Ltd. and states that some package files were modified by ACCESS. It does not list those files or changes.

The reproducible inventory and evidence-file hashes are in the local source record. The original JSON inventory is not included in this public snapshot because it contains local paths.

## Version signals

| Source | Declared value | Interpretation |
|---|---|---|
| Package root | `NS2_23.0.0` | Package label 23.0.0, distinct from the console firmware 23.0.1 reported in the research. |
| WebKit directory | `webkit_3.12.11` | ACCESS/WebKit release label. |
| `WebCore/Configurations/Version.xcconfig` and `JavaScriptCore/Configurations/Version.xcconfig` | `MAJOR=613`, `MINOR=3`, `TINY=9`, i.e. 613.3.9 | Both components declare the same version. |
| `WKC_3.12.11/WebKit/WKC/webkit/WKCVersion.h:26-35` | WKC 7.0.0; customer release 3.12.11; `WKC_WEBKIT_VERSION` macro 613.0 | Directory, customer release, and package labels are consistent. The macro is not referenced elsewhere in the supplied archive. |
| Experiment context | Firmware 23.0.1; User-Agent `AppleWebKit/613.0` | Values reported in the task, not build identifiers. The available WKC code delegates the UA string to a host-application callback. |

Important detail: `WKC_WEBKIT_VERSION` appears only at its definition in the archive. Available code does not use it to build the User-Agent. Instead, `WKC_3.12.11/WebKit/WKC/WebCoreSupport/FrameLoaderClientWKC.cpp:1131-1137` delegates `userAgent(uri)` to `m_appClient->userAgent(uri)`, with the callback declared in `WKC/helpers/FrameLoaderClientIf.h:852`. Nintendo application source is not in the package (`WifiWebAuthApplet` is absent). Matching `613.0` strings therefore do not establish that the macro produced the observed User-Agent.

The values 613.0 and 613.3.9 come from different fields. The package does not document their relationship, so the difference proves neither a build inconsistency nor the exact identity of the running engine.

## Revisions and build identifiers

- The ZIP contains no `.git` directory, WebKit/WKC revision manifest, recognizable browser binary (`.nso`, `.nro`, `.elf`, `.so`, `.dll`, `.dylib`, `.a`, `.o`, `.bin`), or build ID mapping the source to firmware 23.0.1.
- WebCore and WKC files have September 8, 2026 ZIP timestamps. Those describe archive creation/assembly, not the timestamp of each source change.
- A local partial WebKit repository recorded `FETCH_HEAD=5f0480f771ba1749663a8257eafca70af17b7cec`, the May 24, 2026 upstream 312202 commit, parent `e8db86ea1203dcc4109eece64cfe0434d21cf13a`. It is shallow with `blob:none`; without network, the four audited WebCore blobs are missing. It provides commit metadata and a fixed upstream reference, not a compilable checkout or Nintendo provenance.

## Provenance conclusion

**Confirmed:** the archive contains WebKit 3.12.11 / WebCore 613.3.9 with a WKC 3.12.11 layer that defines `WKC_WEBKIT_VERSION` as 613.0. The reported User-Agent has the same string, but available WKC code delegates its creation to the host client.

**Probable:** this source belongs to the WKC 3.12.11 family targeted by the Switch research. Package and client-release labels support this match; the User-Agent alone does not, because the host client supplies it.

**Unknown:** whether this content exactly matches the `WifiWebAuthApplet` binary on firmware 23.0.1, whether that binary contains additional changes, and which build/source identifiers it embeds. The binary or a matching build-ID/source table is missing.

## Public ns2jb sources — checked 2026-11-01

- The public [`pepsipu/ns2jb`](https://gitlab.com/pepsipu/ns2jb) repository showed commit `95f5525089273c5fce0b95047f3600f8442e96ae` (`clarify`, October 22, 2026). Its README describes native functions in FS, lists system software 23.0.1 as a prerequisite, and claims a physical test on October 21. The published Git tree has host code and the FS payload but no WebKit/WKC port, WebCore patch, WebKit source identifier, or manifest linking the browser binary to firmware.
- Pepsipu's October 18 blog post, [“jailbreaking the switch 2”](https://pepsipu.com/blog/2026-10-switch2-jailbreak-ns2jb/), claims a captive-portal WebKit n-day provided an initial native-control-flow entry point. It then lists porting the FS exploit to WebKit as future work. This is the author's public claim, without source code, binary hash, or build ID allowing independent verification of that WebKit branch.
- These pages provide a published claim that ns2jb worked on 23.0.1 and a claim of a WebKit entry point. They do not link the inspected ACCESS/WKC 3.12.11 source to the browser running in that firmware or publish the FS-to-WebKit port described as future work.

The CSSFontFace CVE must remain distinct from 312202: official advisory [WSA-2026-0004](https://webkitgtk.org/security/WSA-2026-0004.html) maps **CVE-2026-43715** to WebKit bug **313577**. Bug **312202** maps to commit `5f0480f` / canonical `313821@main`; these sources do not establish CVE-2026-43715 → bug 312202.
