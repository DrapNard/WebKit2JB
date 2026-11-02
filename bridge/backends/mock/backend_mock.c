#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "../../src/core/internal.h"

static w2jb_status mock_request(const w2jb_request *request, w2jb_reply *reply, int fail) {
    size_t n;
    reply->simulated = 1;
    reply->native_process = 1;
    reply->switch_native_execution = 0;
    /* Keep discovery available when injecting a failure into operational calls. */
    if (fail && request->operation != W2JB_OP_CAPABILITIES) {
        snprintf(reply->result, sizeof(reply->result), "simulated backend failure");
        return W2JB_BACKEND_FAILURE;
    }
    switch (request->operation) {
        case W2JB_OP_CAPABILITIES:
            snprintf(reply->result, sizeof(reply->result), "simulated=1;diagnostic=1;echo=1;connectivity=1;ns2jb-status-probe=1;ns2jb-operations=0;memory=rwx-denied");
            return W2JB_OK;
        case W2JB_OP_DIAGNOSTIC:
            snprintf(reply->result, sizeof(reply->result), "mock diagnostic completed; no external actions");
            return W2JB_OK;
        case W2JB_OP_CONNECTIVITY:
            snprintf(reply->result, sizeof(reply->result), "in-process backend reachable");
            return W2JB_OK;
        case W2JB_OP_ECHO:
            n = request->payload_size < sizeof(reply->result) - 6 ? request->payload_size : sizeof(reply->result) - 6;
            memcpy(reply->result, "echo:", 5);
            if (n) memcpy(reply->result + 5, request->payload, n);
            reply->result[5 + n] = '\0';
            return W2JB_OK;
        default: return W2JB_UNSUPPORTED_OPERATION;
    }
}
static void *mock_alloc(size_t size) { return calloc(1, size); }
static void mock_free(void *ptr) { free(ptr); }
static const w2jb_backend_vtable vtable = {"mock", mock_request, mock_alloc, mock_free};
const w2jb_backend_vtable *w2jb_backend_mock(void) { return &vtable; }
