#include "alloc.h"
#include "statemachine.h"
#include "literal.h"
#include "const.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <stddef.h>
#include <stdint.h>
#include <float.h>
#include <ctype.h>

static val_t console_log(SimpleVM *vm, val_t this, int totarg, val_t *args) {
  printf("yay, console.log called. %p %d\n", vm, totarg);
}

char *read_literals(SimpleVM *vm, char *bcode) {
  int size;
  int i=0;
  char buf[512], *bc = bcode+4;
  
  memcpy(&size, bcode, 4);
  
  while (bc < bcode + size) {
    printf("lit type: %d\n", *bc);
    
    if (*bc == 0) { //string
      int j = 0;
      
      bc++;
      while (*bc && j < sizeof(buf)-1) {
        buf[j] = *bc;
        j++;
        bc++;
      }
      buf[j] = 0;
      
      printf("string literal! %s\n", buf);
      
      LT_GetStrLit(&vm->literals, buf);
      bc++;
    } else if (*bc == 1) { //double
      double d;
      bc++;
      
      memcpy(&d, bc, 8);
      LT_GetLit(&vm->literals, d);
      
      printf("double literal! %lf\n", d);
      bc += 8;
    } else {
      fprintf(stderr, "eek! error decoding literals! %p %d\n", bc, *bc);
      break;
    }
  }
  
  bcode += size+4; //skip bcode length field
  
  return bcode;
}

int main(int argc, char **argv) {
  SimpleVM _vm, *vm = &_vm;
  FILE *file = fopen("out.bin", "rb");
  size_t size;
  char *bcode, *image;
  
  if (!file) {
    fprintf(stderr, "Error: failed to open ./out.bin\n");
    return -1;
  }
  
  fseek(file, 0, SEEK_END);
  size = ftell(file);
  fseek(file, 0, SEEK_SET);
  
  if (!size) {
    fprintf(stderr, "Error: empty file\n");
    return -2;
  }
  
  image = MEM_malloc(size);
  fread(image, size, 1, file);
  
  SVM_Init(vm, 1024);
  bcode = read_literals(vm, image);
  
  vm->regs[IP].p.ptr = (uint64_t)bcode;
  vm->bcode = bcode;
  
  //set up some globals
  vm->global = vm->scope = SVM_MakeObject(vm, TYPE_OBJECT);
  val_t console = SVM_MakeObject(vm, TYPE_OBJECT);
  
  SVM_SetField(vm, vm->global, "console", console);
  SVM_SetField(vm, console, "log", SVM_MakeNativeFunc(vm, console_log));
  
  SVM_Step(vm);
  
  MEM_free(image);
  SVM_Release(vm);
  
  printf("done.\n");
  MEM_printblocks(stderr);
  
  return 0;
}
