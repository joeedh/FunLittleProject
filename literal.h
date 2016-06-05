#ifndef _LITERAL_H
#define _LITERAL_H
#include "statemachine.h"

void LT_Init(LitTable *table);
void LT_Release(LitTable *table);
void LT_EnsureSize(LitTable *table, int size);

int LT_GetStrLit(LitTable *table, char *str);
int LT_GetLit(LitTable *table, val_t dval);

char *LT_GetStr(LitTable *table, int lit);

#endif /* _LITERAL_H */
