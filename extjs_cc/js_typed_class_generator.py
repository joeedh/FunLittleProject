from js_ast import *
from js_process_ast import *
from js_cc import js_parse
from js_global import Glob, glob
from js_typed_classes import resolve_type

import os, sys, os.path, struct, imp, shutil, time, random, math

"""
  okay.  basic  data model of typed objects:
  each object compiles to an array of typed arrays, like so:
  
  [float array, int array, byte array, etc]
  
  an object reference is just an array, like so:
  [reference to above typed arrays, starting offset (in bytes)]
  
"""

FLOAT_ARR = 0
INT_ARR = 1
BYTE_ARR = 2
DOUBLE_ARR = 3
LONGLONG_ARR = 4

def gen_class_code(node, typespace):
  ret = StatementList()
  
  def replace_this(n):
    if type(n) in [IdentNode, VarDeclNode] and n.val == "this":
      n.val = "self"
    
    for c in n.children:
      if type(c) in [FunctionNode, ClassNode, TypedClassNode]: continue
      if type(c) == BinOpNode and c.op == ".":
        replace_this(c[0])
        continue
      
      replace_this(c)
      
  methods = list(node.methods.values()) + list(node.getters.values()) + list(node.setters.values())
  for m in methods:
    if type(m) == MethodNode:
      name = node.name + "__" + m.name
    elif type(m) == MethodGetter:
      name = node.name + "_get__" + m.name
    elif type(m) == MethodSetter:
      name = node.name + "_set__" + m.name
      
    func = FunctionNode(name)
    func.add(m[0].copy())
    func.add(m[1].copy())
    
    func[0].prepend(VarDeclNode(ExprNode([]), name="self"))
    func[0][0].type = TypedClassRef(node)
    func[0][0].add(func[0][0].type)
    
    for c in func:
      replace_this(c)
    
    ret.add(func)
    
  return ret

class TransformVisit (NodeVisit):
  def __init__(self, typespace):
    NodeVisit.__init__(self)
    self.typespace = typespace
    self.required_nodes = []
  
  def FunctionNode(self, node, scope, t, tlevel):
    scope = dict(scope)
    
    for c in node[0]:
      n = c
      while type(n) not in [VarDeclNode, IdentNode]:
        n = n[0]
      scope[n.val] = c
      
    for c in node[1:]:
      t(c, scope, tlevel)
  
  def var_transform(self, cls, var, member):
    #print(cls, var, member)
    if type(member) != str: member = member.val
    
    p = cls.childmap[member]
    if type(p) == VarDeclNode:
      arr = -1
      t = p.type
      while type(t) == StaticArrNode:
        t = t[0]
          
      if type(t) == BuiltinTypeNode:
        if t.type == "int": arr = INT_ARR
        elif t.type == "float": arr = FLOAT_ARR
        elif t.type == "byte": arr = BYTE_ARR
        
      if arr == -1: 
        self.typespace.error("internal error", var)
      
      off = p.start
      ret = js_parse(var.gen_js(0) + "[%d][%d];" % (arr, off), start_node=ArrayRefNode)
      ret.type = p
      
      return ret
    elif type(p) in [MethodGetter, MethodSetter]:
      #see if we have a getter
      if member in cls.getters:
        p = cls.getters[member]
        cls = p.parent
        
        name = cls.name + "_get__" + p.name
        ret = js_parse(name+"($n)", [var], start_node=FuncCallNode)
        
        ret.src = p
        return ret
      else:
        cls = p.parent
        
        name = cls.name + "_set__" + p.name
        ret = js_parse(name+"($n)", [var], start_node=FuncCallNode)
        ret.src = p
      
        return ret
    return IdentNode("[implement me]")
  
  def ArrayRefNode(self, node, scope, t, tlevel):
    #label any child array refs
    
    if type(node.parent) != ArrayRefNode:
      lvl = 0
      n = node
      while type(n) == ArrayRefNode:
        n.lvl = lvl
        n = n[0]
        lvl += 1
      n = node
      for i in range(lvl):
        #n.lvl = lvl - i - 1
        n = n[0]
      
    t(node[0], scope, tlevel)
    t(node[1], scope, tlevel)
    
    if node[0].type != None: 
      print(type(node[0].type.parent))
    
    if node[0].type != None and type(node[0].type.parent) == TypedClassNode:
      #now.  theoretically, we should have a nice little ArrayRefNode
      #as a child
      if type(node[0]) != ArrayRefNode:
        typespace.error("Internal parse error 2",  node)
      
      t = node[0].type.type
      if type(t) != StaticArrNode:
        typespace.error("Invalid array lookup on non-array value", node);
      
      print(node.lvl, "<-------------------------")
      ref = node[0]
      
      b = 1
      for i in range(node.lvl):
        t = t[0]
      
      for i in range(node.lvl):
        t = t.parent
        b *= t.size
        
      print("yay", t.size)
      
      a = ref[1]
      c = node[1]
      
      if type(a) == NumLitNode and type(c) == NumLitNode:
        a.val = int(a.val) + int(c.val)*b
      else:
        ref.replace(a, BinOpNode(a, BinOpNode(NumLitNode(b), c, "*"), "+"))
      
      node.parent.replace(node, ref)
  
  def AssignNode(self, node, scope, t, tlevel):
    t(node[0], scope, tlevel)
    t(node[1], scope, tlevel)
    
    #detect setters, which are inserted by var_transform *only* if
    #a getter doesn't exist, otherwise a getter is inserted and
    #we check if there's a setter here.
    if type(node[0]) == FuncCallNode and hasattr(node[0], "src"):
      #var_transform will insert a getter, if it exists, before
      #a setter.
      if "_get__" in node[0][0].gen_js(0):
        cls = node[0].src.parent
        name = node[0].src.name
        if name in cls.setters:
          n2 = IdentNode(cls.name + "_set__" + name)
          node[0].replace(node[0][0], n2)
        else:
          self.typespace.error("Cannot assign to read-only property "+name, node)
          
      if not "_set__" in node[0].gen_js(0):
        self.typespace.error("Cannot assign values to function calls", node)
      
      n2 = node[1]
      node.remove(n2)
      
      node[0][1].add(n2)
      node.parent.replace(node, node[0])
      
  def BinOpNode(self, node, scope, t, tlevel):
    if node.op == "=":
      self.AssignNode(node, scope, t, tlevel)
      return
    
    if node.op == ".":
      t1 = resolve_type(self.typespace, node[0], scope)
      t2 = resolve_type(self.typespace, node[1], scope)
      
      base = node[0]
      while type(base) not in [VarDeclNode, IdentNode]:
        base = base[0]
      
      if type(t1) == TypedClassNode and type(node[1]) == IdentNode:
        scope = dict(scope)
        scope[node[1].val] = t1.childmap[node[1].val]
        
        node.parent.replace(node, self.var_transform(t1, base, node[1].val))
        return
        
    t(node[0], scope, tlevel)
    t(node[1], scope, tlevel)

