import sys

from js_global import glob, Glob

from js_ast import *
from js_process_ast import *
from js_cc import js_parse

import traceback

builtin_types = [
  "Object",
  "String",
  "Number",
  "Array",
  "Boolean",
  "Iterator",
  "CanIterate",
  "Float32Array",
  "Uint8Array",
  "Uint16Array",
  "Uint32Array",
  "Int32Array",
  "ArrayBuffer",
  "WebGLRenderingContext",
  "WebGLUnifornLocation",
  "MouseEvent",
  "KeyboardEvent",
  "KeyEvent",
  "undefined",
  "ObjectMap",
  "Function",
  "console",
  "Math",
  "WebKitCSSMatrix",
]

builtin_functions = [
]

builtin_code = {
  "Iterator": """
  function Iterator<T>() {
    this.next = function() : T {
    }
  }
  
  """,
  "CanIterate": """
    function CanIterate<T>() {
      this.__iterator__ = function() : Iterator<T> {
      }
    }
  """,
  "Array": """
    function Array<T>() {
      this.length = 0 : int;
      this.push = function(T item) {
      }
    }
  """,
  "console": """
    function console() {
      this.log = function(String str) {
      }
      
      this.trace = function() {
      }
      
      this.debug = function(String str) {
      }
    }
  """, "Math": """
    function Math() {
      this.sqrt = function(float f) : float {
      }
      
      this.floor = function(float f) : float {
      }
      
      this.abs = function(float f) : float {
      }
      
      this.pi = 3.141592654 : float;
    }
  """
 
}

class JSError (Exception):
  pass

