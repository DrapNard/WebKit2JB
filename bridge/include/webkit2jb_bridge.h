#ifndef WEBKIT2JB_BRIDGE_H
#define WEBKIT2JB_BRIDGE_H

#include <stddef.h>
#include <stdint.h>
#include "w2jb/memory_policy.h"

#ifdef __cplusplus
extern "C" {
#endif

#define W2JB_PROTOCOL_VERSION 1u
#define W2JB_MAX_REQUEST_ID 64u
#define W2JB_MAX_PAYLOAD 1024u
#define W2JB_MAX_MESSAGE 4096u
#define W2JB_BACKEND_ID_MAX 32u
#define W2JB_REPLY_TEXT_MAX 2048u
#define W2JB_RELAY_ABI_VERSION 1u

typedef struct w2jb_bridge w2jb_bridge;

typedef enum {
    W2JB_OK = 0,
    W2JB_INVALID_ARGUMENT = 1,
    W2JB_NOT_INITIALIZED = 2,
    W2JB_PROTOCOL_UNSUPPORTED = 3,
    W2JB_MESSAGE_TOO_LARGE = 4,
    W2JB_INVALID_REQUEST_ID = 5,
    W2JB_UNSUPPORTED_OPERATION = 6,
    W2JB_BACKEND_FAILURE = 7,
    W2JB_CAPABILITY_UNAVAILABLE = 8,
    W2JB_MEMORY_POLICY_DENIED = 9
} w2jb_status;

typedef enum {
    W2JB_BACKEND_MOCK = 1,
    W2JB_BACKEND_LINUX = 2,
    W2JB_BACKEND_HORIZON_HOMEBREW = 3
} w2jb_backend_kind;

typedef enum {
    W2JB_OP_CAPABILITIES = 1,
    W2JB_OP_DIAGNOSTIC = 2,
    W2JB_OP_ECHO = 3,
    W2JB_OP_CONNECTIVITY = 4,
    W2JB_OP_NS2JB_COMPATIBILITY = 5,
    W2JB_OP_MEMORY_POLICY = 6
} w2jb_operation;

enum {
    W2JB_RELAY_CAP_CAPABILITIES = 1u << 0,
    W2JB_RELAY_CAP_DIAGNOSTIC = 1u << 1,
    W2JB_RELAY_CAP_ECHO = 1u << 2,
    W2JB_RELAY_CAP_CONNECTIVITY = 1u << 3,
    W2JB_RELAY_CAP_NS2JB_STATUS = 1u << 4,
    W2JB_RELAY_CAP_MEMORY_POLICY = 1u << 5
};

typedef enum {
    W2JB_REGION_CODE = 1,
    W2JB_REGION_MUTABLE_DATA = 2,
    W2JB_REGION_CONSTANT_DATA = 3
} w2jb_region_kind;

enum {
    W2JB_PERM_READ = 1u,
    W2JB_PERM_WRITE = 2u,
    W2JB_PERM_EXECUTE = 4u
};

typedef void (*w2jb_log_fn)(void *context, int level, const char *message);

typedef struct {
    uint32_t struct_size;
    w2jb_backend_kind backend;
    uint32_t timeout_ms;
    int mock_fail_requests;
    w2jb_log_fn logger;
    void *logger_context;
} w2jb_config;

typedef struct {
    uint32_t protocol_version;
    const char *request_id;
    w2jb_operation operation;
    const uint8_t *payload;
    size_t payload_size;
} w2jb_request;

typedef struct {
    uint32_t protocol_version;
    char request_id[W2JB_MAX_REQUEST_ID + 1u];
    char backend_id[W2JB_BACKEND_ID_MAX];
    w2jb_status status;
    int simulated;
    int native_process; /* Operation ran in this native process, not a remote process. */
    int switch_native_execution;
    char result[W2JB_REPLY_TEXT_MAX];
} w2jb_reply;

/* Stable, process-local relay discovery. NS2JB_STATUS only reports availability. */
typedef struct {
    uint32_t struct_size;
    uint32_t abi_version;
    uint32_t protocol_version;
    w2jb_backend_kind backend;
    uint32_t capability_flags;
    int simulated;
    int switch_native_execution;
} w2jb_relay_capabilities;

typedef struct {
    int writable_executable_allocations;
    int code_data_permissions_separate;
    int effective_permissions_verifiable;
    const char *permission_verification;
} w2jb_memory_policy;

typedef struct {
    int readable;
    int writable;
    int executable;
} w2jb_region_permissions;

w2jb_status w2jb_bridge_init(const w2jb_config *config, w2jb_bridge **out_bridge);
void w2jb_bridge_shutdown(w2jb_bridge *bridge);
w2jb_status w2jb_bridge_detect_capabilities(w2jb_bridge *bridge, w2jb_reply *reply);
w2jb_status w2jb_bridge_request(w2jb_bridge *bridge, const w2jb_request *request, w2jb_reply *reply);
/* Explicit native relay API; all operations remain allow-listed and process-local. */
w2jb_status w2jb_bridge_relay_capabilities(w2jb_bridge *bridge, w2jb_relay_capabilities *out_capabilities);
w2jb_status w2jb_bridge_relay_request(w2jb_bridge *bridge, const w2jb_request *request, w2jb_reply *reply);
const char *w2jb_status_name(w2jb_status status);
const char *w2jb_backend_name(w2jb_backend_kind backend);

/* Only process-owned, non-executable data buffers can be allocated here. */
w2jb_status w2jb_bridge_buffer_alloc(w2jb_bridge *bridge, size_t size, void **out_buffer);
void w2jb_bridge_buffer_free(w2jb_bridge *bridge, void *buffer);
w2jb_status w2jb_bridge_check_region_policy(w2jb_region_kind region, unsigned permissions);
/* Legacy capability summary; use w2jb_bridge_memory_policy_report for observations. */
w2jb_memory_policy w2jb_bridge_get_memory_policy(void);
w2jb_status w2jb_bridge_memory_policy_report(w2jb_bridge *bridge, w2jb_memory_policy_report *out_report);
/* Inspects an address in this process only; no remote-process handles are accepted. */
w2jb_status w2jb_bridge_inspect_self_address(const void *address, size_t size, w2jb_region_permissions *out_permissions);

#ifdef __cplusplus
}
#endif
#endif
