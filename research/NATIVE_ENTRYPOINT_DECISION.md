# Decision — Native Entry Points and Horizon UI

**Status: local analysis complete; no Switch action was taken.** This note addresses whether `UwU from Nintendo Switch 2` can be shown through a real Horizon interface without confusing it with browser content.

## Decision

According to its README and test harness, the `ns2jb` repository provides a native execution entry point **inside FS**. This does not make FS a regular application and does not prove that it can request a LibraryApplet. The local WebKit2JB lab shows no native entry point inside `WifiWebAuthApplet`; its test content is HTML/JavaScript/Python, and its dialog NRO remains a standalone artifact.

The libnx-documented route for an arbitrary error message is `errorApplicationCreate` / `errorApplicationShow` from `AppletType_Application`. The Error Applet requires this context on HOS 10.0 and later; using the same wrapper from a LibraryApplet does not meet that condition. `errorSystemCreate` / `errorSystemShow` prepares `ErrorType_System`, but the public material consulted does not define which caller classes are authorized. The type name is not permission.

A regular Application has, according to community analysis of AM services, the `appletOE` proxy and a LibraryApplet creator. This is a source/documentation-consistent route for requesting the Error Applet; **no actual call or display is confirmed on Switch 2 23.0.1**, and there is no evidence that a current lab entry point is this Application. libnx documentation is public but is not official Nintendo documentation; the cited Switch 2 service details come from Switchbrew, a reverse-engineering resource.

**Operational conclusion:** no entry point compatible with `ErrorType_Application` is currently established in ns2jb or the local WebKit2JB project. Calling `errorSystem*` from FS remains hypothetical and cannot be described as authorized. There is no safe, documented integration to add to the existing payload.

## Established contexts

| Entry point | What the local evidence establishes | Status for system UI |
|---|---|---|
| SmileBASIC Application driving ns2jb | The ns2jb README reports a successful hardware run on October 21, 2026. The harness checks the controller Application's Program ID and identifies FS separately as `0400000000000000`. The qualification code expects these identities. | **Incompatible** with the `AppletType_Application` requirement of `errorApplication*` when referring to the FS context. The controller is an Application, but the test code does not show it calling the Error Applet. |
| FS process targeted by ns2jb | The source test targets FS and the pipeline records the native process identity/Program ID. The README describes both native functions as running in FS. The inspected ns2jb repository contains no trace of `errorApplication*`, `errorSystem*`, `appletOE`, or a LibraryAppletError launch. | **Native execution reported/demonstrated**, but system display is **not demonstrated**. The exact AM type and proxy access are not recorded; do not infer `AppletType_None` from the FS Program ID alone. |
| `WifiWebAuthApplet` (captive browser) | Lab observations identify the browser by its User-Agent; Switchbrew classifies `WifiWebAuth` as a LibraryApplet. There is no local `appletGetAppletType()`/Program ID diagnostic for this process on 23.0.1. | `LibraryApplet` type is **probable**, not observed on the target console. If it is a LibraryApplet, `errorApplication*` is incompatible with HOS 10+; no ability to call `errorSystem*` is established. |
| WebKit2JB HTML/JavaScript page | Local test files are web pages/scripts and a Python server. They can render content or invoke browser-managed UI, but there is no Horizon native call in this path. | **Does not meet** the native-execution criterion. UI possibly invoked by a web API remains a browser action and does not prove a native entry point. |
| Lab NRO demonstrator | Standalone compiled source and NRO; code checks process type, displays Program ID/interface/results, and requests `ErrorType_Application`. It has not been launched on Switch. | **Separate candidate**, not an ns2jb/WebKit2JB integration. Its `Application` execution context and effective service access remain unestablished. This NRO branch is complete; do not rebuild it. |

The ns2jb hardware-run claim comes from the repository README. In the examined copy, the `runs` directories and `fs-execution-*.json` files referenced by code are not included, so the reported run cannot be audited from the saved results here. The source documents qualification assertions, but is not itself an independent capture of that run.

## Interface categories and documented preconditions

| Horizon context | Proxy / category described | What the sources support |
|---|---|---|
| Regular `AppletType_Application` | `appletOE`, `IApplicationProxy`, LibraryApplet creator; libnx wrappers such as Error and software keyboard. | This is the context explicitly required by `errorApplicationCreate` since HOS 10.0. libnx documents UTF-8 text and foreground launch of `AppletId_LibraryAppletError`. This establishes the source-level contract, not success on Switch 2 23.0.1. |
| `AppletType_SystemApplication`, `SystemApplet`, `OverlayApplet`, `LibraryApplet` | `appletAE` and interfaces dependent on applet type, according to libnx/Switchbrew. | These are distinct process/application categories; libnx exposing `appletAE` does not grant a non-applet process a system role. Access to controllers and creators varies by type and service. |
| Non-applet system process (FS, sysmodule) | No generic arbitrary-UI route is established in the examined material. | Switchbrew notes that AM proxies generally do not appear usable from processes that are not genuine applets. This is reverse-engineering observation, not a Nintendo specification. The ns2jb FS case has not been diagnosed for AM. |
| Specialized system API called by an authorized application | Constrained-entry LibraryApplet or system UI, such as keyboard, network, or error UI. | These are not general display capabilities. libnx's `swkbdShow` launches `AppletId_LibraryAppletSwkbd` in the foreground; its title/subtitle fields accept UTF-8 text. This proves a documented system-UI API in libnx, but it displays a keyboard, not an error dialog, and does not prove Switch 2 compatibility. |
| `errorSystem*` | Error LibraryApplet configured with `ErrorType_System`. | The libnx wrapper prepares fields and launches the same error applet; no reliable public allowlist of callers was found. From FS or a regular Application: **not demonstrated**. |

