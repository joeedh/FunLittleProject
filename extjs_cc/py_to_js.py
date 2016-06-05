import os, sys, os.path, math, time, random
import ast, re

valid_id = re.compile(r'[a-zA-Z$_]+[a-zA-Z0-9$_]*')

def get_type_name(t):
  s = str(t).replace("<_ast.", "").replace("<class '_ast.", "").replace("'>", "")
  if "object at" in s:
    s = s[:s.find(" ")]
  s = s.replace("[", "").replace("]", "").strip()
  s = s.replace("<class '", "")
  return s

def get_children(node):
  lst = []
  if not isinstance(node, ast.AST):
    if type(node) in [list, tuple, set]:
      lst = []
      for c in node:
        lst.append(c)
    else:
      print(type(node))
      return
  else:
    for k in node._fields:
      lst.append(getattr(node, k))
  return lst
  
class NodeVisit:
  def __init__(self):
    pass
  
  def traverse(self, n, scope=None, tlevel=0):
    if scope == None: scope = {}
    
    if not isinstance(n, ast.AST) and type(n) not in [tuple, list, set]:
      return
    
    name = get_type_name(type(n))
    if not hasattr(self, name):
      if type(n) != list:
        sys.stderr.write("Warning: missing callback for node type " + name + "\n");
      
      for c in get_children(n):
        self.traverse(c, scope, tlevel)
      
      return
    
    def traverse(node, scope, tlevel=0):
      self.traverse(node, scope, tlevel)
    
    getattr(self, name)(n, scope, traverse, tlevel)
      
def tab(n):
  t = ""
  for i in range(n):
    t += "  "
  return t
  
