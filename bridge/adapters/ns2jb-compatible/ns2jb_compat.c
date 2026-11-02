#include "ns2jb_compat.h"
#include <string.h>

_Static_assert(sizeof(w2jb_ns2jb_compat_info_v2) == W2JB_NS2JB_COMPAT_INFO_V2_SIZE,
               "NS2JB compatibility v2 ABI size changed");

static const char NS2JB_UNAVAILABLE_NOTE[] =
    "No license-cleared, platform-neutral NS2JB contract was verified; "
    "Horizon process-control interfaces are unavailable in this bridge.";

/* The upstream source has no verified, license-cleared neutral data interface. */
w2jb_status w2jb_ns2jb_compat_probe_v2(w2jb_bridge *bridge,
                                       w2jb_ns2jb_compat_info_v2 *out_info) {
    if (bridge == 0 || out_info == 0) return W2JB_INVALID_ARGUMENT;
    memset(out_info, 0, sizeof(*out_info));
    out_info->struct_size = (uint32_t)sizeof(*out_info);
    out_info->adapter_version = 2;
    out_info->capability_flags = 0;
    out_info->status = W2JB_CAPABILITY_UNAVAILABLE;
    memcpy(out_info->source_commit, W2JB_NS2JB_SOURCE_COMMIT,
           sizeof(W2JB_NS2JB_SOURCE_COMMIT));
    memcpy(out_info->note, NS2JB_UNAVAILABLE_NOTE, sizeof(NS2JB_UNAVAILABLE_NOTE));
    return W2JB_CAPABILITY_UNAVAILABLE;
}

/* V1 remains ABI-stable and delegates its availability result to the v2 description. */
w2jb_status w2jb_ns2jb_compat_probe(w2jb_bridge *bridge, w2jb_ns2jb_compat_info *out_info) {
    w2jb_ns2jb_compat_info_v2 v2;
    w2jb_status status;
    if (bridge == 0 || out_info == 0) return W2JB_INVALID_ARGUMENT;
    status = w2jb_ns2jb_compat_probe_v2(bridge, &v2);
    out_info->adapter_version = 1;
    out_info->data_protocol_compatible = 0;
    out_info->upstream_ns2jb_ipc_available = 0;
    out_info->privileged_operations_available = 0;
    out_info->unavailable_status = status;
    out_info->note = NS2JB_UNAVAILABLE_NOTE;
    return status;
}
