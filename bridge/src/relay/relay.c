#include <stdio.h>
#include <string.h>
#include "internal.h"
#include "ns2jb_compat.h"

static const char *verification_name(uint32_t state) {
    switch ((w2jb_verification_state)state) {
        case W2JB_VERIFY_PASS: return "PASS";
        case W2JB_VERIFY_FAIL: return "FAIL";
        case W2JB_VERIFY_UNVERIFIED: return "UNVERIFIED";
        case W2JB_VERIFY_UNSUPPORTED: return "UNSUPPORTED";
        default: return "UNKNOWN";
    }
}

static const char *region_name(uint32_t region) {
    switch ((w2jb_memory_region_kind)region) {
        case W2JB_MEMORY_REGION_CODE: return "code";
        case W2JB_MEMORY_REGION_CONSTANT: return "constant";
        case W2JB_MEMORY_REGION_MUTABLE: return "mutable";
        case W2JB_MEMORY_REGION_HEAP: return "heap";
        case W2JB_MEMORY_REGION_STACK: return "stack";
        default: return "unknown";
    }
}

static const char *permissions_name(uint32_t permissions) {
    switch (permissions) {
        case 0: return "---";
        case W2JB_PERM_READ: return "r--";
        case W2JB_PERM_READ | W2JB_PERM_WRITE: return "rw-";
        case W2JB_PERM_READ | W2JB_PERM_EXECUTE: return "r-x";
        case W2JB_PERM_WRITE: return "-w-";
        case W2JB_PERM_EXECUTE: return "--x";
        case W2JB_PERM_WRITE | W2JB_PERM_EXECUTE: return "-wx";
        case W2JB_PERM_READ | W2JB_PERM_WRITE | W2JB_PERM_EXECUTE: return "rwx";
        default: return "---";
    }
}

_Static_assert(sizeof(w2jb_relay_capabilities) == 28u,
               "relay capability ABI changed; increment relay ABI version");

w2jb_status w2jb_bridge_relay_capabilities(w2jb_bridge *bridge,
                                           w2jb_relay_capabilities *out) {
    if (bridge == NULL || !bridge->initialized) return W2JB_NOT_INITIALIZED;
    if (out == NULL || out->struct_size < sizeof(*out)) return W2JB_INVALID_ARGUMENT;
    out->struct_size = (uint32_t)sizeof(*out);
    out->abi_version = W2JB_RELAY_ABI_VERSION;
    out->protocol_version = W2JB_PROTOCOL_VERSION;
    out->backend = bridge->kind;
    out->capability_flags = W2JB_RELAY_CAP_CAPABILITIES |
                            W2JB_RELAY_CAP_DIAGNOSTIC |
                            W2JB_RELAY_CAP_ECHO |
                            W2JB_RELAY_CAP_NS2JB_STATUS |
                            W2JB_RELAY_CAP_MEMORY_POLICY;
    if (bridge->kind != W2JB_BACKEND_HORIZON_HOMEBREW)
        out->capability_flags |= W2JB_RELAY_CAP_CONNECTIVITY;
    out->simulated = bridge->kind == W2JB_BACKEND_MOCK;
    out->switch_native_execution = 0;
    return W2JB_OK;
}

