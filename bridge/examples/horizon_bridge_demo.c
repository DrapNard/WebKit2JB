#include <stdio.h>
#include <switch.h>
#include "webkit2jb_bridge.h"

static void horizon_log(void *context, int level, const char *message) {
    (void)context;
    printf("bridge[%d]: %s\n", level, message);
}

static void print_banner(const char *bridge_state) {
    printf("+------------------------------------+\n");
    printf("|         WebKit2JB v0.1.0           |\n");
    printf("+------------------------------------+\n");
    printf("|                                    |\n");
    printf("|    UwU from Nintendo Switch 2      |\n");
    printf("|                                    |\n");
    printf("|  Backend : Horizon / ARM64         |\n");
    printf("|  Bridge  : %-23s|\n", bridge_state);
    printf("+------------------------------------+\n");
}

int main(void) {
    w2jb_bridge *bridge = NULL;
    w2jb_reply reply;
    w2jb_relay_capabilities relay_capabilities = {sizeof(w2jb_relay_capabilities), 0, 0,
                                                    W2JB_BACKEND_HORIZON_HOMEBREW, 0, 0, 0};
    w2jb_config config = {
        sizeof(w2jb_config), W2JB_BACKEND_HORIZON_HOMEBREW, 1500, 0,
        horizon_log, NULL
    };
    w2jb_request request = {
        W2JB_PROTOCOL_VERSION, "horizon-demo-001", W2JB_OP_DIAGNOSTIC, NULL, 0
    };
    w2jb_status status;
    PadState pad;
    bool bridge_initialized = false;
    int result = 0;

    consoleInit(NULL);
    {
        u32 version = hosversionGet();
        if (version == 0) printf("HOS version: unavailable\n");
        else printf("HOS version: %u.%u.%u\n", HOSVER_MAJOR(version), HOSVER_MINOR(version), HOSVER_MICRO(version));
    }
    status = w2jb_bridge_init(&config, &bridge);
    if (status != W2JB_OK) {
        char error_state[64];
        snprintf(error_state, sizeof(error_state), "ERROR: %s", w2jb_status_name(status));
        print_banner(error_state);
        result = 1;
        goto input_loop;
    }
    bridge_initialized = true;
    print_banner("Initialized");

    status = w2jb_bridge_relay_capabilities(bridge, &relay_capabilities);
    if (status != W2JB_OK) {
        printf("Capabilities: ERROR (%s)\n", w2jb_status_name(status));
        result = 2;
        goto input_loop;
    }
    printf("Relay ABI: %u; protocol: %u; backend: %s\n"
           "Capabilities: 0x%08X; simulated=%d; Switch execution=%d\n",
           relay_capabilities.abi_version, relay_capabilities.protocol_version,
           w2jb_backend_name(relay_capabilities.backend), relay_capabilities.capability_flags,
           relay_capabilities.simulated, relay_capabilities.switch_native_execution);

    status = w2jb_bridge_relay_request(bridge, &request, &reply);
    printf("Diagnostic: %s\n%s\n", w2jb_status_name(status), reply.result);
    if (status != W2JB_OK) result = 3;

    request.request_id = "horizon-memory-policy";
    request.operation = W2JB_OP_MEMORY_POLICY;
    status = w2jb_bridge_relay_request(bridge, &request, &reply);
    printf("W^X policy query: %s\n%s\n", w2jb_status_name(status), reply.result);
    if (status != W2JB_OK) result = 5;

    request.request_id = "horizon-ns2jb-status";
    request.operation = W2JB_OP_NS2JB_COMPATIBILITY;
    status = w2jb_bridge_relay_request(bridge, &request, &reply);
    printf("NS2JB relay: %s\n%s\n", w2jb_status_name(status), reply.result);
    if (status != W2JB_OK) result = 4;

input_loop:
    printf("Press PLUS or B to exit.\n");
    padConfigureInput(1, HidNpadStyleSet_NpadStandard);
    padInitializeDefault(&pad);
    while (appletMainLoop()) {
        padUpdate(&pad);
        if (padGetButtonsDown(&pad) & (HidNpadButton_Plus | HidNpadButton_B)) break;
        consoleUpdate(NULL);
        svcSleepThread(16000000);
    }
    if (bridge_initialized) {
        w2jb_bridge_shutdown(bridge);
        bridge = NULL;
        bridge_initialized = false;
    }
    consoleExit(NULL);
    return result;
}
