# Research data catalog

This catalog describes the original data examined and what is included in this repository.

## Included, path-redacted research data

- [`data/ORIGINAL_SOURCE_MANIFEST.json`](data/ORIGINAL_SOURCE_MANIFEST.json) records the source archive's size, SHA-256, internal version metadata, selected member hashes, and upstream fix identifiers. The archive itself is not copied.
- [`data/SWITCH_REPORT_AGGREGATE.json`](data/SWITCH_REPORT_AGGREGATE.json) records counts and schema distribution for the 193 existing JSON reports, along with deduplication and evidence-limit notes. It contains no raw report bodies, client IPs, user-agent strings, report IDs, or run IDs.
- [`EVIDENCE_MATRIX.md`](EVIDENCE_MATRIX.md) and [`PC_WEBKITGTK_RESULTS.md`](PC_WEBKITGTK_RESULTS.md) summarize the Switch-attributed and PC-only observations separately.
- [`history/legacy-backup-inventory.json`](../history/legacy-backup-inventory.json) lists local legacy backup names, byte sizes, and SHA-256 digests only.

## Source-side counts

The Switch report corpus snapshot contained 193 JSON files: all 193 parsed successfully. It contained 20 explicit schema values plus 10 legacy/unversioned records. Several reports are progress snapshots rather than independent runs: 47 WKC lifetime JSON files reduce to seven unique contents, and 40 are exact duplicate snapshots. The safe FontFace v2 records lack explicit run IDs, so their count is not treated as an independent trial count.

The original source archive was approximately 197 MB compressed and 728 MB uncompressed. It contains tens of thousands of upstream files and is not vendored here. The machine-readable manifest retains the archive hash and hashes for selected version and WebCore/WKC members so the source review can be checked against a separately held copy.

## What the report families say

| Report family | Corpus count | Supported interpretation |
|---|---:|---|
| Storage API and lifetime probes | 52 storage-probe JSON files; 47 WKC lifetime files representing seven distinct payloads | Browser-side storage observations and progress snapshots only. The 40 exact repeats are not independent runs and do not establish privileged filesystem access. |
| WebKit API survey | 34 reports in three declared sessions | The page reported which APIs were available and which bounded checks resolved. User-Agent and capability values are client-supplied. |
| Safe FontFace v2 | Five reports without explicit run IDs | Three report a synchronous getter during `document.fonts.load()` with a loading status; two report resolution without that getter. These are not five proven independent runs. |
| 312202 observations | 11 reports grouped into seven declared runs | Two runs have later `returned` and `finished` phases, with one rejected outcome and one timeout; five have only an `armed` record in this corpus copy. Missing later phases do not identify why they are absent. |
| Local-font survey | 11 reports across two declared runs | Nine are progress snapshots and two are completion reports. Candidate-name misses are probe inputs, not additional runs. |
| CSP, redirect, bridge, and WKC cache/disk checks | Small one-to-three-report families | These document bounded portal/probe outcomes. They do not demonstrate native access to Horizon services or privileged storage. |
| Static source-archive audit | One aggregate report | It counted 164 archive candidates and selected two sources for inspection. Static archive indicators are not evidence about the contents of the running firmware binary. |

These summaries retain the report-level results that are relevant to the research questions while avoiding publication of client identity fields, raw report payloads, or source-local paths. The full schema distribution and aggregate corpus digest are in `data/SWITCH_REPORT_AGGREGATE.json`.

## Deliberately not copied

The repository does not include raw Switch JSON reports, raw Memcheck logs, per-process traces, tarball bundles, package archives, Podman storage, firmware/source archives, private networking configuration, crash-oriented historical backups, or the native demo artifact. These files either contain client identity/local paths, are large environment-specific artifacts, or are not needed to understand the recorded result. The local workspaces retain the original evidence. Hashes are included only where they help identify the corresponding local artifact.

## Integrity limits

An aggregate count or hash is not the underlying evidence. The Switch report values were supplied by the browser page; server persistence confirms receipt, not measurement truth. The PC hashes identify the specific binaries/tests/bundles described in the local reports, but do not make omitted artifacts downloadable from this repository. Any new extraction should preserve the original file, record its source and hash, redact personal metadata, and document the transformation.
