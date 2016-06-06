#ifndef _SIMPLEVM_OBJECT_H
#define _SIMPLEVM_OBJECT_H

#include "vmtypes.h"
#include "const.h"

#include <stdlib.h>
#include <stddef.h>
#include <stdint.h>
//#include <float.h>

//an array of eight-byte fields
typedef struct SVMObject {
  int type;
  val_t *fields;
  int *names;
  int totfield, size;
} SVMObject;

typedef struct SVMFunc {
  SVMObject head;
  
  int entry; //entry point in bytecode
  int totarg; //number of arguments declared in code.  actual count may differ at runtime
  val_t bound_scope; //for continuations
} SVMFunc;

/*NAN integer encoding
   nan       type                 value
0        11    16                                       64
|         |    |                                         |
v         v    v                                         v
11111111111xxxx0000000000000000000000000000000000000000000 
*/
enum {
  TYPE_NUMBER,
  TYPE_OBJECT,
  TYPE_UNDEFINED,
  TYPE_FUNCTION,
  TYPE_CDECL_FUNCTION,
  TYPE_STRING,
  TYPE_ARRAY,
  TYPE_BYTE_ARRAY
};

struct SimpleVM;

val_t SVM_MakeObject(struct SimpleVM *vm, int type);
char *SVM_TypeToStr(val_t dval);

/*frees SVMObject.  deconstructors starting with Free call MEM_free on 
  the passed in pointer.  ones with Release do not, they only free dependent
  data.*/
void SVM_FreeObject(SVMObject *ob); 

int SVM_FindField(struct SimpleVM *vm, val_t val, char *field);
int SVM_FindFieldI(struct SimpleVM *vm, val_t val, int field);

void SVM_SetField(struct SimpleVM *vm, val_t val, char *name, val_t setval);
void SVM_SetFieldI(struct SimpleVM *vm, val_t val, int name, val_t setval);

val_t SVM_GetField(struct SimpleVM *vm, val_t val, char *name);
val_t SVM_GetFieldI(struct SimpleVM *vm, val_t val, int name);

val_t SVM_FuncCall(struct SimpleVM *vm, val_t val, val_t dthis, int totarg, val_t *args);
val_t SVM_SimpleObjCopy(struct SimpleVM *vm, val_t scope);

//encode into 64-bit double
static val_t SVM_Obj2Val(SVMObject *ob) {
  doubleunion_t val;
  
  val.p.ptr = (uint64_t) ob;
  val.p.type = TYPE_OBJECT;
  
  return val.d;
}

static int SVM_IsObj(val_t dval) {
  doubleunion_t val = VAL2UNION(dval);
  
  switch (val.p.type) {
    case TYPE_OBJECT:
    case TYPE_FUNCTION:
    case TYPE_ARRAY:
    case TYPE_BYTE_ARRAY:
      return 1;
    default:
      return 0;
  }
}

//encode into 64-bit double
static SVMObject *SVM_Val2Obj(val_t dval) {
  doubleunion_t val = VAL2UNION(dval);
  
  return SVM_IsObj(dval) ? (SVMObject*) val.p.ptr : NULL;
}

static int SVM_GetType(val_t dval) {
  uint64_t val = *(uint64_t*)&dval;
  
  return (val>>12) & 7;
}

static int val2int(val_t dval) {
  if (isnan(dval)) {
    return 0;
  }
  
  return (int)dval;
}

static val_t int2val(int ival) {
  return (double)ival;
}

static val_t SVM_ValueOf(struct SimpleVM *vm, val_t dval) {
  doubleunion_t val = VAL2UNION(dval);
  
  if (!isnan(dval)) {
    return dval;
  }
  
  switch (val.p.type) {
    case TYPE_OBJECT:
    case TYPE_FUNCTION: {
      val_t retval = SVM_GetField(vm, dval, "valueOf");
      doubleunion_t cb = VAL2UNION(retval);
      
      if (cb.p.type != TYPE_FUNCTION) {
        return JS_NAN;
      }
      
      return SVM_FuncCall(vm, cb.p.ptr, dval, 0, NULL);
    }
    default:
      return JS_NAN;
  }
}

static int SVM_Truthy(val_t dval) {
  doubleunion_t val = VAL2UNION(dval);
  
  if (!isnan(dval)) {
    return dval != 0.0 && dval != -0.0;
  }
  
  switch (val.p.type) {
    case TYPE_NUMBER:
      return JS_NAN;
    default:
      return 0;
  }
}

#endif /* _SIMPLEVM_OBJECT_H */
