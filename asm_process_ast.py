from asm_global import glob
from asm_ast import *
from extjs_cc import js_v7_bytecode as bcode
import struct
import os, sys

class TypeSpace:
  def __init__(self, root):
    self.root = root
    self.methods = {}
    self.labels = {}
    self.symbols = {}
    self.labelstack = []
    self.actlabel = ""
    self.scope = {}
    self.scopestack = []
    
  def error(self, msg, node):
    sys.stderr.write("error %i: %s\n\n" % (node.line, msg));
    sys.exit(-1)
 
class Visitor:
  def __init__(self, typespace):
    self.typespace = typespace
  
  def traverse(self, node):
    #print(node.type)
    
    if not hasattr(self, node.type):
      for c in node:
        self.traverse(c)
      #print("known node type ", node.type)
      return
    
    def traverse():
      for c in node:
        self.traverse(c)
    
    getattr(self, node.type)(node, traverse)

class Label:
  def __init__(self, name, loc=-1):
    self.name = name
    self.loc = loc
  
  def __str__(self):
    return self.name + "@" + hex(self.loc)
    
  def __repr__(self):
    return str(self)
    
class Pass0 (Visitor):
  def __init__(self, ts):
    Visitor.__init__(self, ts)
    self.buf = []
    self.loc = 0
  
  def _out(self, code, arg=None):
    self.buf.append([code, arg])
    self.loc += 8
    
  def Label(self, node, traverse):
    name = node[0].value
    
    if len(self.typespace.scopestack) > 0:
      self._pop()
    self._push()
    
    #if len(self.typespace.labelstack) > 0 and name[0] != '.':
    #  self.typespace.labelstack[-1] = name
    #elif len(self.typespace.labelstack) > 0 and name[0] == ".":
    #  name = self.typespace.labelstack[-1] + name
    if self.typespace.actlabel == "" or name[0] != ".":
      self.typespace.actlabel = name
    elif name[0] == ".":
      name = self.typespace.actlabel + name
    
    if name in self.typespace.labels:
      self.typespace.error(name + " is already defined", node)
      
    self.typespace.labels[name] = Label(name, self.loc)
      
    traverse()
    
  def _push(self):
    self.typespace.scopestack.append(self.typespace.scope)
    self.typespace.scope = dict(self.typespace.scope)
    self.typespace.stackoff = 0
    
  def _pop(self):
    self.typespace.scope = self.typespace.scopestack.pop(-1)
    self.typespace.stackoff = 0
    
  def Inst(self, node, traverse):
    code = node[0].value.lower()
    
    print("c", code)
    
    if code == 'var':
      vname = node[1][0].value
      print("vname:", vname)
      
      self.typespace.scope[vname] = self.typespace.stackoff
      self.typespace.stackoff += 1;
      
      self._out('voidpush')
    elif code == 'putc':
      self._out(code, node[1][0].value)
    else:
      self._out(code, node[1:])
      
    pass
    
def __process(node):
  ts = TypeSpace(node)
  
  visit = Pass0(ts)
  visit.traverse(node)
  
  print(ts.labels)
  
  #for opcode in visit.buf:
  #  print(str(opcode))
    
  return node
  