`errorApplication*` and `errorSystem*` log a system error report according to libnx documentation. `errorResultShow` / `errorCodeShow` is another error category, but carries a `Result`/code and does not provide the desired arbitrary text field. `ErrorType_System` describes message configuration/content, not elevation or call authorization.

## Lead matrix

| Lead | Classification | Reason |
|---|---|---|
| ns2jb executes native code in FS | **Reported by repository; local hardware evidence incomplete** | README reports a hardware run; source checks the FS Program ID and native return values; run logs are absent from the copy. |
| ns2jb opens the Error LibraryApplet from FS | **Not demonstrated** | No `error*`/AM call found; no AM type or applet result recorded. |
| `errorApplication*` from a genuine regular Application | **Documented at libnx level; Switch 2 runtime unconfirmed** | Explicit HOS 10+ precondition and public documentation of the AM route; no 23.0.1 test. |
| `errorApplication*` from `WifiWebAuthApplet` / LibraryApplet | **Incompatible if LibraryApplet type is confirmed** | Error Applet documentation says `ApplicationError` no longer works from non-Application contexts starting with HOS 10. The actual Switch 2 process type has not been measured. |
| `errorSystem*` from FS, LibraryApplet, or Application | **Not demonstrated / permissions unknown** | Documentation describes `ErrorType_System`, not an allowlist of callers; the wrapper alone does not reveal Horizon's authorization decision. |
| `swkbdShow` called by a regular Application | **Documented libnx system UI; not equivalent to an error dialog** | Explicit foreground launch of `LibraryAppletSwkbd` with customizable text fields; target Switch 2 firmware compatibility and authorization are unconfirmed. |
| `alert()`, `prompt()`, or other page UI | **Incompatible with the criterion** | Rendering is triggered by web content; a possible native-looking appearance does not prove execution from a native lab entry point. |
| Add an AM call to the ns2jb FS payload | **Incompatible with the evidence and current constraints** | No AM right is established for FS; `errorSystem*` permissions are unknown. This would be an unverified call to an unauthorized service. No change was made. |

## Missing prerequisites for visible proof

1. An already identified, authorized entry point that actually runs as `AppletType_Application` (or explicit permission documentation for another category). No such entry point is present in ns2jb/WebKit2JB.
2. Independent confirmation of applet model and AM access in the relevant Switch 2 23.0.1 environment. Program ID alone does not prove these permissions.
3. To establish success: a real capture of the dialog with the exact text, independently observed Error LibraryApplet ID/name, caller process type/Program ID, and API results. A caller-only diagnostic does not prove which dialog was displayed.

The first two prerequisites cannot be resolved by local action without a dump, SDK/system binary, or console diagnostic; the third requires observing the Switch. None of this data will be replaced with an assumption. No console interaction, NRO rebuild, ns2jb modification, or service-call attempt was made during this analysis.

## Sources

libnx documents a community library, not an SDK published by Nintendo. Switchbrew pages are community reverse-engineering material; `[S2]` entries mean an item was catalogued by that community, not confirmed by Nintendo or tested against the target firmware.

- [libnx `error.h`](https://switchbrew.github.io/libnx/error_8h.html) — Error API and Application restriction.
- [libnx `error.c`](https://github.com/switchbrew/libnx/blob/master/nx/source/applets/error.c) — construction and launch of `LibraryAppletError`.
- [libnx `applet.c`](https://github.com/switchbrew/libnx/blob/master/nx/source/services/applet.c) — `appletOE` / `appletAE` selection by applet type.
- [libnx `applet.h`](https://github.com/switchbrew/libnx/blob/master/nx/include/switch/services/applet.h) — `AppletType` and `AppletId` enums.
- [libnx `swkbd.h`](https://switchbrew.github.io/libnx/swkbd_8h_source.html) and [`swkbd.c`](https://github.com/switchbrew/libnx/blob/master/nx/source/applets/swkbd.c) — configuration text and `swkbdShow`.
- [Switchbrew AM services](https://switchbrew.org/wiki/AM_services) — proxy categories, access notes, and `[S2]` IDs.
- [Switchbrew Error Applet](https://switchbrew.org/wiki/Error_Applet) — `ApplicationError` content and HOS 10.0 constraint.
- [Switchbrew Internet Browser](https://switchbrew.org/wiki/Internet_Browser) — descriptive classification of WifiWebAuthApplet.

## Stop for this branch

Useful local analyses are complete. No compatible authorized entry point is established; further progress depends on system/runtime data or console intervention, both excluded for this branch. The existing demo NRO is preserved as-is and is not revalidated on device.
