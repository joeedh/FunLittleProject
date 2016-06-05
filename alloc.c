#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <stdint.h>
#include <stddef.h>

#include "alloc.h"
#include "list.h"

#define MEM_MAGIC1  ('M' | ('E'<<8) | ('M'<<16) | ('H'<<24))
#define MEM_MAGIC2  ('M' | ('E'<<8) | ('M'<<16) | ('T'<<24))

//need to pad to sixteen byte boundary
//we have:
//  four int32s
//  three pointers
//
//on 32-bits, that's 28 bytes, which we pad to 32
//on 64-bits, that's 40, which we pad to 48

typedef struct MemNode {
  struct MemNode *next, *prev;
  uint32_t magic1;                   
  
  uint32_t size;
  char *file; //source file   
  uint32_t line; //source line
  
  uint32_t magic2;
#ifdef HAVE_PTR64
  uint64_t pad; //pad to sixteen byte boundary
#else
  uint32_t pad; //pad to sixteen byte boundary
#endif
} MemNode;

List memlist = {NULL, NULL};
#define ERROUT stderr

static void mem_error(FILE *errout, void *mem, char *msg, char *file, int line) {
  fprintf(errout, "Block %p: Error: %s\n\t%s:%d\n", mem, msg, file, line);
}

int _MEM_check(void *mem, FILE *errout, char *file, int line) {
  MemNode *node, *tail;
  
  if (!mem) {
    mem_error(errout, mem, "NULL pointer detected", file, line);
    return 0;
  }
  
  node = mem;
  node--;
  
  if (node->magic1 != MEM_MAGIC1 || node->magic2 != MEM_MAGIC2) {
    mem_error(errout, mem, "Memory node corrupted", file, line);
    return 0;
  }
  
  tail = (MemNode*)(((char*)mem) + node->size);
  if (tail->magic1 != MEM_MAGIC1 || tail->magic2 != MEM_MAGIC2) {
    mem_error(errout, mem, "Memory tail corrupted", file, line);
    return 0;
  }
  
  return 1;
}

void *_MEM_malloc(size_t size, char *file, int line) {
  size += 7 - (size & 7);
  
  MemNode *node = malloc(size + sizeof(MemNode)*2), *tail;
  
  node->file = file;
  node->line = line;
  node->size = size;
  node->magic1 = MEM_MAGIC1;
  node->magic2 = MEM_MAGIC2;
  
  tail = (MemNode*)(((char*)(node+1)) + size);
  *tail = *node;
  tail->next = tail->prev = NULL;
  
  List_Append(&memlist, node);
  
  return node + 1;
}

void *_MEM_calloc(size_t size, char *file, int line) {
  void *ret = _MEM_malloc(size, file, line);
  memset(ret, 0, size);  
  return ret;
}

void *_MEM_realloc(void *mem, size_t size, char *file, int line) {
  MemNode *node = mem;
  void *ret;
  
  if (!size) {
    mem_error(ERROUT, mem, "Error in MEM_realloc(): size was 0", file, line);
    return NULL;
  }
  
  if (!mem)
    return _MEM_malloc(size, file, line);
  if (!_MEM_check(mem, ERROUT, file, line)) //prints any error
    return NULL;
  
  node--;
  ret = _MEM_malloc(size, file, line);
  
  size = size > node->size ? node->size : size;
  memcpy(ret, mem, size);
  _MEM_free(mem, file, line);
  
  return ret;
}

size_t _MEM_size(void *mem, char *file, int line) {
  MemNode *node = mem;
  
  if (!_MEM_check(mem, ERROUT, file, line)) { //prints any error
    return;
  }
  
  node--;
  return node->size;
}

void *_MEM_free(void *mem, char *file, int line) {
  MemNode *node = mem;
  
  if (!_MEM_check(mem, ERROUT, file, line)) { //_MEM_check prints error
    return;
  }
  
  node--;
  node->magic1 = node->magic2 = 0;
  
  List_Remove(&memlist, node);
  free(node);
}

void MEM_printblocks(FILE *out) {
  MemNode *node;
  
  if (!memlist.first) {
    return;
  }
  
  fprintf(out, "\n======Allocated memory blocks==========\n");
  
  for (node=memlist.first; node; node=node->next) {
    fprintf(out, "block %p: size %d\n\t%s:%d\n", node, (int)node->size, node->file, node->line);
    if (!_MEM_check(node+1, out, node->file, node->line)) {
      fprintf(out, "\n");
    }
  }
}
