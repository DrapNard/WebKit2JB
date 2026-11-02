# Switch 2 Report Timeline

This timeline consolidates the existing report records. Original JSON reports and raw run data remain private and are not included here. Stored report timestamps are ISO-8601 UTC. Server filenames use receipt time and can differ by fractions of a second from browser timestamps because JSON is serialized after the event.

## Evidence rules

- A JSON file archived by the server proves the HTTP handler received and stored that report. A local browser `report(...)` call proves only that the page attempted an XHR.
- In older experiments, a `returned` report with the same run ID as an `armed` report corroborates that the browser received a successful HTTP response before continuing. The HTTP response transcript itself was not stored.
- Absence of a later report does not identify the termination cause. A browser close, navigation, network error, or reporter failure can prevent a later record.
- Reports with desktop/mobile Safari User-Agents are not Switch observations. Client IP addresses are deliberately omitted here.

## Consolidated timeline

| Time (UTC) | Stored schema / phase | Recorded result | Interpretation |
|---|---|---|---|
| 2026-10-30 22:44 | `ns2-fontface-survey-v2` | Switch-reported UA; FontFace APIs present; `document.fonts.load()` resolved with count 0. | API availability and ordinary call completion only; no native path or defect. |
| 2026-10-30 22:49–22:58 | `ns2-fontface-custom-load-v1` (three reports) | A custom face was added, returned by `load()`, resolved, reached `loaded`, then was removed from the set. | Repeated JS-visible custom-font behavior. |
| 2026-10-30 23:02–23:04 | `ns2-dual-fontface-normal-v1` (two reports) | `load()` resolved with CSS and JavaScript faces; returned count 2; JS face reached `loaded`. | Normal dual-face loading. |
| 2026-10-30 23:26 | `ns2-fontface-*` armed/returned/finished phases | Initial state: getter false, rule not removed, `load()` not returned. A later record reported return; a final record reported promise rejection with `A network error occurred.` | This run did not record getter firing, CSS rule removal, or the fatal outcome described elsewhere. |
| 2026-10-30 23:39–23:51 | timeline/getter-audit reports | One report recorded `before-load`, `after-load`, then getter; another positive-control getter also occurred after `load()` returned. | These reports do not show getter reentrancy during the load call. |
| 2026-10-30 23:44 | `ns2-buffer-timeline-v1` | A 621,572-byte ArrayBuffer was reported; loading resolved with two faces and final status `loaded`. | Reported browser behavior only. |
| 2026-10-30 23:58 and 2026-10-31 00:04 | `ns2-local-font-survey-v1` progressive records | Several same-run snapshots were stored. The later completed run reported `systemfont`/`SystemFont` matches, getter during its load call, returned count 2, and resolution. | Progressive snapshots are not independent trials. This run records JS-visible reentrancy. |
| 2026-10-31 00:08–00:38 | Several `armed` records | Initial phases were stored without later `returned`/`finished` phases. Some related reports came from non-Switch browsers. | Missing phases do not show whether execution continued. Non-Switch records are excluded as console evidence. |
| 2026-10-31 01:06–01:13 | `ns2-fontface-survey-safe-v2` (two stored Switch reports) | `before-load`, synchronous `getter-A` with `insideLoad=true` and status `loading`, `after-load-return`, then promise resolution with two matching faces. | Confirms synchronous JS reentrancy in this path and normal completion; does not show native client-set state or memory access. |
| 2026-10-31 01:14 | `ns2-fontface-survey-rule-lifecycle-v1` | Two faces (one CSS, one JS) were registered/loaded. After rule deletion, CSS count became zero while the JS face stayed registered through the next task. | JS set-membership behavior only. |
| 2026-10-31 01:19 | `ns2-fontface-survey-css-wrapper-lifetime-v1` | The old CSS wrapper was absent from the set after rule deletion but remained readable; reinsertion created a distinct wrapper. | JavaScript wrapper/set membership, not native destruction or invalid memory. |
| 2026-10-31 01:23 | local-font `armed` record | Switch-reported UA; no later phase in the current private report corpus. Related notes associate the test family with console error 2168-0002, but the error is not present in this JSON report. | The association is not independently proved by this report. |

## Reporting implementation and limits

Older survey uploaders displayed HTTP 204 as saved. The server parses and writes a report before acknowledging it. The experimental reporting flow required an earlier `armed` report acknowledgement before starting its next phase, but the raw response transcript was not stored. A stored `armed` report alone does not establish that later code ran.

These are self-reported browser observations with a User-Agent string; the server receipt proves only that a JSON record arrived. They do not establish native WKC object identity, use-after-free, memory corruption, control-flow impact, or remote code execution. The `2168-0002` association requires independent console evidence and native diagnostics.
