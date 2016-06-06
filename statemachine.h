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
  bytecode_t *bcode;
  
  int error, flag;
  bytecode_t *breakpoint;
  
  List objects;
} SimpleVM;

//SimpleVM->flag
enum { 
  VM_STRICT=1
};

#define READ_REG_UINTPTR_T(vm, i) (*((uintptr_t)(vm->regs+(i))))
#define SCOPE_FIELD_NAME "_$_spar"

//note that strict mode defaults to true
void SVM_Init(SimpleVM *vm, int stacksize);
void SVM_Release(SimpleVM *vm);
int SVM_GetNameId(SimpleVM *vm, const unsigned char *name);
val_t SVM_MakeNativeFunc(SimpleVM *vm, c_callback func);

#endif /* _SIMPLEVM_STATEMACHINE_H */