class TransformVisit (NodeVisit):
  def __init__(self):
    NodeVisit.__init__(self)
    self.buf = ""
    
  def o(self, s):
    s = str(s).replace("\r", "\\r")
    
    self.buf += s
    
  def Module(self, n, scope, t, tlevel):
    self.body(n.body, scope, t, tlevel)
    
  def Name(self, n, scope, t, tlevel):
    if n.id == "self":
      n.id = "this"
      
    self.o(n.id)
    t(get_children(n), scope, tlevel)

  def Store(self, n, scope, t, tlevel):
    t(get_children(n), scope, tlevel)

  def Call(self, n, scope, t, tlevel):
    t(n.func, scope, tlevel)
    self.o("(")
    for i, a in enumerate(n.args):
      if i > 0:
        self.o(", ")
      t(a, scope, tlevel)
    self.o(")")
   
  def Load(self, n, scope, t, tlevel):
    t(get_children(n), scope, tlevel)
    
  def For(self, n, scope, t, tlevel):
    self.o("for (var ")
    t(n.target, scope, tlevel)
    self.o(" in ")
    t(n.iter, scope, tlevel)
    self.o(") {\n")
    
    self.body(n.body, scope, t, tlevel+1)
    
    self.o(tab(tlevel) + "}")
    #t(get_children(n), scope, tlevel)
  
  def endstatem(self, n):
    s = self.buf.strip()
    return not s.endswith("}") and not s.endswith(";")
    
  def body(self, lst, scope, t, tlevel):
    tab = ""
    for i in range(tlevel): tab += "  ";
    
    for n in lst:
      self.o(tab)
      t(n, scope, tlevel)
      if self.endstatem(n):
        self.o(";")
      self.o("\n")
      
  def Num(self, n, scope, t, tlevel):
    self.o(n.n)
  
  def Expr(self, n, scope, t, tlevel):
    t(get_children(n), scope, tlevel)
  
  def If(self, n, scope, t, tlevel):
    self.o("if (")
    
    t(n.test, scope, tlevel)
    self.o(") {\n")
    self.body(n.body, scope, t, tlevel+1)
    self.o(tab(tlevel) + "}")
    
    if n.orelse not in [None, [], tuple()]:
      if len(n.orelse) == 1:
        self.o(" else ")
        t(n.orelse, scope, tlevel)
      else:
        self.o(" else {\n")
        self.body(n.orelse, scope, t, tlevel+1)
        self.o(tab(tlevel) + "}\n")
  
  #binary operators
  def Mod(self, n, scope, t, tlevel):
    self.o("%")
  def Add(self, n, scope, t, tlevel):
    self.o("+")
  def Sub(self, n, scope, t, tlevel):
    self.o("-")
  def Mult(self, n, scope, t, tlevel):
    self.o("*")
  def Div(self, n, scope, t, tlevel):
    self.o("/")
  def Pow(self, n, scope, t, tlevel):
    self.o("**")
  def BitAnd(self, n, scope, t, tlevel):
    self.o("&")
  def BitOr(self, n, scope, t, tlevel):
    self.o("|")
  def BitXor(self, n, scope, t, tlevel):
    self.o("^")
  def And(self, n, scope, t, tlevel):
    self.o(" && ")
  def Or(self, n, scope, t, tlevel):
    self.o(" || ")
  def Not(self, n, scope, t, tlevel):
    self.o("!")
  def Lt(self, n, scope, t, tlevel):
    self.o("<")
  def Gt(self, n, scope, t, tlevel):
    self.o(">")
  def LtE(self, n, scope, t, tlevel):
    self.o("<=")
  def GtE(self, n, scope, t, tlevel):
    self.o(">=")
  def NotEq(self, n, scope, t, tlevel):
    self.o("!=")
  def Index(self, n, scope, t, tlevel):
    t(n.value, scope, tlevel)
  
  def Subscript(self, n, scope, t, tlevel):
    t(n.value, scope, tlevel)
    
    if type(n.slice) == ast.Index:
      self.o("[")
      t(n.slice, scope, tlevel)
      self.o("]")
    else:
      self.o(".slice(")
      t(n.slice.lower, scope, tlevel)
      self.o(", ")
      t(n.slice.upper, scope, tlevel)
      self.o(")")

  #unary operators
  def Invert(self, n, scope, t, tlevel):
    self.o("~")
  def USub(self, n, scope, t, tlevel):
    self.o("-")
   
  def Eq(self, n, scope, t, tlevel):
    self.o("==")
  
  def BoolOp(self, n, scope, t, tlevel):
    for i, c in enumerate(n.values):
      if i > 0:
        t(n.op, scope, tlevel)
      t(c, scope, tlevel)
    
  def Tuple(self, n, scope, t, tlevel):
    self.o("[")
    for i, c in enumerate(n.elts):
      if i > 0: self.o(", ")
      t(c, scope, tlevel)
    self.o("]")
  
  def List(self, n, scope, t, tlevel):
    self.o("[")
    for i, c in enumerate(n.elts):
      if i > 0: self.o(", ")
      t(c, scope, tlevel)
    self.o("]")
  
  def Str(self, n, scope, t, tlevel):
    n.s = n.s.replace("\"", "\\\"")
    totline = n.s.count("\n")
    
    n.s = n.s.replace("\t", "\\t")
    if totline > 0 and totline < 3:
      n.s = n.s.replace("\n", "\\n").replace("\r", "\\r")
      self.o('"%s"' % n.s)
    elif n.s.count("\n") > 2:
      self.o('"""%s"""' % n.s)
    else:
      self.o('"%s"' % n.s)
  
  def Dict(self, n, scope, t, tlevel):
    ks = n.keys
    vs = n.values
    self.o("{")
    for i in range(len(n.keys)):
      if i > 0:
        self.o(", ")
        
      print(ks[i].s)
      m = valid_id.match(ks[i].s)
      if m != None and m.span()[0] == 0 and m.span()[1] == len(ks[i].s):
        self.o(ks[i].s)
      else:
        t(ks[i], scope, tlevel)
      
      self.o(" : ")
      t(vs[i], scope, tlevel)
    self.o("}")
    
  def BinOp(self, n, scope, t, tlevel):
    if type(n.op) == ast.Pow:
      self.o("Math.pow(")
      t(n.left, scope, tlevel)
      self.o(", ")
      t(n.right, scope, tlevel)
      self.o(")")
    elif type(n.op) == ast.In:
      t(n.right, scope, tlevel)
      self.o(".has(")
      t(n.left, scope, tlevel)
      self.o(")")
    elif type(n.op) == ast.NotIn:
      self.o("!")
      t(n.right, scope, tlevel)
      self.o(".has(")
      t(n.left, scope, tlevel)
      self.o(")")
    else:
      t(n.left, scope, tlevel)
      self.o(" ")
      t(n.op, scope, tlevel)
      self.o(" ")
      t(n.right, scope, tlevel)
  
  def AugAssign(self, n, scope, t, tlevel):
    t(n.target, scope, tlevel)
    self.o(" ")
    t(n.op, scope, tlevel)
    self.o("=")
    self.o(" ")
    t(n.value, scope, tlevel)
  
  def Attribute(self, n, scope, t, tlevel):
    t(n.value, scope, tlevel)
    
    self.o(".")
    self.o(n.attr)
    
  def do_scope(self, n, scope, add_var=False):
    k = None
    v = None
    
    if type(n) == ast.Name:
      k = n.id
      v = n
    
    if k != None and k not in scope:
      if type(n) == ast.Name and add_var: 
        self.o("var ")
      scope[k] = v
      
  def Assign(self, n, scope, t, tlevel):
    val = n.value;
    
    lst = n.targets
    if len(lst) == 1 and type(lst[0]) == ast.Tuple:
      lst = lst[0].elts
    
    if len(lst) == 1:
      self.do_scope(lst[0], scope, True)
      
      t(lst[0], scope, tlevel)
      self.o(" = ")
      t(val, scope, tlevel)
    else:
      self.o("var _lst = pythonic_iter(")
      t(val, scope, tlevel)
      self.o(");\n")
      
      for i, c in enumerate(lst):
        self.o(tab(tlevel))
        self.do_scope(c, scope, True)
          
        t(c, scope, tlevel)
        self.o(" = _lst.next().value")
        if i != len(lst)-1:
          self.o(";\n")
    self.o("[[ASSIGN_MARK]]")
    
  def Compare(self, n, scope, t, tlevel):
    if type(n.ops[0]) not in [ast.In, ast.NotIn]:
      t(n.left, scope, tlevel)
    #x < y < z
    #x < y and y < z
    
    lastval = n.left
    for i in range(len(n.comparators)):
      op = n.ops[i]
      val = n.comparators[i]
      
      if i > 0:
        self.o(" && ")
        if type(op) not in [ast.In, ast.NotIn]:
          t(lastval, scope, tlevel)
      
      if type(op) == ast.In:
        t(val, scope, tlevel)
        self.o(".has(")
        t(lastval, scope, tlevel)
        self.o(")")
      elif type(op) == ast.NotIn:
        self.o("!")
        t(val, scope, tlevel)
        self.o(".has(")
        t(lastval, scope, tlevel)
        self.o(")")
      else:
        t(op, scope, tlevel)
        t(val, scope, tlevel)
        
      lastval = val
  
  def arg(self, n, scope, t, tlevel):
    self.o(n.arg)
  
  def arguments(self, n, scope, t, tlevel):
    max = len(n.args)
    for i, c in enumerate(n.args):
      if i > 0:
        self.o(", ")
      t(c, scope, tlevel)
      
      if i < max-len(n.defaults): continue
      
      di = i - max+len(n.defaults)
      self.o("=")
      t(n.defaults[di], scope, tlevel)
      
  def FunctionDef(self, n, scope, t, tlevel, ftype="function"):
    if ftype != "":
      self.o(ftype + " ")

    self.o(n.name)
    
    self.o("(")
    t(n.args, scope, tlevel)
    self.o(") {\n")
    
    self.body(n.body, scope, t, tlevel+1)
    self.o(tab(tlevel) + "}\n")
    
  def ClassDef(self, n, scope, t, tlevel):
    bases = n.bases
    
    print(n._fields)
    self.o("class ")
    self.o(n.name)
    
    if len(bases) > 0:
      self.o(" extends ")
      for i, b in enumerate(bases):
        if i > 0: self.o(", ")
        
        t(b, scope, tlevel)
    
    self.o(" {\n")
    
    t1 = tab(tlevel+1)
    for b in n.body:
      if type(b) != ast.FunctionDef: continue
      
      #destroy self
      if (len(b.args.args) > 0):
        b.args.args.pop(0)
        
      if b.name == "__init__":
        b.name = "constructor"
        
      if b.name == "__iter__":
        b.name = "__iterator__"
      
      self.o(t1)
      self.FunctionDef(b, scope, t, tlevel+1, "")
      
    self.o(tab(tlevel) + "\n}\n")
  
  def Global(self, n, scope, t, tlevel):
    self.o("global ")
    
    for i, n2 in enumerate(n.names):
      if i > 0:
        self.o(", ")
      self.o(n2)
      
  def Return(self, n, scope, t, tlevel):
    self.o("return")
    
    if n.value != None:
      self.o(" ")
    
    t(n.value, scope, tlevel)
  
  def IfExp(self, n, scope, t, tlevel):
    t(n.test, scope, tlevel)
    self.o(" ? ")
    t(n.body, scope, tlevel)
    self.o(" : ")
    t(n.orelse, scope, tlevel)
    
  def While(self, n, scope, t, tlevel):
    self.o("while (")
    t(n.test, scope, tlevel)
    self.o(") {\n")
    
    self.body(n.body, scope, t, tlevel+1)
    self.o(tab(tlevel) + "}\n")
   
  def Break(self, n, scope, t, tlevel):
    self.o("break")
  def Continue(self, n, scope, t, tlevel):
    self.o("continue")
 
def main(buf, infile, outfile):
  n = ast.parse(buf, infile)
  
  print(ast.dump(n))
  visit = TransformVisit()
  visit.traverse(n)
  
  buf = visit.buf.replace("[[ASSIGN_MARK]]", "")
  
  print("\n")
  print(buf)
  
  return buf
  
if len(sys.argv) not in [2, 3]:
  print("Usage: py_to_js.py infile outfile")
else:
  infile = sys.argv[1]
  if len(sys.argv) == 3:
    outfile = sys.argv[2]
  else:
    outfile = None

  file = open(infile)
  buf = file.read()
  file.close()
  
  ret = main(buf, infile, outfile)
  if outfile != None:
    f = open(outfile, "w")
    f.write(ret)
    f.close()