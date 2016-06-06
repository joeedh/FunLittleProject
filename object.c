#include <stdio.h>
#include <string.h>
#include <stdlib.h>

#include "alloc.h"
#include "statemachine.h"
#include "literal.h"

char *SVM_TypeToStr(val_t dval) {
  doubleunion_t val;
  static char tmp[64];
  
  val.d = dval;
  switch (val.p.type) {
    case TYPE_NUMBER:
      return "number";
    case TYPE_OBJECT:
      return "object";
    case TYPE_UNDEFINED:
      return "undefined";
    case TYPE_FUNCTION:
      return "function";
    case TYPE_CDECL_FUNCTION:
      return "cdecl_function";
    case TYPE_STRING:
      return "string";
    case TYPE_ARRAY:
      return "array";
    case TYPE_BYTE_ARRAY:
      return "byte_array";
    default:
      sprintf(tmp, "(bad type code %d)", val.p.type);
      return (char*)tmp;
  }
}
void SVM_FreeObject(SVMObject *ob) {
  if (ob->fields)
    MEM_free(ob->fields);
  if (ob->names)
    MEM_free(ob->names);
  
  MEM_free(ob);
}

int SVM_FindField(SimpleVM *vm, val_t val, char *field) {
  SVMObject *ob = CAST_OBJECT(val);

  if (!ob) {
    return -1;
  }
  
  int i;
  
  if (!ob->names) {
    return -1;
  }
  
  for (i=0; i<ob->totfield; i++) {
    char *name = LT_GetStr(&vm->literals, ob->names[i]);
    
    if (!strcmp(name, field)) {
      return i;
    }
  }
  
  return -1;
}

int SVM_FindFieldI(SimpleVM *vm, val_t val, int field) {
  SVMObject *ob = CAST_OBJECT(val);

  if (!ob) {
    return -1;
  }
  
  int i;
  
  if (!ob->names) {
    return -1;
  }
  
  for (i=0; i<ob->totfield; i++) {
    if (ob->names[i] == field)
      return i;
  }
  
  return -1;
}


val_t SVM_MakeObject(SimpleVM *vm, int type) {
  SVMObject *ob = MEM_calloc(sizeof(*ob));
  LinkNode *node = MEM_malloc(sizeof(*node));
  
  ob->type = TYPE_OBJECT;
  node->value = ob;
  List_Append(&vm->objects, node);
  
  return SVM_Obj2Val(ob);
}

static void svm_obj_ensuresize(SimpleVM *vm, SVMObject *ob, int size) {
  if (size >= ob->size) {
    int newsize = (size+1)*2;
    int *newnames = MEM_malloc(sizeof(*newnames)*newsize);
    val_t *newfields = MEM_malloc(sizeof(*newfields)*newsize);
    
    if (ob->fields) {
      memcpy(newfields, ob->fields, sizeof(*ob->fields)*ob->size);
      memcpy(newnames, ob->names, sizeof(*ob->names)*ob->size);
      
      MEM_free(ob->fields);
      MEM_free(ob->names);
    }
    
    ob->size = newsize;
    ob->names = newnames;
    ob->fields = newfields;
  }
}

void SVM_SetFieldI(SimpleVM *vm, val_t dval, int name, val_t setval) {
  doubleunion_t val = VAL2UNION(dval);
  
  SVMObject *ob = CAST_OBJECT(val);
  if (!ob) {
    //XXX raise an error
    return;
  }
  
  if (val.p.type != TYPE_OBJECT) {
    fprintf(stderr, "Error: not an object!\n");
    return;
  }
  
  int i = SVM_FindFieldI(vm, SVM_Obj2Val(ob), name);
  
  if (i < 0) {
    svm_obj_ensuresize(vm, ob, ob->totfield+1);
    ob->names[ob->totfield++] = name;
    
    i = SVM_FindFieldI(vm, SVM_Obj2Val(ob), name);
  }
  
  ob->fields[i] = setval;
}

void SVM_SetField(SimpleVM *vm, val_t dval, char *name, val_t setval) {
  doubleunion_t val = VAL2UNION(dval);
  
  SVMObject *ob = CAST_OBJECT(val);
  if (!ob) {
    //XXX raise an error
    return;
  }
  
  if (val.p.type != TYPE_OBJECT) {
    fprintf(stderr, "Error: not an object!\n");
    return;
  }
  
  int i = SVM_FindField(vm, SVM_Obj2Val(ob), name);
  if (i < 0) {
    svm_obj_ensuresize(vm, ob, ob->totfield+1);
    ob->names[ob->totfield++] = LT_GetStrLit(&vm->literals, name);
    
    i = SVM_FindField(vm, SVM_Obj2Val(ob), name);
  }
  
  ob->fields[i] = setval;
}

val_t SVM_MakeNativeFunc(SimpleVM *vm, c_callback func) {
  doubleunion_t val;
  
  val.p.type = TYPE_CDECL_FUNCTION;
  val.p.ptr = (uintptr_t)func;
  
  return val.d;
}

val_t SVM_GetField(SimpleVM *vm, val_t val, char *name) {
  SVMObject *ob = CAST_OBJECT(val);
  
  if (!val) {
    return JS_UNDEFINED; //XXX raise error. . .handle primitive types? auto-boxing? or not?
  }
  
  int i = SVM_FindField(vm, SVM_Obj2Val(ob), name);
  
  if (i >= 0) {
    return ob->fields[i];
  }
  
  return JS_UNDEFINED;
}

val_t SVM_GetFieldI(SimpleVM *vm, val_t val, int name) {
  SVMObject *ob = CAST_OBJECT(val);
  
  if (!val) {
    return JS_UNDEFINED; //XXX raise error. . .handle primitive types? auto-boxing? or not?
  }
  
  int i = SVM_FindFieldI(vm, SVM_Obj2Val(ob), name);
  
  if (i >= 0) {
    return ob->fields[i];
  }
  
  return JS_UNDEFINED;
}

val_t SVM_SimpleObjCopy(SimpleVM *vm, val_t scope) {
  SVMObject *ob = SVM_Val2Obj(scope);
  val_t scope2 = SVM_MakeObject(vm, TYPE_OBJECT);
  int i;
  
  for (i=0; i<ob->totfield; i++) {
    SVM_SetFieldI(vm, scope2, ob->names[i], ob->fields[i]);
  }
  
  return scope2;
}
