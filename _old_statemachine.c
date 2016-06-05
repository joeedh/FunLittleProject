#include <stdio.h>
#include <string.h>
#include <stdlib.h>

#include "statemachine.h"

SimpleVM *SVM_Init(int stacksize) {
  SimpleVM *vm = malloc(sizeof(SimpleVM));

  memset(vm, 0, sizeof(SimpleVM));
  
  if (stacksize > 0) {
    udoubleptr_t *stack = malloc(stacksize*sizeof(udoubleptr_t));
    
    //fill with garbage
    memset(stack, 0xff,  stacksize*sizeof(udoubleptr_t));

    //get end of stack since stack grows downward
    vm->regs[SP].p = stack + (stacksize-1)*sizeof(udoubleptr_t);
  }
  
  return vm;
}

#define setbit(f, b, v) (f) = ( (!!((f) & (b)) != !!v) ? ((f) ^ (b)) : (f))

#define arithflags_i(flags, i)\
  setbit(flags, ZF, !i);\\
  setbit(flags, SF, i < 0);
#define arithflags_u(flags, u)\
  setbit(flags, ZF, !u);\\
  setbit(flags, SF, 0);
#define arithflags_d(flags, d)\
  setbit(flags, ZF, !d);\\
  setbit(flags, SF, d < 0);