w2jb_status w2jb_bridge_relay_request(w2jb_bridge *bridge,
                                      const w2jb_request *request,
                                      w2jb_reply *reply) {
    w2jb_status status;
    if (bridge == NULL || !bridge->initialized) return W2JB_NOT_INITIALIZED;
    if (reply == NULL) return W2JB_INVALID_ARGUMENT;
    memset(reply, 0, sizeof(*reply));
    reply->protocol_version = W2JB_PROTOCOL_VERSION;
    status = w2jb_validate_request(request);
    if (status != W2JB_OK) {
        reply->status = status;
        return status;
    }
    memcpy(reply->request_id, request->request_id, strlen(request->request_id) + 1u);
    snprintf(reply->backend_id, sizeof(reply->backend_id), "%s", bridge->backend->name);
    if (request->operation == W2JB_OP_NS2JB_COMPATIBILITY) {
        w2jb_ns2jb_compat_info_v2 info;
        status = w2jb_ns2jb_compat_probe_v2(bridge, &info);
        if (status != W2JB_CAPABILITY_UNAVAILABLE) {
            reply->status = status;
            return status;
        }
        reply->simulated = bridge->kind == W2JB_BACKEND_MOCK;
        reply->native_process = 1;
        reply->switch_native_execution = 0;
        snprintf(reply->result, sizeof(reply->result),
                 "{\"adapterVersion\":%u,\"sourceCommit\":\"%s\","
                 "\"capabilityFlags\":%u,\"status\":\"%s\","
                 "\"licenseConfirmed\":false,\"dataProtocolVerified\":false,"
                 "\"horizonServiceAvailable\":false,"
                 "\"privilegedOperationsAvailable\":false,\"note\":\"%s\"}",
                 info.adapter_version, info.source_commit, info.capability_flags,
                 w2jb_status_name(info.status), info.note);
        reply->status = W2JB_OK;
        w2jb_log(bridge, 1, "NS2JB compatibility status reported; no NS2JB operation invoked");
        return W2JB_OK;
    }
    if (request->operation == W2JB_OP_MEMORY_POLICY) {
        w2jb_memory_policy_report report;
        size_t used;
        uint32_t i;
        memset(&report, 0, sizeof(report));
        report.struct_size = (uint32_t)sizeof(report);
        status = w2jb_bridge_memory_policy_report(bridge, &report);
        if (status != W2JB_OK) {
            reply->status = status;
            return status;
        }
        {
            int prefix = snprintf(reply->result, sizeof(reply->result),
            "{\"abiVersion\":%u,\"backend\":\"%s\",\"overall\":\"%s\","
            "\"writableExecutableRegions\":%u,\"regions\":[",
            report.abi_version, w2jb_backend_name((w2jb_backend_kind)report.backend),
            verification_name(report.overall), report.writable_executable_regions);
            if (prefix < 0 || (size_t)prefix >= sizeof(reply->result)) {
                reply->status = W2JB_BACKEND_FAILURE;
                return W2JB_BACKEND_FAILURE;
            }
            used = (size_t)prefix;
        }
        for (i = 0; i < report.region_count && i < W2JB_MEMORY_POLICY_REGION_COUNT; ++i) {
            const w2jb_memory_region_report *region = &report.regions[i];
            int written = snprintf(reply->result + used, sizeof(reply->result) - used,
                "%s{\"name\":\"%s\",\"expected\":\"%s\",\"observed\":\"%s\",\"status\":\"%s\"}",
                i ? "," : "", region_name(region->region),
                permissions_name(region->expected_permissions),
                permissions_name(region->observed_permissions),
                verification_name(region->verification));
            if (written < 0 || (size_t)written >= sizeof(reply->result) - used) {
                reply->status = W2JB_BACKEND_FAILURE;
                return W2JB_BACKEND_FAILURE;
            }
            used += (size_t)written;
        }
        if (used >= sizeof(reply->result) - 2u) {
            reply->status = W2JB_BACKEND_FAILURE;
            return W2JB_BACKEND_FAILURE;
        }
        memcpy(reply->result + used, "]}", 3u);
        reply->native_process = 1;
        reply->simulated = bridge->kind == W2JB_BACKEND_MOCK;
        reply->switch_native_execution = 0;
        reply->status = W2JB_OK;
        return W2JB_OK;
    }
    status = bridge->backend->request(request, reply, bridge->mock_fail_requests);
    reply->protocol_version = W2JB_PROTOCOL_VERSION;
    snprintf(reply->request_id, sizeof(reply->request_id), "%s", request->request_id);
    snprintf(reply->backend_id, sizeof(reply->backend_id), "%s", bridge->backend->name);
    reply->status = status;
    w2jb_log(bridge, status == W2JB_OK ? 1 : 2,
             status == W2JB_OK ? "relay request completed" : "relay request failed");
    return status;
}
