# Open Questions — Nintendo WebKit 23.0.1

This file lists only questions that remain unresolved by the source and reports summarized in this repository. PC WebKitGTK measurements are useful for their tested binaries, but do not answer questions about the Nintendo browser.

## 1. Which WebKit/WKC build does WifiWebAuthApplet load?

The inspected archive is labeled `NS2_23.0.0`, contains WebKit/WKC 3.12.11, and declares WebCore/JavaScriptCore 613.3.9. The reported console firmware is 23.0.1. The archive contains no browser binary, build ID, revision manifest, or trusted mapping to the firmware's `WifiWebAuthApplet`. The reported `AppleWebKit/613.0` User-Agent is not an identifier: the archived WKC code delegates User-Agent generation to its host client.

**Needed to resolve:** a trustworthy firmware build/source manifest or a legally supplied browser binary with a verifiable build-ID-to-source mapping, including any backports. The current portal and archived source cannot provide this mapping.

## 2. Does the firmware browser perform an invalid native access for WebKit bug 313577?

Existing Switch reports establish JavaScript-observable synchronous reentrancy in the recorded `document.fonts.load()` path. The archived 3.12.11 source has the upstream pre-fix motif. Neither establishes the native client-set state, object lifetime, or an invalid access in the firmware binary. The WebKitGTK Memcheck observations concern separate Linux binaries and are not transferable evidence for Nintendo's port.

**Needed to resolve:** native evidence from the identified firmware browser, such as an authorized symbolized diagnostic or equivalent instrumentation that observes the relevant object lifetime and access. JavaScript-only portal reports cannot establish this.

## 3. What caused the reported console error associated with earlier experiments?

The retained timeline records incomplete report phases and notes an association with error `2168-0002`, but the stored JSON does not independently identify the error's process, exact run, or termination cause. A missing later report cannot distinguish a crash from closure, navigation, network failure, or reporting failure.

**Needed to resolve:** a diagnostic tied to the same run, such as a system crash report, process identification, or symbolized native stack. No such artifact is included in this release snapshot.

## Evidence boundary

The public snapshot excludes raw private Switch and Memcheck reports. Its source summaries support the limits above, not a claim that the Nintendo firmware contains or exercises a vulnerable binary. No further local JavaScript diagnostic would answer the missing binary-provenance or native-memory questions.
