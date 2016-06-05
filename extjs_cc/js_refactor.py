from js_cc import js_parse
from js_process_ast import *
from js_ast import *
from js_global import glob
from js_typespace import *
from js_parser_only_ast import *

import os, sys, struct, time, random, math, os.path
def handle_potential_class(result, ni, typespace):
  c = result[ni]
  op = c[0].gen_js(0).strip();
  
  name = c[1][0].gen_js(0).strip()

  if op == "inherit":
    parents = [c[1][1].gen_js(0).strip()];
  else:
    parents = []
  
  cls = ClassNode(name, parents)
  constructor = None
  
  i = ni-1
  while i >= 0:
    n = result[i]
    if type(n) == FunctionNode:
      if n.name == name:
        constructor = n
        break
        
    i -= 1
  
  if constructor == None:
    typespace.error("Could not find constructor for " + name + ".", result[ni])
  
  
  members = {}
  i = ni;
  m1 = js_parse("obj.prototype.func = {}");
  m2 = js_parse("obj.func = {}");
  while i < len(result):
    n = result[i];
    bad = type(n) != AssignNode
    bad |= type(n[1]) != FunctionNode
    
    if bad: 
      i += 1
      continue
    
    root = n[0]
    while type(root) == BinOpNode:
      root = root[0]
    
    bad = root.gen_js(0).strip() != name
    if bad:
      i += 1
      continue
    
    is_static = False
    if root.parent[1].gen_js(0) == "prototype":
      method_name = root.parent.parent[1].gen_js(0).strip()
    else:
      method_name = root.parent[1].gen_js(0).strip()
      is_static = True
    
    f = n[1]
    
    print(method_name)
    m = MethodNode(method_name)
    m.add(f[0])
    
    if len(f) > 2:
      s = StatementList()
      for c in f.children[1:]:
        s.add(c)
    else:
      m.add(f[1])
    cls.add(m)
    
    i += 1
  
  print(name, parents, constructor.name)
  
  if name != "ClassTest":
    sys.exit()
  
def refactor(data):
  result = js_parse(data)
  if result == None: result = StatementList()
  
  """
  def set_smap(n, smap):
    n.smap = smap
    for c in n:
      set_smap(c, smap)
  smap = SourceMap()
  set_smap(result, smap)
  result.gen_js(0)
  #"""
  
  typespace = JSTypeSpace()
  flatten_statementlists(result, typespace)
  
  for c in result:
    if type(c) == FuncCallNode and c[0].gen_js(0).strip() in ["inherit", "create_prototype"]:
      handle_potential_class(result, result.index(c), typespace)
      
  print(len(result))
  
  
  buf = data
  
  return buf, result
  
