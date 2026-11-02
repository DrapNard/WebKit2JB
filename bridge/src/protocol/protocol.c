#include <string.h>
#include "internal.h"

w2jb_status w2jb_validate_request(const w2jb_request *request) {
    size_t id_length;
    size_t i;
    if (request == NULL || request->request_id == NULL) return W2JB_INVALID_ARGUMENT;
    if (request->protocol_version != W2JB_PROTOCOL_VERSION) return W2JB_PROTOCOL_UNSUPPORTED;
    for (id_length = 0; id_length <= W2JB_MAX_REQUEST_ID &&
         request->request_id[id_length] != '\0'; ++id_length) {}
    if (id_length == 0 || id_length > W2JB_MAX_REQUEST_ID) return W2JB_INVALID_REQUEST_ID;
    for (i = 0; i < id_length; ++i) {
        unsigned char c = (unsigned char)request->request_id[i];
        if (!((c >= 'A' && c <= 'Z') || (c >= 'a' && c <= 'z') ||
              (c >= '0' && c <= '9') || c == '-' || c == '_'))
            return W2JB_INVALID_REQUEST_ID;
    }
    if (request->payload_size > W2JB_MAX_PAYLOAD) return W2JB_MESSAGE_TOO_LARGE;
    if (request->payload_size != 0 && request->payload == NULL) return W2JB_INVALID_ARGUMENT;
    if (request->operation < W2JB_OP_CAPABILITIES ||
        request->operation > W2JB_OP_MEMORY_POLICY)
        return W2JB_UNSUPPORTED_OPERATION;
    if (request->operation != W2JB_OP_ECHO && request->payload_size != 0)
        return W2JB_INVALID_ARGUMENT;
    return W2JB_OK;
}
