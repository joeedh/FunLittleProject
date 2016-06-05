import traceback, sys
from js_ast import *
from js_global import glob, Glob
from js_typespace import *
from js_cc import *
from js_process_ast import *
from js_util_types import *
import os, os.path
from js_type_emit import resolve_types, types_match, templates_match
#rules for registers: 0 and 1 are reserved for our 
#function calling convention; 2, 3, and 4 are used 
#for unary, binary, and trinary expr operatons.
#
#5 is used for shortjmp operations (e.g, if, loops, etc)

MAX_REGISTER = 8
valid_ops = [
  "PUSH",
  "POP",
  "PUSH_UNDEFINED",
  "LOAD_FROM_REG",
  "LOAD_LOCAL_STACK", #writes top of stack with another stack item, arg is offset
  "WRITE_LOCAL_STACK", #writes another stack item with top of stack arg is offset
  "LOAD_REG_REF",
  "LOAD_REG_INT",
  "LOAD_REG_PTR", #register codes all pop values from the stack
  "LOAD_REG_PTR_CONST", #reads from argument, not stack
  "LOAD_REG_EXTERN_PTR", #is turned into a LOAD_REG_PTR later by linker
  "LOAD_REG_UNDEFINED", #load null/void/empty value
  "LOAD_REG_FLOAT",
  "LOAD_SYMBOL_PTR",
  "LOAD_SYMBOL_INT",
  "NATIVE_CALL",
  "LOAD_SYMBOL_FLOAT",
  "WRITE_SYMBOL_REF",
  "WRITE_SYMBOL_INT",
  "WRITE_SYMBOL_FLOAT",
  "LOAD_REG_SYMBOL_PTR",
  "LOAD_OPCODE_PTR", #REMEMBER TO RELINK THIS! use for calculating function calls and the like
  "LOAD_REF", #loads ref from memory address in passed in register 
  "LOAD_CONST_REF",
  "LOAD_CONST_INT",
  "LOAD_CONST_FLOAT",
  "LOAD_INT",
  "WRITE_INT",
  "INT_TO_FLOAT",
  "UNDEFINED_TO_ZERO_INT",
  "FLOAT_TO_INT",
  "LOAD_FLOAT",
  "PUSH_REF",
  "SHORTJMP", #reads stack offset from its argument
  "SHORTJMPTRUE", #jumps if current stack value is true
  "SHORTJMPTRUE_REG", #jumps if a register value is true
  "SHORTJMPFALSE", #jumps if current stack value is false
  "SHORTJMPFALSE_REG", #jumps if a register value is false
  "LONGJMP", #reads from a register
  "PUSHTRY",
  "POPTRY",
  "THROW",
  "INT_TO_FLOAT",
  "FLOAT_TO_INT",
  "ARRAY_REF",
  "ARRAY_SET",
  "ADD_INT",
  "SUB_INT",
  "MUL_INT",
  "DIV_INT",
  "MOD_INT",
  "BITINV",
  "BITAND",
  "BITOR",
  "BITXOR",
  "LSHIFT",
  "RSHIFT",
  "NEGATE", #reads from register, writes to current stack position
  "ADD_FLOAT", #math operations read from registers, but write to stack
  "SUB_FLOAT",
  "MUL_FLOAT",
  "DIV_FLOAT",
  "MOD_FLOAT",
  "LTHAN_INT",
  "GTHAN_INT",
  "LTHANEQ_INT",
  "GTHANEQ_INT",
  "EQ_INT",
  "NOTEQ_INT",
  "NOT_INT",
  "LTHAN_FLOAT",
  "GTHAN_FLOAT",
  "LTHANEQ_FLOAT",
  "GTHANEQ_FLOAT",
  "EQ_FLOAT",
  "NOTEQ_FLOAT",
  "AND",
  "OR",
  
  "ADD",
  "SUB",
  "MUL",
  "DIV",
  
  "IN",  
]

valid_op_set = set(valid_ops)

