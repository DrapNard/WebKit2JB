#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include "webkit2jb_bridge.h"
#include "ns2jb_compat.h"

static const char constant_marker[] = "bridge-constant-data";
static void code_marker(void) {}

static w2jb_bridge *init(w2jb_backend_kind kind, int fail) {
    static w2jb_config config;
    w2jb_bridge *bridge = NULL;
    memset(&config, 0, sizeof(config));
    config.struct_size = sizeof(config);
    config.backend = kind;
    config.timeout_ms = 250;
    config.mock_fail_requests = fail;
    assert(w2jb_bridge_init(&config, &bridge) == W2JB_OK);
    return bridge;
}

static void test_lifecycle_and_linux_backend(void) {
    w2jb_bridge *bridge = init(W2JB_BACKEND_LINUX, 0);
    w2jb_reply reply;
    w2jb_relay_capabilities relay = {sizeof(relay), 0, 0, W2JB_BACKEND_MOCK, 0, 0, 0};
    w2jb_request request = {W2JB_PROTOCOL_VERSION, "req-1", W2JB_OP_DIAGNOSTIC, NULL, 0};
    assert(w2jb_bridge_relay_capabilities(bridge, &relay) == W2JB_OK);
    assert(relay.abi_version == W2JB_RELAY_ABI_VERSION);
    assert(relay.protocol_version == W2JB_PROTOCOL_VERSION);
    assert(relay.backend == W2JB_BACKEND_LINUX && !relay.simulated);
    assert((relay.capability_flags & W2JB_RELAY_CAP_NS2JB_STATUS) != 0);
    assert((relay.capability_flags & W2JB_RELAY_CAP_MEMORY_POLICY) != 0);
    assert((relay.capability_flags & W2JB_RELAY_CAP_CONNECTIVITY) != 0);
    assert(w2jb_bridge_relay_request(bridge, &request, &reply) == W2JB_OK);
    assert(strcmp(reply.request_id, "req-1") == 0);
    assert(strcmp(reply.backend_id, "linux-local") == 0);
    assert(reply.native_process == 1 && reply.simulated == 0 && reply.switch_native_execution == 0);
    assert(strstr(reply.result, "RWX denied") != NULL);
    assert(w2jb_bridge_detect_capabilities(bridge, &reply) == W2JB_OK);
    assert(strstr(reply.result, "exec-allocation=0") != NULL);
    w2jb_bridge_shutdown(bridge);
    assert(w2jb_bridge_relay_capabilities(NULL, &relay) == W2JB_NOT_INITIALIZED);
    relay.struct_size = sizeof(relay) - 1u;
    bridge = init(W2JB_BACKEND_LINUX, 0);
    assert(w2jb_bridge_relay_capabilities(bridge, &relay) == W2JB_INVALID_ARGUMENT);
    w2jb_bridge_shutdown(bridge);
}

static void test_mock_and_failure(void) {
    w2jb_bridge *bridge = init(W2JB_BACKEND_MOCK, 0);
    w2jb_reply reply;
    const uint8_t text[] = "safe";
    w2jb_request request = {W2JB_PROTOCOL_VERSION, "echo-1", W2JB_OP_ECHO, text, sizeof(text) - 1};
    assert(w2jb_bridge_request(bridge, &request, &reply) == W2JB_OK);
    assert(reply.simulated == 1 && reply.switch_native_execution == 0);
    assert(strcmp(reply.result, "echo:safe") == 0);
    w2jb_bridge_shutdown(bridge);
    bridge = init(W2JB_BACKEND_MOCK, 1);
    request.operation = W2JB_OP_CAPABILITIES;
    request.request_id = "capabilities-available";
    assert(w2jb_bridge_detect_capabilities(bridge, &reply) == W2JB_OK);
    assert(strcmp(reply.request_id, "capabilities") == 0);
    request.operation = W2JB_OP_DIAGNOSTIC;
    request.request_id = "diagnostic-fail";
    request.payload = NULL;
    request.payload_size = 0;
    assert(w2jb_bridge_request(bridge, &request, &reply) == W2JB_BACKEND_FAILURE);
    assert(reply.status == W2JB_BACKEND_FAILURE);
    w2jb_bridge_shutdown(bridge);
}

