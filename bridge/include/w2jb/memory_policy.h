#ifndef W2JB_MEMORY_POLICY_H
#define W2JB_MEMORY_POLICY_H

/* Additive, read-only W^X permission report ABI. No permission changes occur. */
#include <stdint.h>

#define W2JB_MEMORY_POLICY_ABI_VERSION 1u
#define W2JB_MEMORY_POLICY_REGION_COUNT 5u

typedef enum {
    W2JB_VERIFY_PASS = 1,
    W2JB_VERIFY_FAIL = 2,
    W2JB_VERIFY_UNVERIFIED = 3,
    W2JB_VERIFY_UNSUPPORTED = 4
} w2jb_verification_state;

typedef enum {
    W2JB_MEMORY_REGION_CODE = 1,
    W2JB_MEMORY_REGION_CONSTANT = 2,
    W2JB_MEMORY_REGION_MUTABLE = 3,
    W2JB_MEMORY_REGION_HEAP = 4,
    W2JB_MEMORY_REGION_STACK = 5
} w2jb_memory_region_kind;

typedef struct {
    uint32_t region;
    uint32_t expected_permissions;
    uint32_t observed_permissions;
    uint32_t verification;
} w2jb_memory_region_report;

typedef struct {
    uint32_t struct_size;
    uint32_t abi_version;
    uint32_t backend;
    uint32_t overall;
    uint32_t writable_executable_regions;
    uint32_t region_count;
    w2jb_memory_region_report regions[W2JB_MEMORY_POLICY_REGION_COUNT];
} w2jb_memory_policy_report;

#endif
