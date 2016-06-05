#include <stdio.h>
#include <string.h>
#include <stdlib.h>

#include "alloc.h"
#include "statemachine.h"
#include "float.h"
#include "const.h"
#include "literal.h"

void LT_Init(LitTable *table) {
  memset(table, 0, sizeof(*table));
}

char *LT_GetStr(LitTable *table, int lit) {
  doubleunion_t val = table->literals[lit];
  
  if (val.p.type != TYPE_STRING) {
    fprintf(stderr, "Error! Not a string!\n");
    return "bleh";
  }
  
  return (char*) val.p.ptr;
}

void LT_Release(LitTable *table) {
  if (table->literals)
    MEM_free(table->literals);
}

void LT_EnsureSize(LitTable *table, int size) {
  if (size >= table->size) {
    int newsize = (size+2)*2; //make sure we're always at least 4 bytes large
    printf("old table: %p, newsize: %d\n", table->literals, newsize);
    
    doubleunion_t *newlit = MEM_malloc(newsize*sizeof(doubleunion_t));
    
    if (table->literals) {
      memcpy(newlit, table->literals, sizeof(val_t)*newsize);
      MEM_free(table->literals);
    }
    
    table->literals = newlit;
    table->size = newsize;
  }
}

static int lt_eq(val_t da, val_t db) {
  doubleunion_t a = VAL2UNION(da), b = VAL2UNION(db);
  int ta = a.p.type, tb = b.p.type;
  
  if (ta == TYPE_STRING && tb == TYPE_STRING) {
    char *sa = (char*) a.p.ptr, *sb = (char*)b.p.ptr;
    return !strcmp(sa, sb);
  } else if (ISNUMBER(da) && ISNUMBER(db)) {
    return a.d == b.d;
  } else if (ISNUMBER(da) !=ISNUMBER(db)) {
    //return NaN
    return 0; //JS_NAN;
  } else {
    fprintf(stderr, "bad literal! ta, tb: %d, %d\n", a.p.type, b.p.type);
    return 0; //eek!
  }
  
  return 0;
}

int LT_GetStrLit(LitTable *table, char *str) {
  doubleunion_t dval;
  
  dval.p.ptr = (uint64_t) str;
  dval.p.type = TYPE_STRING;
  
  return LT_GetLit(table, *(val_t*)&dval);
}

int LT_GetLit(LitTable *table, val_t dval) {
  int i;
  doubleunion_t val = VAL2UNION(dval);
  
  for (i=0; i<table->used; i++) {
    if (lt_eq(val.d, table->literals[i].d)) {
      break;
    }
  }
  
  if (i == table->used) {
    if (val.p.type == TYPE_STRING) { //make copies of strings, if necassary
      val.p.ptr = (uint64_t) strdup((void*)val.p.ptr);
    }
    
    LT_EnsureSize(table, table->used+1);
    table->literals[table->used++] = val;
  }
  
  return i;
}
