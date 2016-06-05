import sys, os.path, os, time, stat, struct, ctypes, io, subprocess, math, random, difflib
import ply, re

from js_lex import plexer
data1 = \
"""
Flags = {SELECT: 1, TEMP: 8}
MeshTypes = {VERT: 1, EDGE: 2, LOOP: 4, FACE: 8}

//$().array
function Arr() {
}

//#$().class
function Element() {
  this.type = 0;
  this.eid = 0;
  this.flag = 0;
  this.index = 0;
  
  this.__hash__ = Element.prototype.__hash__;
  this.toString = Element.prototype.toString;
}

//#$().String
Element.prototype.toString = function() {
  return "[eid: " + this.eid + ", type: " + this.type + "]";
}

//#$().String
Element.prototype.__hash__ = function() {
  return String(this.type + "|" + this.eid);
}

//#$(Vector3=optional).class
function Vector3(vec=[0,0,0]) {
  return [vec[0], vec[1], vec[2]];
}

//#$(Vector3, Vector3).class
function Vertex(co, no) {
  this.prototype = Object.create(Element.prototype);
  Element.call(this);
  
  this.type = MeshTypes.VERT;
  
  this.co = new Vector3(co);
  this.no = new Vector3(no);
  this.loop = null;
  this.edges = new GArray();
  
  //#$().MeshIterate
  Object.defineProperty(this, "faces", {get: function() {
    return new MeshIterate(MeshIter.VERT_FACES, this);
  }});
}
"""

data = \
"""
//#$().class
function Test() {
  this.a = 0;
  
  //#$().undefined
  this.func = function() {
    var d = this.a;
    d += 1;
  }
}

//#$().undefined
Test.prototype.b = function() {
  this.c = 0;
}

"""
###
#"""
f = open("mesh.js", "r")
data = f.read()
f.close()
"""

sys.stdout.write("1 ")
i = 2
for d in data:
  sys.stdout.write(d)
  if d == "\n":
    sys.stdout.write(str(i) + " ")
    i += 1
sys.stdout.write("end<--\n")

plexer.input(data)
while True:
  tok = plexer.token()
  if not tok: break
  print(tok.lineno, [tok.type, tok.value], tok.lexpos)
#"""

from js_ast import *
from js_parse import parser
plexer.lineno = 0
from js_typespace import *

class NoExtraArg:
  pass
  
def parse():
  result = parser.parse(data, lexer=plexer)
  
  #print(result)
  print("\n")
  
  def traverse(node, ntype, func, extra_arg=NoExtraArg, depth=0):
    for c in node.children:
      traverse(c, ntype, func, extra_arg, depth+1)
      
    if type(node) == ntype:
      if extra_arg == NoExtraArg:
        func(node, depth)
      else:
        func(node, depth, extra_arg)
      
  def build_name(node):
    if type(node) == IdentNode:
      return node.val
    elif type(node) == BinOpNode and node.op == ".":
      return build_name(node.children[0])+"."+build_name(node.children[1])
    else:
      return "unknown"

  lines = list(data.split("\n"))    
  typespace = JSTypeSpace()
  
  def find_functions(node, depth):
    if type(node.parent) == AssignNode:
        node.name = build_name(node.parent.children[0])
    
    #add function to global space if necassary
    if type(node.parent.parent) in [int, None]:
      typespace.globals[node.name] = node
    
    #parse type string
    typestr = lines[node.lineno-1].strip()
    typestr = typestr.replace("//", "").replace("/*", "").replace("*/", "").strip()
    if not re.search(r"\#\s?\$", typestr): 
      print("Function %s lacks type information" % node.name)
      return

    typestr = typestr.replace("#", "").strip()

    res = parser.parse(typestr)
    try:
      ret = res.children[0].children[1].val
    except:
      print("Could not get return type for function %s", node.name)
      ret = "undefined"
    
    try:
      types = tuple([x.val if type(x) != AssignNode else str(x.children[0].val) for x in res.children[0].children[0].children[1].children])
    except:
      print("Could not get parameter types for function %s", node.name)
      return
      
    print("%s %s%s"%(ret, node.name, str(types)))
    real_arglen = len(node.children[0].children)
    
    if real_arglen != len(types):
      print("Error: wrong number of function arguments")
      print("%d: %s %s%s"%(node.lineno, ret, node.name, types))

      #build member dict
    node.parameters = types
    node.ret = ret
    
    if func_is_class(node):
      typespace.types[node.name] = node
      node.members = {}
      
  def build_globals():
    for c in result.children:
      if type(c) == AssignNode:
        if type(c.children[0]) == IdentNode:
          globname = c.children[0].val
          gvtype = typespace.build_type(c.children[1], {}, None)
          typespace.globals[globname] = gvtype
        elif type(c.children[0]) == BinOpNode:
          node = typespace.lookup(c.children[0].children[0])
          if node != None:
            node.type = typespace.build_type(c.children[1], {}, None)
            if typespace.member_lookup(node, c.children[0].children[1]) == None:
              if node.type == None:
                typespace.member_add(node, c.children[0].children[1], UnkownTypeNode())
              else:
                typespace.member_add(node, c.children[0].children[1], node.type)
                if type(node) == ObjLitNode and node.is_prototype:
                  typespace.member_add(node.parent, c.children[0].children[1], node.type)
          
  def propegate_types(node, depth, report_unknowns=True):
    locals = {}
    globals = typespace.globals
    
    def trav(n, depth):
      varname = build_name(n.children[0])
      
      vtype = typespace.build_type(n.children[1], locals, node)
      
      if vtype == None:
        if report_unknowns:
          print("Unknown type for variable " + varname +", in function/class " + node.name)
        return
        
      if varname in locals or varname in node.members:
        #print("TODO: check that object member types don't change")
        return
        
      #member assignment
      #print("node:", node.name + ",", "is class:", func_is_class(node), node.ret)
      if func_is_class(node) and "this." in varname and varname.count(".") == 1:
          node.members[varname] = vtype
          if "this.prototype" not in node.members:
            node.members["this.prototype"] = ObjLitNode()
            node.add(node.members["this.prototype"])
          
          varname = varname.replace("this.", "")
          node.members["this.prototype"].add(AssignNode(IdentNode(varname), vtype))
          
          #make sure the prototype is marked as such
          node.members["this.prototype"].name = "prototype"
          node.members["this.prototype"].is_prototype = True
      elif "." not in varname and "[" not in varname and "(" not in varname and varname != "unknown":
          locals[varname] = vtype
        
    traverse(node, AssignNode, trav)
    
  traverse(result, FunctionNode, find_functions)

  traverse(result, FunctionNode, propegate_types, False)
  build_globals()
  traverse(result, FunctionNode, propegate_types, True)
  
parse()
