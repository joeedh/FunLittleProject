from random import random, seed
import time

def find_node(node, ntype, strict=False, depth=0):
  if type(node) == ntype:
    if not (depth == 0 and strict):
      return node
    
  for n in node.children:
    ret = find_node(n, ntype, strict, depth+1)
    if ret != None: return ret
  return None

def traverse_i(n, ntype, func, i, cur=None, use_depth=False, 
             exclude=[], copy_children=False, depth=0):
  if cur == None:
    cur = [0]
  
  if type(n) in exclude and depth != 0:
    return
  
  if copy_children:
    cs = n[:]
  
  if type(n) == ntype: 
    if cur[0] == i:
      cur[0] += 1
      if use_depth:
        func(n, depth)
      else:
        func(n)
    else:
      cur[0] += 1
    
  if not copy_children:
    cs = n.children
    
  for c in cs:
    traverse_i(c, ntype, func, i, cur, use_depth, exclude, copy_children, depth+1)

def null_node(n):
  return n in [0, None]

def traverse(n, ntype, func, use_depth=False, 
             exclude=[], copy_children=False, 
             use_scope=False, scope=None, depth=0):
  if scope == None: scope = {}
  scope = handle_scope(n, scope)
  
  if type(exclude) != list and type(exclude) != tuple and issubclass(exclude, Node):
    exclude = [exclude]
  
  if type(n) in exclude and depth != 0:
    return

  if copy_children:
    cs = n[:]
  
  if type(n) == ntype: 
    if use_depth and use_scope:
      func(n, scope, depth)
    elif use_scope:
      func(n, scope)
    elif use_depth:
      func(n, depth)
    else:
      func(n)
  
  if not copy_children:
    cs = n.children
    
  for c in cs:
    traverse(c, ntype, func, use_depth, exclude, copy_children, use_scope, scope, depth+1)

def validate_class_this_refs(typespace, cls, scope):
  def visit(n):
    #this isn't bound in nested functions
    if type(n) == FunctionNode:
      return;
    
    if type(n) == IdentNode and n.val == "this":
      if type(n.parent) == BinOpNode and n.parent.op == "." and n == n.parent[0]:
        if n.parent[1].gen_js(0).strip() not in scope:
          typespace.error("Unknown property " + n.parent[1].gen_js(0).strip(), n.parent)
      
    for c in n:
      visit(c)
    
  for c2 in cls:
    if type(c2) != VarDeclNode:
      visit(cls)

"""
a.b.?c().?d.f.?d

var _t = undefined;

function qexpr(a) {
  var _t = a.b;
  
  if (_t == undefined) {
    return undefined;
  }
  
  _t = _t.c();
  
  if (_t == undefined) {
    return undefined;
  }
  
  _t = _t.d.f;
  
  if (_t == undefined) {
    return undefined;
  }
  
  _t = _t.d;
  
  return _t;
}

#"""

import hashlib, base64

def transform_exisential_operators(node, typespace):
  vset = set()
  
  def get_ud(n, hash=None):
    if hash == None: 
      hash = hashlib.sha1()
    
    bstr = bytes(str(n.get_line_str())+str(n.lexpos), "latin-1")
    hash.update(bstr);
    
    if n.parent != None:
      get_ud(n.parent)
    
    ret = base64.b64encode(hash.digest())
    ret = str(ret, "latin-1")
    
    ret = ret.replace("=", "").replace("/", "").replace("=", "").replace("+", "").replace("-", "")
    
    return "q" + ret[:8] + "_" + str(n.lexpos)
  
  def visit(n):
    #find distinct chain
    if n.op != ".?": return
    if n in vset: return
    
    vset.add(n);
    id = get_ud(n);
    
    validops = [".", ".?"]
    
    #find head of chain
    p = n
    #print(p.get_line_str())
    while p != None and type(p) == BinOpNode and type(p.parent) == BinOpNode: # and p.op in validops:
      #vset.add(p[0])
      #vset.add(p[1])
      p = p.parent
      vset.add(p)
      #print(p.get_line_str())
      #print(p.parent.get_line_str())
    
    slist = StatementList()
    en = js_parse("_t = _t.$n;", [n[1]], start_node=AssignNode);
    slist.add(en)
    en = en[1]
    
    n2 = n.parent
      
    while n2 != p.parent and type(n2) == BinOpNode: # and n2.parent != p:
      if n2.op != ".?":
        #print(type(p))
        enp = en.parent
        en2 = BinOpNode(en, n2[1], n2.op)
        enp.replace(en, en2)
        en = en2
      else:
        slist.add(js_parse("if (_t == undefined) return undefined;"))
        en = js_parse("_t = _t.$n;", [n2[1]], start_node=AssignNode);
        slist.add(en)
        
      n2 = n2.parent
    
    slist.add(js_parse("return _t;"));
    
    fn = js_parse("""
      function $s(obj) {
        var _t = obj;
        if (_t == undefined) return undefined;
        
        $n
      }""", [id, slist], start_node=FunctionNode);
    
    print(fn.gen_js(1))
    
    #find body to put function in
    p2 = p
    lastp2 = p
    while p2.parent != None and not isinstance(p2, FunctionNode):
      lastp2 = p2
      p2 = p2.parent
    
    if isinstance(p2, FunctionNode):
      p2.insert(1, fn)
    else:
      p2.insert(p2.index(lastp2), fn)
      
    #"""
    cn = FuncCallNode(id)
    cn.add(ExprListNode([n[0]]))
    p.parent.replace(p, cn)
    #"""
    
  #traverse(node, BinOpNode, visit)
  def dovisit(n):
    for c in n:
      dovisit(c)
    
    if type(n) == BinOpNode:
      visit(n)
  
  dovisit(node)
  flatten_statementlists(node, typespace)
  
  
def transform_exisential_operators_old(node, typespace):
  tfuncmap = {}
  idfuncmap = {}
  
  def ensure_tempvar(n, prefix="$_eop"):
    startn = n
    while n.parent != None and not isinstance(n, FunctionNode):
      n = n.parent
    
    if n not in tfuncmap:
      tfuncmap[n] = {}
      idfuncmap[n] = 0
      
    tmap = tfuncmap[n]
    
    if startn not in tmap:
      tmap[startn] = idfuncmap[n];
      idfuncmap[n] += 1
    else:
      idx = tmap[startn]
      tname = "%s%i" % (prefix, idx)
      return tname
      
    idx = tmap[startn]
    tname = "%s%i" % (prefix, idx)
    
    for c in n:
      if type(c) == VarDeclNode and c.val == tname:
        #return tname
        pass
      pass
      
    n2 = VarDeclNode(ExprNode([]), name=tname)
    n2.add(UnknownTypeNode())
    n2.modifiers.add("local")
    n.prepend(n2)
    
    return tname
  
  def has_leaf(n):
    for c in n:
      if type(c) == BinOpNode and c.op == ".?": return True
      if has_leaf(c): return True
      
    return False
  
  doneset = set()
  
  def tag(n):
    doneset.add(n)
    for c in n:
      tag(c);
  
  def has_cond(n):
    if type(n) == BinOpNode and n.op == ".?": return True
    
    n2 = n
    while type(n2.parent) == BinOpNode and type(n2) == BinOpNode and n2.op in [".", ".?"]:
      n2 = n2.parent
      if n2.op == ".?": return True
      
    for c in n:
      if has_cond(c):
        return True
    return False
  
  condset = set()
  def start_tag(n):
    if has_cond(n):
      condset.add(n)
    for c in n:
      start_tag(c)
      
  def visit(n):
    if n in doneset: return
    doneset.add(n)
    
    if type(n) == BinOpNode and n.op in [".", ".?"]:
      start_tag(n)
     
    for c in n:
      visit(c)
      
    if type(n) != BinOpNode: return
    if n.op not in [".?", "."]: return
    if n not in condset: return
    
    #find head of chain
    n2 = n
    while n2.parent != None and type(n2.parent) == BinOpNode and n2.parent.op in [".?", "."]:
      n2 = n2.parent
      
    t = ensure_tempvar(n2, "$_eop_t")
    name = t
    
    idx = -1
    if type(n[0]) == ExprListNode and type(n[1]) == ExprListNode:
      accu = n[0]
      for c in n[1]:
        accu.add(c)
    elif type(n[0]) == ExprListNode:
      accu = n[0]
      idx = 1
    elif type(n[1]) == ExprListNode:
      accu = n[1]
      idx = 0
    else:
      accu = ExprListNode([])
      accu.add_parens = True
      idx = 2
   
    if idx in [0, 1]:
      n2 = js_parse("""
        $s1 = $s1 ? $s1.$n2 : undefined
      """, [name, n[1]], start_node=AssignNode)
      
      accu.add(n2)
    elif idx == 2:
      n2 = js_parse("""
        $s1 = $n2 ? $n2.$n3 : undefined
      """, [name, n[0], n[1]], start_node=AssignNode)
      
      accu.add(n2)
    
    n.parent.replace(n, accu)
    
    #print(n)
    
  def visit1(n):
    if n in doneset: return
    doneset.add(n)
    
    stop = has_leaf(n) #and (type(n) == BinOpNode and n.op == ".?")
    
    for c in n:
      visit(c)
        
    if stop: return
    if type(n) != BinOpNode: return
    if type(n.parent) != BinOpNode: return
    if n.op != ".?": return
    
    #print(stop, n.get_line_str(), n[0].get_line_str(), n[1].get_line_str(), n.op if type(n) == BinOpNode else "")
    
    tname = ensure_tempvar(n, "t")
    
    startn = n
    lst = [tname, n[0], n[0], n[1]]
    n2 = js_parse("$s = $n != undefined ? $n.$n : undefined;", lst, start_node=AssignNode)
    
    accu = ExprListNode([])
    accu.add(n2)
    return
    n = n.parent
    lastn = n
    while n != None and type(n) == BinOpNode and n.op in [".", ".?"]:
      doneset.add(n)
      
      tag(n)
      print(type(n.children[0]), type(n.children[1]))
      lst = [tname, n[1]]
      n3 = js_parse("$s1 = $s1 != undefined ? $s1.$n2 : undefined;", lst, start_node=AssignNode)
      accu.prepend(n3)
      
      lastn = n
      n = n.parent
    
    #print(lastn)
    #startn.parent.remove(startn)
    tag(lastn)
    if lastn in lastn.parent.children:
      print("removing")
      lastn.parent.replace(lastn, accu)
  
  print("--starting")
  visit(node)

