# Evidence matrix

This matrix records what the private laboratory's saved reports and source review support. Raw Switch reports are not included in this curated repository. Client-generated fields remain self-reported even when the matching JSON document was received and persisted by the local server.

| Claim | Local evidence reviewed | What it supports | Boundary |
|---|---|---|---|
| The captive browser exposed `FontFace` and `document.fonts.load()` | Saved JSON report from a Switch-attributed session | The received report records those APIs as available and a basic load promise as resolved. | Confirms report contents, not native implementation details or independently authenticated device identity. |
| A JavaScript-created face could load and later be removed from the set | Several saved reports from separate local-font checks | Reports record promise resolution, a final `loaded` status, and removal from `document.fonts`. | Does not show that the native backing object was destroyed. |
| CSS-backed and JavaScript-created faces could both be returned by a load request | Multiple saved reports | The reports record two matching faces and a resolved request. | JavaScript-visible behavior only; no native lifetime inference follows. |
| A `then` getter ran synchronously during a safe `document.fonts.load()` observation | Two saved safe-survey reports | Event ordering places `getter-A` between the call start and its return; the getter recorded `insideLoad: true` and `loading` status. | Supports JavaScript reentrancy for those recorded executions. The safe getter did not mutate CSS rules. It is not evidence of a use-after-free. |
| JavaScript-visible CSS set membership changed after rule removal | One saved report | The report records one CSS-backed face before removal and none afterward, while a JavaScript-created face remained. | Set membership is not proof of native destruction or invalid access. |
| A retained JavaScript wrapper remained readable after its CSS rule was removed | One saved report | The wrapper's status remained readable, and a later wrapper was reported as a distinct object. | Wrapper identity and readability do not reveal the native object's ownership or allocation state. |
| Some older diagnostic runs did not progress beyond their initial saved phase | Local report corpus snapshot | Initial-phase JSON files lacked matching later-phase files in that snapshot. | The absence of a later report cannot distinguish continued execution, a stopped page, failed upload, or storage elsewhere. |
| A test run was associated with console error `2168-0002` | Investigation notes supplied to the lab | The notes report the association. | The saved report corpus contains no console error field, crash dump, symbolized stack, or independent console diagnostic establishing cause. |
| WebKitGTK 2.52.4 showed invalid accesses under Memcheck and 2.52.6 did not in the archived comparison | Archived PC Memcheck campaign summaries and logs | The specific Linux binaries and captured runs differed as reported. | Linux observations do not establish the behavior of the Nintendo browser binary. The logs are outside this curated repository. |

## Evidence-state vocabulary

1. **Reported by the page** means a value was present in the browser-generated payload.
2. **Received** means the local report service parsed and saved a matching JSON document.
3. **Acknowledged** means the page received a successful HTTP response. Unless the response transcript was separately saved, this is supported by the client/server flow and subsequent same-session records rather than a preserved packet capture.
4. **Independently verified** would require evidence not controlled by the page, such as a native trace or authenticated artifact provenance. The JavaScript observations summarized here do not meet that standard.

## Evidence still needed for native conclusions

- A trusted mapping between the firmware 23.0.1 `WifiWebAuthApplet` binary and the archived Nintendo/ACCESS WebKit sources.
- Native allocation/free/access traces from the Nintendo binary, or an equivalent symbolized diagnostic tied to its exact build.
- The original diagnostic for the reported console error, if the cause of that event is to be established.

The local reports support browser-visible behavior and the receipt of particular JSON records. They do not establish a native memory error, a crash cause, or code execution on Switch 2.
