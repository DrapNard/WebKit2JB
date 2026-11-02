#ifndef W2JB_INTERNAL_H
#define W2JB_INTERNAL_H
#include "webkit2jb_bridge.h"

typedef struct w2jb_backend_vtable {
    const char *name;
    w2jb_status (*request)(const w2jb_request *, w2jb_reply *, int mock_failure);
    void *(*allocate)(size_t);
    void (*deallocate)(void *);
} w2jb_backend_vtable;

struct w2jb_bridge {
    uint32_t initialized;
    w2jb_backend_kind kind;
    uint32_t timeout_ms;
    int mock_fail_requests;
    w2jb_log_fn logger;
    void *logger_context;
    const w2jb_backend_vtable *backend;
};

const w2jb_backend_vtable *w2jb_backend_mock(void);
const w2jb_backend_vtable *w2jb_backend_linux(void);
#ifdef W2JB_BUILD_HORIZON
const w2jb_backend_vtable *w2jb_backend_horizon(void);
#endif
w2jb_status w2jb_validate_request(const w2jb_request *request);
void w2jb_log(w2jb_bridge *bridge, int level, const char *message);
#endif