def gen_manifest_file(result, typespace):
  
  """this bit of code clears all type info.
     helpful for figuring out how much of the program,
     percentage-wise, is already typed.
     
     NOTE: this corrupts the AST tree.
  def rec1(n):
    n.type = UnknownTypeNode()
    for c in n:
      rec1(c)
  rec1(result)
  #"""
  
  def build_func_name(n):
    if type(n) == FunctionNode:
      s1 = "function"
    elif type(n) == MethodGetter:
      s1 = "getter"
    elif type(n) == MethodSetter:
      s1 = "setter"
    elif type(n) == MethodNode:
      s1 = "method"
    
    s1 = n.name
    if type(n) in [MethodGetter, MethodSetter, MethodNode]:
      s1 = n.parent.name + "." + s1
    
    return s1
  def function_sig(n):
    s = n.name + "("
    
    needs_typeinfo = False
    
    for i, c in enumerate(n[0]):
      if i > 0: s += ","
      if c.type != None and type(c.type) != (UnknownTypeNode):
        s += c.type.get_type_str() + " "
      else:
        s += "Object "
        needs_typeinfo = True
        
      s += c.gen_js(0)
    s += ")"
    
    if n.type != None and type(n.type) != UnknownTypeNode:
      s += " : " + n.type.get_type_str();
    elif not (n.name == "constructor" and type(n) == MethodNode):
      def rec(n2):
        if type(n2) == ReturnNode and len(n2[0].gen_js(0).strip()) > 0:
          return True
        
        ret = False
        for c in n2:
          if not isinstance(c, FunctionNode):
            ret |= rec(c)
        return ret
          
      needs_typeinfo = needs_typeinfo or rec(n)
    
    if needs_typeinfo and glob.g_warn_types:
      typespace.warning(build_func_name(n) + " needs typing", n)
    
    return s
    
  def visit_cls(n):
    name = n.name
    parents = [c.gen_js(0) for c in n.parents]
    s = "class " + name + " "
    if len(parents) > 0:
      s += "extends "
      for i, p in enumerate(parents):
        if i > 0: s += ","
        s += p
    s += " {\n"
    
    for c in n:
      if type(c) == VarDeclNode:
        s += c.gen_js(0) + ";\n"
      else:
        s += "  " + function_sig(c) + "\n"
    s += "}"
    
    return s
    
  
  #only visit top-level classes, for now
  s = "EXPORT \"%s\"\n" % glob.g_file
  for c in result:
    if type(c) == ClassNode:
      s += visit_cls(c) + "\n"
    elif type(c) == FunctionNode:
      s += "function " + function_sig(c) + "\n"
    elif type(c) == AssignNode and "." not in c[0].gen_js(0) and "[" not in c[0].gen_js(0):
      if c.type != None and type(c.type) != UnknownTypeNode:
        s += c.type.get_type_str() + " "
      else:
        s += "Object "
        if glob.g_warn_types:
          typespace.warning("type missing for global " + c[0].gen_js(0), c)
      
      s += c[0].gen_js(0)+"\n";
    elif type(c) == VarDeclNode:
      s += "global "
      if c.type != None and type(c.type) != UnknownTypeNode:
        s += c.type.get_type_str() + " "
      else:
        s += "Object "
        if glob.g_warn_types:
          typespace.warning("type missing for global " + c.val, c)
      s += c.val+"\n";
  
  s += "\n"
  #traverse(result, ClassNode, visit_cls)
  return s
  
_the_typespace = None

def expand_harmony_class(result, cls):
  global _the_typespace
  
  arglist = ExprListNode([])
  
  methodlist = ArrayLitNode(ExprListNode([]))
  
  arglist.add(StrLitNode('"'+cls.name+'"'))
  if len(cls.parents) > 0:
    arglist.add(cls.parents[0])
  arglist.add(methodlist)
      
  #find constructor method
  found_con = False
  methods = []
  
  con = None
  for m in cls:
    if type(m) not in [MethodNode, MethodGetter, MethodSetter]:
      continue
      
    if m.name == "constructor":
      found_con = True
      con = m
      
    methods.append(m)
  
  if not found_con:
    #create a default constructor
    if len(cls.parents) > 0:
      slist = js_parse("""
        $s.apply(this, arguments);
      """, [cls.parents[0].gen_js(0)])
    else:
      slist = StatementList()
    
    con = MethodNode("constructor", False);
    con.add(ExprListNode([]))
    con.add(slist)
    methods.append(con)
    
  cls_scope = {}
  for m in methods:
    if type(m) in [MethodNode, MethodGetter, MethodSetter]:
      if m.name != "constructor":
        cls_scope[m.name] = m
      
      if m.name == "eval":
        _the_typespace.error("Class methods can't be named eval", m);
        
      callnode = None
      
      if type(m.name) != str:
        if type(m.name) == BinOpNode:
          name = m.name[1]
          
          if type(name) == IdentNode:
            name = name.val
            
          if type(name) == str:
            fnode = FunctionNode(name)
          else:
            fnode = FunctionNode("(anonymous)")
            fnode.is_anonymous = True
        else:
          fnode = FunctionNode("(anonymous)")
          fnode.is_anonymous = True
          
        callnode = FuncCallNode(BinOpNode("_ESClass", "symbol", "."))
        
        name = m.name
        if type(name) in (int, float):
          name = NumLitNode(name)
        
        callnode.add(ExprListNode([name, fnode]))
      else:
        fnode = FunctionNode(m.name if m.name != "constructor" else cls.name)
        fnode[:] = []
        
      for c in m:
        fnode.add(c.copy())
      
      if callnode != None:
        fnode = callnode
        
      if type(m) == MethodGetter:
        callnode = FuncCallNode(BinOpNode("_ESClass", "get", "."))
        callnode.add(fnode)
        fnode = callnode
      if type(m) == MethodSetter:
        callnode = FuncCallNode(BinOpNode("_ESClass", "set", "."))
        callnode.add(fnode)
        fnode = callnode
      if m.is_static:
        callnode = FuncCallNode(BinOpNode("_ESClass", "static", "."))
        callnode.add(fnode)
        fnode = callnode
      
      methodlist[0].add(fnode)

  con = None
  found_con = False
  
  for m in methods:
    if m.name == "constructor":
      if found_con: raise SyntaxError("Cannot have multiple constructor methods")
      if type(m) != MethodNode: raise SyntaxError("Constructors cannot be get/setters")
      
      found_con = True
      con = m
      
  parent = cls.parents[0] if len(cls.parents) != 0 else None
  
  n = FuncCallNode("_ESClass")
  n.add(arglist)
  n2 = VarDeclNode(n, local=True, name=cls.name);
  
  return n2

def expand_harmony_classes(result, typespace):
  global _the_typespace
  _the_typespace = typespace

  expand_harmony_super(result, typespace)

  def visit(n):
    n.parent.replace(n, expand_harmony_class(typespace, n))
    
  traverse(result, ClassNode, visit)
  flatten_statementlists(result, typespace)
  
