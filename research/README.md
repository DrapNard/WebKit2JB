# WebKit2JB Research Dossier

This dossier summarizes source-level FontFace research and the boundaries of local Switch observations. It does not claim that the inspected archive is byte-identical to Switch firmware. The source review documented here involved no Switch interaction or reproduction.

## Evidence sources

- Nintendo/ACCESS source package `NS2_23.0.0.zip`, SHA-256 `a2bcdfb7ec695d1ac5c790317a1239ccdb40e0ba8e052891c2ebba1314200f90`; its local path is withheld.
- Relevant source tree: `NS2_23.0.0/webkit_3.12.11/`; companion port tree: `NS2_23.0.0/WKC_3.12.11/`.
- The WebKit directory label is 3.12.11; embedded `WebCore/Configurations/Version.xcconfig` reports WebKit 613.3.9. The archive includes an ACCESS OSS copyright notice stating that some files were modified by ACCESS.
- Switch-side observations were JSON reports and local probe output. They record reported JavaScript runs, not native memory diagnostics.
- Upstream comparisons link to official WebKit commits in [PATCH_MATRIX.md](PATCH_MATRIX.md).

## Documents

- [Original research baseline](RESEARCH_BASELINE.md)
- [Data catalog and handling](DATA_CATALOG.md)
- [PC WebKitGTK results](PC_WEBKITGTK_RESULTS.md)
- [Re-entrancy and lifetime analysis](REENTRANCY_ANALYSIS.md)
- [Optional safe FontFace diagnostic design](../docs/OPTIONAL-SAFE-FONTFACE-DIAGNOSTIC.md)
- [Findings and evidence boundary](FINDINGS.md)
- [Evidence matrix](EVIDENCE_MATRIX.md)
- [Source inventory](SOURCE_INVENTORY.md)
- [Version provenance](VERSION_PROVENANCE.md)
- [Upstream patch matrix](PATCH_MATRIX.md)
- [Backport analysis](BACKPORT_ANALYSIS.md)
- [Call graph](CALL_GRAPH.md)
- [Ownership analysis](OWNERSHIP_ANALYSIS.md)
- [Switch timeline](SWITCH_TIMELINE.md)
- [Switch 2 status for 313577](313577_SWITCH_STATUS.md)
- [Manual captive-portal check](SWITCH2_PORTAL_MANUAL_CHECK.md)
- [Local reproduction summary](LOCAL_REPRODUCTION.md)
- [Sanitizer findings](SANITIZER_FINDINGS.md)
- [Native entry-point decision](NATIVE_ENTRYPOINT_DECISION.md)
- [System UI analysis](SYSTEM_UI_ANALYSIS.md)
- [Jmesmykil evidence review](JMESMYKIL_COMPARISON.md)
- [Unresolved questions](UNRESOLVED_QUESTIONS.md)
- [FontFace lifetime model](lifetime-model/RESULTS.md)
- [NS2JB portability notes](ns2jb-portability/PORTABILITY_AUDIT.md)

## Machine-readable research data

- [Original source manifest](data/ORIGINAL_SOURCE_MANIFEST.json)
- [Redacted Switch report aggregate](data/SWITCH_REPORT_AGGREGATE.json)

## Evidence boundary

JavaScript-visible FontFace state and callback ordering do not establish C++ object lifetime or invalid native memory access. WebKitGTK Memcheck observations concern Linux binaries and do not identify the Nintendo firmware engine. The source archive has no browser binary or build-ID map. No crash or code-execution claim is made for Switch 2 firmware 23.0.1.
