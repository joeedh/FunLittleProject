import traceback
from js_ast import *
from js_global import glob, Glob
from js_typespace import *
from js_cc import *
from js_process_ast import *
import os, os.path
import ctypes, struct

class TypeEmitVisit(NodeVisit):
  def __init__(self):
    super(TypeEmitVisit, self).__init__()
    
    self.required_nodes = node_types
    
    for n in set(self.required_nodes):
      if isinstance(n, TypeNode):
        self.required_nodes.remove(n)
  
  def StrLitNode(self, node, scope, emit, tlevel):
    pass
  def NumLitNode(self, node, scope, emit, tlevel):
    pass
  def IdentNode(self, node, scope, emit, tlevel):
    pass
  def BinOpNode(self, node, scope, emit, tlevel):
    handle_nodescope_pre(node, scope)
    
    handle_nodescope_pre(node, scope)
    
  def NegateNode(self, node, scope, emit, tlevel):
    pass
  def TypeofNode(self, node, scope, emit, tlevel):
    pass
  def VarDeclNode(self, node, scope, emit, tlevel):
    pass
  def AssignNode(self, node, scope, emit, tlevel):
    pass
  def ForLoopNode(self, node, scope, emit, tlevel):
    handle_nodescope_pre(node, scope)
    for c in node.children:
      emit(c, scope)
    handle_nodescope_pre(node, scope)
    
  def WhileNode(self, node, scope, emit, tlevel):
    for c in node.children:
      emit(c, scope)
      
  def DoWhileNode(self, node, scope, emit, tlevel):
    for c in node.children:
      emit(c, scope)
      
  def ElseNode(self, node, scope, emit, tlevel):
    for c in node.children:
      emit(c, scope)
      
  def IfNode(self, node, scope, emit):
    for c in node.children:
      emit(c, scope)
      
  def FunctionNode(self, node, scope, emit, tlevel):
    handle_nodescope_pre(node, scope)
    for c in node.children:
      emit(c, scope)
    handle_nodescope_pre(node, scope)
    
  def WithNode(self, node, scope, emit, tlevel):
    handle_nodescope_pre(node, scope)
    for c in node.children:
      emit(c, scope)
    handle_nodescope_pre(node, scope)

  def StatementList(self, node, scope, emit, tlevel):
    for c in node.children:
      emit(c, scope)

def assign_is_member(node):
    return type(node[0]) == BinOpNode and type(node[0][0]) == IdentNode and \
           node[0][0].val == "this" and type(node[0][1]) == IdentNode

def node_type_str(node):
  if node == None: return "None"
  elif type(node) == str: return "str(%s)"%node
  else: return node.get_ntype_name()

def resolve_final_types(node, typespace, scope=None, depth=0):
  handle_nodescope_pre(node, scope)
  
  try:
    ret = resolve_final_types_intern(node, typespace, scope, depth)
  except JSError:
    handle_nodescope_post(node, scope)
    
    raise sys.exc_info()[1]
    return None
    
  handle_nodescope_post(node, scope)
  return ret

def get_func(node, typespace):
    if type(node) == FunctionNode: return node
    elif type(node) == IdentNode: 
      print("<<<<<<<<<", get_func(typespace.get_type(node.val), typespace))
      return get_func(typespace.get_type(node.val), typespace)
    elif type(node) == TypeRefNode: return get_func(typespace.get_type(node.type), typespace)
    elif type(node) == TemplateNode: return get_func(node.name_expr, typespace)
    else: return None

def is_type_call(node, typespace):
  ret = type(node) == IdentNode and type(node.parent) == BinOpNode and node.parent.op == "."
  ret = ret and node == node.parent[1] and type(node.parent[0]) == IdentNode
  
  if not ret: return False
  
  func = get_func(node.parent[0])
  
  return func != None and node_is_class(func) == True

class ScopeSort (str):
  def sort_str(self):
    s = str(self)
    while s.startswith("_"):
      s = s[1:]
    return s.lower()
    
  def __gt__(self, b):
    sa = self.sort_str()
    sb = b.sort_str()
    return sa > sb
    
  def __lt__(self, b):
    sa = self.sort_str()
    sb = b.sort_str()
    return sa < sb
    
  def __eq__(self, b):
    sa = self.sort_str()
    sb = b.sort_str()
    return sa == sb
    