class OPCODE:
  def __init__(self, code, arg=None, comment=None, blocklevel=0, stacklevel=0):
    self.code = code
    self.arg = arg #not all opcodes have args
    self.comment = comment
    self.blocklevel = blocklevel
    self.stacklevel = stacklevel
    
    if code not in valid_op_set:
      raise RuntimeError("Invalid opcode %s in js_opcode_emit.py"%code)
  
  def __str__(self):
    argstr = ""
    if (self.arg != None):
      argstr = " " + str(self.arg)
    cstr = ""
    if self.comment != None:
      cstr += " //" + str(self.comment)
      
    return tab(self.blocklevel) + str(self.stacklevel) + " " + self.code + argstr + cstr
    
typespace = None
op_map = {
  "+" : "ADD",
  "-" : "SUB",
  "/" : "DIV",
  "*" : "MUL",
  "&" : "BITAND",
  "|" : "BITOR",
  "<<" : "LSHIFT",
  ">>" : "RSHIFT",
  "<" : "LTHAN",
  "<=" : "LTHANEQ",
  "==" : "EQ",
  "=>" : "GTHANEQ",
  ">" : "GTHAN",
  "||" : "OR",
  "&&" : "AND",
  "!" : "NOT"
}

class TypeEmitVisit(NodeVisit):
  def __init__(self):
    super(TypeEmitVisit, self).__init__()
    self.codes = []
    self.stacklevels = [0]
    self.funcstack = []
    self.blocklevel = 0
    
    self.required_nodes = node_types
    
    for n in set(self.required_nodes):
      if isinstance(n, TypeNode):
        self.required_nodes.remove(n)
  
  def opcode(self, opcode, arg=None, comment=None):
    if "PUSH" in opcode and opcode != "PUSHTRY":
      self.stacklevels[-1] += 1
    
    if "POP" in opcode and opcode != "POPTRY":
      self.stacklevels[-1] -= 1
    
    if len(self.stacklevels) > 0:
      slvl = self.stacklevels[-1]
    else:
      slvl = 0
    
    self.codes.append(OPCODE(opcode, arg, comment, self.blocklevel, slvl))
  
  def StrLitNode(self, node, scope, emit, tlevel):
    self.opcode("LOAD_CONST_REF", node.val, "string literal")
    
  def NumLitNode(self, node, scope, emit, tlevel):
    if type(node.val) == int:
      t = "INT"
    else:
      t = "FLOAT"
      
    self.opcode("LOAD_CONST_"+t, node.val, "%s literal"%t.lower())
    
  def IdentNode(self, node, scope, emit, tlevel):
    if node.val not in scope:
      sys.stderr.write("IdentNode %s not in scope.\n"%node.val)
      print(scope)
      typespace.error("IdentNode %s not in scope.\n"%node.val, node)
    
    obj = scope[node.val]
    self._gen_var_read(node, scope, self._get_optype(node.type))
    
  def convert_types(self, t1, t2):
    if t1 == "FLOAT" and t2 == "INT":
      self.opcode("INT_TO_FLOAT")
    else:
      self.opcode("FLOAT_TO_INT")
    
  def BinOpNode(self, node, scope, emit, tlevel):
    handle_nodescope_pre(node, scope)
    
    if node.op != ".":
      op = op_map[node.op]
      t1 = self._get_optype(node[0].type)
      t2 = self._get_optype(node[1].type)
      
      emit(node[0], scope)

      self.opcode("PUSH")
      emit(node[1], scope)
      
      if t1 != t2:
        if t1 == "REF":
          typespace.error("Cannot %s %s types with objects"%(op.lower(), t1.lower()))
        if t2 == "REF":
          typespace.error("Cannot %s %s types with objects"%(op.lower(), t1.lower()))
        
        self.convert_types(t1, t2)      
      
      self.opcode("LOAD_REG_"+t1, 3)
      self.opcode("POP")
      self.opcode("LOAD_REG_"+t1, 2);
      
      if t1 == "REF": t1 = ""
      else: t1 = "_" + t1
      self.opcode(op+t1)
    else:
      raise RuntimeError("member lookup not implemented")
    
    handle_nodescope_pre(node, scope)
    
  def NegateNode(self, node, scope, emit, tlevel):
    emit(node[0], scope)
    t = self._get_optype(node[0].type)
    self.opcode("LOAD_REG_"+t, 2)
    self.opcode("NEGATE", 2)
    
  def TypeofNode(self, node, scope, emit, tlevel):
    pass
  
  def VarDeclNode(self, node, scope, emit, tlevel):
    if node.local:
      if len(self.stacklevels) == 0:
        typespace.error("Global variable has local flag", node)
    
      node.stack_off = self.stacklevels[-1]
      self.opcode("PUSH", comment="declare %s"%node.val)
    if node.val in scope and types_match(node.type, scope[node.val].type, typespace):
      node.stack_off = scope[node.val].stack_off
      if len(self.stacklevels) > 1:
        node.local = True
      else:
        node.local = scope[node.val].local
        
    scope[node.val] = node
    if type(node[0]) != ExprNode or len(node[0]) > 0:
      n = AssignNode(IdentNode(node.val), node[0], "=")
      n.type = node.type
      self.AssignNode(n, scope, emit, tlevel)
      
  def _gen_var_read(self, var, scope, optype):
    if type(var) not in [IdentNode, VarDeclNode]:
      raise RuntimeError("Unimplemented var read/write for type %s"%str(type(var)))
      
    if type(var) == IdentNode:
      var = scope[var.val]
    
    if var.local:
      self.opcode("LOAD_LOCAL_STACK", var.stack_off-self.stacklevels[-1])
    else:
      if not optype.startswith("_"): 
        optype = "_" + optype
      self.opcode("LOAD_SYMBOL"+optype, var.val)
      
  def _gen_var_write(self, var, scope, optype):
    if type(var) not in [IdentNode, VarDeclNode]:
      raise RuntimeError("Unimplemented var read/write for type %s"%str(type(var)))
      
    if type(var) == IdentNode:
      var = scope[var.val]
    
    if var.local:
      self.opcode("WRITE_LOCAL_STACK", var.stack_off-self.stacklevels[-1])
    else:
      if not optype.startswith("_"): 
        optype = "_" + optype
      self.opcode("WRITE_SYMBOL"+optype, var.val)
      
  def AssignNode(self, node, scope, emit, tlevel):
    self.opcode("PUSH", comment="begin assignment")
    
    emit(node[1], scope);
    
    if node.mode != "=":
      op = op_map[node.mode[0]]
      t = self._get_optype(node.type)
      
      self.opcode("LOAD_REG_"+t, 2)
      
      self.opcode("PUSH")
      self._gen_var_read(node[0], scope, t)
      self.opcode("LOAD_REG_"+t, 3)
      
      if t == "REF": t = ""
      else: t = "_"+t
      self.opcode(op+t)
      
    self._gen_var_write(node[0], scope, self._get_optype(node.type))
    
    if node.mode != "=":
      self.opcode("POP");
    self.opcode("POP", comment="finish assignment")
    
  def ForLoopNode(self, node, scope, emit, tlevel):
    self.blocklevel += 1
    handle_nodescope_pre(node, scope)
    for c in node.children:
      emit(c, scope)
    handle_nodescope_pre(node, scope)
    self.blocklevel -= 1
    
  def WhileNode(self, node, scope, emit, tlevel):
    self.blocklevel += 1
    for c in node.children:
      emit(c, scope)
    self.blocklevel -= 1
      
  def DoWhileNode(self, node, scope, emit, tlevel):
    self.blocklevel += 1
    for c in node.children:
      emit(c, scope)
    self.blocklevel -= 1
      
  def ElseNode(self, node, scope, emit, tlevel):
    self.blocklevel += 1
    for c in node.children:
      emit(c, scope)
      
    self.blocklevel -= 1
      
  def IfNode(self, node, scope, emit, tlevel):
    self.opcode("PUSH", comment="---begin if")
    emit(node[0], scope)
    t = self._get_optype(node[0].type)
    if t != "INT":
      if t == "FLOAT":
        self.opcode("FLOAT_TO_INT")
      else:
        self.opcode("UNDEFINED_TO_ZERO_INT")
        
    self.opcode("LOAD_REG_"+t, 5)
    self.opcode("POP")
    self.opcode("SHORTJMPFALSE_REG", -1, "if")
    jmpcode1 = len(self.codes)-1
    
    self.blocklevel += 1
    
    self.stacklevels.append(self.stacklevels[-1])
    
    emit(node[1], scope)
    self.stacklevels.pop(-1)
    
    self.opcode("SHORTJMP", -1, "endif")
    jmpcode3 = len(self.codes)-1
    
    if len(node) == 3:
      self.stacklevels.append(self.stacklevels[-1])
      self.codes[jmpcode1].arg = [5, len(self.codes)-jmpcode1-1]
      
      emit(node[2], scope)
      
      self.stacklevels.pop(-1)
    else:
      self.codes[jmpcode1].arg = [5, len(self.codes)-jmpcode1-1]
    
    self.codes[jmpcode3].arg = len(self.codes)-jmpcode3-1
    self.blocklevel -= 1
    
  def stacklevel(self, func_local=True):
    if len(self.stacklevels) > 0:
      if func_local:
        return self.stacklevels[-1]
      else:
        lvl = 0
        for sl in self.stacklevels:
          lvl += sl
        return lvl
    else:
      return 0
  
  def FuncCallNode(self, node, scope, emit, tlevel):
    #there are two cases here.  one is calling a function
    #that is the result of an expression (e.g. member lookup),
    #the other is calling a named function, which pushes 
    #the value itself.
    
    func = node.type
    if len(node[1]) != len(func.children[0]):
      typespace.error("Wrong number of function arguments", node);
    
    for i, a in enumerate(func[0]):
      a2 = node[1][i]
      nt = a2.type
      if type(a2) == FuncCallNode:
        nt = a2.type.type
        if type(nt) == IdentNode:
          nt = TypeRefNode(nt.val)
          
      if not types_match(a.type, nt, typespace):
        typespace.error("Wrong type for argument %i."%(i+1), node);
    
    #XXX REMEMBER TO RELINK THIS!
    self.opcode("LOAD_OPCODE_PTR", -2, "return address")
    jmpcode = len(self.codes)-1
    
    for a in node[1]:
      self.opcode("PUSH")
      emit(a, scope)
    
    if type(node[0]) == IdentNode:
      self.opcode("LOAD_REG_SYMBOL_PTR", [node[0].val, 0]); 
    else:
      self.opcode("PUSH")
      emit(node[0], scope)
      self.opcode("LOAD_REG_PTR", 0);
      self.opcode("POP")
    
    if func.is_native:
      self.opcode("NATIVE_CALL", func.name)
    else:
      self.opcode("LONGJMP", 0, "call %s"%func.name);
    
    self.codes[jmpcode].arg = len(self.codes)
    
    #decrement locals offset.
    #we do this here since the 
    #called function, not the caller,
    #pops the arguments.
    
    self.stacklevels[-1] -= len(func[0])
    
  def FunctionNode(self, node, scope, emit, tlevel):
    if node.is_native: 
      node.opcode_addr = -1
      return
    
    node.opcode_addr = len(self.codes)
    
    self.blocklevel += 1
    handle_nodescope_pre(node, scope)
    
    self.funcstack.append(node)
    self.stacklevels.append(0)
    
    node.stack_start = self.stacklevel()
    node.arg_codetypes = odict()
    args = list(range(len(node.args)))
    for a in node.arg_is:
      args[node.arg_is[a]] = a
    node.arglist = args
    
    for i, k in enumerate(node.arglist):
      a = node.args[k]
      if type(a) == BuiltinTypeNode and a.type == "int":
        atype = "INT"
      if type(a) == BuiltinTypeNode and a.type == "float":
        atype = "FLOAT"
      else:
        atype = "REF"
      
      node.stack_start -= 1
      node.children[0][i].stack_off = -(len(node.arglist)-i)
      a.stack_off = -(len(node.arglist)-i);
      a.local = True
      if type(a) == VarDeclNode:
        a.modifiers.add("local")
        if "global" in a.modifiers:
          a.modifiers.remove("global")
        
      scope[k] = a
      print(scope)
      
    self.opcode("PUSH", comment="start " + node.name)
    for c in node.children[1:]:
      emit(c, scope)

    self.opcode("POP")
    
    if self.codes[-2].code != "LONGJMP":
      while self.stacklevels[-1] > 0:
        self.opcode("POP")
      for a in node.arglist:
        self.opcode("POP", comment=a)

      #this is the undefined return case, so push a null ret value
      self.opcode("LOAD_REG_PTR", 0)
      self.opcode("POP"); self.opcode("PUSH_UNDEFINED")
      self.opcode("LONGJMP", 0, comment="return from "+node.name)
      
      handle_nodescope_post(node, scope)
      self.stacklevels.pop(-1)
      self.funcstack.pop(-1)
      
    self.blocklevel -= 1

  def _get_optype(self, node, add_u=False):
    if type(node) == NumLitNode:
      if type(node.val) == int: s = "INT"
      elif type(node.val) == float: s = "FLOAT"
    elif type(node) == BuiltinTypeNode and node.type == "int":
      s = "INT"
    elif type(node) == BuiltinTypeNode and node.type == "float":
      s = "FLOAT"
    else:
      s = "REF"
    
    if add_u and s != "REF":
      s = "_" + s
      
    return s
    
  def ReturnNode(self, node, scope, emit, tlevel):
    if len(node) > 0:
      self.opcode("PUSH");
      emit(node[0], scope)
    
    func = self.funcstack[-1]
    ntype = self._get_optype(self.funcstack[-1].type)
    self.opcode("LOAD_REG_" + ntype, 1)
    
    while self.stacklevels[-1] > 0:
      self.opcode("POP")
      
    for a in func.arglist:
      self.opcode("POP", comment=a)
    
    self.opcode("LOAD_REG_PTR", 0)
    self.opcode("LOAD_FROM_REG", 1)
    self.opcode("LONGJMP", 0, comment="return from "+func.name)
    
  def WithNode(self, node, scope, emit, tlevel):
    handle_nodescope_pre(node, scope)
    for c in node.children:
      emit(c, scope)
    handle_nodescope_pre(node, scope)

  def StatementList(self, node, scope, emit, tlevel):
    for c in node.children:
      emit(c, scope)