static void test_protocol_validation(void) {
    w2jb_bridge *bridge = init(W2JB_BACKEND_LINUX, 0);
    w2jb_reply reply;
    uint8_t payload[W2JB_MAX_PAYLOAD + 1] = {0};
    w2jb_request request = {W2JB_PROTOCOL_VERSION, "bad id", W2JB_OP_DIAGNOSTIC, NULL, 0};
    assert(w2jb_bridge_request(bridge, &request, &reply) == W2JB_INVALID_REQUEST_ID);
    request.request_id = "version";
    request.protocol_version = 99;
    assert(w2jb_bridge_request(bridge, &request, &reply) == W2JB_PROTOCOL_UNSUPPORTED);
    request.protocol_version = W2JB_PROTOCOL_VERSION;
    request.operation = (w2jb_operation)99;
    assert(w2jb_bridge_request(bridge, &request, &reply) == W2JB_UNSUPPORTED_OPERATION);
    request.operation = W2JB_OP_ECHO;
    request.payload = payload;
    request.payload_size = sizeof(payload);
    assert(w2jb_bridge_request(bridge, &request, &reply) == W2JB_MESSAGE_TOO_LARGE);
    request.operation = W2JB_OP_DIAGNOSTIC;
    request.payload_size = 1;
    assert(w2jb_bridge_request(bridge, &request, &reply) == W2JB_INVALID_ARGUMENT);
    w2jb_bridge_shutdown(bridge);
    assert(w2jb_bridge_request(NULL, &request, &reply) == W2JB_NOT_INITIALIZED);
}

static void test_ns2jb_adapter_is_explicitly_unavailable(void) {
    w2jb_bridge *bridge = init(W2JB_BACKEND_LINUX, 0);
    w2jb_ns2jb_compat_info info;
    w2jb_ns2jb_compat_info_v2 info_v2;
    assert(w2jb_ns2jb_compat_probe(bridge, &info) == W2JB_CAPABILITY_UNAVAILABLE);
    assert(info.data_protocol_compatible == 0);
    assert(info.upstream_ns2jb_ipc_available == 0);
    assert(info.privileged_operations_available == 0);
    assert(info.note != NULL && strstr(info.note, "license-cleared") != NULL);
    assert(w2jb_ns2jb_compat_probe_v2(bridge, &info_v2) == W2JB_CAPABILITY_UNAVAILABLE);
    assert(info_v2.struct_size == sizeof(info_v2));
    assert(info_v2.adapter_version == 2);
    assert(info_v2.capability_flags == 0);
    assert(info_v2.status == W2JB_CAPABILITY_UNAVAILABLE);
    assert(strcmp(info_v2.source_commit, W2JB_NS2JB_SOURCE_COMMIT) == 0);
    assert(strstr(info_v2.note, "license-cleared") != NULL);
    assert(w2jb_ns2jb_compat_probe_v2(NULL, &info_v2) == W2JB_INVALID_ARGUMENT);
    {
        w2jb_request request = {W2JB_PROTOCOL_VERSION, "ns2jb-probe-1",
            W2JB_OP_NS2JB_COMPATIBILITY, NULL, 0};
        w2jb_reply reply;
        assert(w2jb_bridge_request(bridge, &request, &reply) == W2JB_OK);
        assert(strcmp(reply.request_id, "ns2jb-probe-1") == 0);
        assert(reply.native_process == 1 && reply.switch_native_execution == 0);
        assert(strstr(reply.result, "CAPABILITY_UNAVAILABLE") != NULL);
        assert(strstr(reply.result, "privilegedOperationsAvailable\":false") != NULL);
    assert(w2jb_bridge_relay_request(bridge, &request, &reply) == W2JB_OK);
    assert(strstr(reply.result, "\"status\":\"CAPABILITY_UNAVAILABLE\"") != NULL);
    assert(strstr(reply.result, "privilegedOperationsAvailable\":false") != NULL);
    }
    w2jb_bridge_shutdown(bridge);
}