def expand_harmony_super(result, typespace):
  global _the_typespace
  
  _the_typespace = typespace
  
  flatten_statementlists(result, typespace)
      
  def repl_super(cls, method, base, gets, sets, methods):
    def visit(n):
      if n.val != "super":
        return
      #print("found super!", base.val)
      
      if isinstance(n.parent, FuncCallNode):
        n.parent[1].prepend("this")
        n.parent.replace(n, BinOpNode(base.copy(), "call", "."))
      elif isinstance(n.parent, BinOpNode) and n.parent.op == "." and isinstance(n.parent[1], FuncCallNode):
        n3 = n.parent[1].copy()
        n3[1].prepend("this")
        n4 = BinOpNode(n3[0], "call", ".")
        n3.replace(n3[0], n4)
        
        n2 = js_parse("$s.prototype", [base.val, n3], start_node=BinOpNode)
        n.parent.replace(n, n2)
        n.parent.replace(n.parent[1], n3)
      elif isinstance(n.parent, BinOpNode) and n.parent.op == "." and isinstance(n.parent[1], IdentNode):
        typespace.warning("Super property access!", n);
        
        n2 = js_parse("__bind_super_prop(this, $s, $s, '$s')", [cls.name, base.val, n.parent[1].val], start_node=FuncCallNode)
        
        n.parent.parent.replace(n.parent, n2)
      
    traverse(method, IdentNode, visit);

  def visit(node):
    def has_super(node):
      if type(node) == IdentNode and node.val == "super": 
        return True
        
      ret = False
      for c in node:
        ret = ret or has_super(c)
      return ret
  
    if not has_super(node):
      return
      
    gets = {}
    sets = {}
    methods = {}
    
    for c in node:
      if isinstance(c, MethodGetter):
        gets[c.name] = c
      elif isinstance(c, MethodSetter):
        sets[c.name] = c
      elif isinstance(c, MethodNode):
        methods[c.name] = c 
        
    if len(node.parents) > 1:
      typespace.error("Super not allowed in classes with multiple inheritance", node)
    elif len(node.parents) == 0:
      typespace.error("Class " + str(node.name) + " has no parent", node)
    
    for c in node:
      repl_super(node, c, node.parents[0], gets, sets, methods)
  
  traverse(result, ClassNode, visit)
  flatten_statementlists(result, typespace)
  
def expand_requirejs_class(typespace, cls):
  node = FunctionNode(cls.name, 0)  
    
  params = ExprListNode([])
  slist = StatementList()
  vars = [];
  cls_scope = {}
  
  #properties
  for c in cls:
    if type(c) == VarDeclNode:
      cls_scope[c.val] = c;
      cs = c[2:]
      c.children = c.children[:2]
      
      vars.append(c)
      for c2 in cs:
        cls_scope[c2.val] = c2;
        vars.append(c2)
  
  methods = []
  for c in cls:
    if type(c) in [MethodNode, MethodGetter, MethodSetter]:
      if c.name != "constructor":
        cls_scope[c.name] = c
      methods.append(c)
  
  if glob.g_validate_classes:
    validate_class_this_refs(typespace, cls, cls_scope)
  
  #find constructor method
  found_con = False
  con = None
  
  for m in methods:
    if m.name == "constructor":
      if found_con: raise SyntaxError("Cannot have multiple constructor methods")
      if type(m) != MethodNode: raise SyntaxError("Constructors cannot be get/setters")
      
      found_con = True
      
      params = m[0]
      slist = m[1]
      con = m
  
  parent = cls.parents[0] if len(cls.parents) != 0 else None
  
  if found_con == False:
    #build a default constructor
    m = MethodNode("constructor")
    print("generating default constructor...");
    
    params = ExprListNode([])
    slist = StatementList()
    
    m.add(params)
    m.add(slist)
    con = m
  
  vars.reverse();
  for c in vars:
    val = c[0]
    if type(val) == ExprNode and len(val) == 0:
      #val = IdentNode("undefined");
      continue;
      
    a = AssignNode(BinOpNode("this", c.val, "."), val)
    slist.prepend(a)
  
  #do getters/setters
  gets = {}
  sets = {}
  props = set()
  
  for m in methods:
    if m.name == "constructor": continue
    if type(m) == MethodGetter:
      gets[m.name] = m
      props.add(m.name)
      
    if type(m) == MethodSetter:
      sets[m.name] = m
      props.add(m.name)
  
  def to_exprfunc(method):
    f = FunctionNode("(anonymous)", 0)
    f.is_anonymous = True
    
    f.children = method.children
    for c in f.children:
      c.parent = f
    
    f.type = method.type
    
    f.line = method.line
    f.lexpos = method.lexpos
    
    return f
  
  def gen_prop_define(prop, gets, sets, flags=[]):
    #since this is called from *within* the parser, we
    #can't use js_parse().
    name_expr = BinOpNode(IdentNode("Object"), IdentNode("defineProperty"), ".");
    fcall = FuncCallNode(name_expr)
    
    exprlist = ExprListNode([])
    fcall.add(exprlist)
    
    params = ObjLitNode()
    if prop in gets:
      an = AssignNode(IdentNode("get"), to_exprfunc(gets[p]))
      params.add(an)
    if prop in sets:
      an = AssignNode(IdentNode("set"), to_exprfunc(sets[p]))
      params.add(an)
      
    exprlist.add(IdentNode("this"))
    exprlist.add(StrLitNode('"%s"'%prop))
    exprlist.add(params)
    
    return fcall;
  
  def gen_method(cls, m):
    f = FunctionNode(m.name)
    f.children = m.children
    f.name = "(anonymous)"
    f.is_anonymous = True
    
    for c in f.children:
      c.parent = f
    
    if not m.is_static:
      an = AssignNode(IdentNode(m.name), f)
      f = an
    else:
      f2 = FuncCallNode(IdentNode("util.static_method"))
      f2.add(f)
      
      an = AssignNode(IdentNode(m.name), f2)
      f = an
    
    return f
    
  for p in props:
    n = gen_prop_define(p, gets, sets)
    slist.prepend(n)
    

  if found_con == False:
    #call parents hackishly
    lst = list(cls.parents)
    lst.reverse()
    for p in lst:
      if type(p) == str: p = IdentNode(p)
      
      bn = BinOpNode(p, "apply", ".")
      args = ExprListNode([IdentNode("this"), IdentNode("arguments")])
      fn = FuncCallNode(bn)
      fn.add(args)
      slist.prepend(fn)

  node.add(params)
  node.add(slist)
  node.name = "(anonymous)"
  node.is_anonymous = True
  
  an = AssignNode(BinOpNode("exports", cls.name, "."), node)
  vn = VarDeclNode(an, local=True)
  vn.val = cls.name
  
  node = vn
  
  #add stuff outside of the constructor function
  slist = StatementList()
  slist.add(node)
  node = slist
  
  proto = RJSObjLitNode();
  
  if len(cls.parents) != 0:
    #for requirejs, just do single inheritance
    if len(cls.parents) > 1:
      typespace.error("The type system we use for RequireJS doesn't support multiple inheritance", cls)
   
    p = cls.parents[0]
    
    fn = FuncCallNode(IdentNode("util.inherit"))
    fn.add(ExprListNode([IdentNode(cls.name), p, proto]))
    slist.add(AssignNode(BinOpNode(cls.name, "prototype", "."), fn))
  else:
    fn = FuncCallNode(IdentNode("util.init_prototype"))
    fn.add(ExprListNode([IdentNode(cls.name), proto]))
    slist.add(AssignNode(BinOpNode(cls.name, "prototype", "."), fn))
  
  #generate methods
  for m in cls:
    if type(m) != MethodNode: continue
    if m.name == "constructor": continue
    
    n = gen_method(cls, m)
    proto.add(n)
  
  return node
    
def expand_requirejs_classes(result, typespace):
    def visit(n):
      n.parent.replace(n, expand_requirejs_class(typespace, n))
    
    traverse(result, ClassNode, visit)
    flatten_statementlists(result, typespace)
    
class VarBinding:
  def __init__(self, node, name, type):
    self.node = node
    self.name = name
    self.type = type
  
  def copy(self):
    return VarBinding(self.node, self.name, self.type)
    
  def add(self, type):
    self.types.add(type)
    
  def remove(self, type):
    self.types.remove(type)
    
  def __getitem__(self, i):
    return self.types[i]
    
  def __setitem__(self, i, v):
    self.types[i] = v
    
  def __len__(self):
    return len(self.types)
    