def type_size(node, typespace):
  size = 0
  basesize = 0
  t = resolve_type(typespace, node, {})
  
  print(t, "s")
  if type(t) == StaticArrNode:
    n = t
    size = 1
    while type(n) == StaticArrNode:
      size *= n.size
      n = n[0]
    
    size2, basesize = type_size(n, typespace)
    if basesize > 4: basesize = 8
    
    size *= size2
  elif type(t) == BuiltinTypeNode:
    if t.type in ["float", "int"]:
      size = 4
    elif t.type in ["double", "long long"]:
      size = 8
    elif t.type in ["char", "byte"]:
      size = 1
    else:
      typespace.error("Invalid builtin type " + t.type, node)
    basesize = size
  elif type(t) == TypedClassNode:
    if t.size == None: layout_class(t, typespace)
    size = t.size
    
    #typed classes are four-byte-aligned *if*
    #their size is four bytes or less, otherwise
    #they are eight byte aligned.
    basesize = 4 if size <= 4 else 8
    
  return size, basesize
  
def layout_class(node, typespace):
  #struct rules!
  #ints are 32 bits.  so are floats.
  #ints, floats, and structures are 4-byte aligned
  
  #generate list of properties, in right order
  #this of course is not guaranteed by node.props, which 
  #is a dict.
  
  #first 4 bytes are reserved for an integer reference
  #to a class vtable.  in the future, this ref should be
  #omitted if the compiler detects that it's not needed.
  
  props = []
  for c in node:
    if type(c) == VarDeclNode:
      props.append(c)
  
  byte = 4
  for p in props:
    size, basesize = type_size(p, typespace)
    
    if size == 0:
      typespace.error("failed to calculate struct layout", node)
    
    #do byte alignment
    while (byte%basesize) != 0:
      byte += 1
    
    p.start = byte
    p.size = size
    byte += size
    
def do_transform(node, typespace):
  for k in typespace.types:
    t = typespace.types[k]
    if type(t) != TypedClassNode: continue
    layout_class(t, typespace)
    
  visit = TransformVisit(typespace)
  visit.traverse(node)
  
class TypedArrayClassGen:
  def __init__(self):
    self.has_typed_classes = False
    
  def boilerplate(self, node, typespace):
    ret = gen_class_code(node, typespace)
    self.has_typed_classes = True
    return ret
  
  def transform(self, node, typespace):
    print("yay, transform")
    if self.has_typed_classes:
      do_transform(node, typespace)
