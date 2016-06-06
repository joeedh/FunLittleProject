#include <stdint.h>
#include <stddef.h>
#include <string.h>
#include <stdio.h>
#include <stdlib.h>

#include "bytecode.h"

//to find c-style comments.
//note the non-greedy .*?
//see: http://stackoverflow.com/questions/5079243/regular-expression-in-php-take-the-shortest-match
// /\*.*?\*/

#define _(s)\
  case s:\
    return #s;

/*
 * Strings in AST are encoded as tuples (length, string).
 * Length is variable-length: if high bit is set in a byte, next byte is used.
 * Maximum string length with such encoding is 2 ^ (7 * 4) == 256 MiB,
 * assuming that sizeof(size_t) == 4.
 * Small string length (less then 128 bytes) is encoded in 1 byte.
 */
static size_t decode_varint(const unsigned char *p, int *llen) {
  size_t i = 0, string_len = 0;

  do {
    /*
     * Each byte of varint contains 7 bits, in little endian order.
     * MSB is a continuation bit: it tells whether next byte is used.
     */
    string_len |= (p[i] & 0x7f) << (7 * i);
    /*
     * First we increment i, then check whether it is within boundary and
     * whether decoded byte had continuation bit set.
     */
  } while (++i < sizeof(size_t) && (p[i - 1] & 0x80));
  *llen = i;

  return string_len;
}

static size_t bcode_get_varint(char **ops) {
  size_t ret = 0;
  int len = 0;
  
  (*ops)++;
  ret = decode_varint((unsigned char *) *ops, &len);
  
  *ops += len - 1;
  return ret;
}

static uint32_t bcode_get_target(char **ops) {
  uint32_t target;
  
  (*ops)++;
  memcpy(&target, *ops, sizeof(target));
  
  *ops += sizeof(target) - 1;
  return target;
}

struct bcode;
struct v7;
extern uint64_t bcode_decode_lit(struct v7 *v7, struct bcode *bcode, char **ops);

int oplen(struct v7 *v7, struct bcode *bcode, char *ops) {
  char *p = ops;
  
  switch (*p) {
    case OP_DROP:
    case OP_DUP:
    case OP_2DUP:
      return 1;
    case OP_PUSH_LIT:
    case OP_SAFE_GET_VAR:
    case OP_SET_VAR:
    case OP_GET_VAR: {
        return 2;
      //bcode_decode_lit(v7, bcode, &p);
      //return p - ops;
    }
    case OP_CALL:
    case OP_NEW:
      return 2;
    case OP_JMP:
    case OP_JMP_FALSE:
    case OP_JMP_TRUE:
    case OP_JMP_TRUE_DROP:
    case OP_JMP_IF_CONTINUE:
    case OP_TRY_PUSH_CATCH:
    case OP_TRY_PUSH_FINALLY:
    case OP_TRY_PUSH_LOOP:
    case OP_TRY_PUSH_SWITCH: {
      bcode_get_target(&p);
      return p - ops + 1;
    }
    default:
      return 1;
  }
}
  
char *opcode2str(int code) {
  static retring[16][64];
  static retcur = 0;
  
  //code = code & ~128;
  
  switch(code) {
    _(OP_DROP)
    _(OP_DUP)
    _(OP_2DUP)
    _(OP_SWAP)
    _(OP_STASH)
    _(OP_UNSTASH)
    _(OP_SWAP_DROP)
    _(OP_PUSH_UNDEFINED)
    _(OP_PUSH_NULL)
    _(OP_PUSH_THIS)
    _(OP_PUSH_TRUE)
    _(OP_PUSH_FALSE)
    _(OP_PUSH_ZERO)
    _(OP_PUSH_ONE)
    _(OP_PUSH_LIT)
    _(OP_NOT)
    _(OP_LOGICAL_NOT)
    _(OP_NEG)
    _(OP_POS)
    _(OP_ADD)
    _(OP_SUB)
    _(OP_REM)
    _(OP_MUL)
    _(OP_DIV)
    _(OP_LSHIFT)
    _(OP_RSHIFT)
    _(OP_URSHIFT)
    _(OP_OR)
    _(OP_XOR)
    _(OP_AND)
    _(OP_EQ_EQ)
    _(OP_EQ)
    _(OP_NE)
    _(OP_NE_NE)
    _(OP_LT)
    _(OP_LE)
    _(OP_GT)
    _(OP_GE)
    _(OP_INSTANCEOF)
    _(OP_TYPEOF)
    _(OP_IN)
    _(OP_GET)
    _(OP_SET)
    _(OP_SET_VAR)
    _(OP_GET_VAR)
    _(OP_SAFE_GET_VAR)
    _(OP_JMP)
    _(OP_JMP_TRUE)
    _(OP_JMP_FALSE)
    _(OP_JMP_TRUE_DROP)
    _(OP_JMP_IF_CONTINUE)
    _(OP_CREATE_OBJ)
    _(OP_CREATE_ARR)
    _(OP_NEXT_PROP)
    _(OP_FUNC_LIT)
    _(OP_CALL)
    _(OP_NEW)
    _(OP_CHECK_CALL)
    _(OP_RET)
    _(OP_DELETE)
    _(OP_DELETE_VAR)
    _(OP_TRY_PUSH_CATCH)
    _(OP_TRY_PUSH_FINALLY)
    _(OP_TRY_PUSH_LOOP)
    _(OP_TRY_PUSH_SWITCH)
    _(OP_TRY_POP)
    _(OP_AFTER_FINALLY)
    _(OP_THROW)
    _(OP_BREAK)
    _(OP_CONTINUE)
    _(OP_ENTER_CATCH)
    _(OP_EXIT_CATCH)
    _(MYOP_CREATE_FUNC)
    default: {
      char *msg = code >= OP_MAX ? "(unknown" : "(missing/reserved opcode";
      char *ret = (char*) retring[retcur];
      
      sprintf(ret, "%s: %d)", msg, code);
      retcur = (retcur + 1) & 15;
      
      return ret;
    }
  }
}
