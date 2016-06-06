import traceback, sys
from js_ast import *
from js_global import glob, Glob
from js_typespace import *
from js_cc import *
from js_process_ast import *
from js_util_types import *
import os, os.path
from js_type_emit import resolve_types, types_match, templates_match

from js_v7_bytecode import *
from js_process_ast import NodeVisit, traverse

class Scope (dict):
  pass

def fix_function_calls(result, typespace):
  doneset = set()
  
  def visit(n):
    if n.parent == None: return
    if type(n.parent) != BinOpNode or n.parent.op != ".": return
    
    doneset.add(n._id)
    
    p = n.parent
    p2 = p.parent
    p.replace(n, n[0])
    print("FOUND!")
    
    n.replace(n[0], p)
    p2.replace(p, n)
    #print("N!!!", n)
  
  def traverse2(node, ntype, visit):
    if type(node) == ntype and node._id not in doneset:
      visit(node)
    
    for c in node:
      if c._id not in doneset:
        #doneset.add(c._id)
        traverse2(c, ntype, visit)
      
  traverse2(result, FuncCallNode, visit)
  print("-->", result, "::")
   
class NodeVisit2:
  def __init__(self, typespace):
    self.required_nodes = set()
    self.typespace = typespace
    
  def traverse(self, node):
    typestr = type(node).__name__
    
    if not hasattr(self, typestr) and typestr in self.required_nodes:
      raise RuntimeError("Unimplemented node visit for node type %s", typestr)
    elif not hasattr(self, typestr):
      for c in node:
        self.traverse(c)
      return
      
    def trav(node):
      self.traverse(node)
    
    getattr(self, typestr)(node, trav)

class IDGen:
  def __init__(self):
    self.idgen = 0
    
  def next(self):
    self.idgen += 1
    return self.idgen - 1;
    
class ConstPool:
  def __init__(self, idgen):
    self.map = {}
    self.consts = []
    self.idgen = idgen
    
  def get(self, const):
    if const in self.map:
      return self.map[const][1]
    
    self.map[const] = [len(self.consts), self.idgen.next()]
    self.consts.append(const)
    
    return self.map[const][1]

bin_opmap = {
  "+" : "add",
  "-" : "sub",
  "*" : "mul",
  "/" : "div",
  ">" : "gt",
  "<" : "lt",
  "==" : "eq",
  "<=" : "lte",
  ">=" : "gte",
  "&"  : "band",
  "&&" : "land",
  "|"  : "bor",
  "||" : "lor",
  "^"  : "bxor",
  "!"  : "linv",
  "~"  : "binv"
};

class Label(str):
  def __new__(self, arg=""):
    str.__new__(self, arg)
    self.labelgen = 0 if type(arg) != Label else arg.labelgen
    return self
    
