from js_cc import js_parse

from js_ast import *
from js_process_ast import *
from js_global import glob
from js_typespace import *

_s_rec_idgen = 1

class ScopeRecord:
  def __init__(self, type, name):
    global _s_rec_idgen
    
    self.type = type
    self.name = name
    self.func_nest = 0; #how deep into nested functions are we
    self.nest = 0; 
    self.uuid = "$_"+type+"_" + name + str(_s_rec_idgen);
    
    _s_rec_idgen += 1
  
  def __repr__(self):
    return str(self)
  
  def __str__(self):
    s = "ScopeRecord(name="+str(self.name)
    s += ", type=" + str(self.type) + ", nest=" + str(self.nest)
    s += ", uuid=" + str(self.uuid) + ", func_nest="
    s += str(self.func_nest)+")"
    
    return s
    
  def copy(self):
    ret = ScopeRecord(self.type, self.name)
    ret.uuid = self.uuid;
    ret.nest = self.nest;
    ret.func_nest = self.func_nest;
    
    return ret

class Scope(dict):
  pass
  
def copy_scope(scope):
  scope2 = Scope(scope)
  scope2.parent = scope
  if hasattr(scope, "func_parent"):
    scope2.func_parent = scope.func_parent
    
  scope = scope2
    
  for k in scope:
    if type(scope[k]) == ScopeRecord:
      scope[k] = scope[k].copy()
      scope[k].nest += 1
      
  return scope
  
class LetVisitor (NodeVisit):
  def __init__(self, typespace):
    NodeVisit.__init__(self)
    self.typespace = typespace
    self.required_nodes = set()
  
  def FunctionNode(self, node, scope, traverse, tlevel):
    scope2 = copy_scope(scope)
    scope2.func_parent = scope
    scope = scope2
    
    for k in scope:
      if scope[k].type == "let":
        scope[k].func_nest += 1
        
    for arg in node[0]:
      val = arg.val
      scope[val] = ScopeRecord("argument", val)

    for c in node[1:]:
      traverse(c, scope, tlevel)
  
  def IdentNode(self, node, scope, traverse, tlevel):
    if type(node.parent) == BinOpNode and node.parent.op == "." and node == node.parent[1]:
      return
      
    if node.val in scope and scope[node.val].type == "let":
      node.val = scope[node.val].uuid
  
  def ForLoopNode(self, node, scope, traverse, tlevel):
    scope = copy_scope(scope)
    
    for c in node:
      traverse(c, scope, tlevel)
    
  def VarDeclNode(self, node, scope, traverse, tlevel):
    if node.val in scope:
      if scope[node.val].nest == 0 and "let" in node.modifiers:
        self.typespace.error(node.val + " is alreaady let-declared", node);
      else:
        del scope[node.val]
    
    if "let" in node.modifiers:
      if hasattr(scope, "func_parent") and node.val in scope.func_parent:
        p = scope.func_parent
        
        if p[node.val].type == "let" and p[node.val].func_nest == 0:
          self.typespace.error("Tried to let variable that was \n\t\tlet'd in parent function scope", node);
          
      if node.val in scope and scope[node.val].type == "let":
        self.typespace.error(node.val + " is alreaady let-declared", node);
      
      rec = ScopeRecord("let", node.val)
      scope[node.val] = rec
      node.val = rec.uuid
      
    for c in node:
      traverse(c, scope, tlevel)
      
  def StatementList(self, node, scope, traverse, tlevel):
    scope = copy_scope(scope)
    
    for c in node:
      traverse(c, scope, tlevel)
      
def process_let(node, typespace):
  flatten_statementlists(node, typespace);
    
  visit = LetVisitor(typespace)
  visit.traverse(node);
  