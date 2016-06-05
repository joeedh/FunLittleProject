#ifndef _CONST_H
#define _CONST_H

#if defined(__x86_64__) || defined(_M_IA64) || defined(_M_IA64) || defined(_WIN64)
#define PTRSIZE 8
#define HAVE_PTR64
#else
#define PTRSIZE 4
#endif

#define JS_NAN 0x7fff
#define JS_UNDEFINED 0x1ffd
#define JS_NULL      0x1ffd //XXX should be different than undefined somehow
#define JS_TRUE      ((0x7fff) | (1<<16))
#define JS_FALSE     0x7fff;

#define JS_THIS_STR  "$this$"

#define CAST_OBJECT(val) ((SVMObject*)(*(doubleunion_t*)&(val)).p.ptr)
//detects numbers, as well as real numeric NaNs
#define ISNUMBER(val) (!isnan(val) || (*(doubleunion_t*)(&(val))).p.type == TYPE_NUMBER)

#define BREAKPOINT_NONE ((bytecode_t*)0x7FFFFFFFL)

#endif /* _CONST_H */
