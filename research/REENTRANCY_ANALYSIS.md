# Re-entrancy and object-lifetime analysis

This note consolidates the original source review without reproducing old trigger pages or report identifiers.

## Three distinct lifetime/state concerns

1. **312202 — retained face ownership.** `FontFaceSet::load` obtains a set of matching CSS faces and then invokes operations that can synchronously re-enter script. The archived source uses non-owning `reference_wrapper<CSSFontFace>` results at this boundary. The upstream change retains strong `Ref<CSSFontFace>` ownership while the operation proceeds. The relevant question is whether removal of a CSS rule can release the last owner while the in-flight result still refers to the face.
2. **313577 — current client membership.** The archived `iterateClients` path snapshots strong references to clients, then notifies them. Strong references preserve the client objects, but the archived path does not re-check that a snapshotted client is still registered immediately before notification. The upstream change skips clients detached by an earlier callback. This is distinct from the face-result ownership change in 312202.
3. **322233 — transition ordering.** The archived status-change path notifies clients before storing the new status. A synchronous callback can therefore re-enter while the previous status remains visible. The upstream change commits the new status before callbacks while preserving the old/new values for notification.

The three fixes address related callback/lifetime territory, but they are not interchangeable and their issue numbers must not be conflated.

## What the browser-side reports add

Some stored safe-survey reports describe a JavaScript `then` getter occurring synchronously while `document.fonts.load()` was still on the stack. The getter only recorded an event and returned; it did not mutate a stylesheet. The aggregate counts and caveats are in [`data/SWITCH_REPORT_AGGREGATE.json`](data/SWITCH_REPORT_AGGREGATE.json).

This supplies evidence of JavaScript re-entrancy in reported executions. It does not show that a native client was detached, that a `CSSFontFace` lost its last owner, that a native callback used a freed object, or that the relevant native access happened in the Switch binary.

## Evidence ladder

| Step | Evidence available | What remains unproven |
|---|---|---|
| JavaScript callback occurs during a font load | Some stored reports record the getter inside the call. | Independent authentication of each client measurement. |
| CSS-visible state changes | Other local reports record changes to the set after stylesheet mutation. | Native object destruction or invalid access. |
| Source has a pre-fix motif | The supplied WebKit 3.12.11 tree matches the pre-fix ownership/client/state patterns. | That this exact source was built into firmware 23.0.1. |
| Native invalid access occurs | Memcheck recorded invalid accesses in separate WebKitGTK Linux tests. | Attribution of every access to a source function, and transfer to WKC/Horizon. |
| Execution control or native code execution | No such evidence exists in the Switch or PC research record. | All transitions from memory corruption to control flow and execution. |

The archived source's provenance gap remains decisive: no browser binary, Build ID, or trusted source-to-firmware map for WifiWebAuthApplet is present. See [`RESEARCH_BASELINE.md`](RESEARCH_BASELINE.md) and [`UNRESOLVED_QUESTIONS.md`](UNRESOLVED_QUESTIONS.md).