def print_scope(scope):
  keys = []
  for k in scope.keys():
    t = node_type_str(scope[k])
    
    end = "Node"
    if "Node" not in t:
      end = "Type"
      
    if end not in t:
      keys.append([k, t])
      continue
      
    span = t[0:t.find(end)]
    t2 = end
    if span.endswith("Type"):
      t2 = "Type"
      span = span[:-4]
      
    t = span
    if len(t) > 10:
      t = t[:10]
    keys.append([k, t])
    
  stack = [ScopeSort("%s: %s"%(k1, k2)) for k1,k2 in keys]
  stack.sort()
  
  s = ""
  for i, s2 in enumerate(stack):
    if i > 0: s += ", "
    s += s2
  if glob.g_debug_typeinfer:
    print(s)
  
def resolve_final_types_intern(node, typespace, scope=None, depth=0):
  if scope == None: scope = NodeScope()
  
  print_scope(scope)  
  if glob.g_debug_typeinfer:
    print(tab(depth, " ") + "--",node.get_ntype_name() + " " + node.extra_str())
  
  if type(node) == NumLitNode:
    node.final_type = BuiltinTypeNode(node.get_type_str())
    
    ret = node.final_type
  elif type(node) == ForInNode:
    c1 = resolve_final_types(node[1], typespace, scope, depth+1)
    
    func = get_func(c1, typespace)
    if glob.g_debug_typeinfer:
      print(func)
    if type(func) != FunctionNode:
      typespace.error("Invalid iteration object", node)
    
    if "__iterator__" in func.members:
      func = get_func(func.type, typespace)
    
    if func == None:
      typespace.error("Invalid iteration object (could not resolve __iteration__ return type)", node)
    
    c2 = None
    if "next" in func.members:  
      c2 = resolve_final_types(func.members["next"], typespace, scope, depth+1)
    
    if c2 == None:
      typespace.error("Invalid iteration object (could not resolve next)", node)
    
    node.final_type = c2
    node[0].final_type = c2
    scope[node[0].val] = c2
  elif type(node) == ArrayRefNode:  
    c = resolve_final_types(node[0], typespace, scope, depth+1)
    resolve_final_types(node[1], typespace, scope, depth+1)
    
    if glob.g_debug_typeinfer:
      print(c)
    if type(c) == TemplateNode:
      node.final_type = TemplateStandInType()
      resolve_final_types(c[1], typespace, scope, depth+1)
    else:
      node.final_type = typespace.get_type("Object")
    
  elif type(node) == StrLitNode:
    node.final_type = BuiltinTypeNode("String")
    
    ret = node.final_type
  elif type(node) == InitCallNode:
    for c in node.children[1:]:
       resolve_final_types(c, typespace, scope, depth+1)
    node.final_type = VoidTypeNode()
    
  elif type(node) == TypeRefNode:
    node.final_type = typespace.get_type(node.type, scope)
    if node.template != None:
      node.template.name_expr = IdentNode(node.type)
      node.template.final_type = node.final_type
      node.final_type = node.template
   
    if node.final_type == None:
      typespace.error("Could not resolve type %s"%node.val, node)
  elif type(node) == IdentNode:
    if node.val == "false": 
      node.final_type = BuiltinTypeNode("bool")
    elif node.val == "true": 
      node.final_type = BuiltinTypeNode("bool")
    
    if node.type != None:
      node.final_type = node.type
      
    if node.final_type == None:
      node.final_type = typespace.get_type(node.val, scope)
    
    if node.final_type == None:
      if glob.g_debug_typeinfer:
        print(node.parent.parent)
      typespace.error("Could not resolve variable or member %s"%node.val, node)
  elif type(node) == BinOpNode:
    c1 = resolve_final_types(node[0], typespace, scope, depth+1)
    if node.op == ".":
      func = get_func(c1, typespace)
      if glob.g_debug_typeinfer:
        print(node[0], c1, func)
      
      if type(func) != FunctionNode:
        typespace.error("Cannot use . member lookup operation on non-objects", node)
      
      funclist = []
      while func != None:
        funclist = [func] + funclist
        func = func.class_parent
      
      funclist.reverse()
      for func in funclist:
        for c in func.members:
          scope[c] = func.members[c]
    c2 = resolve_final_types(node[1], typespace, scope, depth+1)
        
    if node.op == ".":
      node.final_type = c2
    else:
      node.final_type = c1
  elif type(node) == NegateNode:
    node.final_type = resolve_final_types(node[0], typespace, scope, depth+1)
    
    if node.final_type == None:
        typespace.error("Could not resolve type : %s" % node[0].extra_str(), node)
  elif type(node) == FuncCallNode:
    node.final_type = resolve_final_types(node[0], typespace, scope, depth+1)
    
    if node.final_type == None:
        typespace.error("Could not resolve type : %s" % node[0].extra_str(), node)
    
    for c in node[1]:
      resolve_final_types(c, typespace, scope, depth+1)
      
    if node.template != None:
      node.template.name_expr = node[0]
      node.final_type = node.template
  elif type(node) == KeywordNew:
    node.final_type = resolve_final_types(node[0], typespace, scope, depth+1)
    if node.final_type == None:
      typespace.error("Could not resolve type", node)
  elif type(node) == ArrayLitNode:
    node.final_type = typespace.types["Array"]
    
    lastt = None
    same_types = True
    global_type = None
    for c in node[0].children:
      resolve_final_types(c, typespace, scope, depth+1)
      
      if lastt != None and not types_match(lastt, c.final_type, typespace):
        same_types = False
        
      lastt = c.final_type
      if global_type == None: 
        global_type = lastt
      elif type(lastt) == BuiltinTypeNode and lastt.type == "float":
        global_type = lastt
     
    if same_types and lastt != None:
      tn = TemplateNode(ExprListNode([global_type]))
      tn.name_expr = IdentNode("Array")
      tn.add(tn.name_expr)
      
      node.final_type = tn
  elif type(node) == ObjLitNode:
    node.final_type = typespace.types["ObjectMap"]
    
    lastt = None
    same_types = True
    global_type = None
    for c in node.children:
      resolve_final_types(c[1], typespace, scope, depth+1)
      c[0].final_type = c[1].final_type
      c.final_type = c[1].final_type
      
      if lastt != None and not types_match(lastt, c[0].final_type, typespace):
        same_types = False
        
      lastt = c[0].final_type
      if global_type == None: 
        global_type = lastt
      elif type(lastt) == BuiltinTypeNode and lastt.type == "float":
        global_type = lastt
     
    if same_types:
      tn = TemplateNode(ExprListNode([global_type]))
      tn.name_expr = IdentNode(node.final_type.name)
      tn.add(tn.name_expr)
      
      node.final_type = tn
  elif type(node) == VarDeclNode:
    if type(node[1]) != UnknownTypeNode:
      node.final_type = node[1]
      
      scope[node.val] = node.final_type
      
      return node.final_type
    else:
      node.final_type = resolve_final_types(node[0], typespace, scope, depth+1)
      if node.final_type == None:
        typespace.error("Could not resolve type %s"%node.val, node)
        
      scope[node.val] = node.final_type
  elif type(node) == AssignNode:
    if node.type != None:
      node.final_type = node.type
      
      return node.final_type
    else:
      try:
        node.final_type = resolve_final_types(node[0], typespace, scope, depth+1)
      except JSError:
        node.final_type = None
        
      if node.final_type == None:
        node.final_type = resolve_final_types(node[1], typespace, scope, depth+1)
        if type(node[0]) == BinOpNode and type(node[0][0]) == IdentNode and \
           node[0][0].val == "this" and type(node[0][1]) == IdentNode:
          func = scope["this"]
          func.members[node[0][1].val] = node.final_type
      else:
        c = resolve_final_types(node[1], typespace, scope, depth+1)
        if assign_is_member(node):
          node.final_type = c
        
    if node.final_type == None:
      typespace.error("Could not resolve type", node)
  elif type(node) == FunctionNode:
    if "this" in scope:
      if scope["this"].template != None:
        for a in scope["this"].template[0]:
          scope[get_arg_name(a)] = TemplateStandInType()
        
    if node.template != None:
      for a in node.template[0]:
        scope[get_arg_name(a)] = TemplateStandInType()
    
    for a in node[0]:
      if a.type == None or type(a.type) == UnknownTypeNode:
        a.final_type = resolve_final_types(a, typespace, scope, depth+1)
        if node.final_type == None:
          typespace.error("Could not resolve type", node)
      else:
        a.final_type = a.type
       
      if a.final_type == None:
        if type(a.final_type) in IdentNode:
          a.final_type = typespace.get_type(a.final_type.val)
      
      scope[get_arg_name(a)] = a.final_type
    for c in node[1:]:
      resolve_final_types(c, typespace, scope, depth+1)
    
    
    node.final_type = node.type if node.type != None else VoidTypeNode()
    
    return typespace.types["Function"]
  else:
    for c in node.children:
      resolve_final_types(c, typespace, scope, depth+1)
  
  if glob.g_debug_typeinfer:
    print("------------------------at end for " +node.get_ntype_name())
  
  return node.final_type