static void test_wx_policy_and_effective_linux_permissions(void) {
    w2jb_bridge *bridge = init(W2JB_BACKEND_LINUX, 0);
    w2jb_memory_policy policy = w2jb_bridge_get_memory_policy();
    w2jb_region_permissions p;
    void *buffer = NULL;
    assert(policy.writable_executable_allocations == 0);
    assert(w2jb_bridge_check_region_policy(W2JB_REGION_MUTABLE_DATA,
        W2JB_PERM_READ | W2JB_PERM_WRITE) == W2JB_OK);
    assert(w2jb_bridge_check_region_policy(W2JB_REGION_CONSTANT_DATA,
        W2JB_PERM_READ) == W2JB_OK);
    assert(w2jb_bridge_check_region_policy(W2JB_REGION_CODE,
        W2JB_PERM_READ | W2JB_PERM_EXECUTE) == W2JB_CAPABILITY_UNAVAILABLE);
    assert(w2jb_bridge_check_region_policy(W2JB_REGION_MUTABLE_DATA,
        W2JB_PERM_READ | W2JB_PERM_WRITE | W2JB_PERM_EXECUTE) == W2JB_MEMORY_POLICY_DENIED);
    assert(w2jb_bridge_check_region_policy(W2JB_REGION_CODE,
        W2JB_PERM_READ | W2JB_PERM_WRITE | W2JB_PERM_EXECUTE) == W2JB_MEMORY_POLICY_DENIED);
    assert(w2jb_bridge_buffer_alloc(bridge, 64, &buffer) == W2JB_OK);
    assert(w2jb_bridge_inspect_self_address(buffer, 64, &p) == W2JB_OK);
    assert(p.readable && p.writable && !p.executable);
    w2jb_bridge_buffer_free(bridge, buffer);
    assert(w2jb_bridge_inspect_self_address(constant_marker, sizeof(constant_marker), &p) == W2JB_OK);
    assert(p.readable && !p.writable && !p.executable);
    assert(w2jb_bridge_inspect_self_address((const void *)(uintptr_t)&code_marker, 1, &p) == W2JB_OK);
    assert(p.readable && !p.writable && p.executable);
    {
        w2jb_memory_policy_report report;
        w2jb_request request = {W2JB_PROTOCOL_VERSION, "memory-policy-1",
                                W2JB_OP_MEMORY_POLICY, NULL, 0};
        w2jb_reply reply;
        memset(&report, 0, sizeof(report));
        report.struct_size = sizeof(report);
        assert(w2jb_bridge_memory_policy_report(bridge, &report) == W2JB_OK);
        assert(report.abi_version == W2JB_MEMORY_POLICY_ABI_VERSION);
        assert(report.overall == W2JB_VERIFY_PASS);
        assert(report.writable_executable_regions == 0);
        assert(report.region_count == W2JB_MEMORY_POLICY_REGION_COUNT);
        for (uint32_t i = 0; i < report.region_count; ++i) {
            assert(report.regions[i].verification == W2JB_VERIFY_PASS);
            assert((report.regions[i].observed_permissions &
                (W2JB_PERM_WRITE | W2JB_PERM_EXECUTE)) !=
                (W2JB_PERM_WRITE | W2JB_PERM_EXECUTE));
        }
        assert(w2jb_bridge_relay_request(bridge, &request, &reply) == W2JB_OK);
        assert(strcmp(reply.request_id, "memory-policy-1") == 0);
        assert(strstr(reply.result, "\"overall\":\"PASS\"") != NULL);
        assert(strstr(reply.result, "\"name\":\"stack\"") != NULL);
        report.struct_size = sizeof(report) - 1u;
        assert(w2jb_bridge_memory_policy_report(bridge, &report) == W2JB_INVALID_ARGUMENT);
        request.operation = W2JB_OP_ECHO;
        assert(w2jb_bridge_relay_request(bridge, &request, &reply) == W2JB_OK);
    }
    w2jb_bridge_shutdown(bridge);
}

int main(void) {
    test_lifecycle_and_linux_backend();
    test_mock_and_failure();
    test_protocol_validation();
    test_ns2jb_adapter_is_explicitly_unavailable();
    test_wx_policy_and_effective_linux_permissions();
    puts("bridge tests: PASS");
    return 0;
}