class CodeEmitVisitor (NodeVisit2):
  def __init__(self, typespace):
    NodeVisit2.__init__(self, typespace)
    self.buf = ""
    
    self.labelstack = []
    self.label = Label("__$global");
    self.ifstack = [] #end-of-if-else-chain label stack
    
    self.scopestack = []
    self.scope = Scope()
    self.required_nodes = []
    
    self.constids = IDGen()
    
    self.num_constpool = ConstPool(self.constids)
    self.str_constpool = ConstPool(self.constids)
    self.re_constpool = ConstPool(self.constids)
    self.id_constpool = self.str_constpool #ConstPool(self.constids)
    
    self.constidgen = 0
    self.tlevel = 0
    self.do_indent = True
  
  def push_label(self, label):
    self.labelstack.append(self.label)
    self.label = Label(label)
    self.out(label + ":\n")
    self.tlevel += 1
  
  def pop_label(self):
    self.label = self.labelstack.pop(-1)
    self.tlevel -= 1
    
    return self.label
    
  def out(self, string):
    string = str(string)
    
    tab = ""
    for s in range(self.tlevel):
      tab += "  "
    
    if self.do_indent:
      self.buf += tab
      self.do_indent = False
    
    if "\n" in string:
      self.do_indent = True
      
    self.buf += str(string)
    
  def FunctionNode(self, node, traverse):
    self.push_label(node.name)
    
    for c in node[1:]:
      traverse(c)
      
    if not self.buf.strip().endswith("ret"):
      self.out("ret\n");
    
    self.pop_label()
    #XXX
    #self.out("endfunction\n\n");
    
    #XXX need to deal with continuations, nested functions, etc.
    #for now though. . .
    
    self.out(";add function to scope\n");
    self.out("cf %s, %d\n" % (node.name, len(node[0])));
    self.out("sv " + node.name + "\n");
    self.out("drop\n\n");
  
  def value_traverse(self, node, traverse):
    if type(node) in [IdentNode, StrLitNode, NumLitNode]:
      self.out("push ")
    traverse(node)
    self.out("\n")
    
  def ReturnNode(self, node, traverse):
    #find owner function node
    p = node
    while p != None and not isinstance(p, FunctionNode):
      p = p.parent
    
    if p == None:
      self.typespace.error("Return outside of function", node)
      
    if len(node) == 1:
      self.value_traverse(node[0], traverse)
    
    self.out("ret\n");
    pass
    
  def NumLitNode(self, node, traverse):
    self.out(node.val) #"$"+str(self.num_constpool.get(node.val))+"N ")
  
  def IdentNode(self, node, traverse):
    self.out(node.val) #"$"+str(self.num_constpool.get(node.val))+"ID ")
  
  def StrLitNode(self, node, traverse):
    self.out(node.val) #"$"+str(self.num_constpool.get(node.val))+"S ")
  
  def ArrayRefNode(self, node, traverse):
    self.out("push object ")
    traverse(node[0])
    self.out("\n")
    
    self.out("push ")
    traverse(node[1])
    self.out("\n")
  
  def templabel(self, type):
    label = ".tmp_" + type + str(self.label.labelgen)
    
    self.label.labelgen += 1
    return label
  
  def IfWithoutElse(self, node, traverse):
    self.out("\n;if (" + node[0].gen_js(0) + ")\n")
    traverse(node[0])
    label = self.templabel("if")
    self.out("jz " + label + "\n\n")
    traverse(node[1])
    
    if type(node.parent) == ElseIfNode:
      print(self.ifstack)
      self.out(";escape if chain\n");
      self.out("jmp " + self.ifstack[-1] + "\n")
      
    self.out("\n" + label + ":\n");
  
  def if_next(self, node):
    p = node.parent
    lastp = node
    
    while p.parent and type(p) in [IfNode, ElseNode, ElseIfNode]:
      lastp = p
      p = p.parent
    
    ni = p.index(lastp)
    while p.parent != None and ni+1 >= len(p):
      lastp = p
      p = p.parent
      ni = p.index(lastp)
    
    return p[ni+1]
    
  def IfWithElse(self, node, traverse):
    endlabel = self.templabel("if")
    self.ifstack.append(endlabel)
    
    self.IfWithoutElse(node, traverse)
    for c in node[2:]:
      traverse(c)
    
    self.out(";end of if chain\n");
    self.out(endlabel + ":\n")
    
    #self.ifstack.pop(-1)
    
  def IfNode(self, node, traverse):
    #see if we have an else
    #ni = node.parent.index(node)
    #if ni+1 < len(node.parent):
    #  print("\n\n", node.parent[ni+1], "\n\n")
    
    #has_else = ni+1 < len(node.parent)
    #has_else = has_else and type(node.parent[ni+1]) in [ElseNode, ElseIfNode]
    has_else = len(node) > 2
    
    if has_else:
      self.IfWithElse(node, traverse)
    else:
      self.IfWithoutElse(node, traverse)
      
    print("HAS_ELSE", has_else)
    
  def AssignNode(self, node, traverse):
    self.out("push ")
    traverse(node[0])
    self.out("\npush ")
    traverse(node[1])
    self.out("\n")
    self.out("set\n")
    
  def VarDeclNode(self, node, traverse):
    for c in node[1:]:
      traverse(c)
      
    self.out(";declare " + node.val + "\n")
    self.tlevel += 1
    
    if type(node[0]) in [IdentNode, NumLitNode, StrLitNode]:
      self.out("push ")
      self.traverse(node[0])
      self.out("\n");
    else:
      traverse(node[0])
    
    self.out("setvar " + node.val + "\n")
    self.out("drop\n");
    
    self.tlevel -= 1
    
    self.scope[node.val] = node;
    
  def FuncCallNode(self, node, traverse):
    #self.tlevel += 1
    
    self.out(";BEGIN_CALL calc & push function pointer\n")
    if type(node[0]) == IdentNode:
      self.out("push " + node[0].val + "\n")
    else:
      traverse(node[0])
    
    self.out(";push this\n");
    
    #see if we have a this on the stack
    if type(node[0]) == BinOpNode and node[0].op == ".":
      #so, we should have this value on stack already
      #actually, stack should be:
      # |
      # V
      # function
      # this value
      #
      
      #transform to:
      #
      # function
      # this value
      # function
      # this value
      self.out("dup2;\n")
      
      #remove extraneous stack entry
      #
      # function
      # this value
      # this value
      self.out("drop;\n")
      self.out("swap;\n")
      
      #stack should now have this is right place (hopefully)
    else:
      self.out("push undefined\n")
      self.out("swap\n")
      
    self.out(";push arguments\n");
    for i in range(len(node[1])):
      self.out("push ")
      traverse(node[1][i])
      self.out("\n")
    
    self.out("call %i\n" % len(node[1]))
    
    #self.tlevel -= 1
    pass
    
  def BinOpNode(self, node, traverse):
    #self.tlevel += 1
    
    print("eek!", node.op)
    
    if node.op == ".":
      if type(node[0]) == IdentNode:
        self.out("gv " + node[0].val + "\n")
      else:      
        traverse(node[0])
        
      if type(node[1]) == IdentNode:
        self.out("push " + node[1].val)
        self.out("\n")
      else:      
        traverse(node[1])
      
      self.out("get\n")
    else:
      if type(node[0]) in [IdentNode, NumLitNode, StrLitNode]:
        self.out("push " + str(node[0].val))
        self.out("\n")
      else:      
        traverse(node[0])
        
      if type(node[1]) in [IdentNode, NumLitNode, StrLitNode]:
        self.out("push " + str(node[1].val))
        self.out("\n")
      else:      
        traverse(node[1])
      
      self.out(bin_opmap[node.op]+"\n")
      
    self.out("\n");
    #self.tlevel -= 1

