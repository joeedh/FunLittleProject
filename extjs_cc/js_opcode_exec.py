import traceback, sys
from js_opcode_emit import MAX_REGISTER
from js_global import glob

opcode_map = {}

code = 0
def _gen_code():
  global code
  code += 1
  return code - 1

opcode_map["PUSH"] = _gen_code()
opcode_map["POP"] = _gen_code()
opcode_map["PUSH_UNDEFINED"] = _gen_code()
opcode_map["LOAD_FROM_REG"] = _gen_code()
opcode_map["LOAD_LOCAL_STACK"] = _gen_code() 
opcode_map["WRITE_LOCAL_STACK"] = _gen_code()
opcode_map["LOAD_REG_REF"] = _gen_code()
opcode_map["LOAD_REG_INT"] = _gen_code()
opcode_map["LOAD_REG_PTR"] = _gen_code() 
opcode_map["LOAD_REG_EXTERN_PTR"] = _gen_code()
opcode_map["LOAD_REG_UNDEFINED"] = _gen_code() 
opcode_map["LOAD_REG_FLOAT"] = _gen_code()
opcode_map["LOAD_SYMBOL_PTR"] = _gen_code()
opcode_map["LOAD_SYMBOL_INT"] = _gen_code()
opcode_map["NATIVE_CALL"] = _gen_code()
opcode_map["LOAD_SYMBOL_FLOAT"] = _gen_code()
opcode_map["WRITE_SYMBOL_REF"] = _gen_code()
opcode_map["WRITE_SYMBOL_INT"] = _gen_code()
opcode_map["WRITE_SYMBOL_FLOAT"] = _gen_code()
opcode_map["LOAD_REG_SYMBOL_PTR"] = _gen_code()
opcode_map["LOAD_OPCODE_PTR"] = _gen_code() 
opcode_map["WRITE_REG_INT"] = _gen_code()
opcode_map["WRITE_REG_FLOAT"] = _gen_code()
opcode_map["WRITE_REG_REF"] = _gen_code()
opcode_map["WRITE_REG_PTR"] = _gen_code()
opcode_map["LOAD_REF"] = _gen_code() 
opcode_map["WRITE_REF"] = _gen_code()
opcode_map["LOAD_CONST_REF"] = _gen_code()
opcode_map["LOAD_CONST_INT"] = _gen_code()
opcode_map["LOAD_CONST_FLOAT"] = _gen_code()
opcode_map["INT_TO_FLOAT"] = _gen_code()
opcode_map["UNDEFINED_TO_ZERO_INT"] = _gen_code()
opcode_map["FLOAT_TO_INT"] = _gen_code()
opcode_map["LOAD_FLOAT"] = _gen_code()
opcode_map["WRITE_REF_LOCAL"] = _gen_code()
opcode_map["WRITE_INT_LOCAL"] = _gen_code() 
opcode_map["WRITE_FLOAT_LOCAL"] = _gen_code() 
opcode_map["LOAD_REF_LOCAL"] = _gen_code()
opcode_map["LOAD_INT_LOCAL"] = _gen_code()
opcode_map["LOAD_FLOAT_LOCAL"] = _gen_code()
opcode_map["PUSH_REF"] = _gen_code()
opcode_map["SHORTJMP"] = _gen_code() 
opcode_map["SHORTJMPTRUE"] = _gen_code() 
opcode_map["SHORTJMPTRUE_REG"] = _gen_code() 
opcode_map["SHORTJMPFALSE"] = _gen_code() 
opcode_map["SHORTJMPFALSE_REG"] = _gen_code() 
opcode_map["LONGJMP"] = _gen_code() 
opcode_map["PUSHTRY"] = _gen_code()
opcode_map["POPTRY"] = _gen_code()
opcode_map["THROW"] = _gen_code()
opcode_map["INT_TO_FLOAT"] = _gen_code()
opcode_map["FLOAT_TO_INT"] = _gen_code()
opcode_map["ARRAY_REF"] = _gen_code()
opcode_map["ARRAY_SET"] = _gen_code()
opcode_map["ADD_INT"] = _gen_code()
opcode_map["SUB_INT"] = _gen_code()
opcode_map["MUL_INT"] = _gen_code()
opcode_map["DIV_INT"] = _gen_code()
opcode_map["MOD_INT"] = _gen_code()
opcode_map["BITINV"] = _gen_code()
opcode_map["BITAND"] = _gen_code()
opcode_map["BITOR"] = _gen_code()
opcode_map["BITXOR"] = _gen_code()
opcode_map["LSHIFT"] = _gen_code()
opcode_map["RSHIFT"] = _gen_code()
opcode_map["NEGATE"] = _gen_code() 
opcode_map["ADD_FLOAT"] = _gen_code()
opcode_map["SUB_FLOAT"] = _gen_code()
opcode_map["MUL_FLOAT"] = _gen_code()
opcode_map["DIV_FLOAT"] = _gen_code()
opcode_map["MOD_FLOAT"] = _gen_code()
opcode_map["LTHAN_INT"] = _gen_code()
opcode_map["GTHAN_INT"] = _gen_code()
opcode_map["LTHANEQ_INT"] = _gen_code()
opcode_map["GTHANEQ_INT"] = _gen_code()
opcode_map["EQ_INT"] = _gen_code()
opcode_map["NOTEQ_INT"] = _gen_code()
opcode_map["NOT_INT"] = _gen_code()
opcode_map["LTHAN_FLOAT"] = _gen_code()
opcode_map["GTHAN_FLOAT"] = _gen_code()
opcode_map["LTHANEQ_FLOAT"] = _gen_code()
opcode_map["GTHANEQ_FLOAT"] = _gen_code()
opcode_map["EQ_FLOAT"] = _gen_code()
opcode_map["NOTEQ_FLOAT"] = _gen_code()
opcode_map["AND"] = _gen_code()
opcode_map["OR"] = _gen_code()
opcode_map["ADD"] = _gen_code()
opcode_map["SUB"] = _gen_code()
opcode_map["MUL"] = _gen_code()
opcode_map["DIV"] = _gen_code()
opcode_map["IN"] = _gen_code()
opcode_map["LOAD_REG_PTR_CONST"] = _gen_code()

