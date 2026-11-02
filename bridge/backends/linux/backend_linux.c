#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "../../src/core/internal.h"

static w2jb_status linux_request(const w2jb_request *request, w2jb_reply *reply, int unused) {
    size_t n;
    (void)unused;
    reply->simulated = 0;
    reply->native_process = 1;
    reply->switch_native_execution = 0;
    switch (request->operation) {
        case W2JB_OP_CAPABILITIES:
            snprintf(reply->result, sizeof(reply->result), "backend=linux-local;diagnostic=1;echo=1;connectivity=1;ns2jb-status-probe=1;ns2jb-operations=0;owned-data-memory=1;exec-allocation=0");
            return W2JB_OK;
        case W2JB_OP_DIAGNOSTIC:
            snprintf(reply->result, sizeof(reply->result), "Linux bridge process responded; memory policy RWX denied");
            return W2JB_OK;
        case W2JB_OP_CONNECTIVITY:
            snprintf(reply->result, sizeof(reply->result), "in-process Linux backend reachable");
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
static void *linux_alloc(size_t size) { return calloc(1, size); }
static void linux_free(void *ptr) { free(ptr); }
static const w2jb_backend_vtable vtable = {"linux-local", linux_request, linux_alloc, linux_free};
const w2jb_backend_vtable *w2jb_backend_linux(void) { return &vtable; }
