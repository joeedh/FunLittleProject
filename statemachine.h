#ifndef _SIMPLEVM_STATEMACHINE_H
#define _SIMPLEVM_STATEMACHINE_H

#include <stdint.h>

#include "bytecode.h"
#include "object.h"
#include "list.h"

typedef struct LitTable {
  doubleunion_t *literals;
  int used, size;
} LitTable;

typedef struct SimpleVM {
  LitTable literals;
  
  doubleunion_t regs[TOTREGISTER], *stackhead;
  uintptr_t excepthandlers[TOTEXCEPTION];
  val_t scope, global, exception;
  
  int error;
  bytecode_t *breakpoint;
  
  List objects;
} SimpleVM;

#define READ_REG_UINTPTR_T(vm, i) (*((uintptr_t)(vm->regs+(i))))
#define SCOPE_FIELD_NAME "_$_spar"

void SVM_Init(SimpleVM *vm, int stacksize);
void SVM_Release(SimpleVM *vm);
int SVM_GetNameId(SimpleVM *vm, const unsigned char *name);
val_t SVM_MakeNativeFunc(SimpleVM *vm, c_callback func);

#endif /* _SIMPLEVM_STATEMACHINE_H */
