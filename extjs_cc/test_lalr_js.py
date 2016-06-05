from ply import yacc

def LRGeneratorTable(grammar, method, log):
  print("GRAMMAR!", dir(grammar), "!GRAMMAR");
  
yacc.LRGeneratedTable = LRGeneratorTable

import js_parse
