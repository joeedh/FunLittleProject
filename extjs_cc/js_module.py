from js_global import *
from js_ast import *
from js_cc import js_parse
from js_process_ast import *

def module_transform(node, typespace):
  flatten_statementlists(node, typespace);
  
  depends = set()
  
  def at_root(n):
    p = n
    while p != None:
      if isinstance(p, FunctionNode):
        return False
      p = p.parent
    return True
 
  def varvisit(n, startn):
      return
      n2 = js_parse("""
        _es6_module.add_global('$s', $s);
      """, [n.val, n.val]);
      
      startn.parent.insert(startn.parent.index(startn)+1, n2);
      
      for n2 in n[2:]:
        varvisit(n2, startn);
  
  def exportvisit(n):
    if not at_root(n):
      typespace.error("Export statements cannot be within functions or classes", n)
    
    pi = n.parent.index(n)
    n.parent.remove(n)
    
    for n2 in n[:]:
      n.remove(n2)
      n.parent.insert(pi, n2)
      pi += 1
     
    if not n.is_default:
      n2 = js_parse("""
        $s = _es6_module.add_export('$s', $s);
      """, [n.name, n.name, n.name]);
    else: 
      n2 = js_parse("""
        $s = _es6_module.set_default_export('$s', $s);
      """, [n.name, n.name, n.name]);
      
    n.parent.insert(pi, n2)
    
  def exportfromvisit(n):
    n2 = js_parse("""
      import * as _$s1 from '$s1';
      
      for (var k in _$s1) {
        _es6_module.add_export(k, _$s1[k], true);
      }
    """, [n.name.val])
    
    n.parent.replace(n, n2)
  #print(node)

  #ahem.  if I do this one first, I can use  import statements in it :)
  #. . .also, how cool, it captures the dependencies, too

  traverse(node, ExportFromNode, exportfromvisit, copy_children=True);
  traverse(node, ExportNode, exportvisit, copy_children=True);
  
  #fetch explicit global variables
  globals = [];
  
  def kill_assignments(n):
    n.replace(n[0], ExprNode([]))
    for c in n:
      if type(c) == VarDeclNode:
        kill_assignments(c)
  
  def global_to_var(n):
    if type(n) == VarDeclNode and "global" in n.modifiers:
      n.modifiers.remove("global")
      n.modifiers.add("local")
      
    for c in n:
      global_to_var(c)
      
  def transform_into_assignments(n, parent, pi):
    if type(n) == VarDeclNode and not (type(n[0]) == ExprNode and len(n[0]) == 0):
      n2 = AssignNode(IdentNode(n.val), n[0])
      n.parent.remove(n)
      parent.insert(pi, n2)
      
    for c in n:
      transform_into_assignments(c, parent, pi)
      
  for c in node:
    if type(c) == VarDeclNode and "global" in c.modifiers:
      c2 = c.copy()
      kill_assignments(c2);
      global_to_var(c2);

      globals.append(c2)
      transform_into_assignments(c, c.parent, c.parent.index(c))
      
      
  #to maintain backward compatibility, add everything in module to
  #global namespace (for now).
  
  if glob.g_autoglobalize:
    for n in node[:]:
      if type(n) in [ClassNode, FunctionNode, VarDeclNode]:
        if type(n) == VarDeclNode:
          nname = n.val
        else:
          nname = n.name
          
        n2 = js_parse("""
          $s = _es6_module.add_global('$s', $s);
        """, [nname, nname, nname]);
        n.parent.insert(n.parent.index(n)+1, n2)
      elif type(n) == VarDeclNode:
        varvisit(n, n);
    
  def visit(n):
    if not at_root(n):
      typespace.error("Import statements cannot be within functions or classes", n)
      
    modname = n[0].val
    
    depends.add(modname)
    
    if len(n) == 1: #import module name
      n.parent.replace(n, js_parse("""
        es6_import(_es6_module, '$s');
      """, [modname]));
    else:
      slist = StatementList()
      n.parent.replace(n, slist)
      
      for n2 in n[1:]:
        if n2.name == "*":
          n3 = js_parse("""
            var $s = es6_import(_es6_module, '$s');
          """, [n2.bindname, modname]);
          
          slist.add(n3);
        else:
          n3 = js_parse("""
          var $s = es6_import_item(_es6_module, '$s', '$s');
          """, [n2.bindname, modname, n2.name]);
          
          slist.add(n3)
  
  traverse(node, ImportNode, visit)
  flatten_statementlists(node, typespace)
  
  def class_visit(n):
    n2 = js_parse("""
      _es6_module.add_class($s);
    """, [n.name])
    n.parent.insert(n.parent.index(n)+1, n2);
    
  traverse(node, ClassNode, class_visit)
  flatten_statementlists(node, typespace)
  
  deps = "["
  for i, d in enumerate(depends):
    if i > 0: 
      deps += ", "
      
    deps += '"'+d+'"'
  deps += "]"
  
  fname = glob.g_file
  if "/" in fname or "\\" in fname:
    fname = os.path.split(fname)[1]
  fname = fname.strip().replace("/", "").replace("\\", "").replace(".js", "")
  
  safe_fname = "_" + fname.replace(" ", "_").replace(".", "_").replace("-", "_") + "_module";
  
  header = "es6_module_define('"+fname+"', "+deps+", function " + safe_fname + "(_es6_module) {"
  header += "});";
  
  #print(header)
  
  node2 = js_parse(header)
  
  func = node2[0][1][2]
  
  for n in node:
    func.add(n)
    
  node.children = []
  for g in globals:
    node.add(g)
    
  node.add(node2)
  
  
  