int SVM_Step(SimpleVM *vm) {
  uintptr_t ip = vm->regs[IP].p;
  uintptr_t sp = vm->regs[SP].p;
  uintptr_t flags = vm->regs[FLAGS].p;
  uintptr_t except = vm->regs[EXCEPT].p;
  
  bytecode_t *code = (bytecode_t*) ip;
  ip += sizeof(bytecode_t);
  
  doubleunion_t *stack = (doubleunion_t*) sp;
  int i;
  unsigned int u;
  double d;
  
  switch (ip->code) {
    case INC_I32:
      vm->regs[code->arg.args[0]].i += 1;
      break;
    case DEC_I32:
      vm->regs[code->arg.args[0]].i -= 1;
      break;
    case INC_U32:
      vm->regs[code->arg.args[0]].u += 1;
      break;
    case DEC_U32:
      vm->regs[code->arg.args[0]].u -= 1;
      break;
    case ADD_I32_RR:
      vm->regs[code->arg.args[0]].i += vm->regs[code->arg.args[1]].i;
      arithflags_i(vm->regs[code->arg.args[0]].i);
      break;
    case ADD_U32_RR:
      vm->regs[code->arg.args[0]].u += vm->regs[code->arg.args[1]].u;
      arithflags_u(vm->regs[code->arg.args[0]].u);
      break;
    case ADD_F64_RR:
      vm->regs[code->arg.args[0]].d += vm->regs[code->arg.args[1]].d;
      arithflags_d(vm->regs[code->arg.args[0]].d);
      break;
    case SUB_I32_RR:
      vm->regs[code->arg.args[0]].i -= vm->regs[code->arg.args[1]].i;
      arithflags_i(vm->regs[code->arg.args[0]].i);
      break;
    case SUB_U32_RR:
      vm->regs[code->arg.args[0]].u -= vm->regs[code->arg.args[1]].u;
      arithflags_u(vm->regs[code->arg.args[0]].u);
      break;
    case SUB_F64_RR:
      vm->regs[code->arg.args[0]].d -= vm->regs[code->arg.args[1]].d;
      arithflags_d(vm->regs[code->arg.args[0]].d);
      break;
    case MUL_I32_RR:
      vm->regs[code->arg.args[0]].i *= vm->regs[code->arg.args[1]].i;
      arithflags_i(vm->regs[code->arg.args[0]].i);
      break;
    case MUL_U32_RR:
      vm->regs[code->arg.args[0]].u *= vm->regs[code->arg.args[1]].u;
      arithflags_u(vm->regs[code->arg.args[0]].u);
      break;
    case MUL_F64_RR:
      vm->regs[code->arg.args[0]].d *= vm->regs[code->arg.args[1]].d;
      arithflags_d(vm->regs[code->arg.args[0]].d);
      break;
    case DIV_I32_RR:
      vm->regs[code->arg.args[0]].i /= vm->regs[code->arg.args[1]].i;
      arithflags_i(vm->regs[code->arg.args[0]].i);
      break;
    case DIV_I32_RR:
      vm->regs[code->arg.args[0]].u /= vm->regs[code->arg.args[1]].u;
      arithflags_u(vm->regs[code->arg.args[0]].u);
      break;
    case DIV_F64_RR:
      vm->regs[code->arg.args[0]].d /= vm->regs[code->arg.args[1]].d;
      arithflags_d(vm->regs[code->arg.args[0]].d);
      break;
    case MOD_I32_RR:
      vm->regs[code->arg.args[0]].i = vm->regs[code->arg.args[0]].i % vm->regs[code->arg.args[1]].i;
      arithflags_i(vm->regs[code->arg.args[0]].i);
      break;
    case MOD_U32_RR:
      vm->regs[code->arg.args[0]].u = vm->regs[code->arg.args[0]].u % vm->regs[code->arg.args[1]].u;
      arithflags_u(vm->regs[code->arg.args[0]].u);
      break;
    case MOD_F64_RR:
      vm->regs[code->arg.args[0]].d = fmod(vm->regs[code->arg.args[0]].d, vm->regs[code->arg.args[1]].d);
      arithflags_d(vm->regs[code->arg.args[0]].d);
      break;
    case BAND_I32_RR:
      vm->regs[code->arg.args[0]].i = vm->regs[code->arg.args[0]].i & vm->regs[code->arg.args[1]].i;
      arithflags_i(vm->regs[code->arg.args[0]].i);
      break;
    case BAND_U32_RR:
      vm->regs[code->arg.args[0]].u = vm->regs[code->arg.args[0]].u & vm->regs[code->arg.args[1]].u;
      arithflags_u(vm->regs[code->arg.args[0]].u);
      break;
    case BAND_F64_RR:
      vm->regs[code->arg.args[0]].d = (double)(((int)vm->regs[code->arg.args[0]].d) & ((int)vm->regs[code->arg.args[1]].d));
      arithflags_d(vm->regs[code->arg.args[0]].d);
      break;
    case BOR_I32_RR:
      vm->regs[code->arg.args[0]].i = vm->regs[code->arg.args[0]].i | vm->regs[code->arg.args[1]].i;
      arithflags_i(vm->regs[code->arg.args[0]].i);
      break;
    case BOR_U32_RR:
      vm->regs[code->arg.args[0]].u = vm->regs[code->arg.args[0]].u | vm->regs[code->arg.args[1]].u;
      arithflags_u(vm->regs[code->arg.args[0]].u);
      break;
    case BOR_F64_RR:
      vm->regs[code->arg.args[0]].d = (double)(((int)vm->regs[code->arg.args[0]].d) | ((int)vm->regs[code->arg.args[1]].d));
      arithflags_d(vm->regs[code->arg.args[0]].d);
      break;
    case LOR_I32_RR:
      vm->regs[code->arg.args[0]].i = vm->regs[code->arg.args[0]].i || vm->regs[code->arg.args[1]].i;
      break;
    case LOR_U32_RR:
      vm->regs[code->arg.args[0]].u = vm->regs[code->arg.args[0]].u || vm->regs[code->arg.args[1]].u;
      break;
    case LOR_F64_RR:
      vm->regs[code->arg.args[0]].i = (int)vm->regs[code->arg.args[0]].d || (int)vm->regs[code->arg.args[1]].d;
      break;
    case VOIDPUSH:
      state--;
      break;
    case VOIDPOP:
      state++;
      break;
    case CMP_I32I32_R: {
      int a = vm->regs[code->arg.args[0]].i;
      int b = vm->regs[code->arg.args[1]].i;
      a -= b;
      
      flags = flags & ~(ZF|SF|OF);
      flags |= ((a < 0)<<SF) | (a == 0)<<ZF;
      break;
    }
    case CMP_U32U32_R: {
      unsigned int a = vm->regs[code->arg.args[0]].u;
      unsigned int b = vm->regs[code->arg.args[1]].u;
      a -= b;
      
      flags = flags & ~(ZF|SF|OF);
      flags |= (a == 0) << ZF;
      break;
    }
    case CMP_F64F64_R:
    case CMP_I32F64_R:
    case CMP_F64I32_R:
    case CMP_U32F64_R:
    case CMP_F64U32_R:
      //arithflags_(vm->regs[code->arg.args[0]].);
      break;
    case MOV_MEM32_R:
      vm->regs[code->reg].i = *((int*)code->arg.p);
      break;
    case MOV_R_MEM32:
       *((int*)code->arg.p) = vm->regs[code->reg].i;
      break;
    case MOV_MEM64_R:
      vm->regs[code->reg].d = *((double*)code->arg.p);
      break;
    case MOV_R_MEM64:
       *((double*)code->arg.p) = vm->regs[code->reg].d;
      break;
    case MOV_CONST32_R:
      vm->regs[code->reg].i = code->args.i;
      break;
    case MOV_CONST64_R:
      vm->regs[code->reg].d = code->args.d;
      break;
    case PUSH:
      *stack-- = vm->regs[code->arg.reg];
      break;
    case POP:
      vm->regs[code->arg.reg] = *stack++;
      break;
    case CALL_REL: //relative call
      (stack--)->p = ip;
      ip += code->arg.i;
      break;
    case CALL_ABS: //absolute call
      (stack--)->p = ip;
      ip = code->arg.p;
      break;
    //no arguments for ret/iret
    case RET:
      ip = (stack--)->p;
      break;
    case IRET: //kindof a reserved opcode, for now
      ip = (stack--)->p;
      break;
    
    //jmps take one argument: relative address to jmp to
    case JMP:
      ip += code->arg.i;
      break;
    case JNE:
      if (!(flags & ZF)) {
        ip += code->arg.i;
      }
      break;
    case JE:
      if (flags & ZF) {
        ip += code->arg.i;
      }
      break;
    case JLE:
      if ((flags & ZF) || (flags & SF)) {
        ip += code->arg.i;
      }
      break;
    case JLT:
      if (!(flags & ZF) && (flags & SF)) {
        ip += code->arg.i;
      }
      break;
    case JGT:
      if (!(flags & ZF) && !(flags & SF)) {
        ip += code->arg.i;
      }
      break;
    case JGE:
      if ((flags & ZF) || !(flags & SF)) {
        ip += code->arg.i;
      }
      break;
    case PUSH_CONSTI32: //used for building strings
      (stack--)->i = code->arg.i;
      break;
    case ALLOCOBJ_R: //argument is [type: register] obj address is put in register
      vm->regs[code->reg].p = (uintptr_t) SVM_Alloc(code->arg.args[0]);
      break;
    case ADDFIELD_R_NAMED: //argument: [type, register, name] where is name id from string pool
      vm->regs[code->reg] = (uintptr_t) SVM_AllocField(code->arg.args[0], code->arg.args[1]);
      break;
    case ADDFIELD_RR: //argument: [type, output register]
      vm->regs[code->reg] = (uintptr_t) SVM_AllocField(code->arg.args[0], 0);
      break;
    case GETFIELD_RR: { //argument: register
      double field; 
     
      if (!SVM_GetField((SVMObject*) vm->regs[code->reg].p, vm->regs[code->arg.args[1]].i, &field)) {
        (stack--)->p = ip;
        ip = vm->excepthandlers[NOTEXISTS];
      } else {
        vm->regs[code->arg.args[0]].d = field;
      }
      break;
    }
    case GETFIELD_RI: { //argument: register
      double field; 
     
      if (!SVM_GetField((SVMObject*) vm->regs[code->reg].p, code->arg.args[1], &field)) {
        (stack--)->p = ip;
        ip = vm->excepthandlers[NOTEXISTS];
      } else {
        vm->regs[code->arg.args[0]].d = field;
      }
      break;
    }
    case GETFIELDTYPE_R: { //argument: register
      int fieldtype; 
     
      if (!SVM_GetFieldType((SVMObject*) vm->regs[code->reg].p, code->arg.args[1], &fieldtype)) {
        (stack--)->p = ip;
        ip = vm->excepthandlers[NOTEXISTS];
      } else {
        vm->regs[code->arg.args[0]].d = fieldtype;
      }
      break;
    }
    case SETFIELD_RRR: { //argument: objectreg, nameidreg, valuereg
      double field; 
     
      if (!SVM_SetField((SVMObject*) vm->regs[code->reg].p, vm->regs[code->arg.args[1]], vm->regs[code->arg.args[0]].d)) {
        (stack--)->p = ip;
        ip = vm->excepthandlers[NOTEXISTS];
      }
      break;
    }
    case SETFIELD_RIR: { //argument: objectreg, nameid, valuereg
      double field; 
     
      if (!SVM_SetField((SVMObject*) vm->regs[code->reg].p, code->arg.args[1], vm->regs[code->arg.args[0]].d)) {
        (stack--)->p = ip;
        ip = vm->excepthandlers[NOTEXISTS];
      }
      break;
    }
    case GETNAMEID_STACK: { //arguments: out register, length of name on stack
      unsigned char buf[64];
      int i, ilen = code->arg.args[0];
      
      for (int i=0; i<ilen; i++) {
        buf[i] = (unsigned char)(stack-i-1)->i;
      }
      
      buf[i] = 0;
      vm->regs[code->reg] = SVM_GetNameId(vm, buf);
      break;
    }
    case STDOUT_PUTC:
      fputc(code->arg.i, stdout);
      break;
    case STDOUT_PUTC_R:
      fputc(vm->regs[code->reg]->i, stdout);
      break;
    default:
      (stack--)->p = ip;
      ip = vm->excepthandlers[INVALID_OPCODE];
      break;
  }
  
  vm->regs[IP].p = ip;
  vm->regs[SP].p = sp;
  vm->regs[FLAGS].p = flags;
  vm->regs[EXCEPT].p = except;
}
