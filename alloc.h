#ifndef _ALLOC_H
#define _ALLOC_H

#include <stdint.h>
#include <stddef.h>
#include <stdio.h>

#define MEM_check(mem, errout) _MEM_check(mem, errout, __FILE__, __LINE__)
#define MEM_size(mem) _MEM_size(mem, __FILE__, __LINE__)

#define MEM_malloc(size) _MEM_malloc(size, __FILE__, __LINE__)
#define MEM_calloc(size) _MEM_calloc(size, __FILE__, __LINE__) //like malloc but zeroes memory
#define MEM_realloc(mem, size) _MEM_realloc(mem, size, __FILE__, __LINE__) //does not zero new memory

#define MEM_free(mem) _MEM_free(mem, __FILE__, __LINE__)

void MEM_printblocks(FILE *out);

int _MEM_check(void *mem, FILE *errout, char *file, int line);
void *_MEM_malloc(size_t size, char *file, int line);
void *_MEM_calloc(size_t size, char *file, int line);
void *_MEM_realloc(void *mem, size_t size, char *file, int line);
size_t _MEM_size(void *mem, char *file, int line);
void *_MEM_free(void *mem, char *file, int line);

#endif /* _ALLOC_H */
