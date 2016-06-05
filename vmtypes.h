#ifndef _VM_TYPES
#define _VM_TYPES

struct SimpleVM;
struct LitTable;

typedef double val_t;
typedef val_t (*c_callback)(struct SimpleVM *vm, val_t dthis, int totarg, val_t *args);

//double encoding
typedef union doubleunion_t {
  val_t d;
  struct {
    uint64_t ptr:48;
    uint64_t type:4;
    uint64_t exp:12;
  } p;
} doubleunion_t;

#define UNION2VAL(val) (*(val_t*)&(val))
#define VAL2UNION(dval) (*(doubleunion_t*)&(dval))

#endif /* _VM_TYPES */