class NodeScope:
  def __init__(self, parent=None): 
    self.scopestack = []
    self.scope = {}
    self.childscopes = []
    if parent != None:
      parent.childscopes.append(self)
      #for k in self.parent:
      #  self[k] = self.parent[k].copy()
        
    self.parent = parent    
  
  def __str__(self):
    return str(self.scope.keys())
  def __repr__(self):
    return str(self)
  
  def push(self):
    self.scopestack.append(self.scope)
    self.scope = dict(self.scope)
    if hasattr(glob, "g_debug_typeinfer") and glob.g_debug_typeinfer:
      print("===pushing...===")
    #for k in self.scope:
    #  self.scope[k] = self.scope[k].copy()
      
  def pop(self):
    if hasattr(glob, "g_debug_typeinfer") and glob.g_debug_typeinfer:
      print("===popping...===")
    d = self.scope
    self.scope = self.scopestack.pop(-1)
    return d
  
  def __getitem__(self, item):
    return self.scope[item]
  
  def __setitem__(self, item, val):
    self.scope[item] = val
  
  def __contains__(self, item):
    return item in self.scope
  
  def __delitem__(self, item):
    del self.scope[item]
    
  def __len__(self):
   return len(self.scope)
  
  def __iter__(self):
    return iter(self.scope)
  
  def keys(self):
    return self.scope.keys()
  
  def values(self):
    return self.scope.values()  
    
class NodeVisit:
  def __init__(self):
    pass
  
  def traverse(self, node, scope=None, tlevel=0):
    if scope == None and tlevel > 0:
      raise RuntimeError("NodeVisit.traverse called without scope")
      
    if scope == None:
      scope = {}
      
    if scope == None: scope = NodeScope()
    
    typestr = type(node).__name__
    if not hasattr(self, typestr) and typestr in self.required_nodes:
      raise RuntimeError("Unimplemented node visit for node type %s", typestr)
    
    if not hasattr(self, typestr):
      for c in node.children:
        self.traverse(c, scope, tlevel)
    else:
      getattr(self, typestr)(node, scope, self.traverse, tlevel)
 
def tab2(t):
  s = ""
  for i in range(t):
    s += "  "
  return s

class RequireJSWriter (NodeVisit):
  def __init__(self):
    self.required_nodes = []
    NodeVisit.__init__(self)
    self.buf = ""
  
  def o(self, s):
    self.buf += str(s)
  
  def traverse(self, node, scope=None, tlevel=-1):
    return NodeVisit.traverse(self, node, scope, tlevel)
    
  def endstatem(self, node):
    sb = self.buf.strip()
    ret = not sb.endswith("\n") 
    ret = ret and(not sb.endswith("}") or type(node) in [AssignNode, BinOpNode])
    return ret
    
  def IdentNode(self, node, scope, t, tlevel):
    self.o(node.val)
  
  def NumLitNode(self, node, scope, t, tlevel):
    self.o(node.val)
  
  def StatementList(self, node, scope, t, tlevel):
    t1 = tab2(tlevel)
    t2 = tab2(tlevel+1)
    for c in node:
      self.o(t1)
      t(c, scope, tlevel+1)
      if self.endstatem(c):
        self.o(";");
      self.o("\n");
  
  def ForLoopNode(self, node, scope, t, tlevel):
    t1 = tab2(tlevel)
    self.o("for (")
    t(node.children[0], scope, tlevel)
    self.o(") {\n")
    t(node.children[1], scope, tlevel+1)
    self.o(t1+"}\n");
    
  def ForInNode(self, node, scope, t, tlevel):
    t(node[0], scope, tlevel)
    self.o(" in ")
    self.o(node[1])
    
  def ForCNode(self, node, scope, t, tlevel):
    t(node[0], scope, tlevel)
    self.o("; ")
    t(node[1], scope, tlevel)
    self.o("; ")
    t(node[2], scope, tlevel)
    
  def IfNode(self, node, scope, t, tlevel):
    t1 = tab2(tlevel)
    
    self.o("if (")
    t(node[0], scope, tlevel)
    self.o(") {\n")
    t(node[1], scope, tlevel+1)
    self.o(t1+"}\n");
    
  def ElseNode(self, node, scope, t, tlevel):
    t1 = tab2(tlevel)
    if self.buf.endswith("\n"):
      self.buf = self.buf[:-2]
    self.o(" else ")
    
    if type(node[0]) == StatementList:
      self.o("{\n")
      t(node[0], scope, tlevel+1);
      self.o(t1+"}\n");
    else:
      t(node[0], scope, tlevel)
      
  def BinOpNode(self, node, scope, t, tlevel):
    t(node[0], scope, tlevel)
    if node.op in ["in", "instanceof", "&&", "||", "<", ">", "<=", ">=", "==", "!=", "===", "!=="]:
      self.o(" %s "%node.op)
    else:
      self.o(node.op)
    t(node[1], scope, tlevel)
    
  def NegateNode(self, node, scope, t, tlevel):
    self.o("-")
    t(node[0], scope, tlevel)
    
  def AssignNode(self, node, scope, t, tlevel):
    t(node[0], scope, tlevel)
    self.o(" %s "%node.mode)
    t(node[1], scope, tlevel)
    
  def WhileNode(self, node, scope, t, tlevel):
    t1 = tab2(tlevel)
    
    self.o("while (")
    t(node[0], scope, tlevel)
    self.o(") {\n")
    t(node[1], scope, tlevel+1)
    self.o(t1+"}\n")
    
  def FunctionNode(self, node, scope, t, tlevel):
    self.o("function ")
    if not node.is_anonymous:
      self.o(node.name)
    self.o("(")
    t(node[0], scope, tlevel)
    self.o(") {\n")
    
    t1 = tab2(tlevel+1)
    for c in node[1:]:
      self.o(t1)
      t(c, scope, tlevel+1)
      if self.endstatem(node):
        self.o(";")
      self.o("\n")
    
    self.o(tab2(tlevel)+"}\n")
    
  def ExprListNode(self, node, scope, t, tlevel):
    for i, c in enumerate(node):
      if i > 0:
        self.o(", ")
      t(c, scope, tlevel)
      
  def VarDeclNode(self, node, scope, t, tlevel):
    if "global" in node.modifiers: return
    
    if "local" in node.modifiers:
      self.o("var ")
    
    self.o(node.val)
    if len(node[0].gen_js(0).strip()) > 0: #type(node[0]) not in [ExprListNode, ExprListNode] or len(node[0]) > 0:
      self.o(" = ")
      t(node[0], scope, tlevel)
  
  
  def BreakNode(self, node, scope, t, tlevel):
    self.o("break");
  def YieldNode(self, node, scope, t, tlevel):
    self.o("yield");
    if len(node) != 0:
      self.o(" ")
      t(node[0], scope, tlevel)
  
  def ContinueNode(self, node, scope, t, tlevel):
    self.o("continue");
    
  def ReturnNode(self, node, scope, t, tlevel):
    self.o("return");
    if len(node) != 0:
      self.o(" ")
      t(node[0], scope, tlevel)
  
  def FuncCallNode(self, node, scope, t, tlevel):
    t(node[0], scope, tlevel)
    self.o("(")
    t(node[1], scope, tlevel)
    self.o(")")
    
  def StrLitNode(self, node, scope, t, tlevel):
    self.o(node.val)
  
  def ArrayRefNode(self, node, scope, t, tlevel):
    t(node[0], scope, tlevel)
    self.o("[")
    t(node[1], scope, tlevel)
    self.o("]")
    
  def ClassNode(self, node, scope, t, tlevel):
    #find constructor
    cls = None
    for m in node:
      if type(m) == MethodNode and m.name == "constructor":
        cls = m
        break
    
    if cls == None:
      typespace.error("Need constructor for class", node)
    
    t1 = tab2(tlevel)
    
    self.o("var %s = exports.%s = function(" % (cls.name, cls.name));
    t(cls[0], scope, tlevel)
    self.o(") {\n")
    t(cls[1], scope, tlevel)
    self.o(t1+"}\n")
    pass
    
  def MethodNode(self, node, scope, t, tlevel):
    self.o(node.name)
  def MethodGetter(self, node, scope, t, tlevel):
    pass
  def MethodSetter(self, node, scope, t, tlevel):
    pass
  def ExprNode(self, node, scope, t, tlevel):
    pass
  
def handle_nodescope_pre(n, scope):
    if type(n) in [IdentNode, VarDeclNode]:
      """
      p = n.parent
      add = False
      while p not in [None, 0]:
        if type(p) in [FunctionNode, ForLoopNode, DoWhileNode, WhileNode, 
                       WithNode, CaseNode, DefaultCaseNode, IfNode, ElseNode,
                       TryNode, CatchNode]:
          break
        
        if type(p) in [AssignNode, VarDeclNode]:
          add = True
          break
          
        p = p.parent
      
      #if add and n.final_type != None:
      #  scope[n.val] = VarBinding(n, n.final_type, n.val)
      
      #"""
      pass
      
    elif type(n) in [FunctionNode, ForLoopNode, DoWhileNode, 
                     TryNode, CatchNode, SwitchNode, WhileNode,
                     IfNode, ElseNode]:
      if type(n) == FunctionNode:
        if n.parent == None or type(n.parent) in [StatementList, FunctionNode]:
          scope[n.name] = n #VarBinding(n, n.name, n.final_type)
          scope["this"] = n
      
      scope.push()
          
    elif type(n) == BinOpNode and n.op == ".":
      scope.push()