def transform_init_calls(node, typespace):
  def transform_class_init(node):
    valid = type(node.parent) == BinOpNode and node.parent.op == "." 
    valid = valid and node == node.parent[1] and type(node.parent[0]) == IdentNode
    
    func = get_func(node.parent[0], typespace)
    if func != None:
      n = InitCallNode(IdentNode(func.name))
      n.template = node.template
      for c in node.children[1:]:
        n.add(c)
        
      node.parent.parent.replace(node.parent, n)
  traverse(node, FuncCallNode, transform_class_init)
  
typespace = None
def resolve_types(node, typespace2=None):
  global typespace
  
  if typespace2 != None: typespace = typespace2
  
  print("Type emit!")
  
  typespace = JSTypeSpace()
  typespace.infer_types([node])
  
  def remove_unknown_types(node):
    if type(node.type) == UnknownTypeNode:
      node.type = None
    
    if type(node) == FunctionNode:
      for k in node.members:
        if type(node.members[k]) == UnknownTypeNode:
          if len(node.members[k]) > 0 and type(node.members[k][0]) == FunctionNode:
            node.members[k] = node.members[k][0].type
            if node.members[k] == None:
              node.members[k] = VoidTypeNode()
          else:
            node.members[k] = None
          
    for c in node.children:
      remove_unknown_types(c)
      
  remove_unknown_types(node)
  transform_init_calls(node, typespace)
  
  try:
    resolve_final_types(node, typespace)
  except JSError:
    s = traceback.format_exc() #limit=4)
    lines = s.split("\n")
    for i in range(len(lines)):
      l = lines[i].split(" ")
      line = ""
      for part in l:
        if len(part) == 0:
          line += " "
          continue
        
        part = part.strip()
        if part[0] == ",": part = part[1:]
        if part[-1] == ",": part = part[:-1]
        part = part.strip()
        
        if part[0] == '"' and part[-1] == '"':
          part = part[1:-1]
          
        if part.endswith(".py"):
          part = os.path.split(part)[1]
        
        line += part + " "
      lines[i] = line
      if i%2 == 0:
        lines[i] += "\n"
    
    if len(lines) > 12:
      lines = lines[len(lines)-12:]
      
    for l in lines:
      print(l)
            
    sys.exit(-1)
    
  def final_types_to_types(n):
    if type(n.type) != str:
      n.type = n.final_type
    for c in n.children:
      final_types_to_types(c)
  
  final_types_to_types(node)
  #node_emit = TypeEmitVisit()
  #node_emit.traverse(node)
  
  if glob.g_debug_typeinfer:
    print(node)

def resolve_struct(node):
  i = 0
  print("yay", node.name, node.members)
  for k in node.members:
    m = node.members[k]
    if type(m) == FunctionNode: continue
    print(m.type)
  
def resolve_structs(nfiles, typespace2=None):
  global typespace
  
  if typespace2 != None:
    typespace = typespace2
  
  typespace.filenodes = nfiles
  
  traverse_files(FunctionNode, resolve_struct); 
  