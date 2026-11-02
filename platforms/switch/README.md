# Switch portal adapter

`index.html`, `diagnostics.js`, and `portal.js` retain their existing URLs. The page loads `/shared/capabilities.js` and `/shared/reporting.js` before the portal code; `api-probe.py` serves these from a fixed route map under the existing same-origin CSP.

The diagnostics still start only from the visible button. Capability checks run before the FontFace APIs are used. Missing requirements return `result: "unsupported"` with the missing feature names. Each event stores a small snapshot of `document.fonts` and the active face state. HTTP reporting accepts only a matching 200 duplicate or 201 new-report acknowledgment; on error the JSON stays visible and no automatic retry occurs.

The compatibility target is conservative ES5 script syntax. This is syntax-level hygiene only: the host WebKit/WKC version and runtime behavior are not verified by Node's parser or the PC containers. No console test was run for this integration.