def handle_nodescope_post(n, scope):
    if type(n) in [FunctionNode, ForLoopNode, DoWhileNode, WhileNode, 
                   WithNode, CaseNode, DefaultCaseNode, IfNode, ElseNode,
                   TryNode, CatchNode]:
      scope.pop()
    elif type(n) == BinOpNode and n.op == ".":
      scope.pop()
    

def templates_match(n1, n2):
  if n1 != None and n2 == None: return False
  if n1 == None and n2 != None: return False
  
  return len(n1[0]) == len(n2[0])
  
def types_match(n1, n2, typespace):
  if type(n1) == TypeRefNode and n1.template == None:
    n1 = typespace.get_type(n1.type)
  if type(n2) == TypeRefNode and n2.template == None:
    n2 = typespace.get_type(n2.type)
    
  if type(n1) == IdentNode:
    n1 = typespace.get_type(n1.val)
  if type(n2) == IdentNode:
    n2 = typespace.get_type(n2.val)
  if type(n1) == BuiltinTypeNode and n1.type in typespace.functions:
    n1 = typespace.get_type(n1.type)
    
  if type(n2) == BuiltinTypeNode and n2.type in typespace.functions:
    n2 = typespace.get_type(n2.type)
  
  if type(n1) != type(n2): 
    if type(n1) == BuiltinTypeNode and type(n2) == IdentNode:
      if n1.type == "String" and n2.val == "String": return True
    if type(n2) == BuiltinTypeNode and type(n1) == IdentNode:
      if n2.type == "String" and n1.val == "String": return True
     
    if type(n1) == TemplateNode and type(n2) == FunctionNode:
      if type(n1.name_expr) == IdentNode and n1.name_expr.val == n2.val:
        return templates_match(n1, n2.template)
        
    if type(n2) == TemplateNode and type(n1) == FunctionNode:
      if type(n2.name_expr) == IdentNode and n2.name_expr.val == n1.val:
        return templates_match(n2, n1.template)
        
    return False
  if type(n1) == BuiltinTypeNode:
    return n1.compatible(n2)
  elif type(n1) == VoidTypeNode: return True
  elif type(n1) == FunctionNode:
    return n1 == n2
    
def handle_scope(n, scope):
    if type(n) in [IdentNode, VarDeclNode]:
      scope[n.val] = n
    elif type(n) in [FunctionNode, ForLoopNode, DoWhileNode, 
                     TryNode, CatchNode, SwitchNode, WhileNode,
                     IfNode, ElseNode]:
      scope = dict(scope)
      if type(n) == FunctionNode:
        scope[n.name] = n
    elif type(n) == BinOpNode and n.op == ".":
      scope = dict(scope)
    
    return scope
    
def flatten_statementlists(node, typespace):
  if node == None: 
    print("None passed to flatten_statementlists")
    return
    
  def visit_slists(n):
    if not null_node(n.parent) and type(n.parent) in [FunctionNode, StatementList]:
      p = n.parent
      i = p.index(n)
      
      p.remove(n)
      
      for c in n:
        p.insert(i, c)
        i += 1
  
  traverse(node, StatementList, visit_slists, copy_children=True)  
  """
  if node.gen_js(0) != c:
    if typespace != None:
      typespace.error("Internal parser error in flatten_statementlists", node)
    return None
  #"""
  
  return node  

def kill_bad_globals(node, typespace):
  def recurse(n, scope, tlevel=0):
    def descend(n2, start=0):
      for c in n2.children[start:]:
        recurse(c, scope, tlevel)
    
    if type(n) == FunctionNode:
      scope = dict(scope)
      args = n.get_args()
      
      for i, a in enumerate(args):
        scope[a] = n[0][i];
        
      descend(n, 1);
    elif type(n) == BinOpNode and n.op == ".":
      scope = dict(scope) #not sure what to do here
      descend(n)
    elif type(n) == VarDeclNode:
      scope[n.val] = n;
      descend(n[0])
      
      if len(n) > 2:
        descend(n, 2);
    elif type(n) == AssignNode:
      if type(n.parent) == ObjLitNode:
        descend(n)
        return
        
      #if n[0].gen_js(0).replace(";", "").strip() == "mode":
      #  raise "sd"
      if type(n[0]) in [IdentNode, VarDeclNode] and n[0].val not in scope:
        print(scope.keys())
        typespace.error("Undeclared global %s"%n[0].val, n[0])      
      descend(n);
    else:
      descend(n);
  
  sc = {}
  recurse(node, sc, 0);

  
from js_cc import js_parse
from js_ast_match import ast_match

def add_func_opt_code(result, typespace):
  def visit_func(node):
    if len(node) < 2:
      #should we still insert opt initialization code
      #in empty functions?  like if people want to write
      #evil, hackish code like function(i=do_something()) {},
      #which would turn into function(i) { if (i == undefined) do_something();}
      #
      #yeek.
      
      #print("Warning: function defined without any statements")
      node.add(StatementList())
    
    #ensure we have a proper statement list
    if type(node[1]) != StatementList:
      sl = StatementList()
      sl.add(node[1])
      node.replace(node[1], sl)
      
    was_opt = False
    codelist = []
    
    for p in node[0]:
      if type(p) == IdentNode:
        is_opt = False
      else:
        is_opt = p[0].gen_js(0).strip() != "";
      
      if not is_opt and was_opt:
        typespace.error("Cannot have required parameter after an optional one", node)
        
      name = p.val
      if is_opt: 
        was_opt = True
        code = js_parse("""
          if ($s1 == undefined) {
            $s1 = $n2;
          }
        """, (name, p[0]));
        codelist.append(code)
      
        p.parent.replace(p, IdentNode(p.val))
        
    codelist.reverse()
    for code in codelist:
        node[1].prepend(code)
  
  traverse(result, FunctionNode, visit_func)
  flatten_statementlists(result, typespace)
  
typespace = None

def traverse_files(ntype, func, use_depth=False, exclude=[], copy_children=False):
  for n in typespace.filenodes:
    traverse(n, ntype, func, use_depth, exclude, copy_children)

def get_arg_name(arg):
  if type(arg) in [IdentNode, VarDeclNode]:
    return arg.val
  else:
    for c in arg.children:
      ret = get_arg_name(c)
      if type(ret) == str: return ret
  return None

  
