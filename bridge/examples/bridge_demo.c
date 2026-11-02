#include <stdio.h>
#include <string.h>
#include "webkit2jb_bridge.h"

static void log_message(void *context, int level, const char *message) {
    FILE *stream = context == NULL ? stderr : (FILE *)context;
    fprintf(stream, "bridge[%d]: %s\n", level, message);
}

int main(void) {
    w2jb_bridge *bridge = NULL;
    w2jb_reply reply;
    w2jb_config config = {sizeof(w2jb_config), W2JB_BACKEND_LINUX, 1500, 0, log_message, stderr};
    w2jb_request request = {W2JB_PROTOCOL_VERSION, "demo-001", W2JB_OP_DIAGNOSTIC, NULL, 0};
    w2jb_status status = w2jb_bridge_init(&config, &bridge);
    if (status != W2JB_OK) {
        fprintf(stderr, "init: %s\n", w2jb_status_name(status));
        return 1;
    }
    status = w2jb_bridge_request(bridge, &request, &reply);
    printf("backend=%s simulated=%s status=%s result=%s\n", reply.backend_id,
           reply.simulated ? "yes" : "no", w2jb_status_name(status), reply.result);
    w2jb_bridge_shutdown(bridge);
    return status == W2JB_OK ? 0 : 2;
}
