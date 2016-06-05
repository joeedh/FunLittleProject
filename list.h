#ifndef _LIST_H
#define _LIST_H

//abstract 'class' interface
typedef struct Link {
  struct Link *next, *prev;
} Link;

//example of how to make linkable structs
typedef struct LinkNode {
  struct LinkNode *next, *prev;
  void *value;
} LinkNode;

typedef struct List {
  void *first, *last;
} List;

void List_Append(List *list, void *vitem);
void List_Remove(List *list, void *vitem);

#endif /* _LIST_H */