rev_opcode_map = {}
for k in opcode_map:
  rev_opcode_map[opcode_map[k]] = k
  
class StackItem:
  def __init__(self, value=None):
    self.value = value
  def __str__(self):
    return str(self.value)
  def __repr__(self):
    return str(self)
  
class Object:
  def __init__(self):
    self.init = None
    self.type_name = ""
    self.methods = {}
    self.properties = {}
    self.child_classes = []
    self.class_parent = None
  def __str__(self):
    return "(obj)"
  def __repr__(self):
    return str(self)

class UndefinedType(Object):
  def __str__(self):
    return "None"

Undefined = UndefinedType()

def do_print(machine, string):
  print("print:", str(string))

def do_fstr(machine, f):
  return str(f)
  
do_print.totarg = 1
do_fstr.totarg = 1

class Interpretor:
  def __init__(self):
    self.functions = {"print" : do_print, "fstr" : do_fstr} #native functions
    self.globals = {}
    self.stack = [StackItem()]
    self.code = []
    self.cur = 0
    self.registers = [Undefined for x in range(MAX_REGISTER)]
    self.error = 0
    self.trystack = []
    self.opfuncs = [0 for x in range(len(opcode_map)+2)]
    
    for k in opcode_map:
      if hasattr(self, k):
        self.opfuncs[opcode_map[k]] = getattr(self, k)
  
  def reset(self):
    self.cur = 0
    self.registers = [Undefined for x in range(MAX_REGISTER)]
    self.stack = [StackItem()]
    
  def run_function(self, code, funcnode, args):
    self.reset()
    self.code = code
    
    self.stack.append(StackItem(-1))
    for a in args:
      self.stack.append(StackItem(a))
    
    self.run(code, funcnode.opcode_addr, do_reset=False)
    
  def run(self, code, entry, do_reset=True):
    limit = 500
    
    if do_reset:
      self.reset()
      
    self.code = code;
    self.cur = entry;
    
    print("\n")
    print("starting stack:")
    st = self.stack[:]
    st.reverse()
    for s in st:
      print("  " + str(s.value))
    
    print("\n")
    
    def rev(lst):
      l = lst[:]
      l.reverse()
      return str(l)
      
    i = 0
    code = self.code
    while i < limit:
      c = code[self.cur]
      self.cur += 1
      try:
        self.opfuncs[c.type](c.arg)
      except:
        if glob.g_debug_opcode:
          print("%03d %d %s %s | %s %s"%(c.i, c.code, str(c.arg), rev(self.stack[-4:len(self.stack)]), str(self.registers)))
        traceback.print_stack()
        traceback.print_exc()
        sys.exit(-1)
      
      if glob.g_debug_opcode:
        print("%03d %s %s | %s %s"%(c.i, c.code, str(c.arg), rev(self.stack[-4:len(self.stack)]), str(self.registers)))
        
      if self.cur < 0: break
      i += 1
    
    print("\n")
    print("finished", i)
    
  def PUSH(self, args=None):
    self.stack.append(StackItem())

  def POP(self, args=None):
    return self.stack.pop(-1)

  def PUSH_UNDEFINED(self, args):
    self.stack.push(StackItem(Undefined))

  def LOAD_FROM_REG(self, args):
    self.stack[-1].value = self.registers[args]

  def LOAD_LOCAL_STACK(self, args):
    #print(self.stack)
    self.stack[-1].value = self.stack[args].value
 
  def WRITE_LOCAL_STACK(self, args):
    self.stack[args].value = self.stack[-1].value
 
  def LOAD_REG_PTR_CONST(self, args):
    self.registers[args[0]] = args[1]
    
  def LOAD_REG_REF(self, args):
    self.registers[args] = self.stack[-1].value

  def LOAD_REG_INT(self, args):
    self.registers[args] = self.stack[-1].value

  def LOAD_REG_PTR(self, args):
    self.registers[args] = self.stack[-1].value

  def LOAD_REG_EXTERN_PTR(self, args):
    raise RuntimeError("Opcode not fully processed")

  def LOAD_REG_UNDEFINED(self, args):
    self.registers[args] = Undefined
 
  def LOAD_REG_FLOAT(self, args):
    self.registers[args] = self.stack[-1].value

  def LOAD_SYMBOL_PTR(self, args):
    raise RuntimeError("Opcode not fully processed")

  def LOAD_SYMBOL_INT(self, args):
    raise RuntimeError("Opcode not fully processed")

  def NATIVE_CALL(self, fname):
    args = []

    totarg = self.functions[fname].totarg
    for i in range(self.functions[fname].totarg):
      args.append(self.POP(None).value)
      
    ret = self.functions[fname](self, *args)
    
    #return to calling code, with value ret
    self.LOAD_REG_PTR(0) #save return value  
    self.stack[-1].value = ret
    
    self.LONGJMP(0)
    
  def LOAD_SYMBOL_FLOAT(self, args):
    raise RuntimeError("Incomplete opcode")

  def WRITE_SYMBOL_REF(self, args):
    raise RuntimeError("Incomplete opcode")

  def WRITE_SYMBOL_INT(self, args):
    raise RuntimeError("Incomplete opcode")

  def WRITE_SYMBOL_FLOAT(self, args):
    raise RuntimeError("Incomplete opcode")

  def LOAD_REG_SYMBOL_PTR(self, args):
    self.registers[args] = self.stack

  def LOAD_OPCODE_PTR(self, args):
    self.stack[-1].value = args

  def LOAD_REF(self, args):
    self.stack[-1].value = args

  def LOAD_CONST_REF(self, args):
    self.stack[-1].value = args

  def LOAD_CONST_INT(self, args):
    self.stack[-1].value = args

  def LOAD_CONST_FLOAT(self, args):
    self.stack[-1].value = args

  def INT_TO_FLOAT(self, args):
    self.stack[-1].value = float(self.stack[-1].value)
    
  def UNDEFINED_TO_ZERO_INT(self, args):
    self.stack[-1].value = 0

  def FLOAT_TO_INT(self, args):
    self.stack[-1].value = int(self.stack[-1].value)

  def PUSH_REF(self, args):
    self.stack.append(StackItem(args))

  def SHORTJMP(self, args):
    self.cur += args
 
  def SHORTJMPTRUE(self, args):
    if self.stack[-1] not in [0, None, Undefined]:
      self.cur += args
 
  def SHORTJMPTRUE_REG(self, args):
    print(self.stack[-1])
    if self.registers[arg[0]] not in [0, None, Undefined]:
      self.cur += args[1]
      
  def SHORTJMPFALSE(self, args):
    if self.stack[-1] in [0, None, Undefined]:
      self.cur += args
 
  def SHORTJMPFALSE_REG(self, args):
    if self.registers[args[0]] in [0, None, Undefined]:
      self.cur += args[1]
 
  def LONGJMP(self, args):
    self.cur = self.registers[args]

  def PUSHTRY(self, args):
    self.trystack.append(args)

  def POPTRY(self, args):
    self.trystack.pop()

  def THROW(self, args):
    self.throw_error(args)

  def ARRAY_REF(self, args):
    pass

  def ARRAY_SET(self, args):
    pass

  def ADD_INT(self, args):
    self.stack[-1].value = int(self.registers[2] + self.registers[3])

  def SUB_INT(self, args):
    self.stack[-1].value = int(self.registers[2] - self.registers[3])

  def MUL_INT(self, args):
    self.stack[-1].value = int(self.registers[2] * self.registers[3])

  def DIV_INT(self, args):
    self.stack[-1].value = int(self.registers[2] / self.registers[3])

  def MOD_INT(self, args):
    self.stack[-1].value = int(self.registers[2] % self.registers[3])

  def BITINV(self, args):
    pass
    
  def BITAND(self, args):
    self.stack[-1].value = self.registers[2] & self.registers[3]

  def BITOR(self, args):
    self.stack[-1].value = self.registers[2] | self.registers[3]

  def BITXOR(self, args):
    self.stack[-1].value = self.registers[2] ^ self.registers[3]

  def LSHIFT(self, args):
    self.stack[-1].value = self.registers[2] << self.registers[3]

  def RSHIFT(self, args):
    self.stack[-1].value = self.registers[2] >> self.registers[3]

  def NEGATE(self, args):
    pass
 
  def ADD_FLOAT(self, args):
    self.stack[-1].value = self.registers[2] + self.registers[3]

  def SUB_FLOAT(self, args):
    self.stack[-1].value = self.registers[2] - self.registers[3]

  def MUL_FLOAT(self, args):
    self.stack[-1].value = self.registers[2] * self.registers[3]

  def DIV_FLOAT(self, args):
    self.stack[-1].value = self.registers[2] / self.registers[3]

  def MOD_FLOAT(self, args):
    self.stack[-1].value = self.registers[2] % self.registers[3]

  def LTHAN_INT(self, args):
    self.stack[-1].value = self.registers[2] < self.registers[3]

  def GTHAN_INT(self, args):
    self.stack[-1].value = self.registers[2] > self.registers[3]

  def LTHANEQ_INT(self, args):
    self.stack[-1].value = self.registers[2] <= self.registers[3]

  def GTHANEQ_INT(self, args):
    self.stack[-1].value = self.registers[2] >= self.registers[3]

  def EQ_INT(self, args):
    self.stack[-1].value = self.registers[2] == self.registers[3]

  def NOTEQ_INT(self, args):
    self.stack[-1].value = self.registers[2] != self.registers[3]

  def NOT_INT(self, args):
    pass

  def LTHAN_FLOAT(self, args):
    self.stack[-1].value = self.registers[2] < self.registers[3]

  def GTHAN_FLOAT(self, args):
    self.stack[-1].value = self.registers[2] > self.registers[3]

  def LTHANEQ_FLOAT(self, args):
    self.stack[-1].value = self.registers[2] <= self.registers[3]

  def GTHANEQ_FLOAT(self, args):
    self.stack[-1].value = self.registers[2] >= self.registers[3]

  def EQ_FLOAT(self, args):
    self.stack[-1].value = self.registers[2] == self.registers[3]

  def NOTEQ_FLOAT(self, args):
    self.stack[-1].value = self.registers[2] != self.registers[3]

  def AND(self, args):
    self.stack[-1].value = self.registers[2] and self.registers[3]

  def OR(self, args):
    self.stack[-1].value = self.registers[2] or self.registers[3]

  def ADD(self, args):
    pass

  def SUB(self, args):
    pass

  def MUL(self, args):
    pass

  def DIV(self, args):
    pass

  def IN(self, args):
    pass
  
