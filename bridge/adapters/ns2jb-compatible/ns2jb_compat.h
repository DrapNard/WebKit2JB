#ifndef W2JB_NS2JB_COMPAT_H
#define W2JB_NS2JB_COMPAT_H
#include "webkit2jb_bridge.h"
typedef struct {
    uint32_t adapter_version;
    int data_protocol_compatible;
    int upstream_ns2jb_ipc_available;
    int privileged_operations_available;
    w2jb_status unavailable_status;
    const char *note;
} w2jb_ns2jb_compat_info;

#define W2JB_NS2JB_SOURCE_COMMIT "95f5525089273c5fce0b95047f3600f8442e96ae"
#define W2JB_NS2JB_COMPAT_INFO_V2_SIZE 256u

enum {
    W2JB_NS2JB_LICENSE_CONFIRMED = 1u << 0,
    W2JB_NS2JB_DATA_PROTOCOL_VERIFIED = 1u << 1,
    W2JB_NS2JB_HORIZON_SERVICE_AVAILABLE = 1u << 2,
    W2JB_NS2JB_PRIVILEGED_OPERATIONS_AVAILABLE = 1u << 3
};

/* Read-only capability description. Zero flags means no upstream contract is usable here. */
typedef struct {
    uint32_t struct_size;
    uint32_t adapter_version;
    uint32_t capability_flags;
    w2jb_status status;
    char source_commit[41];
    char note[W2JB_NS2JB_COMPAT_INFO_V2_SIZE - 57u];
} w2jb_ns2jb_compat_info_v2;

w2jb_status w2jb_ns2jb_compat_probe(w2jb_bridge *bridge, w2jb_ns2jb_compat_info *out_info);
w2jb_status w2jb_ns2jb_compat_probe_v2(w2jb_bridge *bridge,
                                       w2jb_ns2jb_compat_info_v2 *out_info);
#endif