def build_classes(nfiles):
  global typespace
  
  def func_visit(n):
    if n.is_anonymous: return
    if n.name in typespace.func_excludes: return
    
    def find_this(n2):
      if n2.op == "." and type(n2[0]) == IdentNode and n2[0].val == "this":
        n.class_type = "class"
      
    if n.class_type == "func":
      traverse(n, BinOpNode, find_this, exclude={FunctionNode});
    
    p = n.parent
    while not null_node(p) and type(p) != FunctionNode:
      p = p.parent
    
    if type(p) == FunctionNode:
      if n.name in p.functions:
        msg = "Nested function %s in %s already exists" % (n.name, p.name)
        typespace.error(msg, n)
      
      p.functions[n.name] = n
    else:
      if n.name in typespace.functions:
        msg = "Function %s already exists" % (n.name)
        n2 = typespace.functions[n.name]
        msg += "\n\tPrevious definition at %s:%d" % (n2.file, n2.line)
        typespace.error(msg, n)
      
      typespace.functions[n.name] = n
    
    for i, c in enumerate(n[0].children):
      n.args[c.val] = c
      n.arg_is[c.val] = i
  
  def exprfunc_visit(n):
    if not n.is_anonymous: return
    
    #figure out if we're a method function
    
    #find parent function
    p = n.parent
    while not null_node(p) and type(p) != FunctionNode:
      p = p.parent
    
    p1 = p
    
    #find parent assignment
    path = []
    p = n.parent
    path.append(p)
    while not null_node(p) and type(p) not in [AssignNode, FunctionNode]:
      p = p.parent
      path.append(p)
     
    path.reverse()
    if len(path) == 0:
      return 
    if type(p) != AssignNode:
      return
      
    cs = p.children
    parent = None
    if type(p1) == FunctionNode:
      parent = p1
      is_valid = type(cs[0]) == BinOpNode\
                 and type(cs[0][0]) == IdentNode\
                 and type(cs[0][1]) == IdentNode\
                 and cs[0][0].val == "this"
    else:
      c = cs[0].gen_js(0)
      i = c.find(".prototype")
      if i < 0:
        is_valid = False
      else:
        parent = c[:c.find(".")]
        if parent not in typespace.functions:
          typespace.error("Could not find class function %s"%parent, n)
          
        parent = typespace.functions[parent]
        c = c[i:]
        is_valid = c.count(".") == 2
    
    if is_valid:
      if not func_is_class(parent):
        parent.class_type = "class"
      
      n.class_type = "method"
      c = cs[0].gen_js(0)
      c = c[c.rfind(".")+1:]
      
      if type(parent) == StatementList:
        typespace.error("yeek", n)
        
      n.path = parent.name + "." + c
      
      n.name = c
      parent.members[n.name] = n
      
    i = 0
  
  def new_visit(n):
    if type(n[0]) == IdentNode:
      if n[0].val not in typespace.functions:
        typespace.error("Could not find type constructor %s"%n[0].val, n)
      
      f = typespace.functions[n[0].val]
      if not func_is_class(f):
        f.class_type = "class"
  
  traverse_files(FunctionNode, func_visit)
  traverse_files(FunctionNode, new_visit)
  traverse_files(FunctionNode, exprfunc_visit)
  
  def build_members(node):
    if not func_is_class(node): return
    
    def visit(n):
      c = n[0].gen_js(0)
      print(c)
   
      if c.startswith("this.") and c.count(".") == 1 and c.count("(") == 0 and c.count("[") == 0:
        c = c[5:]
        #print(node.name + "." + c)
        if c in node.members and type(node.members[c]) == FunctionNode:
          if node.members[c] != n[1]:
            typespace.error("Overriding method functions is not allowed", n)
        elif c not in node.members:
          if n.type != None: n[1].type = n.type
          node.members[c] = n[1]
    for c in node[1:]:
      traverse(c, AssignNode, visit, exclude=[FunctionNode])
  
  def global_prototype_assignments(node):
    c = node[0].gen_js(0)
    if not ".prototype" in c: return
    
    if c.strip().endswith(".prototype") and c.count(".")==1 and c.count("[")==0 and c.count(")")==0:
      n = c[:c.find(".prototype")]
      if n not in typespace.functions:
        typespace.error("Could not find function %s"%n, node)
      
      n = typespace.functions[n]
      n.members["prototype"] = node[1]
    elif c.count(".") == 2 and c.count("[") == 0 and c.count("(") == 0:
      n = c[:c.find(".prototype")]
      c = c[c.rfind(".prototype.")+len(".prototype."):]
      
      if n not in typespace.functions:
        typespace.error("Could not find function %s"%n, node)
      
      n = typespace.functions[n]
      n.members[c] = node[1]
    
  traverse_files(AssignNode, global_prototype_assignments, exclude=[FunctionNode])
  
  def add_logrecs(n):
    if typespace.get_record(n) != None:
      enlist = typespace.get_record(n)
      for en in enlist:
        #print(n.get_path(), en.arg in [a.val for a in n[0]])
        en.func = n.get_path()
        n.logrecs.append(en)
        
  traverse_files(FunctionNode, add_logrecs)
        
  print("\n")
  traverse_files(FunctionNode, build_members)
  
  def base_inherit(node):
    parent = "Object"
    
    if "__iterator__" in node.members:
      parent = "CanIterate"
    elif "next" in  node.members and type(node.members["next"]) == FunctionNode:
      parent = "Iterator"
      
    parent = typespace.types[parent]
    node.class_parent = parent
  
  def resolve_inheritance(node):
    #search for .prototype = calls at the global level, as well as calls to
    #inherit()
    if not func_is_class(node): return
    
    #the easy case
    
    if "prototype" in node.members:
      n = node.members["prototype"]
      if type(n) == ObjLitNode:
        base_inherit(node, "Object")
      else:
        while type(n) == UnknownTypeNode:
          n = n[0]
        n1 = n
        n2 = js_parse("Object.create(obj.prototype);")[0]
        
        #normalize        
        n1 = js_parse(n1.gen_js(0), start_node=BinOpNode)
        if node_structures_match(n1, n2): #ast_match("Object.create($class.prototype);", n1, start_node=BinOpNode): # node_structures_match(n1, n2):
          parent = n1[1][1][0][0].val
          #print(node.name, parent)
          if parent not in typespace.functions:
            typespace.error("Unknown parent type %s"%parent, n1)
            
          parent = typespace.functions[parent]
          node.class_parent = parent
        else:
          typespace.error("Unknown parent code line: \"%s\""%n1.gen_js(1), n1)
        
    
  traverse_files(FunctionNode, resolve_inheritance)
  
  def resolve_inheritance_inherit(node):
    if node[0].gen_js(0) != "inherit": return
    
    js = node[0].gen_js(0)
    
    sn = js_parse("inherit(obj1, obj2)")[0]
    
    print(node, sn)
    ret = ast_match("inherit($class, $class);", node.gen_js(0));
    
    if not ret: #node_structures_match(node, sn):
      typespace.error("Could not parse inherit line", node)
    
    n = node[1][0]
    parent = node[1][1]
    
    tname = n.get_type_name()
    if tname not in typespace.functions:
      typespace.error("Could not find function %s"%tname, node)
    
    ptname = parent.get_type_name()
    if ptname not in typespace.functions:
      typespace.error("Could not find function %s"%ptname, node)
    
    n = typespace.functions[tname]
    parent = typespace.functions[ptname]
    
    if n.class_parent != None:
      typespace.error("Parent prototype for type %s is already set"%n.name, node)
    
    if not func_is_class(n):
      n.class_type = "class"
    if not func_is_class(parent):
      parent.class_type = "class"
    
    n.class_parent = parent
    
  traverse_files(FuncCallNode, resolve_inheritance_inherit)
  
  def resolve_basic_class_types(node):
    if not func_is_class(node): return
    if node.class_parent != None: return
    ntype = "Object"

    base_inherit(node)
  
  traverse_files(FunctionNode, resolve_basic_class_types)
  
  def set_child_class_refs(node):
    if not func_is_class(node): return
    
    #if node.name in node.class_parent.child_classes:
    #  typespace.error("Duplicate child class names detected", node)
    
    node.class_parent.child_classes[node.name] = node
  
  def find_iter_iters(node):
    if not func_is_class(node): return
    
    
    if not ("next" in node.members and type(node.members["next"]) == FunctionNode):
      return
    
    """
    found_it = [False]
    def find_stop_iter(n):
      if n.val == "StopIteration":
        found_it[0] = True
      
    traverse(node, IdentNode, find_stop_iter)
    """
    
    print(node.class_parent==None)
    #print(node.name)
    
  #traverse_files(FunctionNode, find_iter_iters)
  
  def find_root_types(node):
    if not func_is_class(node): return
  
    root = node
    while root.class_parent != None and root.class_parent.is_builtin == False:
      root = root.class_parent
      if not func_is_class(root):
        root.class_types = "class"
    
    root_types[root.name] = root
  
  traverse_files(FunctionNode, set_child_class_refs)

  root_types = {}
  traverse_files(FunctionNode, find_root_types)
  
  rts = list(root_types.keys())
  rts.sort()
  for r in rts:
    if root_types[r].class_parent != None:
      cname = root_types[r].class_parent.name
    else:
      cname = None
    #print(r, root_types[r].class_type, cname)


def node_structures_match(n1, n2):
  s1 = [n1]
  s2 = [n2]
  
  while len(s1) > 0 and len(s2) > 0:
    n1 = s1.pop(-1)
    n2 = s2.pop(-1)
    if type(n1) != type(n2): return False
    for c in n1.children:
      s1.append(c)
    for c in n2.children:
      s2.append(c)
  
  if len(s1) > 0 or len(s2) > 0: return False
  return True

def common_parent(n1, n2):
  p1 = n1
  p2 = n2
  
  lst1 = []
  while p1 != None and p1.name != "Object" and p1 != typespace.functions["Object"]:
    lst1.append(p1)
    p1 = p1.class_parent
    
  lst2 = []
  while p2 != None and p2.name != "Object" and p2 != typespace.functions["Object"]:
    lst2.append(p2)
    p2 = p2.class_parent
  
  for l in lst1:
    if l in lst2:
      return l
      
  return None

