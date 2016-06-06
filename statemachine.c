#include <stdio.h>
#include <string.h>
#include <stdlib.h>

#include "alloc.h"
#include "statemachine.h"
#include "literal.h"
#include "const.h"

static unsigned char interrupt_helper[] = {
  OP_DROP,
  OP_RET
};

void SVM_Init(SimpleVM *vm, int stacksize) {
  memset(vm, 0, sizeof(SimpleVM));
  
  LT_Init(&vm->literals);
  
  vm->breakpoint = BREAKPOINT_NONE;
  vm->flag = VM_STRICT;
  
  if (stacksize > 0) {
    val_t *stack = MEM_malloc(stacksize*sizeof(val_t));
    
    //fill with garbage
    memset(stack, 0xff,  stacksize*sizeof(val_t));

    //get end of stack since stack grows downward
    vm->regs[SP].p.ptr = (uint64_t)(stack + (stacksize-1)*sizeof(val_t));
    vm->stackhead = (doubleunion_t*) stack;
  }
}

//does not free vm itself
void SVM_Release(SimpleVM *vm) {
  val_t scope = vm->scope;
  LinkNode *node, *next;
  
  //free all objects
  for (node=vm->objects.first; node; node=next) {
    next = node->next;
    
    SVM_FreeObject((SVMObject*) node->value);
    MEM_free(node);
  }

  /*
  while (scope != JS_UNDEFINED) {
    SVMObject *obj = SVM_Val2Obj(scope);
    val_t scope2 = SVM_GetField(vm, scope, SCOPE_FIELD_NAME);
    
    SVM_FreeObject(obj);
    
    scope = scope2;
  }*/
  
  LT_Release(&vm->literals);
  MEM_free(vm->stackhead);
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

static void _debug_vm(SimpleVM *vm) {
  int i;
  doubleunion_t *sp = (doubleunion_t*) vm->regs[SP].p.ptr;
  
  fprintf(stderr, "\n========Stack=========\n");
  
  for (i=0; i<10; i++) {
    fprintf(stderr, ".p.ptr:%p .p.type:%s .d:%lf\n", (void*)sp[i].p.ptr, SVM_TypeToStr(sp[i].d), sp[i].d);
  }
}

int SVM_Step(SimpleVM *vm) {
  bytecode_t *code = (bytecode_t*) vm->regs[IP].p.ptr;
  uintptr_t flags = vm->regs[FLAGS].p.ptr;
  uintptr_t except = vm->regs[EXCEPT].p.ptr;
  
  doubleunion_t *sp = (doubleunion_t*) vm->regs[SP].p.ptr;
  int use_strict = vm->flag & VM_STRICT;
  
  while (code != vm->breakpoint) {
    double d;
    unsigned int u;
    int i;
    int opcode = *code++;
    
    extern char *opcode2str(int code);
    printf("0x%.5x: 0x%.2x      %s   ", (int)(code - vm->bcode - 1), opcode, opcode2str(opcode));
    
    switch (opcode) {
    case OP_DROP:
      sp += 1;
    case OP_DUP:
      *(sp-1) = *sp;
      sp--;
      
      break;
    case OP_2DUP:
      *(sp-1) = *sp;
      *(sp-2) = *(sp+1);
      sp -= 2;
      
      break;
    case OP_SWAP:
      *(sp-1) = *sp;
      *sp = *(sp+1);
      *(sp+1) = *(sp-1);
      
      break;
    case OP_STASH:
      vm->regs[RSTASH] = *sp;
      break;
    case OP_UNSTASH:
      *sp = vm->regs[RSTASH];
      vm->regs[RSTASH].d = int2val(0);
      break;
    case OP_SWAP_DROP:
      *(sp+1) = *sp;
      sp += 1;
      break;
    case OP_PUSH_UNDEFINED:
      (*--sp).d = JS_UNDEFINED;
      break;
    case OP_PUSH_NULL:
      (*--sp).d = JS_NULL;
      break;
    case OP_PUSH_THIS:
      (*--sp) = vm->regs[RTHIS];
      break;
    case OP_PUSH_TRUE:
      (*--sp).d = JS_TRUE;
      break;
    case OP_PUSH_FALSE:
      (*--sp).d = JS_FALSE;
      break;
    case OP_PUSH_ZERO:
      (*--sp).d = JS_FALSE;
      break;
    case OP_PUSH_ONE:
      (*--sp).d = JS_TRUE;
      break;
    case OP_PUSH_LIT: {
      int n=0;
      doubleunion_t val;
      
      memcpy(&n, code, 4);
      code += 4;
      
      (*--sp) = val = vm->literals.literals[n];
      printf(" %p %s %lf", (void*)val.p.ptr, SVM_TypeToStr((int)val.d), val.d);
      
      if (val.p.type == TYPE_STRING) {
        fprintf(stdout, " \"%s\"",  (char*)val.p.ptr);
      }
      
      break;
    }
    case OP_NOT:
      sp->d = int2val(~val2int(sp->d));
      break;
    case OP_LOGICAL_NOT:
      sp->d = !SVM_Truthy(sp->d);
      break;
    case OP_NEG:
      sp->d = -(SVM_ValueOf(vm, sp->d));
      break;
    case OP_POS: //result of Number(val)
      //XXX wrong?
      sp->d = SVM_ValueOf(vm, sp->d);
      break;
    case OP_ADD: {//TODO: strings
      val_t val = (val_t)SVM_ValueOf(vm, sp->d) + (val_t)SVM_ValueOf(vm, (sp+1)->d);
      (++sp)->d = val;
      
      break;
    }
    case OP_SUB: {     
      val_t val = (val_t)SVM_ValueOf(vm, sp->d) - (val_t)SVM_ValueOf(vm, (sp+1)->d);
      (++sp)->d = val;
      
      break;
    }
    case OP_REM: { //modula % operator
      double a = SVM_ValueOf(vm, sp->d), b = SVM_ValueOf(vm, (sp+1)->d);
      a = ((int)(a / b))*b;
      if (a < 0) {
        a += b;
      }
      
      (++sp)->d = a;
      break;
    }
    case OP_MUL: {
      val_t val = (val_t)SVM_ValueOf(vm, sp->d) * (val_t)SVM_ValueOf(vm, (sp+1)->d);
      (++sp)->d = val;
      
      break;
    }
    case OP_DIV: {
      val_t a = (val_t)SVM_ValueOf(vm, sp->d), b = (val_t)SVM_ValueOf(vm, (sp+1)->d);
      
      if (b == 0.0) {
        a = JS_NAN;
      } else {
        a /= b;
      }
      
      (++sp)->d = a;
      
      break;
    }
    case OP_URSHIFT: 
      break;
    case OP_LSHIFT:
    case OP_RSHIFT:  
    case OP_OR:      
    case OP_XOR:     
    case OP_AND: {
      int a = val2int(SVM_ValueOf(vm, sp->d)), b = val2int(SVM_ValueOf(vm, (sp+1)->d));
      
      switch (opcode) {
        case OP_LSHIFT:
          a = a << b;
          break;
        case OP_RSHIFT:
          a = a >> b;
          break;
        case OP_OR:
          a = a | b;
          break;
        case OP_XOR:
          a = a ^ b;
          break;
        case OP_AND:
          a = a & b;
          break;
      }
      
      (++sp)->d = int2val(a);
      break;
    }
    case OP_EQ_EQ:
      sp[1].d = sp[0].d == sp[1].d;
      sp += 1;
      break;
    case OP_EQ:    
      break;
    case OP_NE:    
      break;
    case OP_NE_NE: 
      break;
    case OP_LT:    
      break;
    case OP_LE:   
      break;
    case OP_GT:   
      break;
    case OP_GE:   
      break;
    case OP_INSTANCEOF:
      break;
    case OP_TYPEOF:
      break;
    case OP_IN:
      break;
    case OP_GET: {
      doubleunion_t propval = *sp;
      doubleunion_t thisval = *(sp+1);
      sp++;
      
      if (propval.p.type == TYPE_STRING) {
        sp->d = SVM_GetField(vm, thisval.d, (char*)propval.p.ptr);
      } else {
        //XXX todo: throw exception here
        fprintf(stderr, "bad property passed to OP_GET!\n");
      }
      break;
    }
    case OP_SET:
      break;
    case OP_SET_VAR: {
      int lit;
      
      memcpy(&lit, code, 4);
      code += 4;
      
      /* let's just not support implicit global assignments at all
         that would require adding a "mark as local scope" opcode
         for variables
        
      if (use_strict && SVM_FindFieldI(vm, vm->scope, lit) < 0) {
        fprintf(stderr, "global assignment error\n");
        //XXX todo: raise exception;
        break;
      }*/
      
      SVM_SetFieldI(vm, vm->scope, lit, sp->d);
      break;
    }
    case OP_SAFE_GET_VAR:
    case OP_GET_VAR: {
      int lit;
      val_t val;
      
      memcpy(&lit, code, 4);
      code += 4;
      
      printf(" %d", lit);
      
      val = SVM_GetFieldI(vm, vm->scope, lit);
      (--sp)->d = val;
      
      /* XXX need to check that variable exists in scope
         and raise exception if it does not */
      /*
      if (SVM_FindFieldI(vm, vm->scope, lit) < 0) {
      }
      */
      break;
    }
    case OP_JMP_TRUE:
    case OP_JMP_FALSE:
    case OP_JMP_TRUE_DROP:
    case OP_JMP: {
      int off, ok;
      val_t val;
      
      memcpy(&off, code, 4);
      
      switch (opcode) {
        case OP_JMP_TRUE:
          ok = SVM_Truthy(sp->d);
          break;
        case OP_JMP_FALSE:
          ok = !SVM_Truthy(sp->d);
          break;
        case OP_JMP_TRUE_DROP:
          ok = SVM_Truthy(sp->d);
          if (ok) {
            sp++;
          }
          break;
      }
      
      if (ok) {
        code += off-1;
      } else {
        code += 4;
      }
      
      break;
    }
    //not supported for now
    //case OP_JMP_IF_CONTINUE:
    //  break;
    case OP_CREATE_OBJ:
      (--sp)->d = SVM_MakeObject(vm, TYPE_OBJECT);
      break;
    case MYOP_CREATE_FUNC: {
      val_t func = SVM_MakeObject(vm, TYPE_FUNCTION);
      SVMFunc *obj = (SVMFunc*) SVM_Val2Obj(func);
      
      memcpy(&obj->entry, code, 4);
      code += 4;
      memcpy(&obj->totarg, code, 2);
      code += 2;
      
      (--sp)->d = func;
      break;
    }
    case OP_CREATE_ARR:
      (--sp)->d = SVM_MakeObject(vm, TYPE_ARRAY);
      break;
    case OP_NEXT_PROP:
      break;
    case OP_FUNC_LIT:
      break;
    case OP_CALL:
    case OP_NEW: {
      int totarg = *code++;
      SVMFunc *func;
      doubleunion_t val, thisval;
      
      sp += totarg;
      
      val = *sp++;
      thisval = *sp++;
      
      fprintf(stdout, "bleh: %p %d:%s", (void*)val.p.ptr, val.p.type, SVM_TypeToStr(val.d));
      if (val.p.type == TYPE_STRING) {
        fprintf(stdout, " \"%s\"\n",  (char*)val.p.ptr);
      } else {
        fprintf(stdout, "\n");
      }
      
      if (val.p.type == TYPE_CDECL_FUNCTION) {
        val_t ret;
        
        c_callback cb = (c_callback) val.p.ptr;
        
        //typedef val_t (*c_callback)(struct SimpleVM *vm, val_t dthis, int totarg, val_t *args);
        ret = cb(vm, thisval.d, totarg, (val_t*)(sp-totarg+2));
        (--sp)->d = ret;
      } else if (val.p.type == TYPE_FUNCTION) {
        func = (SVMFunc*) SVM_Val2Obj(val.d);
        
        (--sp)->p.ptr = (uint64_t) code + 1;
        code = (bytecode_t*) func->entry;        
      } else {
        fprintf(stdout, "invalid function! %p %s\n", (void*)val.p.ptr, SVM_TypeToStr(val.d));
      }
      
      break;
    }
    case OP_CHECK_CALL:
      break;
    case OP_RET:
      code = (bytecode_t*) sp->p.ptr;
      sp++;
      break;
    case OP_DELETE:
      break;
    case OP_DELETE_VAR:
      break;
    case OP_TRY_PUSH_CATCH: {
      int off;
      uintptr_t *tstack = (uintptr_t*) vm->regs[RTRYSTACK].p.ptr;
      
      memcpy(&off, code, 4);
      
      *--tstack = (uintptr_t) code+off-4; //ip
      *--tstack = (uintptr_t) sp;         //sp
      
      break;
    }
    case OP_TRY_PUSH_FINALLY:
      break;
    case OP_TRY_PUSH_LOOP:
      break;
    case OP_TRY_PUSH_SWITCH:
      break;
    case OP_TRY_POP:
      break;
    case OP_AFTER_FINALLY:
      break;
    case OP_THROW:
      break;
    case OP_BREAK:
      break;
    case OP_CONTINUE:
      break;
    case OP_ENTER_CATCH:
      break;
    case OP_EXIT_CATCH:
      break;
    default:
      fprintf(stderr, "ERROR! bad opcode 0x%x\n", opcode);
      _debug_vm(vm);
      
      goto exitloop;
    }
    
    printf("\n");
  }
  
exitloop:
  vm->regs[IP].p.ptr = (uint64_t) code;
  vm->regs[SP].p.ptr = (uintptr_t) sp;
  vm->regs[FLAGS].p.ptr = flags;
  vm->regs[EXCEPT].p.ptr = except;
}

int SVM_PushScope(struct SimpleVM *vm) {
  val_t scope = SVM_SimpleObjCopy(vm, vm->scope);
  
  //set scope parent
  SVM_SetField(vm, scope, SCOPE_FIELD_NAME, vm->scope);
  vm->scope = scope;
  
  return 0;
}

int SVM_PopScope(struct SimpleVM *vm) {
  val_t scope = SVM_GetField(vm, vm->scope, SCOPE_FIELD_NAME);
  
  if (scope == JS_UNDEFINED) {
    //XXX throw some sort of exception
    return -1;
  }
  
  vm->scope = scope;
  
  return 0;
}

void SVM_FlagInterrupt(struct SimpleVM *vm, int interrupt, int arg) {
}

void SVM_Exception(struct SimpleVM *vm, int exc, val_t arg) {
  uintptr_t *tstack = (uintptr_t *)vm->regs[RTRYSTACK].p.ptr;
  
  if (tstack >= 0) {
    doubleunion_t *sp;
    
    //unwind stack
    vm->regs[SP].p.ptr = *tstack;
    //jump to handler
    vm->regs[IP].p.ptr = *tstack;
    
    //pop try/catch stack
    tstack++;
    vm->regs[RTRYSTACK].p.ptr = (uint64_t)tstack;
    
    //push exception arg
    sp = (doubleunion_t *) vm->regs[SP].p.ptr;
    (--sp)->d = arg;
  }
  
  //XXX uncaught exception!
  fprintf(stderr, "Error: uncaught exception %d!\n", exc);
  exit(-1);
}

void SVM_Interrupt(struct SimpleVM *vm, val_t handler, int interrupt, val_t arg) {
  //this is like SVM_FuncCall, but doesn't run the vm
  doubleunion_t val = VAL2UNION(handler);
  
  if (val.p.type == TYPE_FUNCTION) {
    SVMFunc *ob = (SVMFunc*)SVM_Val2Obj(handler);
    doubleunion_t *sp = (doubleunion_t*) vm->regs[SP].p.ptr;
    val_t scope;
    int i;
    
    if (!ob) { //XXX add exception!
      return;
    }
    
    //clone global scope
    scope = SVM_SimpleObjCopy(vm, vm->global);
    SVM_SetField(vm, scope, SCOPE_FIELD_NAME, vm->scope);
    vm->scope = scope;
    
    //set return pointer into interrupt return helper code
    (--sp)->p.ptr = (uint64_t) interrupt_helper;
    
    //push argument
    (--sp)->d = arg;
    
    //set this var to undefined
    SVM_SetField(vm, vm->scope, JS_THIS_STR, JS_UNDEFINED);
    
    //set instruction and stack pointers
    vm->regs[IP].p.ptr = ob->entry;
    vm->regs[SP].p.ptr = (uint64_t) sp;
    
    //push stack return value
    (--sp)->p.ptr = vm->regs[IP].p.ptr;
  } else if (val.p.type == TYPE_CDECL_FUNCTION) {
    c_callback cb = (c_callback) val.p.ptr;
    
    cb(vm, JS_UNDEFINED, 1, &arg);
  } else {
    //XXX raise exception
  }
}

val_t SVM_FuncCall(struct SimpleVM *vm, val_t dval, val_t dthis, int totarg, val_t *args) {
  doubleunion_t val = VAL2UNION(dval);
  
  if (val.p.type == TYPE_FUNCTION) {
    SVMFunc *ob = (SVMFunc*) SVM_Val2Obj(dval);
    doubleunion_t *sp = (doubleunion_t*) vm->regs[SP].p.ptr;
    int i;
    bytecode_t *bp;
    
    if (!ob) { //XXX add exception!
      return JS_UNDEFINED;
    }

    SVM_PushScope(vm);
    
    bp = vm->breakpoint; //save existing breakpoint
    
    (--sp)->p.ptr = vm->regs[IP].p.ptr;  //push stack return value
    vm->breakpoint = (bytecode_t*) vm->regs[IP].p.ptr; //but, break afterwards
    
    SVM_SetField(vm, vm->scope, JS_THIS_STR, dval); //set this var
    
    //push arguments in reverse order
    for (i=0; i<totarg; i++) {
      (--sp)->d = args[totarg-i-1];
    }
    
    //set instruction and stack pointers
    vm->regs[IP].p.ptr = ob->entry;
    vm->regs[SP].p.ptr = (uint64_t) sp;
    
    //run function bytecode
    SVM_Step(vm);
    
    //cleanup
    sp += totarg;
    vm->breakpoint = bp;
    SVM_PopScope(vm);
    
    //return value should be in RRETVAL register
    return vm->regs[RRETVAL].d;
  } else if (val.p.type == TYPE_CDECL_FUNCTION) {
    c_callback cb = (c_callback) val.p.ptr;
    
    return cb(vm, dthis, totarg, args);
  } else {
    return JS_UNDEFINED; //XXX raise exception
  }
}
