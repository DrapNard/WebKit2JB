#ifndef W2JB_AARCH64_SYSROOT_STRING_H
#define W2JB_AARCH64_SYSROOT_STRING_H
#include <stddef.h>
extern void *memcpy(void *destination, const void *source, size_t count);
extern void *memset(void *destination, int value, size_t count);
extern size_t strlen(const char *string);
#endif
