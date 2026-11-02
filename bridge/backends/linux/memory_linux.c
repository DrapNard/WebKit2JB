#define _GNU_SOURCE
#include <stdint.h>
#include <stdio.h>
#include "webkit2jb_bridge.h"

w2jb_status w2jb_bridge_inspect_self_address(const void *address, size_t size, w2jb_region_permissions *out) {
    FILE *maps;
    char line[512];
    uintptr_t first = (uintptr_t)address;
    uintptr_t last;
    if (address == NULL || size == 0 || out == NULL || first > UINTPTR_MAX - size) return W2JB_INVALID_ARGUMENT;
    last = first + size;
    maps = fopen("/proc/self/maps", "r");
    if (maps == NULL) return W2JB_CAPABILITY_UNAVAILABLE;
    while (fgets(line, sizeof(line), maps) != NULL) {
        unsigned long begin = 0, end = 0;
        char permissions[5] = {0};
        if (sscanf(line, "%lx-%lx %4s", &begin, &end, permissions) == 3 &&
            first >= (uintptr_t)begin && last <= (uintptr_t)end) {
            out->readable = permissions[0] == 'r';
            out->writable = permissions[1] == 'w';
            out->executable = permissions[2] == 'x';
            fclose(maps);
            return W2JB_OK;
        }
    }
    fclose(maps);
    return W2JB_CAPABILITY_UNAVAILABLE;
}