from js_opcode_exec import *

def link_symbols(codes):
  for c in codes:
    if c.code == "LOAD_REG_SYMBOL_PTR":
      func = typespace.functions[c.arg[0]]
      reg = c.arg[1]
      c.code = "LOAD_REG_PTR_CONST"
      c.arg = [c.arg[1], func.opcode_addr]
      
def code_to_int(codes):
  for c in codes:
    c.type = opcode_map[c.code]
  
def gen_opcode(node, typespace2):
  global typespace
  
  combine_if_else_nodes(node)
  
  typespace = typespace2
  resolve_types(node, typespace2)
  visit = TypeEmitVisit()
  visit.traverse(node, None)
  
  link_symbols(visit.codes)
  code_to_int(visit.codes)
  
  i = 0
  for c in visit.codes:
    if glob.g_debug_opcode:
      print("%03d %s" % (i, c))
    c.i = i
    i += 1
    
  from js_opcode_emit import Interpretor
  
  machine = Interpretor()
  machine.run_function(visit.codes, typespace.functions["main"], [1, 2.0])
  
def gen_opcode_files(rootnodes, typespace):
  pass

if __name__ == "__main__":
  lines = ["%s: %d"%(k, opcode_map[k]) for k in opcode_map]
  lines.sort()
  for l in lines:
    print(l)
  sys.exit()