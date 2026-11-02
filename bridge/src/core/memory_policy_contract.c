#include "webkit2jb_bridge.h"

w2jb_status w2jb_bridge_check_region_policy(w2jb_region_kind region, unsigned permissions) {
    const unsigned known = W2JB_PERM_READ | W2JB_PERM_WRITE | W2JB_PERM_EXECUTE;
    if ((permissions & ~known) != 0 || (permissions & W2JB_PERM_READ) == 0)
        return W2JB_INVALID_ARGUMENT;
    if ((permissions & (W2JB_PERM_WRITE | W2JB_PERM_EXECUTE)) ==
        (W2JB_PERM_WRITE | W2JB_PERM_EXECUTE)) return W2JB_MEMORY_POLICY_DENIED;
    if (region == W2JB_REGION_CODE) {
        if (permissions != (W2JB_PERM_READ | W2JB_PERM_EXECUTE)) return W2JB_MEMORY_POLICY_DENIED;
        return W2JB_CAPABILITY_UNAVAILABLE; /* code pages are linker/loader-owned */
    }
    if (region == W2JB_REGION_MUTABLE_DATA)
        return permissions == (W2JB_PERM_READ | W2JB_PERM_WRITE) ? W2JB_OK : W2JB_MEMORY_POLICY_DENIED;
    if (region == W2JB_REGION_CONSTANT_DATA)
        return permissions == W2JB_PERM_READ ? W2JB_OK : W2JB_MEMORY_POLICY_DENIED;
    return W2JB_INVALID_ARGUMENT;
}

w2jb_memory_policy w2jb_bridge_get_memory_policy(void) {
    w2jb_memory_policy policy;
    policy.writable_executable_allocations = 0;
#ifdef W2JB_BUILD_HORIZON
    policy.code_data_permissions_separate = 0;
    policy.effective_permissions_verifiable = 0;
    policy.permission_verification = "not exposed by this backend; executable allocation is unavailable";
#else
    policy.code_data_permissions_separate = 1;
    policy.effective_permissions_verifiable = 1;
    policy.permission_verification = "Linux /proc/self/maps probe available for owned buffers and static segments";
#endif
    return policy;
}