class JSTypeSpace:
  def empty_type(self):
    n = FunctionNode("(unknown type)", 0)
    n.class_type = "class"
    
    return n
    
  def __init__(self):
    self.functions = {}
    self.types = {}
    self.globals = {}
    self.logrec = []
    self.logmap = {}
    self.builtin_typenames = builtin_types
    self.func_excludes = set(["inherit", "inherit_multiple", "define_static", "create_prototype", "prior"])
    
    self.functions["inherit"] = js_parse("function inherit(Object a, Object b) : void { };", start_node=FunctionNode)
    
    for t in builtin_types:
      n = BuiltinTypeNode(t)
      n.ret = "class"
      n.members = {}
      
      #"""
      if t in builtin_code:
        fn = js_parse(builtin_code[t], exit_on_err=False, start_node=FunctionNode);
        if fn == None:
          sys.stderr.write("Warning: could not compile internal type code in JSTypeSpace.__init__\n")
          #self.error("js_parse error", n);
          glob.g_error = False
          return
        else:
          self.types[fn.name] = fn
          for n in fn.children[1:]:
            if type(n) == AssignNode and type(n[0]) == BinOpNode and \
              n[0].op == "." and type(n[0][0]) == IdentNode and n[0][0].val == "this" \
               and type(n[0][1]) == IdentNode:
               
              if type(n[1]) == FunctionNode and n.type == None:
                n.type = VoidTypeNode()
                
              if n[1].type != None:
                fn.members[n[0][1].val] = n[1].type
              else:
                fn.members[n[0][1].val] = n.type
      else:
        if t != "Object":
          fn = js_parse("function %s(value) {};"%t, exit_on_err=False, start_node=FunctionNode);
        elif t != "undefined":
          fn = js_parse("function %s() {};"%t, exit_on_err=False, start_node=FunctionNode);
      """
      fn = None
      #"""
      
      if fn == None or len(fn.children) == 0:
        sys.stderr.write("Warning: could not compile internal type code in JSTypeSpace.__init__\n")
        #self.error("js_parse error", n);
        glob.g_error = False
        return
      else:
        while fn != None and type(fn) != FunctionNode and len(fn.children) > 0:
          fn = fn.children[0]
        
        if type(fn) != FunctionNode:
          sys.stderr.write("\nWarning: could not compile internal type code in JSTypeSpace.__init__\n")
          return
        if t == "Array":
          fn.class_type = "array"
        else:
          fn.class_type = "class"
        
        fn.is_builtin = True
        fn.is_native = True
        fn.ret = n
        self.functions[t] = fn
        self.types[t] = fn
    
    funcs = self.functions
    funcs["Number"].add_class_child(funcs["Boolean"])
    funcs["Array"].add_class_child(funcs["String"])
    funcs["CanIterate"].add_class_child(funcs["Array"])
    funcs["CanIterate"].add_class_child(funcs["ObjectMap"])
    for k in funcs:
      if k == "Object": continue
      
      f = funcs[k]
      if f.class_parent == None:
        funcs["Object"].add_class_child(f)
        
  def add_builtin_methods(self):
    for k in self.functions:
      f = self.functions[k]
      if not node_is_class(f): continue
  
  def warning(self, msg, srcnode):
    sys.stderr.write("\n%s:(%s): warning: %s"%(srcnode.file, srcnode.line+1, msg))
  
  def error(self, msg, srcnode):
    if glob.g_print_stack:
      pass #traceback.print_stack()
    
    sys.stderr.write("\n%s:(%s): error: %s\n"%(srcnode.file, srcnode.line+1, msg))
    sys.stderr.write(" " + glob.g_lines[srcnode.line] + "\n")
    
    raise JSError("%s:(%s): error: %s\n"%(srcnode.file, srcnode.line+1, msg))
  
  def get_type(self, type, scope={}):
    print("typespace.get_type call:", type)
    if type in scope:
      ret = scope[type]
    elif type in self.functions: 
      print(self.functions[type])
      if node_is_class(self.functions[type]):
        ret =  self.functions[type]
      elif self.functions[type].type == None:
        ret = VoidTypeNode()
      else:
        ret = self.functions[type].type
    elif type in self.types:
      ret =  self.types[type]
    else:
      ret =  None
      
    return ret
    
  def limited_eval(self, node):
    if type(node) in [IdentNode, StrLitNode, NumLitNode]:
      return node.val
    elif type(node) in [ExprNode, ExprListNode] and len(node.children) > 0:
      return self.limited_eval(node.children[-1])
    elif type(node) == BinOpNode:
      return self.limited_eval(node.children[1])
    elif type(node) == ArrayRefNode:
      None       
  
  def _find_in_scope(self, name, locals, func):
    globals = self.globals
    
    if name in locals:
      return locals[name]
    elif name in globals:
      return globals[name]
    elif func != None and name in func.members:
      return func.members[name]
    
  def lookup(self, node, locals={}, func=None, depth=0):
    if type(node) == IdentNode:
      if depth == 0:
        return self._find_in_scope(node.val, {}, None)
      else:
        return node
    elif type(node) == BinOpNode and node.op == ".":
      if type(node.children[0]) == IdentNode:
        var = self._find_in_scope(node.children[0].val, locals, func)
        
        if var == None: return None
        
        ret = self.member_lookup(var, node.children[1])
        return ret
      else:
        var = self.lookup(node.children[0], locals, func)
        
        return self.member_lookup(var, node.children[1])
  
  """
  def member_add(self, node, mname, member):
    if type(node) == FunctionNode:
      node.members[mname] = member
    elif type(node) == ObjLitNode:
      node.add(AssignNode(IdentNode(mname), member))
      
  def member_lookup(self, node, member):
    member = member.val
    
    if type(node) == FunctionNode:
      member = "this." + member
      if member in node.members:
        return node.members[member]
    elif type(node) == ObjLitNode:
      for m in node.children:
        mname = self.limited_eval(m.children[0])
        if mname == member:
          return m.children[1]
  """
  
  def build_type(self, node, locals, func):
    is_class = func != None and func_is_class(func)
    
    globals = self.globals
    
    #handle builtins first
    if type(node) == NumLitNode:
      return self.types["number"]
    elif type(node) == StrLitNode:
      return self.types["string"]
    elif type(node) == ArrayLitNode:
      return node
    elif type(node) == ObjLitNode:
      return node
    elif type(node) == FunctionNode:
      return node
      
    if type(node) == IdentNode:
      var = node.val
      if var == "this":
        var = node
        while var != None and not node_is_class(var):
          var = var.parent
        
        if var == None:
          return None
      elif var in locals:
        var = locals[var]
      elif "this." in var and var in func.members:
        var = func.members[var]
      elif var in globals:
        var = globals[var]
      elif var in self.types:
        var = self.types[var]
      else:
        return None
       
      return var
      
    if type(node) == ExprNode:
      return self.build_type(node.children[0], locals, func)
    elif type(node) == BinOpNode:
      if node.op == ".":
        t = self.build_type(node.children[0], locals, func)
        if t != None:
          name = self.limited_eval(node.children[1])
          return self.member_lookup(t, node.children[1])
        else:
          return None
      else:
        return self.build_type(node.children[1], locals, func)
    elif type(node) == KeywordNew:
      var = node.children[0]
      if type(var) == FuncCallNode:
        return self.build_type(var.children[0], locals, func)
      elif type(var) == IdentNode:
        return self.build_type(var, locals, func)
    if type(node) == FuncCallNode:
        return self.build_type(node.children[0], locals, func)
    
    if isinstance(node, BuiltinType):
      return node
    
    print("build_types IMPLEMENT ME: %s"%str(type(node)))
   
  def infer_types(self, nfiles):
      self.filenodes = nfiles
      infer_types(self)
