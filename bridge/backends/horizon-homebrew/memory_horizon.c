#include "webkit2jb_bridge.h"

w2jb_status w2jb_bridge_inspect_self_address(const void *address, size_t size, w2jb_region_permissions *out) {
    if (address == 0 || size == 0 || out == 0) return W2JB_INVALID_ARGUMENT;
    out->readable = 0;
    out->writable = 0;
    out->executable = 0;
    /* This backend does not query memory maps or request executable rights. */
    return W2JB_CAPABILITY_UNAVAILABLE;
}