def validate_code(result, typespace):
  pass
  
def create_elseif_nodes(result, typespace):
  def visit(node):
    n = node[0]
      
    while type(n) == StatementList:
      if len(n) > 1:
        return
      n = n[0]
    
    if type(n) == IfNode:
      node.parent.replace(node, ElseIfNode(n))
    
  traverse(result, ElseNode, visit)
  
  def visit2(node):
    if type(node) in [ElseIfNode, ElseNode]:
      ni = node.parent.index(node)
      if ni == 0:
        typespace.error("invalid else 1", node)
      
      prev = node.parent[ni-1]
      
      print("PREV", type(prev))
      
      if type(prev) != IfNode:
        typespace.error("invalid else 2", node)
      
      node.parent.remove(node)
      prev.add(node)
    else:
      i = 0
      while i < len(node):
        i_inc = 1 if type(node[i]) not in [ElseIfNode, ElseNode] else 0
        
        visit2(node[i])
        i += i_inc
  
  #collapse if nodes
  visit2(result)
  print("\n\n", result, "\n\n")

  
def v7_emit_bytecode(result, typespace):
  validate_code(result, typespace)
  fix_function_calls(result, typespace)
  create_elseif_nodes(result, typespace)
  
  #print("\n\n", result, "\n\n")
  
  visit = CodeEmitVisitor(typespace)
  
  visit.traverse(result);
  return visit.buf
