from js_global import glob
from js_typespace import *
from js_ast import *
from js_process_ast import *
from js_util_types import *
from js_cc import SourceMap
import js_ast;

add_n = False

class MinOutVisit (NodeVisit):
  def __init__(self, smap):
    NodeVisit.__init__(self);
    self.smap = smap;
    
    #self.max_col = 75;
    self.max_col = 2500000
    self.col = 0;
    self.required_nodes = s = set()
    
    for k in js_ast.__dict__:
      n = js_ast.__dict__[k]
      try:
        if not issubclass(getattr(js_ast, k), Node):
          continue;
      except TypeError:
        continue
      s.add(k)
    
    self.buf = ""
  
  def out(self, node, str):
    node.s(str)
    self.buf += str
    self.col += len(str)
  
  def endst(self):
    return self.buf.endswith(";") #or self.buf.endswith("}")
  
  def PreDec(self, node, scope, t, tlevel):
    o = self.out
    
    o(node, "--")
    t(node[0])

  def WhileNode(self, node, scope, t, tlevel):
    o = self.out
    o(node, "while (")
    t(node[0])
    o(node, ")")
    
    o(node, "{")
    t(node[1])
    o(node, "}")
    
  def PostInc(self, node, scope, t, tlevel):
    o = self.out
    
    t(node[0])
    o(node, "++")
    

  def VarDeclNode(self, node, scope, t, tlevel):
    if "global" in node.modifiers: return
    o = self.out
    
    if "local" in node.modifiers or node.local:
      if type(node.parent) != VarDeclNode:
        o(node, "var ")
      
    o(node, node.val)
    if len(node) > 0 and not (type(node[0]) == ExprNode and len(node[0])==0):
      o(node, "=")
      t(node[0])
      
    if len(node) > 2:
      for c in node.children[2:]:
        o(node, ",")
        t(c)

  def VarRefNode(self, node, scope, t, tlevel):
    o = self.out
    pass

  def BuiltinTypeNode(self, node, scope, t, tlevel):
    o = self.out
    pass

  def VoidTypeNode(self, node, scope, t, tlevel):
    o = self.out
    pass

  def UnknownTypeNode(self, node, scope, t, tlevel):
    o = self.out
    pass

  def StrLitNode(self, node, scope, t, tlevel):
    o = self.out
    o(node, node.val);

  def IdentNode(self, node, scope, t, tlevel):
    o = self.out
    o(node, node.val)
    
  def TypeRefNode(self, node, scope, t, tlevel):
    o = self.out

  def ForInNode(self, node, scope, t, tlevel):
    o = self.out
    
    t(node[0])
    o(node, " in ")
    t(node[1])

  def IfNode(self, node, scope, t, tlevel):
    o = self.out
    
    o(node, "if (")
    t(node[0])
    o(node, ")")
    
    if type(node.children[1]) != ObjLitNode:
      o(node, "{")
    
    t(node.children[1])
    
    if type(node.children[1]) != ObjLitNode:
      o(node, "}")
    
    if len(node) > 2:
      for n in node.children[2:]:
        t(n)
    
  def DefaultCaseNode(self, node, scope, t, tlevel):
    o = self.out
    
    o(node, " default:{")
    t(node[0])
    o(node, "}")
    
  def ForCNode(self, node, scope, t, tlevel):
    o = self.out
    
    t(node[0])
    o(node, ";")
    t(node[1])
    o(node, ";")
    t(node[2])

  def NumLitNode(self, node, scope, t, tlevel):
    o = self.out
    
    o(node, node.fmt())

  def WithNode(self, node, scope, t, tlevel):
    o = self.out
    o(node, "with(")
    t(node[0])
    o(node, "){")
    t(node[1])
    o(node, "}")

  def ThrowNode(self, node, scope, t, tlevel):
    o = self.out
    o(node, "throw ")
    t(node[0])

  def ForLoopNode(self, node, scope, t, tlevel):
    o = self.out
    
    o(node, "for (")
    t(node[0])
    o(node, ") {")
    t(node[1])
    o(node, "}")

  def TypeofNode(self, node, scope, t, tlevel):
    o = self.out
    o(node, "typeof ")
    t(node[0])

  def KeywordNew(self, node, scope, t, tlevel):
    o = self.out
    o(node, "new ")
    t(node[0])

  def ObjLitNode(self, node, scope, t, tlevel):
    o = self.out
    
    o(node, "{")
    for i, c in enumerate(node):
      if i > 0:
        o(node, ",")
      t(c[0]); o(node, ":"); t(c[1])
    o(node, "}")

  def DoWhileNode(self, node, scope, t, tlevel):
    o = self.out
    o(node, "do{")
    t(node[1])
    o(node, "}while(")
    t(node[0])
    o(node, ")")

  def SwitchNode(self, node, scope, t, tlevel):
    o = self.out
    o(node, "switch(")
    t(node[0])
    o(node, "){")
    for c in node.children[1:]:
      t(c)
      if not self.endst():
        o(c, ";")
      if add_n:
        o(node, "\n")
    o(node, "}")
  
  def BitInvNode(self, node, scope, t, tlevel):
    o = self.out
    
    o(node, "~")
    t(node[0])
    
  def AssignNode(self, node, scope, t, tlevel):
    o = self.out
    
    t(node[0])
    o(node, node.mode)
    t(node[1])

  def ReturnNode(self, node, scope, t, tlevel):
    o = self.out
    o(node, "return ")
    t(node[0])

  def ElseNode(self, node, scope, t, tlevel):
    o = self.out
    
    if type(node[0]) == IfNode:
      o(node, "else ")
      t(node[0])
    else:
      o(node, "else {")
      t(node[0])
      o(node, "}")

  def TryNode(self, node, scope, t, tlevel):
    o = self.out
    o(node, "try{")
    if add_n:
      o(node, "\n")
    
    t(node[0])
    if not self.endst():
      o(node, ";")
    
    if add_n:
      o(node, "\n")
    
    o(node, "}")
    
    for c in node.children[1:]:
      t(c)
      if not self.endst():
        o(c, ";")
      if add_n:
        o(node, "\n")
  
  def FuncRefNode(self, noded, scope, t, tlevel):
    pass
    
  def StatementList(self, node, scope, t, tlevel):
    o = self.out
    
    excl = set([IfNode, ElseNode, TryNode, DoWhileNode, WhileNode, CatchNode, ForLoopNode, SwitchNode])
    
    for c in node.children:
      t(c, scope, t);
      if type(c) not in excl and not self.endst(): #(not self.endst() or type(c) == AssignNode):
        o(node, ";")
      
      if add_n:
        o(node, "\n")
      if self.col > self.max_col:
        self.col = 0
        o(node, "\n")
      
  def TemplateNode(self, node, scope, t, tlevel):
    o = self.out
    if len(node) > 0:
      t(node[0])
    
  def PreInc(self, node, scope, t, tlevel):
    o = self.out
    o(node, "++")
    t(node[0])

  def TrinaryCondNode(self, node, scope, t, tlevel):
    o = self.out
    
    t(node[0])
    o(node, " ? ")
    t(node[1])
    o(node, " : ")
    t(node[2])

  def LogicalNotNode(self, node, scope, t, tlevel):
    o = self.out
    o(node, "!")
    t(node[0])

  def PostDec(self, node, scope, t, tlevel):
    o = self.out
    
    t(node[0])
    o(node[0], "--")

  def NegateNode(self, node, scope, t, tlevel):
    o = self.out
    
    o(node, "-")
    t(node[0])

  def ExprListNode(self, node, scope, t, tlevel):
    o = self.out
    if node.add_parens:
      o(node, "(")
      
    for i, c in enumerate(node):
      if i > 0:
        o(node, ",")
      t(c)
      
    if node.add_parens:
      o(node, ")")

  def InitCallNode(self, node, scope, t, tlevel):
    self.FuncCallNode(node, scope, t, tlevel)

  def FunctionNode(self, node, scope, t, tlevel):
    o = self.out
    
    o(node, "function")

    if node.name != "" and node.name != "(anonymous)":
      o(node, " " + node.name + "(")
    else:
      o(node, "(")
    
    for i, c in enumerate(node[0]):
      if i > 0:
        o(node, ",")
      t(c)
    o(node, "){")
    
    excl = set([IfNode, ElseNode, TryNode, DoWhileNode, WhileNode, CatchNode, ForLoopNode, SwitchNode])
    
    for c in node.children[1:]:
      t(c)
      if type(c) not in excl and not self.endst():
        o(c, ";")
      if add_n:
        o(node, "\n")
        
    o(node, "}")
    
  def DeleteNode(self, node, scope, t, tlevel):
    o = self.out
    
    o(node, "delete ")
    t(node[0])

  def ExprNode(self, node, scope, t, tlevel):
    self.ExprListNode(node, scope, t, tlevel)

  def RegExprNode(self, node, scope, t, tlevel):
    o = self.out
    o(node, node.val)

  def ArrayLitNode(self, node, scope, t, tlevel):
    o = self.out
    
    o(node, "[")
    t(node[0])
    o(node, "]")

  def FuncCallNode(self, node, scope, t, tlevel):
    o = self.out
    
    t(node[0])
    o(node, "(")
    if len(node) > 1:
      t(node[1])
    o(node, ")")

  def BinOpNode(self, node, scope, t, tlevel):
    o = self.out
    
    t(node[0])
    if node.op == "in":
      o(node, " in ")
    elif node.op == "instanceof":
      o(node, " instanceof ")
    else:
      o(node, node.op)
    
    t(node[1])
    
  def CaseNode(self, node, scope, t, tlevel):
    o = self.out
    
    o(node, "case(")
    t(node[0])
    o(node, "): {")
    t(node[1])
    o(node, "}")

  def NullStatement(self, node, scope, t, tlevel):
    o = self.out
    
    p = node.parent
    if type(p) in [WhileNode, ForLoopNode, IfNode, ElseNode]:
      o(node, ";")
      if add_n:
        o(node, "\n")

  def FinallyNode(self, node, scope, t, tlevel):
    o = self.out
    o(node, "finally{")
    t(node[0])
    o(node, "}")
    
  def CatchNode(self, node, scope, t, tlevel):
    o = self.out
    
    o(node, "catch(")
    t(node[0])
    o(node, "){")
    t(node[1])
    o(node, "}")
  
  def BreakNode(self, node, scope, t, tlevel):
    o = self.out
    o(node, "break")

  def YieldNode(self, node, scope, t, tlevel):
    o = self.out
    o(node, "yield")
    if len(node) > 0:
      o(node, " ")
      t(node[0])

  def ArrayRefNode(self, node, scope, t, tlevel):
    o = self.out
    
    t(node[0])
    o(node, "[")
    t(node[1])
    o(node, "]")

  def ContinueNode(self, node, scope, t, tlevel):
    o = self.out
    
    o(node, "continue")
  
  def TypeRefNode(self, node, scope, t, tlevel):
    o = self.out
    
    if type(node.type) == str:
      o(node, node.type)
    else:
      t(node.type)

from js_cc import js_parse
def js_minify(node):
  smap = SourceMap()
  def set_smap(node, smap):
    node.smap = smap
    for n in node:
      set_smap(n, smap)
    
  set_smap(node, smap)
  
  visit = MinOutVisit(smap);
  visit.traverse(node, {})
  
  #js_parse(visit.buf)
  
  return visit.buf, visit.smap
  
if __name__ == "__main__":
  result = js_parse("""
    function bleh(a, b) {
      c = 0;
      d = 2;
      return e;
    }
    
    var a = bleh() + 3;
    var r = /a/g;
    if (a == 0) {
      b = b==0 ? c : a;
    } else if (b == 2) {
      console.log(c);
    }
    
    var obj = {a: b, c: 2};
    var arr = [0, 2, 3, 4];
    
    switch (a) {
      case 2:
        break;
      default:
        break;
    }
    
    function GArray(input) {
      Array<T>.call(this);
      b = 0;
    }
  """)
  
  if __name__ == "__main__":
    print(result)
    buf = js_minify(result)
    print(buf);
    
