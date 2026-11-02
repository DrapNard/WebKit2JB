#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <switch.h>
#include "../../src/core/internal.h"

static w2jb_status horizon_request(const w2jb_request *request, w2jb_reply *reply, int unused) {
    u32 version;
    (void)unused;
    reply->simulated = 0;
    reply->native_process = 1;
    reply->switch_native_execution = 0;
    switch (request->operation) {
        case W2JB_OP_CAPABILITIES:
            version = hosversionGet();
            if (version == 0) {
                snprintf(reply->result, sizeof(reply->result),
                         "backend=horizon-homebrew;hos=unknown;owned-data-memory=1;exec-allocation=0;network-bridge=0;ns2jb-status-probe=1;ns2jb-operations=0");
            } else {
                snprintf(reply->result, sizeof(reply->result),
                         "backend=horizon-homebrew;hos=%u.%u.%u;owned-data-memory=1;exec-allocation=0;network-bridge=0;ns2jb-status-probe=1;ns2jb-operations=0",
                         HOSVER_MAJOR(version), HOSVER_MINOR(version), HOSVER_MICRO(version));
            }
            return W2JB_OK;
        case W2JB_OP_DIAGNOSTIC:
            snprintf(reply->result, sizeof(reply->result),
                     "libnx homebrew process responded; RWX denied; effective permissions not inspected");
            return W2JB_OK;
        case W2JB_OP_ECHO:
            if (request->payload_size >= sizeof(reply->result) - 6) return W2JB_MESSAGE_TOO_LARGE;
            memcpy(reply->result, "echo:", 5);
            if (request->payload_size) memcpy(reply->result + 5, request->payload, request->payload_size);
            reply->result[5 + request->payload_size] = '\0';
            return W2JB_OK;
        case W2JB_OP_CONNECTIVITY:
            snprintf(reply->result, sizeof(reply->result), "network transport not implemented by Horizon backend");
            return W2JB_CAPABILITY_UNAVAILABLE;
        default: return W2JB_UNSUPPORTED_OPERATION;
    }
}
static void *horizon_alloc(size_t size) { return calloc(1, size); }
static void horizon_free(void *ptr) { free(ptr); }
static const w2jb_backend_vtable vtable = {"horizon-homebrew", horizon_request, horizon_alloc, horizon_free};
const w2jb_backend_vtable *w2jb_backend_horizon(void) { return &vtable; }