def process_logrec():
  global typespace
  
  printlist = []
  
  def return_rec_visit(n):
    if len(n.logrecs) == 0: return #only do functions with records
    
    t = odict()
    argtypes = odict()
    for en in n.logrecs:
      if en.vtype == "r": continue
      
      if en.arg not in t:
        t[en.arg] = []
      t[en.arg].append(en.type)

    #print(t)
    
    for k in t:
      types = []
      common = []
      
      for a in t[k]:
        if a not in typespace.functions:
          f = typespace.empty_type()
        else:
          f = typespace.functions[a]
        
        types.append(f)      
      
      tlen = len(types)
      for t2 in types[:]:
        if t2.name == "undefined":
          types.remove(t2)
      
      for j in range(tlen):
        i1 = 0
        i2 = 1
        while i1 < len(types):
          if i1 == 0: i2 = 1
          else: i2 = 0
          
          if len(types) == 1: break
          
          c = common_parent(types[i1], types[i2])
          while i2 < len(types):
            if i2 != i1:
              c = common_parent(types[i1], types[i2])
              if c != None:
                break
            i2 += 1
          
          if c != None:
            nn1 = types[i1]
            nn2 =  types[i2]
            types.remove(nn1)
            types.remove(nn2)
            
            types.insert(i1, c)
            
          i1 += 1
          
          if i2 >= len(types):
            i2 = 0
      
      argtypes[k] = types
    
    s = n.get_path() + "("
    for i, n2 in enumerate(n[0]):
      k = n2.val
      n.lrec_args[k] = []
      
      if i > 0: s += ", "
      if k in argtypes:
        if k in typespace.functions:
          cls = typespace.functions[k]
        
        for j, v in enumerate(argtypes[k]):
          if j > 0: s += "|"
          s += v.name
          n.lrec_args[k].append(v)
      else:
        n.lrec_args[k].append(typespace.empty_type())
        s += "(unknown type)"
      s += " " + k
    s += ")"
    if "()" not in s:
      if "(unknown type)" not in s:
        printlist.append(s)
      else:
        printlist.append("-" + n.get_path() + str([n3.val for n3 in n[0]]) + str(list(argtypes.keys())))
  traverse_files(FunctionNode, return_rec_visit)
  printlist.sort()
  
  f = open("signatures.txt", "w")
  f.write("\n============\n")
  
  for l in printlist:
    print(l)
    f.write(l+"\n")
  f.close()
  
  #[print(l) for l in printlist]
  
def is_root(node):
  return node.class_parent == None

def tab(t, tstr="  "):
  s = ""
  for i in range(t):
    s += tstr
  return s

def get_roots():
  global typespace  
  
  roots = []
  def print_tree(n, tlevel=0):
    s = tab(tlevel) + n.name
    print(s)
    for c in n.child_classes.values():
      print_tree(c, tlevel+1)
      
  for c in typespace.functions.values():
    if not func_is_class(c) or not is_root(c): continue
    roots.append(c)
  
  return roots

#we two sources of type information: user-supplied annotation,
#and the type log.  first we should validate the user type annoation,
#then we have to apply a series of rules to reduce the types.

class TypeSet:
  def __init__(self, input=[]):
    self.map = odict()
    self.data = []
    
    for i in input:
      self.add(i)
    
  def add(self, item):
    h = item.__setval__()
    if h in self.map: return
    
    self.map[h] = len(self.data)
    self.data.append(item)
    
  def remove(self, item):
    i = self.map[item.__setval__()]
    data = self.data[i]
    
    self.data.pop(i)
    del self.map[item.__setval__()]
  
  def __getitem__(self, item):
    return self.data[item]
  
  def __setitem__(self, idx, val):
    if item < 0 or item >= len(self):
      raise RuntimeError("Item out of bounds in TypeSet.__setitem__: len: %d, item: %s" % (len(self), str(item)))
    
    d = self.data[idx]
    self.data.remove(d)
    del self.datamap[d.__setval__()]
    
    self.datamap[val.__setval__()] = idx
    self.data[idx] = val

  def __iter__(self):
    def iter():
      for d in self.data:
        yield d
    return iter()
  
  def len(self):
    return len(self.data)
  
  def join(self, b):
    c = TypeSet(self)
    for d in b:
      c.add(d)
  
  def __add__(self, b):
    return self.join(self, b)
  
  def copy(self):
    return TypeSet(self)
  
  def __contains__(self, item):
    return item.__setval__() in self.map
    
  def __sub__(self, b):
    c = self.copy()
    
    for d in b:
      if d in c:
        c.remove(d)
        
    return c
  
def process_type_annotation():
  global typespace
  roots = get_roots()
  for node in roots:
    pass

def print_class_hiearchy():
  global typespace  
  
  def print_tree(n, tlevel=0):
    s = tab(tlevel) + n.name
    print(s)
    
    lst = list(n.child_classes.keys())
    lst.sort();
    for k in lst:
      c = n.child_classes[k]
      print_tree(c, tlevel+1)
    
  roots = []    
  for k in typespace.functions:
    c = typespace.functions[k]
    if not func_is_class(c) or not is_root(c): continue
    roots.append(k)
  
  roots.sort()
  for k in roots:
    print_tree(typespace.functions[k])

def handle_dot_scope(n, scope):
  pass
  
def handle_scope_infer(n, scope):
    if type(n) in [IdentNode, VarDeclNode]:
      scope[n.val] = n
    elif type(n) in [FunctionNode, ForLoopNode, DoWhileNode, 
                     TryNode, CatchNode, SwitchNode, WhileNode,
                     IfNode, ElseNode]:
      scope = NodeScope(scope)
      if type(n) == FunctionNode:
        scope[n.name] = n
    elif type(n) == BinOpNode and n.op == ".":
      scope = handle_dot_scope(n, scope)
    
    return scope

def set_const_types():
  global typespace
  
  def visit_num(n):
    if n.type != None: return
    
    if type(n.val) == float: n.type = BuiltinTypeNode("float")
    else: n.type = BuiltinTypeNode("int")
    
  def visit_str(n):
    if n.type != None: return
    
    n.type = typespace.functions["String"]
    
  def visit_reg(n):
    if n.type != None: return
    
    n.type = typespace.functions["String"]
    
  traverse_files(NumLitNode, visit_num);
  traverse_files(StrLitNode, visit_str);
  traverse_files(RegExprNode, visit_reg);

def filter_binop_assigns():
  global typespace
  
  def visit_binop(n):
    if n.op != "=": return
    if type(n.parent) not in [StatementList, FunctionNode]: return
    
    assign = AssignNode(n[0], n[1], "=")
    assign.type = n.type
    
    n.parent.replace(n, assign)
    
  traverse_files(BinOpNode, visit_binop)
  
def infer_types(ts):
  global typespace
  typespace = ts
  
  filter_binop_assigns()
  
  build_classes(ts.filenodes)
  process_logrec()
  
  if glob.g_do_annote:
    process_type_annotation()
  
  if glob.g_print_classes:
    print_class_hiearchy()
  
  set_const_types()

def replace_instanceof(result, typespace):
  def visiti(node):
    name = glob.g_instanceof_func
    
    #make sure we're not inside g_instanceof_func (__instance_of) itself.
    p = node
    while p != None and type(p) != FunctionNode:
      p = p.parent
    
    if p != None and type(p) == FunctionNode and p.name == name:
      #sys.stderr.write("ignoring %s implementation in instaneof replacement\n"%name);
      return
      
    if node.op != "instanceof": return
    
    fn = FuncCallNode(IdentNode(name))
    params = ExprListNode([node[0], node[1]])
    params.line = node.line; params.lexpos = node.lexpos
    fn.add(params)
    fn.line = node.line; fn.lexpos = node.lexpos;
    
    node.parent.replace(node, fn);
    
  traverse(result, BinOpNode, visiti)
  
  #print("\n")

