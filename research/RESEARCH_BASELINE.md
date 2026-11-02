# Original research baseline and evidence map

This document consolidates the original source review, the Switch-attributed browser observations, and the separate WebKitGTK experiments. It is an index of what was actually examined, not a claim that the Nintendo firmware is vulnerable.

## Research questions

The work began with three separate WebCore lifetime/state changes. They must remain distinct:

| Issue | Upstream change | Source-level effect | Current Switch conclusion |
|---|---|---|---|
| WebKit 312202 | [`5f0480f771ba1749663a8257eafca70af17b7cec`](https://github.com/WebKit/WebKit/commit/5f0480f771ba1749663a8257eafca70af17b7cec) | Keeps matched `CSSFontFace` objects strongly owned across synchronous re-entry. | The archived source has the pre-fix ownership motif; runtime native lifetime is not demonstrated. |
| WebKit 313577 / CVE-2026-43715 | [`5aedb82710ba578f61501106e78f6b25b7f7a558`](https://github.com/WebKit/WebKit/commit/5aedb82710ba578f61501106e78f6b25b7f7a558) | Checks that a snapshotted client remains registered before notifying it. | The archived source has the pre-fix client-notification motif; the firmware binary is unidentified. |
| WebKit 322233 | [`64a55fd574c40d8fda92b4f114d2a2afb9f0ec71`](https://github.com/WebKit/WebKit/commit/64a55fd574c40d8fda92b4f114d2a2afb9f0ec71) | Commits the new status before notifying clients, preserving the old/new pair for callbacks. | A matching pre-fix ordering appears in the archived source; no native Switch execution evidence exists. |

313577 is the issue associated with CVE-2026-43715. That CVE is not assigned here to 312202 or 322233.

## Original source package examined

The read-only source review examined an archive labeled `NS2_23.0.0`. Its recorded SHA-256 is `a2bcdfb7ec695d1ac5c790317a1239ccdb40e0ba8e052891c2ebba1314200f90`; the archive is not included in this repository. It contains a WebKit directory labeled 3.12.11 whose embedded WebCore and JavaScriptCore version is 613.3.9, and a WKC 3.12.11 tree with WKC API 7.0.0 metadata. A separate older WebKit tree reports 601.7.4.

The WKC version macro `613.0` is present in version metadata, but the inspected WKC code delegates User-Agent generation to a host application callback. The macro is not evidence that the Switch browser binary is WebKit 613.0 or 613.3.9. The archived WKC tree did not contain a separately named FontFace implementation or exact matches for the audited methods. That negative source search does not establish what is present in an unprovided firmware binary.

The archive label is 23.0.0, while the reported console firmware under study is 23.0.1. The archive contains source but no WifiWebAuthApplet browser binary, firmware Build ID, or trusted source-to-binary mapping. See the machine-readable, path-redacted [source manifest](data/ORIGINAL_SOURCE_MANIFEST.json).

## Switch-attributed observations

The local report corpus contains browser-submitted JSON. It records JavaScript-visible capabilities, font-loading outcomes, callback ordering, and client-side phases. The server's receipt of JSON proves that those bytes were stored; it does not independently authenticate the browser's measurements or reveal C++ allocation lifetime. The [redacted dataset catalog](data/SWITCH_REPORT_AGGREGATE.json) records the corpus inventory and deduplication limits without publishing raw reports, client IP addresses, user-agent strings, or report identifiers.

The strongest safe observation is that some saved reports record a `FontFace.prototype.then` getter during `document.fonts.load()`, with `insideLoad: true` and a `loading` status. Other saved safe-survey reports record resolution without that getter. The getter in the safe survey only records an event; it does not mutate CSS rules. These observations establish JavaScript re-entry for the recorded reports, not a native use-after-free.

Prior reports of error `2168-0002` cannot be attributed from the saved JSON: the corpus lacks a matching crash report, process identity, or symbolized native stack. Incomplete phases are not proof of a crash.

## Separate PC evidence

The WebKitGTK work ran in isolated x86-64 Podman images and is summarized independently in [PC WebKitGTK results](PC_WEBKITGTK_RESULTS.md). Source-tag inspection established which tested versions contained the 312202 source motif. Memcheck runs observed invalid accesses for a separate 313577 test comparison. Those are facts about the tested Linux builds only.

The standalone C++ ASan exercise and the 64-KiB ELF runner are educational, independent programs. The ELF was launched through its ordinary runner path; it was never launched by WebKit or by corrupting memory. Neither component proves native execution through a browser vulnerability.

## What would change the Switch conclusion

The remaining gap is not another JavaScript diagnostic. A conclusion about firmware 23.0.1 requires (1) a trusted mapping between the exact WifiWebAuthApplet binary and the reviewed source/build, including backports, and (2) native evidence from that exact binary that identifies the relevant object lifetime and invalid access. Neither is in the current corpus. Until both are available, presence of the mechanism in the running firmware remains **NOT DEMONSTRATED**.

## Data handling

The original workspace remains the source of truth for raw reports, test pages, signed packages, Memcheck bundles, firmware/source archives, and local container storage. This repository contains English analytical summaries and redacted aggregate metadata. See [history policy](../docs/TRANSLATION-AND-HISTORY.md) for the boundary.
