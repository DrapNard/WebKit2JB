# Memory policy and W^X

The bridge never allocates executable memory. Its only dynamic-memory API returns zeroed data owned by the current bridge process. Requests for writable-and-executable permissions are rejected as MEMORY_POLICY_DENIED; requests to allocate code pages are rejected as CAPABILITY_UNAVAILABLE, even when the caller asks for RX only. Code pages belong to the linker/loader. Constants are ordinary const objects. The bridge does not call mmap(PROT_EXEC), mprotect, Horizon SVC permission-changing APIs, or any remote-process memory API.

| Platform | Mutable data | Constants/code | Effective-permission inspection | Verified here |
|---|---|---|---|---|
| Linux x86-64 | calloc owned by bridge; expected RW, never X | linker/loader-owned; ELF load segments and stack are checked for RWX | /proc/self/maps, current process only | Yes: test checks RW data, R constant, RX function, and ELF program headers |
| Linux ARM64 | Same C ownership model | toolchain/linker owns executable segments | /proc/self/maps is the intended inspection path | Cross-compiled static archive and freestanding ABI/protocol/W^X smoke under QEMU; the full backend and `/proc/self/maps` path were not executed under ARM64 |
| Horizon homebrew | libnx process heap via calloc, owned by the homebrew process | linker/loader-owned; no code-page allocation in this bridge | Not implemented; this backend reports CAPABILITY_UNAVAILABLE for permission inspection | NRO compiled; ELF PT_LOADs are RX/R/RW with no RWX segment. The ELF has no GNU_STACK header, so its presence does not verify runtime stack permissions. No console test |

The Horizon backend does not infer that the homebrew process has permission to create executable regions. It reports only the active HOS version through the public libnx hosversionGet() utility, when available. This says nothing about WifiWebAuthApplet or any other process.

The Linux permission check reads /proc/self/maps and does not open process handles or inspect another process. It checks that the full requested address range is contained in one mapping. An unavailable or unmapped range returns CAPABILITY_UNAVAILABLE.

`w2jb_bridge_memory_policy_report()` samples one address from each bridge-owned
region class (RX function, R constant, RW mutable global, bridge heap buffer,
and local stack byte). Its result states are `PASS`, `FAIL`, `UNVERIFIED`, and
`UNSUPPORTED`. This is a sample of the current bridge process, not a scan of
every mapping or an observation of WebKitWebProcess. The additive relay
operation `memory-policy` is available in protocol v1 and is surfaced in the
portal. The Python simulator returns `UNSUPPORTED`; the Horizon backend also
returns `UNSUPPORTED` because no verified current-process map query is
implemented. No mapping permission is changed to test the checker.

The legacy `w2jb_bridge_get_memory_policy()` remains for ABI compatibility and
describes backend support only. It is not a runtime result. Use the explicit
report operation for observed permissions.

Run the host check with:

    cmake -S bridge -B bridge/build
    cmake --build bridge/build
    ctest --test-dir bridge/build --output-on-failure
