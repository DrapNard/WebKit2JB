# Optional safe FontFace observation

This is an English summary of a local, optional diagnostic design. The HTML page and route it originally described are **not included or served by this curated release**. No new Switch campaign is implied.

## Intended observations

- Load the existing static test font resource.
- Record JavaScript-visible `FontFace.status`, `document.fonts.status`, and set size around load events.
- Record whether `document.fonts.load()` settles and whether the `FontFace.prototype.then` getter is consulted synchronously. The getter only appends an event and returns `undefined`.
- Submit a report with resource hashes, build provenance, and the server's HTTP 201/200 acknowledgement.

The safe design does not create or delete CSS rules, remove a face from the font set, or mutate the set during loading. It is distinct from the upstream crash-oriented regression test.

## Interpretation limits

JavaScript events expose Web API state and callback order. They do not expose the C++ client list, `CSSFontFace` ownership, object destruction, or invalid native accesses. They cannot establish a use-after-free or its absence. A report acknowledged by the server establishes receipt only; browser-supplied measurements remain self-reported.
