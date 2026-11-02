#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "internal.h"

void w2jb_log(w2jb_bridge *bridge, int level, const char *message) {
    if (bridge != NULL && bridge->logger != NULL) bridge->logger(bridge->logger_context, level, message);
}

const char *w2jb_status_name(w2jb_status status) {
    static const char *names[] = {"OK", "INVALID_ARGUMENT", "NOT_INITIALIZED",
        "PROTOCOL_UNSUPPORTED", "MESSAGE_TOO_LARGE", "INVALID_REQUEST_ID",
        "UNSUPPORTED_OPERATION", "BACKEND_FAILURE", "CAPABILITY_UNAVAILABLE",
        "MEMORY_POLICY_DENIED"};
    if ((unsigned)status >= sizeof(names) / sizeof(names[0])) return "UNKNOWN";
    return names[status];
}

const char *w2jb_backend_name(w2jb_backend_kind backend) {
    switch (backend) {
        case W2JB_BACKEND_MOCK: return "mock";
        case W2JB_BACKEND_LINUX: return "linux-local";
        case W2JB_BACKEND_HORIZON_HOMEBREW: return "horizon-homebrew";
        default: return "unknown";
    }
}

w2jb_status w2jb_bridge_init(const w2jb_config *config, w2jb_bridge **out_bridge) {
    w2jb_bridge *bridge;
    const w2jb_backend_vtable *backend = NULL;
    if (config == NULL || out_bridge == NULL || config->struct_size < sizeof(w2jb_config))
        return W2JB_INVALID_ARGUMENT;
    *out_bridge = NULL;
    switch (config->backend) {
        case W2JB_BACKEND_MOCK: backend = w2jb_backend_mock(); break;
        case W2JB_BACKEND_LINUX:
#ifdef W2JB_BUILD_HORIZON
            return W2JB_CAPABILITY_UNAVAILABLE;
#else
            backend = w2jb_backend_linux();
#endif
            break;
        case W2JB_BACKEND_HORIZON_HOMEBREW:
#ifdef W2JB_BUILD_HORIZON
            backend = w2jb_backend_horizon();
#else
            return W2JB_CAPABILITY_UNAVAILABLE;
#endif
            break;
        default: return W2JB_INVALID_ARGUMENT;
    }
    bridge = (w2jb_bridge *)calloc(1, sizeof(*bridge));
    if (bridge == NULL) return W2JB_BACKEND_FAILURE;
    bridge->initialized = 1;
    bridge->kind = config->backend;
    bridge->timeout_ms = config->timeout_ms == 0 ? 1500u : config->timeout_ms;
    bridge->mock_fail_requests = config->mock_fail_requests != 0;
    bridge->logger = config->logger;
    bridge->logger_context = config->logger_context;
    bridge->backend = backend;
    *out_bridge = bridge;
    w2jb_log(bridge, 1, "bridge initialized");
    return W2JB_OK;
}

void w2jb_bridge_shutdown(w2jb_bridge *bridge) {
    if (bridge == NULL) return;
    w2jb_log(bridge, 1, "bridge stopped");
    bridge->initialized = 0;
    free(bridge);
}

w2jb_status w2jb_bridge_request(w2jb_bridge *bridge, const w2jb_request *request, w2jb_reply *reply) {
    return w2jb_bridge_relay_request(bridge, request, reply);
}

w2jb_status w2jb_bridge_detect_capabilities(w2jb_bridge *bridge, w2jb_reply *reply) {
    const w2jb_request request = {W2JB_PROTOCOL_VERSION, "capabilities", W2JB_OP_CAPABILITIES, NULL, 0};
    return w2jb_bridge_request(bridge, &request, reply);
}

w2jb_status w2jb_bridge_buffer_alloc(w2jb_bridge *bridge, size_t size, void **out_buffer) {
    if (bridge == NULL || !bridge->initialized) return W2JB_NOT_INITIALIZED;
    if (out_buffer == NULL || size == 0 || size > W2JB_MAX_MESSAGE) return W2JB_INVALID_ARGUMENT;
    *out_buffer = bridge->backend->allocate(size);
    return *out_buffer == NULL ? W2JB_BACKEND_FAILURE : W2JB_OK;
}

void w2jb_bridge_buffer_free(w2jb_bridge *bridge, void *buffer) {
    if (bridge != NULL && bridge->initialized && buffer != NULL) bridge->backend->deallocate(buffer);
}
