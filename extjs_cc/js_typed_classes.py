from js_global import glob, Glob
from js_ast import *
from js_process_ast import *
from js_cc import js_parse

"""
typed class a extends b {
  int a, b[32] = {0, 2, 2}; //rest of array will be zero'd
  bleh;
}

okay, typed classes!  a few rules:

* no type inference within typed class code
* single inheritance only
* valid array initializers
"""

def load_typed_class(node, typespace):
  #propagate node.getters/setters/props/methods
  node.start(typespace)
  
  if node.name in typespace.types:
    typespace.error(node.name + " is already defined", node)
    
  typespace.types[node.name] = node
  
class TypedClassValidator (NodeVisit):
  def __init__(self, typespace):
    NodeVisit.__init__(self)
    self.required_nodes = []
    self.typespace = typespace
    
  def TypedClassNode(self, node, scope, t, tlevel):
    scope["this"] = node
    for c in node:
      t(c, scope, tlevel)
  
  def MethodNode(self, node, scope, t, tlevel):
    scope = dict(scope)
    for c in node[0]:
      n = c
      while type(n) not in [VarDeclNode, IdentNode]:
        n = n[0]
      scope[n.val] = n
      
    for c in node[1:]:
      t(c, scope, tlevel)
    
  def MethodGetter(self, node, scope, t, tlevel):
    self.MethodNode(node, scope, t, tlevel)
    if node.type == None or type(node.type) == UnknownTypeNode:
      self.typespace.error("type required for gettter " + node.name, node)
      
  def MethodSetter(self, node, scope, t, tlevel):
    def rec(ts, n):
      if type(n) == ReturnNode:
        if not (len(n) == 0 or type(n[0]) == ExprNode and len(n[0]) == 0):
          ts.error("setters can't return anything", n)
        
      for c in n:
        if type(c) in [FunctionNode, MethodNode, ClassNode, TypedClassNode]: continue
        rec(ts, c)
    
    self.MethodNode(node, scope, t, tlevel)
    
    #the parameters of setters must be typed
    if node[0][0].type == None or type(node[0][0].type) == UnknownTypeNode:
      self.typespace.error("type required for setter argument " + node.name, node)
    
    #setters can't have a return type
    if node.type != None and type(node.type) != UnknownTypeNode:
      self.typespace.error("setters can't have return types", node)
    
    #make sure all return statements have no value
    rec(self.typespace, node)
    
  def FunctionNode(self, node, scope, t, tlevel):
    #remove 'this'
    scope = dict(scope)
    if "this" in scope: del scope["this"]
    for c in node:
      t(c, scope, tlevel)
  
  def BinOpNode(self, node, scope, t, tlevel):
    if node.op == "." and type(node[1]) == IdentNode:
      b = type(node[1]) == IdentNode
      b = b and (type(node[0]) == IdentNode and node[0].val in scope and type(scope[node[0].val]) == TypedClassNode)
      
      if b:
        if node[1].val not in scope[node[0].val].childmap:
          self.typespace.error("typed class " + scope[node[0].val].name + " has no member '" + node[1].val + "'", node)
        scope = dict(scope)
        scope[node[1].val] = scope[node[0].val].childmap[node[1].val]
   
    t(node[0], scope, tlevel)
    t(node[1], scope, tlevel)
  
  def AssignNode(self, node, scope, t, tlevel):
    #print(resolve_type(self.typespace, node, scope))
    t1 = base_type(resolve_type(self.typespace, node[0], scope))
    t2 = base_type(resolve_type(self.typespace, node[1], scope))
    
    print(t1, t2)
    if not types_match(t1, t2):
      self.typespace.error("type mismatch", node)

def types_match(t1, t2):
  if type(t1) == BuiltinTypeNode and type(t2) == BuiltinTypeNode: return t1.type == t2.type
  else: return t1 != None and type(t1) != UnknownTypeNode and t1 == t2

def base_type(node):
  if type(node) == MethodGetter:
    return base_type(node.type)
  elif type(node) == MethodSetter:
    return base_type(node[0][0].type)
  elif type(node) == MethodNode:
    return base_type(node.type)
  elif type(node) == ArrayRefNode:
    return base_type(node[0])
  elif type(node) == StaticArrNode:
    return base_type(node[0])
  elif type(node) == FunctionNode:
    return base_type(node[0])
  elif type(node) == VarDeclNode:
    return base_type(node.type)
  
  return node
  
def resolve_type_intern(typespace, node, scope):
  #higher level nodes first, then type nodes
  if type(node) == BinOpNode:
    t1 = resolve_type_intern(typespace, node[0], scope)
    
    if node.op == "." and type(node[1]) == IdentNode and type(t1) == TypedClassNode:
      if node[1].val not in t1.childmap:
        typespace.error("typed class " + t1.name + " has no member " + node[1].val, node)
      ret = t1.childmap[node[1].val] 
      if type(ret) == VarDeclNode:
        return ret.type
      else:
        return ret
    elif node.op == ".":
      return node[1].type
  elif type(node) == StaticArrNode:
    return node
  elif type(node) == ArrayRefNode:
    
    n = node[0]
    while type(n) == ArrayRefNode:
      n = n[0]
    
    ret = base_type = resolve_type_intern(typespace, n, scope)
    n = node
    while type(n) == ArrayRefNode:
      n = n[0]
      ret = ret[0]
    return ret
  elif type(node) == AssignNode:
    return resolve_type_intern(typespace, node[0], scope)
  elif type(node) == IdentNode and node.val in scope:
    return resolve_type_intern(typespace, scope[node.val], scope)
  elif type(node) == IdentNode and node.val in typespace.types:
    return typespace.types[node.val]
  elif type(node) == TypedClassNode:
    return node
  elif type(node) == str and node in ["int", "float", "byte", "char", "double", "short"]:
    return BuiltinTypeNode(node)
  elif type(node) == NumLitNode:
    return BuiltinTypeNode("float" if ("." in str(node.val) or "e" in str(node.val)) else "int")
  elif type(node) == VarDeclNode:
    return resolve_type(typespace, node.type, scope)
  elif type(node) == TypedClassRef:
    return node.type
  elif type(node.type) == MethodGetter:
    return resolve_type(typespace, node.type.type, scope)
  elif isinstance(node, TypeNode):
    return node
  
  return node.type

def resolve_type(typespace, node, scope):
  ret = resolve_type_intern(typespace, node, scope)
  if type(ret) == TypedClassRef:
    return ret.type
  return ret
  
def validate_typed_class(node, typespace):
  nvisit = TypedClassValidator(typespace)
  nvisit.traverse(node)

from js_typed_class_generator import TypedArrayClassGen
def expand_typed_classes(node, typespace):
  gen = TypedArrayClassGen()
  
  def load_classes(n):
    load_typed_class(n, typespace)
    
  def validate_classes(n):
    validate_typed_class(n, typespace)
  
  def gen_boilerplate(n):
    ret = gen.boilerplate(n, typespace)
    n._boilerplate = ret
  
  def do_finish(n):
    if type(n.parent) != StatementList: return
    
    n.parent.replace(n, n._boilerplate)
    
  #step one: load classes
  traverse(node,  TypedClassNode, load_classes)
  
  #step two: validate ast tree
  traverse(node, TypedClassNode, validate_classes)
  
  #step three: generate boilerplate code
  traverse(node, TypedClassNode, gen_boilerplate)
  
  #step four: get rid of TypeClassNode's
  traverse(node, TypedClassNode, do_finish)
  
  #step five: apply main code transformation
  gen.transform(node, typespace)
  
  #flatten any nested statement lists
  flatten_statementlists(node, typespace)
  