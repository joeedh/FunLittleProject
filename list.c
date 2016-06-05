#include <stdlib.h>
#include "list.h"

void List_Append(List *list, void *vitem) {
  Link *l = (Link*) vitem;
  
  if (!list->first) {
    l->next = l->prev = NULL;
    list->first = list->last = l;
  } else {
    l->prev = list->last;
    l->next = NULL;
    ((Link*)list->last)->next = l;
    list->last = l;
  }
}

void List_Remove(List *list, void *vitem) {
  Link *l = (Link*) vitem;
  
  if (l == list->first) {
    list->first = l->next;
  }
  
  if (l == list->last) {
    list->last = l->prev;
  }
  
  if (l->prev)
    l->prev->next = l->next;
  if (l->next)
    l->next->prev = l->prev;
}
