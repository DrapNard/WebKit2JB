#ifndef W2JB_AARCH64_SYSROOT_STDIO_H
#define W2JB_AARCH64_SYSROOT_STDIO_H
#include <stddef.h>
typedef struct w2jb_aarch64_FILE FILE;
extern FILE *fopen(const char *path, const char *mode);
extern int fclose(FILE *stream);
extern char *fgets(char *buffer, int size, FILE *stream);
extern int sscanf(const char *input, const char *format, ...);
extern int snprintf(char *buffer, size_t size, const char *format, ...);
#endif