def process_docstrings(result, typespace):
  dprop = glob.g_docstring_propname
  vset = set()
  
  def case1(node, dstr):
    #simple case; the node's parent is a statementlist
    if type(node.parent) != StatementList: return False
    if node.is_anonymous: return False
    
    node.remove(dstr)
    n = BinOpNode(IdentNode(node.name), IdentNode(dprop), ".")
    n = AssignNode(n, dstr)
    
    node.parent.insert(node.parent.index(node)+1, n)
    return True
  
  #a = func() {}, where a is part of a statementlist
  def case2(node, dstr):
    def count_funcs(n2):
      ret = 0
      if type(n2) == FunctionNode: 
        ret += 1
        if n2 == node: return ret
      
      for c in n2:
        ret += count_funcs(c)
      return ret
    
    
    #make sure we're part of a valid assignnode
    n = node
    lastn = n;
    while n != None:
      lastn = n
      n = n.parent
      if type(n) not in [BinOpNode, IdentNode, AssignNode]: break
      
    if type(n) not in [StatementList, FunctionNode]: return False
    if type(lastn) != AssignNode: return False
    
    an = lastn;
    if count_funcs(an) != 1: return False
    
    dstr.parent.remove(dstr);
    
    dn = dstr
    node.parent.replace(node, dn);
    n2 = js_parse(an.gen_js(0), start_node=AssignNode)
    node.parent.replace(dn, node)
    
    n2.replace(n2[0], BinOpNode(n2[0], IdentNode(dprop), "."))
    an.parent.insert(an.parent.index(an)+1, n2)
    return True
  
  def case3(node, dstr): #static class methods
    if node.parent == None: return
    if type(node.parent.parent) != FuncCallNode: return
    if (node.parent.parent[0].gen_js(0) != "define_static"): return
    
    lastn = node
    slist = node.parent
    while slist != None and type(slist) != StatementList and not isinstance(slist, FunctionNode):
      lastn = slist
      slist = slist.parent
    
    if slist == None: return
    
    fc = node.parent
    sname = fc[1]
    sname = sname.gen_js(0).replace("'", "").replace('"', "")
    
    #print(fc[0], "dsfsdf")
    #sys.exit()
    #return
    n = js_parse("$n.$s.__doc__ = $n;", [fc[0], sname, dstr])
    
    dstr.parent.remove(dstr)
    slist.insert(slist.index(lastn)+1, n)
    return True
    
  cases = [case1, case2, case3]
  def visit(node):
    if node in vset:
      return
    vset.add(node)
    
    if len(node) == 1: return
    n = node[1]
    while len(n) > 0 and type(n) == StatementList:
      n = n[0]
    
    if type(n) != StrLitNode: return
    dstr = n
    
    tfound = 0
    for c in cases:
      if c(node, dstr):
        if len(node) == 1:
          node.add(StatementList())
        tfound = True
        break
        
    if not tfound:
      p = node.parent
      i = node.parent.index(node)
      if node in node.parent:
        node.parent.remove(node)
      node.remove(dstr)
      
      sys.stderr.write("%s(%i): Warning: could not statically compile docstring for function\n  \"%s\"." % (node.file, node.line, node.name))
      sys.stderr.write("  Docstring will be set at runtime instead\n\n");
      
      bn = ExprListNode([node, dstr])
      cn = FuncCallNode("define_docstring")
      cn.add(bn)
      p.insert(i, cn)
      
  traverse(result, FunctionNode, visit);

valid_randstr = "abcdefghijklmnopqrstuvwxyz"
valid_randstr += valid_randstr.upper() + "0123456789_"
_last_rs_time = time.time()
def randstr(n):
  global _last_rs_time
  
  if (time.time() - _last_rs_time > 0.25):
    seed(time.time()*6)
    _last_rs_time = time.time()
    
  s = ""
  for i in range(n):
    s += valid_randstr[int(random()*len(valid_randstr)*0.99999)]
      
  return s

def gen_useful_funcname(p2):
  def is_ok(s):
    if len(s) == 0: return False
    for c in s:
      if c not in valid_randstr: return False
    return True
  
  p2 = p2.parent
  while p2 != None and type(p2) != AssignNode:
    p2 = p2.parent
  
  suffix = ""
  if p2 != None: #okay, we belong to an anonymous function with no usable name
    #find right-most usable identnode in the lvalue's ast tree
    n2 = p2[0]
    while len(n2) > 0:
      s = n2.gen_js(0).replace("prototype.", "").replace(".", "_")
      if is_ok(s):
        suffix = s
        break
      n2 = n2[-1]
    
    if not is_ok(suffix):
      s = n2.gen_js(0)
      if is_ok(s):
        suffix = s
  else:
    suffix = randstr(4)
  
  if len(suffix) == 0: suffix = randstr(2)
  return suffix
  
def process_static_vars(result, typespace):

  #if inside a class, returns class node
  def inside_class(n):
    if type(n) == ClassNode or (type(n) == FuncCallNode and n[0].gen_js(0) == "_ESClass"):
      return n
    
    if n.parent != None:
      return inside_class(n.parent)
    return False
    
  def visit(node):
    if "static" not in node.modifiers: return
    inclass = inside_class(node)
    
    #make sure we aren't carrying any child vardecl nodes
    #(e.g var a, b, c, d) with us.
    for c in list(node[2:]):
      node.remove(c)
      node.parent.insert(node.parent.index(node), c)
    
    #helper function for generating (hopefully) unique suffixes
    #from parent nodes
    def is_ok(s):
      if len(s) == 0: return False
      for c in s:
        if c not in valid_randstr: return False
      return True
    
    #we need to extract a useful name for the static
    p = node.parent
    while p != None and not isinstance(p, FunctionNode):
      p = p.parent
    
    if p == None:
      return #we're already a static global variable
    
    suffix = randstr(2)
    if p.is_anonymous:
      suffix = gen_useful_funcname(p)
    else:
      #see if we're a nested function.  if so, build a chain of suffices.
      suffix = p.name
      p2 = p.parent
      while p2 != None:
        if isinstance(p2, FunctionNode):
          suffix = gen_useful_funcname(p2) + "_" + suffix
        p2 = p2.parent

    name = "$" + node.val + "_" + suffix
    
    scope = {}
    scope[node.val] = name
    
    def replace_var(n, scope):
      if type(n) in [IdentNode, VarDeclNode] and n.val in scope:
        n.val = scope[n.val]
      
      if type(n) == BinOpNode and n.op == ".":
        #don't traverse into the right side of . operators
        replace_var(n[0], scope)
        if type(n[1]) in [IdentNode, VarDeclNode]:
          return
        elif type(n[1]) == FuncCallNode: #need to fix this edge case: function calls operator precedence is messed up
          replace_var(n[1][1:], scope)
          return
        replace_var(n[1], scope)
      elif type(n) == FunctionNode:
        #hrm, not sure how best to handle this one.
        #avoid replacement in exprfunctions?
        #well, for now, just convert them.
        
        #don't convert arguments
        scope = dict(scope)
        for c in n[0]:
          p = c
          while len(p) > 0 and type(p) not in [IdentNode, VarDeclNode]:
            p = p[0]
          p = p.gen_js(0).strip();
          scope[p] = p
        
        for c in n.children[1:]:
          replace_var(c, scope)
      else:
        for c in n:
          replace_var(c, scope)
    
    #find parent scope
    p = node.parent
    while p != None and not isinstance(p, FunctionNode):
      p = p.parent
    
    replace_var(p, scope)
    func = p
    
    #now find global scope, and insert
    lastp = node
    p = node.parent
    
    #find parent function first, then find surrounding closure or global scope
    for si in range(2):
      while p.parent != None and not isinstance(p, FunctionNode):
        lastp = p
        p = p.parent
        
      if si == 0 and p.parent != None: 
        lastp = p
        p = p.parent
      
    pindex = p.index(lastp)
    node.parent.remove(node)
    
    if inclass:
      #add declaration
      decl = VarDeclNode(ExprNode([]), local=True, name=node.val)
      p.insert(pindex, decl)
      
      while inclass.parent != None and inclass.parent != p:
        inclass = inclass.parent
        
      if inclass.parent == None:
        pindex += 2
      else:
        pindex = p.index(inclass) + 1
      
      while pindex < len(p) and hasattr(p[pindex], "_was_static") and getattr(p[pindex], "_was_static"):
        pindex += 1
      
    node._was_static = True
    p.insert(pindex, node)
    
    node.modifiers.remove("static")
    node.modifiers.add("local")
         
  traverse(result, VarDeclNode, visit);

from js_global import glob
from js_typespace import *
from js_ast import *
from js_util_types import *

import js_ast
node_types = set()

for k in js_ast.__dict__:
  n = js_ast.__dict__[k]
  try:
    if not issubclass(getattr(js_ast, k), Node):
      continue;
  except TypeError:
    continue
  node_types.add(k)
 
def process_arrow_function_this(result, typespace):
  idgen = [1];
  doneset = set()
  
  hash = glob.g_file
  import hashlib
  hash = hashlib.sha1(bytes(hash, "utf8")).digest()
  import base64
  hash = str(base64.b64encode(hash), "latin-1")
  hash = hash.replace("+", "_").replace("/", "_").replace("=", "_").replace(".", "_").replace("-", "_")
  hash = hash.replace("&", "_")
  
  hash = hash[:4]
  
  def replace_this(n, name):
    if type(n) == IdentNode and n.val == 'this':
      n.val = name
    else:
      for c in n.children:
        if isinstance(c, FunctionNode):
          continue
        replace_this(c, name)
        
  def visit(node):
    if not node.is_arrow: return
    if node.parent == None: return
    if node._id in doneset: return
    
    doneset.add(node._id)
    
    p = node.parent
    pi = p.index(node)
    
    while p is not None and not isinstance(p, StatementList) \
          and not isinstance(p, FunctionNode):
      if p is not None:
        pi = p.parent.index(p)
      p = p.parent
   
    if p is None:
      #impossible
      typespace.error("Impossible, no outer statementlist.  That's can't happen", node)
    
    name = "$_" + hash + "awthis_" + str(idgen[0])
    idgen[0] += 1
    
    namenode = VarDeclNode('this', name=name, local=True)
    p.insert(pi, namenode)
    
    replace_this(node, name)
    
  traverse(result, FunctionNode, visit)
  
  