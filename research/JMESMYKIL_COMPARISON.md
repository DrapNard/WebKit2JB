# Review of the Jmesmykil captive-portal research repository

Reviewed 2026-11-01 against the public repository [Jmesmykil/switch2-captive-portal-research](https://github.com/Jmesmykil/switch2-captive-portal-research). No source was copied. The repository states that it has no open-source license; public visibility alone does not grant reuse rights.

## Published components and evidence boundaries

The reviewed repository contains a local DNS/HTTP connectivity helper, browser-side diagnostic modules, a Python report service, small media fixtures, and host-side tests. The DNS helper is a constrained local resolver rather than a general forwarding service. Its HTTP component handles connectivity-check requests and redirects them to the local diagnostic service. These pieces describe a research portal, not an Internet gateway or a production authentication system.

The browser modules combine API/environment inspection with bounded active checks, such as loading a local font or measuring a small rendered sample. Their result labels describe the checks implemented by the page; they do not independently validate native memory safety or firmware identity. The separately published crash-oriented pages and takeover material are outside the safe diagnostic set and are not reproduced or integrated here.

## Evidence quality

The repository's roadmap makes claims beyond what its packaged tests and user-interface status labels alone can establish. A success label, completed harness, caught exception, or submitted report is not independent proof of a memory primitive, native execution, kernel operation, or firmware modification. The review found material gaps between some advertised outcomes and the validation performed by the corresponding page. Those claims should be treated as author assertions unless backed by raw, independently checkable artifacts.

Likewise, a browser report can show that a client submitted particular values, and a server can prove that it received and stored them. Neither fact authenticates the client's measurements. The repository's build identifiers, module hashes, request identifiers, bounded JSON handling, and acknowledgements improve traceability and delivery semantics; they do not make browser-supplied results trustworthy by themselves.

## Comparison with WebKit2JB

WebKit2JB serves its portal, diagnostics, report storage, summary, and bridge endpoints from its local service. It preserves structured JSON reports and uses explicit HTTP status acknowledgements. Its local report metadata can identify the served build and resource hashes, while still marking browser observations as client-reported.

The reference's strict, non-forwarding DNS behavior is useful for an isolated local test profile. The adaptation belongs in an optional DNS configuration; it should not replace an active resolver without authorization. The portal should continue to distinguish a successful HTTP response from a verified diagnostic outcome.

For captive-portal compatibility, the useful engineering ideas are bounded response handling, explicit request/report identifiers, module revision tracking, stable acknowledgements, and clear diagnostic selection. These are general design observations, not copied implementation. The reference repository's license status prevents source reuse unless its authors grant suitable rights.

## Risk classes

| Material | Classification | Treatment in WebKit2JB |
|---|---|---|
| API-presence and environment metadata | Low-impact observation | Keep results labeled as page-reported and platform-dependent. |
| Local-font loading and rendering checks | Active but bounded diagnostic | Require explicit user selection, record timeouts and cleanup state, and avoid interpreting them as native lifetime evidence. |
| Reentrant or crash-oriented proof-of-concept pages | Potentially destabilizing | Excluded from the captive portal and from this curated source snapshot. |
| Roadmap/dashboard status claims | Unverified unless supported by artifacts | Do not treat labels as proof; require reproducible, attributable evidence. |

## Adaptation and limits

The local adaptation uses a separate DNS profile for isolated setups, retains existing portal routes and report behavior, and tests GET/HEAD and report acknowledgement contracts locally. No test on a Switch is implied by those checks. No external page, diagnostic, or server from the reference repository was executed during this review.

Even when the captive browser reports a particular user-agent or JavaScript capability, those values remain client-reported. Hardware validation requires a manually initiated console session and device/firmware metadata. The available browser-side observations do not prove a native use-after-free or code execution.