def process(result):
  class ReLink:
    def __init__(self, loc, inst_loc, label, wid=4, rel=True):
      self.loc = loc
      self.inst_loc = inst_loc
      self.label = label
      self.wid = wid
      self.rel = rel
    
    def __repr__(self):
      return "{loc=%s, symbol=%s, rel=%s, wid=%s}" % (self.loc, self.label, self.wid, self.rel)
      
  typespace = TypeSpace(result)
  
  lit_table = {}
  
  labels = {}
  labelstack = []
  label = "global"
  stack = []
  symbols = []
  newsyms = []
  
  out = []
  
  def encode_int32(i):
    c = struct.pack("i", i)
    return list(c)
  def encode_double(i):
    c = struct.pack("d", i)
    return list(c)
    
  def encode_pointer(i):
    return encode_int32(i)
  
  #do as much label linking as possible
  def do_link():
    newsyms = []
    for sym in symbols:
      if sym.label not in labels:
        newsyms.append(sym)
        continue
      
      addr = labels[sym.label]
      if sym.rel:
        addr -= sym.inst_loc
      
      print("SYM", sym.label, "ADDR", addr)
      out[sym.loc:sym.loc+4] = encode_int32(addr)
      
    symbols[:] = newsyms
    print(symbols)
    
  def isnum(s):
    try:
      return True if float(s) is not None else False
    except:
      return False
    return True
    
  def do_label(node):
    label = node[0].value
    
    if not label.startswith("."):
      #link . locals
      do_link()
      
      #reset . locals
      for k in list(labels.keys()):
        if k.startswith("."):
          del labels[k]
    
    labels[label] = len(out)
    
    print(node[0].value)
   
  def get_lit(lit):
    if lit in lit_table:
      return lit_table[lit]
    
    lit_table[lit] = len(lit_table)
    return lit_table[lit]
  
  def concat(a, b):
    for item in b:
      a.append(item)
    return a
    
  def do_push(node):
    if node[1][0].type == "ID" and node[1][0].value == "undefined":
      out.append(bcode.mnomics["OP_PUSH_UNDEFINED"])
    elif node[1][0].type == "ID" and node[1][0].value == "null":
      out.append(bcode.mnomics["OP_PUSH_NULL"])
    elif node[1][0].type == "ID" and node[1][0].value == "true":
      out.append(bcode.mnomics["OP_PUSH_TRUE"])
    elif node[1][0].type == "ID" and node[1][0].value == "false":
      out.append(bcode.mnomics["OP_PUSH_FALSE"])
    elif node[1][0].type == "NUM":
      out.append(bcode.mnomics["OP_PUSH_LIT"])
      concat(out, encode_int32(get_lit(int(node[1][0].value))))
    elif node[1][0].type in ["ID", "STRLIT"]:
      out.append(bcode.mnomics["OP_PUSH_LIT"])
      concat(out, encode_int32(get_lit(node[1][0].value)))
    else:
      print(node[1][0].type)
      raise RuntimeError("eek! in do_push")
    #print(node)
    
  def do_inst(node):
    itype = node[0].value
    
    if itype == "push":
      do_push(node)
    elif itype == "pop":
      pass
    elif itype in ["jmp", "jz", "jnz"]:
      out.append(itype)
      val = node[1][0].value
      if isnum(val):
        out.append(int(val))
      else: #ReLink(loc, label, wid=4, rel=True):
        symbols.append(ReLink(len(out), len(out)-1, val))
        out.append(-1)
        out.append(-1)
        out.append(-1)
        out.append(-1)
        
    elif itype == "call":
      out.append(itype)
      out.append(int(node[1][0].value))
    elif itype == "setvar":
      arg = node[1][0].value
      out.append(itype)
      concat(out, encode_int32(get_lit(arg)))
    else:
      out.append(itype)
      return #XXX
      typespace.error("unknown instruction " + itype, node)
    #print(node)
    
  for n in result:
    if n.type == "Inst":
      do_inst(n)
    elif n.type == "Label":
      do_label(n)
    elif n.type == "NL-nop":
      pass
    else:
      typespace.error("bad ast node", n)
  
  #do linking
  do_link();
  
  #print literals
  print("-------literals----------")
  lits = list(range(len(lit_table)))
  for k in lit_table:
    if type(k) == str:
      val = '"' + k + '"'
    else:
      val = k
      
    lits[lit_table[k]] = val
  
  litout = []
  for i, l in enumerate(lits):
    hexc = hex(i)[2:].upper()
    
    while len(hexc) < 2:
      hexc = "0" + hexc
    print(hexc + ": " + str(l))
    
    if type(l) == str:
      litout.append(0)
      l = bytes(l[1:-1], "latin-1")
      
      for i in range(len(l)):
        litout.append(l[i])
      litout.append(0)
    else:
      litout.append(1)
      l = encode_double(l)
      for j in range(len(l)):
        litout.append(l[j])
      
  print("\n")
  
  #print instructions
  s = "\n"
  for i, c in enumerate(out):
    if type(c) == str:
      s += "\n" + ("%.4x: " % (i)).upper() + c + "\t"
    else:
      hexc = hex(c)[2:].upper()
      while len(hexc) < 2:
        hexc = "0" + hexc
      s += " " + hexc
  
  print("=======", s)
  
  mmap = dict(bcode.mnomics)
  mmap["jz"] = bcode.opmap["OP_JMP_TRUE"]
  mmap["jnz"] = bcode.opmap["OP_JMP_FALSE"]
  mmap["setvar"] = bcode.opmap["OP_SET_VAR"]
  mmap["getvar"] = bcode.opmap["OP_GET_VAR"]
  mmap["dup2"] = bcode.opmap["OP_2DUP"]
  
  s2 = b""
  s3 = ""
  for c in out:
    if type(c) == str:
      c = mmap[c]
    s2 += bytes([c])
    s3 += hex(c)[2:].upper()
  
  print(s3)
  
  sout = encode_int32(len(litout)) + litout + encode_int32(len(out)) + out
  
  for i, c in enumerate(sout):
    if type(c) == str:
      sout[i] = mmap[c]
  
  sout = bytes(sout)
  
  if glob.outfile != "":
    f = open(glob.outfile, "wb")
    f.write(sout)
    f.close()
    
  
  