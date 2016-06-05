from js_ast import *
from js_process_ast import NodeVisit
import js_ast

def tab(n):
  s = ""
  for i in range(n):
    s += "  "
  return s

class ES6Formatter (NodeVisit):
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
  
  def traverse(self, node, scope={}, tlevel=0):
    self.out(node, node.c())
    NodeVisit.traverse(self, node, scope, tlevel)
    
  def out(self, node, str):
    node.s(str)
    self.buf += str
    self.col += len(str)
  
  def endst(self):
    return self.buf.endswith(";") #or self.buf.endswith("}")
  
  def PreDec(self, node, scope, t, tlevel):
    o = self.out
    
    o(node, "--")
    t(node[0], scope, tlevel)

  def WhileNode(self, node, scope, t, tlevel):
    o = self.out
    o(node, "while (")
    t(node[0], scope, tlevel)
    o(node, ")")
    
    o(node, " {\n")
    t(node[1])
    o(node, "}\n")
    
  def PostInc(self, node, scope, t, tlevel):
    o = self.out
    
    t(node[0], scope, tlevel)
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
      t(node[0], scope, tlevel)
      
    if len(node) > 2:
      for c in node.children[2:]:
        o(node, ",")
        t(c, scope, tlevel+1)

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
    
    t(node[0], scope, tlevel)
    o(node, " in ")
    t(node[1])

  def IfNode(self, node, scope, t, tlevel):
    o = self.out
    
    o(node, "if (")
    t(node[0], scope, tlevel)
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
    t(node[0], scope, tlevel)
    o(node, "}")
    
  def ForCNode(self, node, scope, t, tlevel):
    o = self.out
    
    t(node[0], scope, tlevel)
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
    t(node[0], scope, tlevel)
    o(node, "){")
    t(node[1])
    o(node, "}")

  def ThrowNode(self, node, scope, t, tlevel):
    o = self.out
    o(node, "throw ")
    t(node[0], scope, tlevel)

  def ForLoopNode(self, node, scope, t, tlevel):
    o = self.out
    
    o(node, "for (")
    t(node[0], scope, tlevel)
    o(node, ") {")
    t(node[1])
    o(node, "}")

  def TypeofNode(self, node, scope, t, tlevel):
    o = self.out
    o(node, "typeof ")
    t(node[0], scope, tlevel)

  def KeywordNew(self, node, scope, t, tlevel):
    o = self.out
    o(node, "new ")
    t(node[0], scope, tlevel)

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
    t(node[0], scope, tlevel)
    o(node, ")")

  def SwitchNode(self, node, scope, t, tlevel):
    o = self.out
    o(node, "switch(")
    t(node[0], scope, tlevel)
    o(node, "){")
    for c in node.children[1:]:
      t(c, scope, tlevel+1)
      if not self.endst():
        o(c, ";")
      o(node, "\n")
    o(node, "}")
  
  def BitInvNode(self, node, scope, t, tlevel):
    o = self.out
    
    o(node, "~")
    t(node[0], scope, tlevel)
    
  def AssignNode(self, node, scope, t, tlevel):
    o = self.out
    
    t(node[0], scope, tlevel)
    o(node, node.mode)
    t(node[1])

  def ReturnNode(self, node, scope, t, tlevel):
    o = self.out
    o(node, "return ")
    t(node[0], scope, tlevel)

  def ElseNode(self, node, scope, t, tlevel):
    o = self.out
    
    if type(node[0]) == IfNode:
      o(node, "else ")
      t(node[0], scope, tlevel)
    else:
      o(node, "else {")
      t(node[0], scope, tlevel)
      o(node, "}")

  def TryNode(self, node, scope, t, tlevel):
    o = self.out
    o(node, "try{")
    o(node, "\n")
    
    t(node[0], scope, tlevel)
    if not self.endst():
      o(node, ";")
    
    o(node, "\n")
    
    o(node, "}")
    
    for c in node.children[1:]:
      t(c, scope, tlevel+1)
      if not self.endst():
        o(c, ";")
      o(node, "\n")
  
  def FuncRefNode(self, noded, scope, t, tlevel):
    pass
    
  def StatementList(self, node, scope, t, tlevel):
    o = self.out
    
    excl = set([IfNode, ElseNode, TryNode, DoWhileNode, WhileNode, CatchNode, ForLoopNode, SwitchNode])
    
    for c in node.children:
      o(node, tab(tlevel))
      
      t(c, scope, tlevel+1);
      if type(c) not in excl and not self.endst(): #(not self.endst() or type(c) == AssignNode):
        o(node, ";")
      
      o(node, "\n")
      if self.col > self.max_col:
        self.col = 0
        o(node, "\n")
      
  def TemplateNode(self, node, scope, t, tlevel):
    o = self.out
    if len(node) > 0:
      t(node[0], scope, tlevel)
    
  def PreInc(self, node, scope, t, tlevel):
    o = self.out
    o(node, "++")
    t(node[0], scope, tlevel)

  def TrinaryCondNode(self, node, scope, t, tlevel):
    o = self.out
    
    t(node[0], scope, tlevel)
    o(node, " ? ")
    t(node[1])
    o(node, " : ")
    t(node[2])

  def LogicalNotNode(self, node, scope, t, tlevel):
    o = self.out
    o(node, "!")
    t(node[0], scope, tlevel)

  def PostDec(self, node, scope, t, tlevel):
    o = self.out
    
    t(node[0], scope, tlevel)
    o(node[0], "--")

  def NegateNode(self, node, scope, t, tlevel):
    o = self.out
    
    o(node, "-")
    t(node[0], scope, tlevel)

  def ExprListNode(self, node, scope, t, tlevel):
    o = self.out
    if node.add_parens:
      o(node, "(")
      
    for i, c in enumerate(node):
      if i > 0:
        o(node, ",")
      t(c, scope, tlevel+1)
      
    if node.add_parens:
      o(node, ")")

  def InitCallNode(self, node, scope, t, tlevel):
    self.FuncCallNode(node, scope, t, tlevel)

  def FunctionNode(self, node, scope, t, tlevel):
    o = self.out
    
    o(node, "function")
    if not node.is_anonymous:
      o(node, " " + node.name + "(")
    else:
      o(node, "(")
    
    for i, c in enumerate(node[0]):
      if i > 0:
        o(node, ",")
      t(c, scope, tlevel+1)
    o(node, ") {\n")
    
    excl = set([IfNode, ElseNode, TryNode, DoWhileNode, WhileNode, CatchNode, ForLoopNode, SwitchNode])
    
    for c in node.children[1:]:
      o(c, tab(tlevel))
      t(c, scope, tlevel+1)
      if type(c) not in excl and not self.endst():
        o(c, ";")
      o(node, "\n")
        
    o(node, "}")
    
  def DeleteNode(self, node, scope, t, tlevel):
    o = self.out
    
    o(node, "delete ")
    t(node[0], scope, tlevel)

  def ExprNode(self, node, scope, t, tlevel):
    self.ExprListNode(node, scope, t, tlevel)

  def RegExprNode(self, node, scope, t, tlevel):
    o = self.out
    o(node, node.val)

  def ArrayLitNode(self, node, scope, t, tlevel):
    o = self.out
    
    o(node, "[")
    t(node[0], scope, tlevel)
    o(node, "]")

  def FuncCallNode(self, node, scope, t, tlevel):
    o = self.out
    
    t(node[0], scope, tlevel)
    o(node, "(")
    if len(node) > 1:
      t(node[1])
    o(node, ")")

  def BinOpNode(self, node, scope, t, tlevel):
    o = self.out
    
    t(node[0], scope, tlevel)
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
    t(node[0], scope, tlevel)
    o(node, "): {")
    t(node[1])
    o(node, "}")

  def NullStatement(self, node, scope, t, tlevel):
    o = self.out
    
    p = node.parent
    if type(p) in [WhileNode, ForLoopNode, IfNode, ElseNode]:
      o(node, ";")
      o(node, "\n")

  def CatchNode(self, node, scope, t, tlevel):
    o = self.out
    
    o(node, "catch(")
    t(node[0], scope, tlevel)
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
      t(node[0], scope, tlevel)

  def ArrayRefNode(self, node, scope, t, tlevel):
    o = self.out
    
    t(node[0], scope, tlevel)
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
  
  def MethodNode(self, node, scope, t, tlevel):
    o = self.out
    
  def MethodGetter(self, node, scope, t, tlevel):
    o = self.out
    
  def MethodSetter(self, node, scope, t, tlevel):
    o = self.out
    
  def ClassNode(self, node, scope, t, tlevel):
    o = self.out
  
def format_es6(node, typespace):
  fmt = ES6Formatter(None)
  fmt.traverse(node, "")
  return fmt.buf