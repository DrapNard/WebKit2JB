#include <stddef.h>
#include "webkit2jb_bridge.h"
#include "ns2jb_compat.h"
#include "internal.h"

_Static_assert(sizeof(void *) == 8, "AArch64 LP64 pointer size");
_Static_assert(sizeof(w2jb_config) == 32, "w2jb_config ABI size");
_Static_assert(offsetof(w2jb_config, logger) == 16, "w2jb_config logger offset");
_Static_assert(sizeof(w2jb_request) == 40, "w2jb_request ABI size");
_Static_assert(offsetof(w2jb_request, payload) == 24, "w2jb_request payload offset");
_Static_assert(sizeof(w2jb_reply) == 2168, "w2jb_reply ABI size");
_Static_assert(sizeof(w2jb_memory_policy) == 24, "w2jb_memory_policy ABI size");
_Static_assert(sizeof(w2jb_ns2jb_compat_info) == 32, "NS2JB v1 ABI size");
_Static_assert(offsetof(w2jb_ns2jb_compat_info, note) == 24, "NS2JB v1 note offset");
_Static_assert(sizeof(w2jb_ns2jb_compat_info_v2) == 256, "NS2JB v2 ABI size");
_Static_assert(offsetof(w2jb_ns2jb_compat_info_v2, source_commit) == 16, "NS2JB v2 commit offset");
_Static_assert(offsetof(w2jb_ns2jb_compat_info_v2, note) == 57, "NS2JB v2 note offset");
_Static_assert(sizeof(w2jb_relay_capabilities) == 28, "relay ABI v1 size");
_Static_assert(offsetof(w2jb_relay_capabilities, capability_flags) == 16, "relay ABI v1 capability offset");
_Static_assert(sizeof(w2jb_memory_policy_report) == 104, "memory policy report ABI v1 size");

int w2jb_aarch64_abi_smoke(void) {
    w2jb_request good;
    w2jb_request old_version;
    w2jb_request ns2jb_compatibility;
    w2jb_relay_capabilities relay = {sizeof(relay), 0, 0, W2JB_BACKEND_LINUX, 0, 0, 0};
    good.protocol_version = W2JB_PROTOCOL_VERSION;
    good.request_id = "arm64_01";
    good.operation = W2JB_OP_DIAGNOSTIC;
    good.payload = NULL;
    good.payload_size = 0;
    old_version.protocol_version = 9;
    old_version.request_id = "arm64_02";
    old_version.operation = W2JB_OP_DIAGNOSTIC;
    old_version.payload = NULL;
    old_version.payload_size = 0;
    ns2jb_compatibility.protocol_version = W2JB_PROTOCOL_VERSION;
    ns2jb_compatibility.request_id = "arm64_ns2jb_01";
    ns2jb_compatibility.operation = W2JB_OP_NS2JB_COMPATIBILITY;
    ns2jb_compatibility.payload = NULL;
    ns2jb_compatibility.payload_size = 0;
    if (w2jb_validate_request(&good) != W2JB_OK) return 11;
    if (w2jb_validate_request(&old_version) != W2JB_PROTOCOL_UNSUPPORTED) return 12;
    if (w2jb_validate_request(&ns2jb_compatibility) != W2JB_OK) return 15;
    if (relay.struct_size != sizeof(relay) || W2JB_RELAY_ABI_VERSION != 1u) return 16;
    if (w2jb_bridge_check_region_policy(W2JB_REGION_MUTABLE_DATA,
        W2JB_PERM_READ | W2JB_PERM_WRITE | W2JB_PERM_EXECUTE) != W2JB_MEMORY_POLICY_DENIED) return 13;
    if (w2jb_bridge_check_region_policy(W2JB_REGION_CODE,
        W2JB_PERM_READ | W2JB_PERM_EXECUTE) != W2JB_CAPABILITY_UNAVAILABLE) return 14;
    return 0;
}
