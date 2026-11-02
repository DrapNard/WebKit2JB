# System UI Applet Evidence Review

The current decision on native entry points and Horizon UI categories is summarized in [NATIVE_ENTRYPOINT_DECISION.md](NATIVE_ENTRYPOINT_DECISION.md). This note records what public libnx and Switchbrew documentation supports, and what remains unverified for Switch 2 firmware 23.0.1.

## Scope and repository findings

The reviewed NS2JB checkout describes native functions executing in the `FS` process. Its checked-in payload is an NSO; rebuilding it from source requires Zig on the development host. The reviewed source did not contain calls to libnx error-applet helpers or code that creates an application process. The separate libnx homebrew demo was built as an NRO, but was not run on a console.

The NS2JB README reports a hardware demonstration, but no matching device log was available in the reviewed materials. That statement is therefore not independently verified here. No conclusion about an actual applet launch follows from the source or from a successful NRO build.

## Public API behavior

| Interface | Documented behavior | Limitation |
|---|---|---|
| `errorApplicationCreate` / `errorApplicationShow` | Prepare and launch the Error LibraryApplet with `ErrorType_Application`; message fields use UTF-8. | Since HOS 10.0, the create call is documented for `AppletType_Application`; other contexts may cause the applet to raise a fatal error. The applet also records an error report. |
| `errorSystemCreate` / `errorSystemShow` | Prepare and launch the same LibraryApplet with `ErrorType_System`. | The API documentation does not establish which caller process types are authorized. This is not evidence of a fallback available to ordinary applications. |
| `AppletId_LibraryAppletError` | Identifies the Error LibraryApplet (ID `0x0E`; historical Program ID `0100000000001005`). | Knowing the applet ID does not grant the caller permission to create or launch it. |

The [libnx implementation](https://github.com/switchbrew/libnx/blob/master/nx/source/applets/error.c) uses a shared helper to create the Error LibraryApplet in the foreground, provide its configuration, and start it. The wrappers do not locally verify the caller's process category. That absence of a library-side check does not establish that Horizon or the applet will authorize a particular caller.

The [libnx API documentation](https://switchbrew.github.io/libnx/error_8h.html) is explicit that `errorApplicationCreate` is restricted to an application context from HOS 10.0 onward. It does not state an equivalent caller restriction for `errorSystemCreate`. The [AM services documentation](https://switchbrew.org/wiki/AM_services#appletAE) distinguishes the regular-application `appletOE` path from `appletAE` used by system or other applet contexts, and cautions that the latter is not generally available to arbitrary processes. These sources describe platform interfaces, not authorization behavior verified on firmware 23.0.1.

## What the evidence supports

- **Documented for Horizon generally:** the Error LibraryApplet accepts application or system error configurations and can display caller-provided text. The Error Applet documentation says application errors are unavailable from non-application contexts on HOS 10.0 and later.
- **Listed for Switch 2:** Switchbrew's AM services table lists `LibraryAppletError`. This establishes documented presence in the Switch 2 service model, not permission for a given process or successful execution on firmware 23.0.1.
- **Found in the reviewed NS2JB source:** the documented execution context is `FS`; no Error Applet wrapper or applet-creation call was found. This does not establish that the process has the applet services or permissions needed to request system UI.
- **Not demonstrated:** the actual process type used by the NS2JB path, its applet-service access, the Switch 2 authorization of `ErrorType_System`, binary compatibility of these libnx calls on firmware 23.0.1, or successful rendering on hardware.

The libnx initialization source returns without opening applet services when its applet type is `AppletType_None`. The NS2JB source reviewed here does not identify its process using libnx or prove that this exact applet type applies to its `FS` execution path. Therefore the process category cannot be inferred from these sources alone.

## NRO and process-context distinction

A homebrew NRO and its NACP metadata do not, by themselves, make the program a regular application. The launch environment determines the process context. A separately compiled NRO is not interchangeable with the NSO payload used by NS2JB: they are different artifact formats and execute in different contexts.

The reviewed standalone demo was designed to request an application-type error dialog only after checking the process type reported by Horizon. A successful build and static inspection establish only that an artifact was produced and contains the expected code and message. They do not establish that it ran, that Horizon authorized the request, or that a system-owned dialog appeared. No console launch was performed for this review.

The API documentation also notes that error reporting affects the system error history. Any hardware verification must therefore be an explicitly authorized user action. No such action is part of this evidence review.

## Relationship to WebKit2JB and NS2JB

There is no demonstrated runtime integration between WebKit2JB, the NS2JB `FS` path, and the standalone homebrew demo. A browser page, an HTTP response from a PC, an NRO build, or native code executing in another process does not prove that WebKit can launch an application or request a system applet.

No applet-launch mechanism or call into the Error Applet was added to the NS2JB payload. Such an integration would require a documented and authorized Horizon entry point with the necessary process context; none is established by the reviewed source or public documentation.

## Evidence required for a hardware claim

A claim that Horizon displayed the requested text would require independent evidence that:

1. The text appeared in the system Error LibraryApplet, rather than in WebKit or a homebrew-rendered screen.
2. The caller process type and requested error category were identified from an authorized source.
3. The firmware and relevant software versions were recorded.
4. The result was observed on the console; a function return code or compiled artifact alone is insufficient.

No such hardware evidence is present in the reviewed artifacts.

## Conclusion

**Confirmed by public documentation:** the libnx error-applet APIs, UTF-8 message fields, the documented application-context restriction for `errorApplicationCreate`, and the Switch 2 listing of `LibraryAppletError` in Switchbrew.

**Confirmed in the reviewed local source:** NS2JB describes native execution in `FS`; the reviewed code does not call the error-applet wrappers. A separate homebrew NRO build is not evidence of execution on hardware.

**Unknown:** whether an ordinary application may use `ErrorType_System`, whether the NS2JB execution context has any relevant AM capability, and whether the APIs behave as documented on Switch 2 firmware 23.0.1.

**Result:** the system-UI path is not demonstrated for WebKit2JB or NS2JB. A build, JavaScript observation, or PC-side bridge response cannot establish native system-UI execution on the console.
