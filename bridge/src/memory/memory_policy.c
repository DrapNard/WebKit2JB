#include "internal.h"

_Static_assert(sizeof(w2jb_memory_policy_report) == 104u,
               "memory-policy ABI changed; increment memory-policy ABI version");
#include <string.h>

static const char constant_anchor[] = "w2jb-constant-anchor";
static volatile unsigned char mutable_anchor = 1u;

static void code_anchor(void) {
    /* Address-only probe: this function is never called by a memory policy request. */
}
static uint32_t encode_permissions(const w2jb_region_permissions *permissions) {
    return (permissions->readable ? W2JB_PERM_READ : 0u) |
           (permissions->writable ? W2JB_PERM_WRITE : 0u) |
           (permissions->executable ? W2JB_PERM_EXECUTE : 0u);
}

static void inspect_region(const void *address, size_t size,
                           w2jb_memory_region_report *report) {
    w2jb_region_permissions observed = {0, 0, 0};
    w2jb_status status;
    status = w2jb_bridge_inspect_self_address(address, size, &observed);
    if (status == W2JB_OK) {
        report->observed_permissions = encode_permissions(&observed);
        if (observed.writable && observed.executable) {
            report->verification = W2JB_VERIFY_FAIL;
        } else if (report->observed_permissions == report->expected_permissions) {
            report->verification = W2JB_VERIFY_PASS;
        } else {
            report->verification = W2JB_VERIFY_FAIL;
        }
    } else if (status == W2JB_CAPABILITY_UNAVAILABLE) {
        report->verification = W2JB_VERIFY_UNSUPPORTED;
    } else {
        report->verification = W2JB_VERIFY_UNVERIFIED;
    }
}

static uint32_t aggregate_verification(const w2jb_memory_policy_report *report) {
    uint32_t i;
    int has_unverified = 0;
    int has_unsupported = 0;
    for (i = 0; i < report->region_count; ++i) {
        switch ((w2jb_verification_state)report->regions[i].verification) {
            case W2JB_VERIFY_FAIL: return W2JB_VERIFY_FAIL;
            case W2JB_VERIFY_UNVERIFIED: has_unverified = 1; break;
            case W2JB_VERIFY_UNSUPPORTED: has_unsupported = 1; break;
            default: break;
        }
    }
    if (has_unverified) return W2JB_VERIFY_UNVERIFIED;
    if (has_unsupported) return W2JB_VERIFY_UNSUPPORTED;
    return W2JB_VERIFY_PASS;
}

w2jb_status w2jb_bridge_memory_policy_report(w2jb_bridge *bridge,
                                              w2jb_memory_policy_report *out) {
    volatile unsigned char stack_anchor = 0u;
    void *heap_anchor = NULL;
    union { void (*function)(void); const void *object; } code_address;
    uint32_t i;
    if (bridge == NULL || !bridge->initialized) return W2JB_NOT_INITIALIZED;
    if (out == NULL || out->struct_size < sizeof(*out)) return W2JB_INVALID_ARGUMENT;

    memset(out, 0, sizeof(*out));
    out->struct_size = (uint32_t)sizeof(*out);
    out->abi_version = W2JB_MEMORY_POLICY_ABI_VERSION;
    out->backend = (uint32_t)bridge->kind;
    out->region_count = W2JB_MEMORY_POLICY_REGION_COUNT;
    out->writable_executable_regions = 0u;

    code_address.function = code_anchor;
    out->regions[0] = (w2jb_memory_region_report){W2JB_MEMORY_REGION_CODE,
        W2JB_PERM_READ | W2JB_PERM_EXECUTE, 0u, W2JB_VERIFY_UNVERIFIED};
    out->regions[1] = (w2jb_memory_region_report){W2JB_MEMORY_REGION_CONSTANT,
        W2JB_PERM_READ, 0u, W2JB_VERIFY_UNVERIFIED};
    out->regions[2] = (w2jb_memory_region_report){W2JB_MEMORY_REGION_MUTABLE,
        W2JB_PERM_READ | W2JB_PERM_WRITE, 0u, W2JB_VERIFY_UNVERIFIED};
    out->regions[3] = (w2jb_memory_region_report){W2JB_MEMORY_REGION_HEAP,
        W2JB_PERM_READ | W2JB_PERM_WRITE, 0u, W2JB_VERIFY_UNVERIFIED};
    out->regions[4] = (w2jb_memory_region_report){W2JB_MEMORY_REGION_STACK,
        W2JB_PERM_READ | W2JB_PERM_WRITE, 0u, W2JB_VERIFY_UNVERIFIED};

    inspect_region(code_address.object, 1u, &out->regions[0]);
    inspect_region(constant_anchor, sizeof(constant_anchor), &out->regions[1]);
    inspect_region((const void *)&mutable_anchor, sizeof(mutable_anchor), &out->regions[2]);
    if (w2jb_bridge_buffer_alloc(bridge, 32u, &heap_anchor) == W2JB_OK) {
        inspect_region(heap_anchor, 32u, &out->regions[3]);
        w2jb_bridge_buffer_free(bridge, heap_anchor);
    } else {
        out->regions[3].verification = W2JB_VERIFY_UNVERIFIED;
    }
    inspect_region((const void *)&stack_anchor, sizeof(stack_anchor), &out->regions[4]);

    out->overall = aggregate_verification(out);
    for (i = 0; i < out->region_count; ++i) {
        if ((out->regions[i].observed_permissions &
             (W2JB_PERM_WRITE | W2JB_PERM_EXECUTE)) ==
            (W2JB_PERM_WRITE | W2JB_PERM_EXECUTE)) {
            ++out->writable_executable_regions;
            out->overall = W2JB_VERIFY_FAIL;
        }
    }
    return W2JB_OK;
}
